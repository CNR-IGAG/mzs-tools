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
from functools import partial
from pathlib import Path

from qgis.core import (
    Qgis,
    QgsApplication,
    QgsTask,
    QgsVectorLayerExporterTask,
)
from qgis.gui import QgsMessageBarItem
from qgis.PyQt import QtCore
from qgis.PyQt.QtCore import QCoreApplication
from qgis.PyQt.QtWidgets import QProgressBar, QPushButton
from qgis.utils import iface

from ..__about__ import __version__
from ..core.mzs_project_manager import MzSProjectManager
from ..plugin_utils.logging import MzSToolsLogger
from ..plugin_utils.qt_compat import get_alignment_flag
from .export_project_files_task import ExportProjectFilesTask
from .export_siti_lineari_task import ExportSitiLineariTask
from .export_siti_puntuali_task import ExportSitiPuntualiTask
from .standard_project import (
    STANDARD_SHAPEFILE_EXPORTS,
    create_standard_export_folder,
    postprocess_exported_shapefile,
)


class ExportDataTaskManager:
    """Manages the lifecycle of data export tasks (shapefiles, siti puntuali,
    siti lineari, project files), including logging setup, progress reporting
    and task sequencing.

    The dialog is responsible only for collecting user input and building the
    plain-data parameters; this class owns everything that happens after the
    user clicks "Start export".

    Parameters
    ----------
    output_path:
        Root output directory chosen by the user.
    indagini_output_format:
        One of ``"mdb"`` or ``"sqlite"``.
    standard_version_string:
        Short standard version label, e.g. ``"S42"``.
    cdi_tabelle_model_file:
        Filename of the CdI_Tabelle template to copy (relative to the plugin
        ``data/`` directory).
    debug_mode:
        When ``True``, sets the file logger to DEBUG level.
    """

    def __init__(
        self,
        output_path: Path,
        indagini_output_format: str,
        standard_version_string: str,
        cdi_tabelle_model_file: str,
        debug_mode: bool,
    ):
        self.iface = iface

        self.log = MzSToolsLogger.log

        self.prj_manager = MzSProjectManager.instance()

        self.output_path = output_path
        self.indagini_output_format = indagini_output_format
        self.standard_version_string = standard_version_string
        self.cdi_tabelle_model_file = cdi_tabelle_model_file
        self.debug_mode = debug_mode

        self.file_logger: logging.Logger = logging.getLogger("mzs_tools.tasks.export_data")
        if not self.file_logger.hasHandlers():
            handler = MzSToolsLogger()
            self.file_logger.addHandler(handler)

        self._tasks: list[QgsTask] = []
        self._task_failed: bool = False
        self._completed_count: int = 0

        self.progress_bar: QProgressBar | None = None
        self.log_file_path: Path | None = None
        self.file_handler: logging.FileHandler | None = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def start_export_tasks(self):
        """Prepare logging, build the export directory structure and submit
        tasks to the QGIS task manager."""
        if not self.prj_manager.project_path:
            self.log("No project is currently loaded!", log_level=2)
            return

        self._setup_logging()

        self.file_logger.info(f"Output directory: {self.output_path}")
        if not self.output_path.exists():
            self.output_path.mkdir(parents=True)

        comune_data = self.prj_manager.get_project_comune_data()
        exported_project_path = create_standard_export_folder(
            self.output_path,
            comune_data.cod_istat,
            comune_data.comune,
            self.indagini_output_format,
            self.standard_version_string,
            self.cdi_tabelle_model_file,
        )
        self.file_logger.info(f"Exported project path: {exported_project_path}")

        # Progress bar in the message bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximum(100)
        self.progress_bar.setAlignment(get_alignment_flag("AlignLeft", "AlignVCenter"))
        progress_msg: QgsMessageBarItem = self.iface.messageBar().createMessage(  # type: ignore[attr-defined]
            "MzS Tools", self.tr("Data export in progress...")
        )
        progress_msg.layout().addWidget(self.progress_bar)

        cancel_button = QPushButton(self.tr("Cancel"))
        cancel_button.clicked.connect(self.cancel_tasks)
        progress_msg.layout().addWidget(cancel_button)

        self.iface.messageBar().pushWidget(progress_msg, Qgis.MessageLevel.Info)  # type: ignore[attr-defined]

        # Global progress signal — used only for the visual progress bar
        QgsApplication.taskManager().progressChanged.connect(self._on_tasks_progress)

        for table_name, (shapefile_name, role) in STANDARD_SHAPEFILE_EXPORTS.items():
            layer_id = self.prj_manager.find_layer_by_table_name_role(table_name, role)
            if layer_id:
                layer = self.prj_manager.current_project.mapLayer(layer_id)
                path = exported_project_path / shapefile_name
                task = QgsVectorLayerExporterTask(
                    layer,  # type: ignore
                    str(path),
                    "ogr",
                    layer.crs(),
                    options={"driverName": "ESRI Shapefile"},
                )
                task.exportComplete.connect(partial(postprocess_exported_shapefile, table_name, path))
                task.errorOccurred.connect(self._on_shapefile_export_error)
                task.taskCompleted.connect(self._on_single_task_done)
                task.taskTerminated.connect(self._on_single_task_terminated)
                self._tasks.append(task)
                self.file_logger.info(f"Starting task to export {table_name} to {shapefile_name}")
                QgsApplication.taskManager().addTask(task)

        # export indagini puntuali data in mdb or sqlite
        export_siti_puntuali_task = ExportSitiPuntualiTask(exported_project_path, self.indagini_output_format)

        # export siti lineari as subtask of puntuali to avoid concurrent db writes
        export_siti_lineari_task = ExportSitiLineariTask(exported_project_path, self.indagini_output_format)
        export_siti_puntuali_task.addSubTask(
            export_siti_lineari_task, [], QgsTask.SubTaskDependency.ParentDependsOnSubTask
        )
        export_siti_puntuali_task.taskCompleted.connect(self._on_single_task_done)
        export_siti_puntuali_task.taskTerminated.connect(self._on_single_task_terminated)
        self._tasks.append(export_siti_puntuali_task)
        QgsApplication.taskManager().addTask(export_siti_puntuali_task)

        # export project files (attachments, plots, etc.)
        export_project_files_task = ExportProjectFilesTask(exported_project_path)
        export_project_files_task.taskCompleted.connect(self._on_single_task_done)
        export_project_files_task.taskTerminated.connect(self._on_single_task_terminated)
        self._tasks.append(export_project_files_task)
        QgsApplication.taskManager().addTask(export_project_files_task)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _setup_logging(self):
        """Set up file-based logging for the export tasks."""
        timestamp = QtCore.QDateTime.currentDateTime().toString("yyyy-MM-dd_hh-mm-ss")
        filename = f"data_export_{timestamp}.log"
        log_dir = self.prj_manager.project_path / "Allegati" / "log"  # type: ignore
        log_dir.mkdir(exist_ok=True, parents=True)

        self.log_file_path = log_dir / filename
        self.file_handler = logging.FileHandler(self.log_file_path, encoding="utf-8")
        formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
        self.file_handler.setFormatter(formatter)
        self.file_logger.addHandler(self.file_handler)

        self.file_logger.setLevel(logging.DEBUG if self.debug_mode else logging.INFO)

        self.file_logger.info(f"MzS Tools version {__version__} - Data export log")
        self.file_logger.info(f"Log file: {self.log_file_path}")
        self.file_logger.info("############### Data export started")

    def _on_tasks_progress(self, taskid, progress):
        with contextlib.suppress(Exception):
            self.progress_bar.setValue(int(progress))  # type: ignore[union-attr]

    def _on_single_task_done(self):
        """Called when one of our tracked tasks completes successfully."""
        self._completed_count += 1
        self._maybe_finalize()

    def _on_single_task_terminated(self):
        """Called when one of our tracked tasks fails or is cancelled."""
        self._task_failed = True
        self._completed_count += 1
        self._maybe_finalize()

    def _maybe_finalize(self):
        if self._completed_count >= len(self._tasks):
            self._on_all_tasks_done()

    def _on_all_tasks_done(self):
        if not self._task_failed:
            msg = self.tr("Data exported successfully")
            level = Qgis.MessageLevel.Success
        else:
            msg = self.tr("Data export completed with errors. Check the log for details.")
            level = Qgis.MessageLevel.Warning

        self.file_logger.info(f"{'#' * 15} {msg}")
        self.iface.messageBar().clearWidgets()  # type: ignore[attr-defined]
        log_text = self.log_file_path.read_text(encoding="utf-8") if self.log_file_path else ""
        self.iface.messageBar().pushMessage(  # type: ignore[attr-defined]
            "MzS Tools",
            msg,
            log_text or "...",
            level=level,
            duration=0,
        )

        self._disconnect_signals()
        self._cleanup_logger()

    def cancel_tasks(self):
        self.file_logger.warning(f"{'#' * 15} Data export cancelled. Terminating all tasks")
        self._disconnect_signals()
        QgsApplication.taskManager().cancelAll()

        self.iface.messageBar().clearWidgets()  # type: ignore[attr-defined]
        self.iface.messageBar().pushMessage(  # type: ignore[attr-defined]
            "MzS Tools", self.tr("Data export cancelled!"), level=Qgis.MessageLevel.Warning
        )
        self._cleanup_logger()

    def _disconnect_signals(self):
        """Safely disconnect from all tracked signals."""
        with contextlib.suppress(RuntimeError, TypeError):
            QgsApplication.taskManager().progressChanged.disconnect(self._on_tasks_progress)
        for task in self._tasks:
            with contextlib.suppress(RuntimeError, TypeError):
                task.taskCompleted.disconnect(self._on_single_task_done)
            with contextlib.suppress(RuntimeError, TypeError):
                task.taskTerminated.disconnect(self._on_single_task_terminated)

    def _cleanup_logger(self):
        """Remove and close the per-run file handler."""
        if self.file_handler:
            self.file_logger.removeHandler(self.file_handler)
            self.file_handler.close()
            self.file_handler = None

    def _on_shapefile_export_error(self, result, msg):
        self.file_logger.error(f"Error during export: {msg} - {result}")

    def tr(self, message: str) -> str:
        return QCoreApplication.translate(self.__class__.__name__, message)
