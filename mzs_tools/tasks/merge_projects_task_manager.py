# -----------------------------------------------------------------------------
# Copyright (C) 2018-2026, CNR-IGAG LabGIS <labgis@igag.cnr.it>
# This file is part of MzS Tools.
#
# MzS Tools is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# MzS Tools is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with MzS Tools.  If not, see <https://www.gnu.org/licenses/>.
# -----------------------------------------------------------------------------

import contextlib
import logging
from pathlib import Path

from qgis.core import Qgis, QgsApplication
from qgis.gui import QgsMessageBarItem
from qgis.PyQt import QtCore
from qgis.PyQt.QtCore import QCoreApplication
from qgis.PyQt.QtWidgets import QProgressBar, QPushButton
from qgis.utils import iface

from ..__about__ import __version__
from ..core.mzs_project_manager import MzSProjectManager
from ..plugin_utils.logging import MzSToolsLogger
from ..plugin_utils.qt_compat import get_alignment_flag
from .merge_projects_task import MergeProjectsTask, SourceProject


class MergeProjectsTaskManager:
    """Manages the lifecycle of the project merge task: logging setup, progress reporting and result messages.

    The current project must be the (empty) merged project created with
    ``MzSProjectManager.create_merged_project``.
    """

    def __init__(self, sources: list[SourceProject]):
        self.iface = iface

        self.log = MzSToolsLogger.log

        self.prj_manager = MzSProjectManager.instance()

        self.sources = sources

        self.file_logger: logging.Logger = logging.getLogger("mzs_tools.tasks.merge_projects")
        if not self.file_logger.hasHandlers():
            handler = MzSToolsLogger()
            self.file_logger.addHandler(handler)

        self.task_failed: bool = False
        self.progress_bar: QProgressBar | None = None
        self.log_file_path: Path | None = None
        self.file_handler: logging.FileHandler | None = None
        self._task: MergeProjectsTask | None = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def start_merge_tasks(self):
        """Prepare logging and submit the merge task to the QGIS task manager."""
        if not self.prj_manager.project_path:
            self.log("No project is currently loaded!", log_level=2)
            return

        # File-based logging
        log_dir = self.prj_manager.project_path / "Allegati" / "log"
        log_dir.mkdir(parents=True, exist_ok=True)
        timestamp = QtCore.QDateTime.currentDateTime().toString("yyyy-MM-dd_hh-mm-ss")
        self.log_file_path = log_dir / f"merge_projects_{timestamp}.log"
        self.file_handler = logging.FileHandler(self.log_file_path, encoding="utf-8")
        formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
        self.file_handler.setFormatter(formatter)
        self.file_logger.addHandler(self.file_handler)
        self.file_logger.setLevel(logging.INFO)
        self.file_logger.info(f"MzS Tools version {__version__} - Project merge log")
        self.file_logger.info(f"Log file: {self.log_file_path}")
        self.file_logger.info(f"Merged project: {self.prj_manager.project_path}")
        self.file_logger.info("Source projects:")
        for source in self.sources:
            self.file_logger.info(f"  {source.cod_istat} - {source.path}")
        self.file_logger.info("############### Project merge started")

        # Progress bar in the message bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximum(100)
        self.progress_bar.setAlignment(get_alignment_flag("AlignLeft", "AlignVCenter"))
        progress_msg: QgsMessageBarItem = self.iface.messageBar().createMessage(  # type: ignore[attr-defined]
            "MzS Tools", self.tr("Merging projects in progress...")
        )
        progress_msg.layout().addWidget(self.progress_bar)

        cancel_button = QPushButton(self.tr("Cancel"))
        cancel_button.clicked.connect(self.cancel_tasks)
        progress_msg.layout().addWidget(cancel_button)

        self.iface.messageBar().pushWidget(progress_msg, Qgis.MessageLevel.Info)  # type: ignore[attr-defined]

        task = MergeProjectsTask(self.sources)
        self._task = task
        task.progressChanged.connect(self._on_task_progress)
        task.taskTerminated.connect(self._on_task_terminated)
        task.taskCompleted.connect(self._on_task_completed)
        task.taskTerminated.connect(self._on_task_completed)

        QgsApplication.taskManager().addTask(task)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _on_task_progress(self, progress):
        with contextlib.suppress(Exception):
            self.progress_bar.setValue(int(progress))  # type: ignore[union-attr]

    def _on_task_terminated(self):
        """Called when the task fails or is cancelled."""
        self.task_failed = True

    def _on_task_completed(self):
        if not self.task_failed:
            msg = self.tr("Projects merged successfully")
            level = Qgis.MessageLevel.Success
        else:
            msg = self.tr(
                "Project merge failed: the merged project is incomplete. "
                "Check the log, delete the project folder and retry."
            )
            level = Qgis.MessageLevel.Critical

        self.file_logger.info(f"{'#' * 15} {msg}")
        self.iface.messageBar().clearWidgets()  # type: ignore[attr-defined]
        log_text = self.log_file_path.read_text(encoding="utf-8") if self.log_file_path else ""  # type: ignore[union-attr]
        self.iface.messageBar().pushMessage(  # type: ignore[attr-defined]
            "MzS Tools",
            msg,
            log_text or "...",
            level=level,
            duration=0,
        )

        self._disconnect_signals()
        self.iface.mapCanvas().refreshAllLayers()  # type: ignore[attr-defined]
        self._cleanup_logger()

    def cancel_tasks(self):
        self.file_logger.warning(f"{'#' * 15} Project merge cancelled. Terminating task")
        self._disconnect_signals()
        if self._task:
            with contextlib.suppress(RuntimeError):
                self._task.cancel()

        self.iface.messageBar().clearWidgets()  # type: ignore[attr-defined]
        self.iface.messageBar().pushMessage(  # type: ignore[attr-defined]
            "MzS Tools",
            self.tr("Project merge cancelled: the merged project is incomplete."),
            level=Qgis.MessageLevel.Warning,
            duration=0,
        )
        self.iface.mapCanvas().refreshAllLayers()  # type: ignore[attr-defined]
        self._cleanup_logger()

    def _disconnect_signals(self):
        """Safely disconnect all task signals."""
        if self._task:
            for signal, slot in (
                (self._task.progressChanged, self._on_task_progress),
                (self._task.taskTerminated, self._on_task_terminated),
                (self._task.taskCompleted, self._on_task_completed),
                (self._task.taskTerminated, self._on_task_completed),
            ):
                with contextlib.suppress(RuntimeError, TypeError):
                    signal.disconnect(slot)

    def _cleanup_logger(self):
        """Remove and close the per-run file handler."""
        if self.file_handler:
            self.file_logger.removeHandler(self.file_handler)
            self.file_handler.close()
            self.file_handler = None

    def tr(self, message: str) -> str:
        return QCoreApplication.translate(self.__class__.__name__, message)
