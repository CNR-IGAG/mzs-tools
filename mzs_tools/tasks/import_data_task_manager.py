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

from qgis.core import Qgis, QgsApplication, QgsTask
from qgis.gui import QgsMessageBarItem
from qgis.PyQt import QtCore
from qgis.PyQt.QtCore import QCoreApplication
from qgis.PyQt.QtWidgets import QProgressBar, QPushButton
from qgis.utils import iface

from ..__about__ import __version__
from ..core.mzs_project_manager import MzSProjectManager
from ..plugin_utils.logging import MzSToolsLogger
from ..plugin_utils.qt_compat import get_alignment_flag
from .import_shapefile_task import ImportShapefileTask
from .import_siti_lineari_task import ImportSitiLineariTask
from .import_siti_puntuali_task import ImportSitiPuntualiTask


class ImportDataTaskManager:
    """Manages the lifecycle of data import tasks (siti puntuali, siti lineari,
    shapefiles), including logging setup, progress reporting and task sequencing.

    The dialog is responsible only for collecting user input and building the
    plain-data parameters; this class owns everything that happens after the
    user clicks "Start import".

    Parameters
    ----------
    standard_proj_paths:
        Path information for each layer/file in the source project directory.
        Must be a *clean* copy with no Qt-widget references (i.e. the
        ``"checkbox"`` key must have been removed by the caller).
    input_path:
        Root directory of the source project being imported.
    indagini_data_source:
        One of ``"mdb"``, ``"sqlite"``, ``"csv"``, or ``None``.
    mdb_password:
        Optional password for the Access .mdb database.
    csv_files_found:
        Mapping of found CSV/TXT file paths as returned by the dialog's CSV
        validation logic.
    reset_sequences:
        Whether to reset the *indagini* auto-increment sequences before import.
    import_spu:
        Whether to run the *siti puntuali* import task.
    import_sln:
        Whether to run the *siti lineari* import task.
    selected_shapefiles:
        Names of shapefile entries (keys in *standard_proj_paths*) that the
        user selected for import.
    debug_mode:
        When ``True``, sets the file logger to DEBUG level.
    """

    def __init__(
        self,
        standard_proj_paths: dict,
        input_path: Path,
        indagini_data_source: str | None,
        mdb_password: str | None,
        csv_files_found: dict | None,
        reset_sequences: bool,
        import_spu: bool,
        import_sln: bool,
        selected_shapefiles: list[str],
        debug_mode: bool,
    ):
        self.iface = iface

        self.log = MzSToolsLogger.log

        self.prj_manager = MzSProjectManager.instance()

        self.standard_proj_paths = standard_proj_paths
        self.input_path = input_path
        self.indagini_data_source = indagini_data_source
        self.mdb_password = mdb_password
        self.csv_files_found = csv_files_found
        self.reset_sequences = reset_sequences
        self.import_spu = import_spu
        self.import_sln = import_sln
        self.selected_shapefiles = selected_shapefiles
        self.debug_mode = debug_mode

        self.file_logger: logging.Logger = logging.getLogger("mzs_tools.tasks.import_data")
        if not self.file_logger.hasHandlers():
            handler = MzSToolsLogger()
            self.file_logger.addHandler(handler)

        self.task_failed: bool = False
        self.progress_bar: QProgressBar | None = None
        self.log_file_path: Path | None = None
        self.file_handler: logging.FileHandler | None = None
        self._tasks: list[QgsTask] = []
        self._first_task: QgsTask | None = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def start_import_tasks(self):
        """Prepare logging, run pre-import steps and submit tasks to the
        QGIS task manager."""
        if not self.prj_manager.project_path:
            self.log("No project is currently loaded!", log_level=2)
            return

        # Ensure the standard Allegati sub-directories exist
        for sub_dir in ("Altro", "Documenti", "log", "Plot", "Spettri"):
            (self.prj_manager.project_path / "Allegati" / sub_dir).mkdir(parents=True, exist_ok=True)

        # File-based logging
        timestamp = QtCore.QDateTime.currentDateTime().toString("yyyy-MM-dd_hh-mm-ss")
        self.log_file_path = self.prj_manager.project_path / "Allegati" / "log" / f"data_import_{timestamp}.log"
        self.file_handler = logging.FileHandler(self.log_file_path, encoding="utf-8")
        formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
        self.file_handler.setFormatter(formatter)
        self.file_logger.addHandler(self.file_handler)
        self.file_logger.setLevel(logging.DEBUG if self.debug_mode else logging.INFO)
        self.file_logger.info(f"MzS Tools version {__version__} - Data import log")
        self.file_logger.info(f"Log file: {self.log_file_path}")
        self.file_logger.info("############### Data import started")

        # Pre-import steps
        backup_path = self.prj_manager.backup_database()
        self.file_logger.info(f"Database backup created at {backup_path}")

        if self.reset_sequences:
            self.file_logger.warning("Resetting Indagini sequences")
            self.prj_manager.reset_indagini_sequences()

        self.file_logger.info(
            f"Importing data from {self.input_path} using {self.indagini_data_source} for Indagini data"
        )

        # Build task list
        tasks: list[QgsTask] = []

        if self.import_spu:
            tasks.append(
                ImportSitiPuntualiTask(
                    self.standard_proj_paths,
                    data_source=self.indagini_data_source,  # type: ignore[arg-type]
                    mdb_password=self.mdb_password,
                    csv_files=self.csv_files_found,
                )
            )

        if self.import_sln:
            tasks.append(
                ImportSitiLineariTask(
                    self.standard_proj_paths,
                    data_source=self.indagini_data_source,  # type: ignore[arg-type]
                    mdb_password=self.mdb_password,
                    csv_files=self.csv_files_found,
                )
            )

        for shapefile_name in self.selected_shapefiles:
            tasks.append(ImportShapefileTask(self.standard_proj_paths, shapefile_name))

        if not tasks:
            self.file_logger.warning("No tasks selected for import!")
            self._cleanup_logger()
            return

        self.file_logger.info(f"Selected tasks: {[t.description() for t in tasks]}")

        # Progress bar in the message bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximum(100)
        self.progress_bar.setAlignment(get_alignment_flag("AlignLeft", "AlignVCenter"))
        progress_msg: QgsMessageBarItem = self.iface.messageBar().createMessage(  # type: ignore[attr-defined]
            "MzS Tools", self.tr("Data import in progress...")
        )
        progress_msg.layout().addWidget(self.progress_bar)

        cancel_button = QPushButton(self.tr("Cancel"))
        cancel_button.clicked.connect(self.cancel_tasks)
        progress_msg.layout().addWidget(cancel_button)

        self.iface.messageBar().pushWidget(progress_msg, Qgis.MessageLevel.Info)  # type: ignore[attr-defined]

        # Connect progress to the global signal (fires for all tasks, used for the bar only)
        QgsApplication.taskManager().progressChanged.connect(self._on_tasks_progress)

        # Submit tasks: single task goes directly; multiple tasks are chained
        # sequentially so that each one runs only after the previous completes.
        if len(tasks) == 1:
            first_task = tasks[0]
        else:
            first_task = previous_task = tasks[0]
            for task in tasks[1:]:
                previous_task.addSubTask(task, [], QgsTask.SubTaskDependency.ParentDependsOnSubTask)
                previous_task = task

        # Use per-task signals to avoid false positives from unrelated QGIS tasks.
        # taskTerminated fires only for OUR tasks that actually fail or are cancelled.
        self._tasks = tasks
        for task in tasks:
            task.taskTerminated.connect(self._on_any_task_terminated)

        # first_task runs last in the chain; its completion signals the end of the whole import.
        self._first_task = first_task
        first_task.taskCompleted.connect(self._on_tasks_completed)
        first_task.taskTerminated.connect(self._on_tasks_completed)

        QgsApplication.taskManager().addTask(first_task)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _on_tasks_progress(self, taskid, progress):
        with contextlib.suppress(Exception):
            self.progress_bar.setValue(int(progress))  # type: ignore[union-attr]

    def _on_any_task_terminated(self):
        """Called when *any* of our tasks is terminated (failed or cancelled)."""
        self.task_failed = True

    def _on_tasks_completed(self):
        if not self.task_failed:
            msg = self.tr("Data imported successfully")
            level = Qgis.MessageLevel.Success
        else:
            msg = self.tr("Data import completed with errors. Check the log for details.")
            level = Qgis.MessageLevel.Warning

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
        self.file_logger.warning(f"{'#' * 15} Data import cancelled. Terminating all tasks")
        self._disconnect_signals()
        QgsApplication.taskManager().cancelAll()

        self.iface.messageBar().clearWidgets()  # type: ignore[attr-defined]
        self.iface.messageBar().pushMessage(  # type: ignore[attr-defined]
            "MzS Tools", self.tr("Data import cancelled!"), level=Qgis.MessageLevel.Warning
        )
        self.iface.mapCanvas().refreshAllLayers()  # type: ignore[attr-defined]
        self._cleanup_logger()

    def _disconnect_signals(self):
        """Safely disconnect from the global progress signal and all per-task signals."""
        with contextlib.suppress(RuntimeError, TypeError):
            QgsApplication.taskManager().progressChanged.disconnect(self._on_tasks_progress)
        for task in self._tasks:
            with contextlib.suppress(RuntimeError, TypeError):
                task.taskTerminated.disconnect(self._on_any_task_terminated)
        if self._first_task:
            with contextlib.suppress(RuntimeError, TypeError):
                self._first_task.taskCompleted.disconnect(self._on_tasks_completed)
            with contextlib.suppress(RuntimeError, TypeError):
                self._first_task.taskTerminated.disconnect(self._on_tasks_completed)

    def _cleanup_logger(self):
        """Remove and close the per-run file handler."""
        if self.file_handler:
            self.file_logger.removeHandler(self.file_handler)
            self.file_handler.close()
            self.file_handler = None

    def tr(self, message: str) -> str:
        return QCoreApplication.translate(self.__class__.__name__, message)
