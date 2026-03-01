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
import shutil
from functools import partial
from pathlib import Path

from qgis.core import (
    Qgis,
    QgsApplication,
    QgsField,
    QgsTask,
    QgsVectorLayer,
    QgsVectorLayerExporterTask,
    edit,
)
from qgis.gui import QgsMessageBarItem
from qgis.PyQt import QtCore
from qgis.PyQt.QtCore import QCoreApplication, QMetaType
from qgis.PyQt.QtWidgets import QProgressBar, QPushButton
from qgis.utils import iface

from ..__about__ import DIR_PLUGIN_ROOT, __version__
from ..core.constants import STANDARD_SHAPEFILES_INT_FIELDS
from ..core.mzs_project_manager import MzSProjectManager
from ..plugin_utils.logging import MzSToolsLogger
from ..plugin_utils.qt_compat import get_alignment_flag
from .export_project_files_task import ExportProjectFilesTask
from .export_siti_lineari_task import ExportSitiLineariTask
from .export_siti_puntuali_task import ExportSitiPuntualiTask


class ExportDataTaskManager:
    """Manages the lifecycle of data export tasks (shapefiles, siti puntuali,
    siti lineari, project files), including logging setup, progress reporting,
    and task sequencing.

    Parameters
    ----------
    exported_project_path:
        Path to the output directory where the exported project will be created.
    indagini_output_format:
        One of ``"mdb"`` or ``"sqlite"``.
    standard_proj_paths:
        Path information for each layer/file in the source project. Not used in
        export but kept for API consistency with ImportDataTaskManager.
    debug_mode:
        When ``True``, sets the file logger to DEBUG level.
    """

    def __init__(
        self,
        exported_project_path: Path,
        indagini_output_format: str,
        standard_proj_paths: dict | None = None,
        debug_mode: bool = False,
    ):
        self.iface = iface

        self.log = MzSToolsLogger.log

        self.prj_manager = MzSProjectManager.instance()

        self.exported_project_path = exported_project_path
        self.indagini_output_format = indagini_output_format
        self.standard_proj_paths = standard_proj_paths or {}
        self.debug_mode = debug_mode

        self.file_logger: logging.Logger = logging.getLogger("mzs_tools.tasks.export_data")
        if not self.file_logger.hasHandlers():
            handler = MzSToolsLogger()
            self.file_logger.addHandler(handler)

        self.task_failed: bool = False
        self.progress_bar: QProgressBar | None = None
        self.log_file_path: Path | None = None
        self.file_handler: logging.FileHandler | None = None
        self._tasks: list[QgsTask] = []
        self.total_tasks: int = 0
        self.completed_tasks: int = 0
        self.failed_tasks: list[str] = []

    def start_export_tasks(self):
        """Prepare logging, create output structure, and submit tasks to the
        QGIS task manager."""
        if not self.prj_manager.project_path:
            self.log("No project is currently loaded!", log_level=2)
            return

        # Setup file-based logging
        timestamp = QtCore.QDateTime.currentDateTime().toString("yyyy-MM-dd_hh-mm-ss")
        filename = f"data_export_{timestamp}.log"
        log_dir = self.prj_manager.project_path / "Allegati" / "log"
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

        # Create output directory structure
        self.file_logger.info(f"Output directory: {self.exported_project_path}")

        ms_paths = [
            "BasiDati",
            "GeoTec",
            "Indagini",
            "Indagini/Documenti",
            "MS1",
            "MS23",
            "MS23/Spettri",
            "Plot",
            "Progetti",
            "Vestiture",
        ]

        for ms_path in ms_paths:
            ms_path = self.exported_project_path / ms_path
            ms_path.mkdir(parents=True, exist_ok=True)

        # Copy the db file to the output directory
        if self.indagini_output_format == "mdb":
            cdi_tabelle_path = DIR_PLUGIN_ROOT / "data" / "CdI_Tabelle_4.2.mdb"
            shutil.copy(cdi_tabelle_path, self.exported_project_path / "Indagini" / "CdI_Tabelle.mdb")
        elif self.indagini_output_format == "sqlite":
            cdi_tabelle_path = DIR_PLUGIN_ROOT / "data" / "CdI_Tabelle.sqlite"
            shutil.copy(cdi_tabelle_path, self.exported_project_path / "Indagini" / "CdI_Tabelle.sqlite")

        # Setup progress UI
        self._setup_progress_ui()

        # Connect task manager signals
        QgsApplication.taskManager().progressChanged.connect(self._on_tasks_progress)
        QgsApplication.taskManager().statusChanged.connect(self._on_task_status_changed)
        QgsApplication.taskManager().allTasksFinished.connect(self._on_tasks_completed)

        # Build and submit tasks
        self._create_and_submit_tasks()

        self.total_tasks = QgsApplication.taskManager().count()

    def _setup_progress_ui(self):
        """Create progress bar and cancel button in message bar."""
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximum(100)
        self.progress_bar.setAlignment(get_alignment_flag("AlignLeft", "AlignVCenter"))
        self.progress_msg: QgsMessageBarItem = self.iface.messageBar().createMessage(  # type: ignore
            "MzS Tools", self.tr("Data export in progress...")
        )
        self.progress_msg.layout().addWidget(self.progress_bar)

        cancel_button = QPushButton()
        cancel_button.setText(self.tr("Cancel"))
        cancel_button.clicked.connect(self.cancel_tasks)
        self.progress_msg.layout().addWidget(cancel_button)

        self.iface.messageBar().pushWidget(self.progress_msg, Qgis.MessageLevel.Info)  # type: ignore

    def _create_and_submit_tasks(self):
        """Create and submit all export tasks."""
        # table - shapefile mapping
        shapefile_mapping = {
            "comuni": ("BasiDati/comuni_istat.shp", "base"),
            "comune_progetto": ("BasiDati/comune_progetto.shp", "base"),
            "elineari": ("GeoTec/Elineari.shp", "editing"),
            "epuntuali": ("GeoTec/Epuntuali.shp", "editing"),
            "forme": ("GeoTec/Forme.shp", "editing"),
            "geoidr": ("GeoTec/Geoidr.shp", "editing"),
            "geotec": ("GeoTec/Geotec.shp", "editing"),
            "instab_geotec": ("GeoTec/Instab_geotec.shp", "editing"),
            "sito_puntuale": ("Indagini/Ind_pu.shp", "editing"),
            "sito_lineare": ("Indagini/Ind_ln.shp", "editing"),
            "instab_l1": ("MS1/Instab.shp", "editing"),
            "isosub_l1": ("MS1/Isosub.shp", "editing"),
            "stab_l1": ("MS1/Stab.shp", "editing"),
            "instab_l23": ("MS23/Instab.shp", "editing"),
            "isosub_l23": ("MS23/Isosub.shp", "editing"),
            "stab_l23": ("MS23/Stab.shp", "editing"),
        }

        # Create tasks to export shapefiles
        for table_name, (shapefile_name, role) in shapefile_mapping.items():
            layer_id = self.prj_manager.find_layer_by_table_name_role(table_name, role)
            if layer_id:
                layer = self.prj_manager.current_project.mapLayer(layer_id)
                path = self.exported_project_path / shapefile_name
                task = QgsVectorLayerExporterTask(
                    layer,  # type: ignore
                    str(path),
                    "ogr",
                    layer.crs(),
                    options={"driverName": "ESRI Shapefile"},
                )

                task.exportComplete.connect(partial(self._on_shapefile_export_complete, table_name, path))
                task.errorOccurred.connect(self._on_shapefile_export_error)

                self.file_logger.info(f"Starting task to export {table_name} to {shapefile_name}")
                QgsApplication.taskManager().addTask(task)
                self._tasks.append(task)

        # Export indagini puntuali data in mdb or sqlite
        export_spu_task = ExportSitiPuntualiTask(self.exported_project_path, self.indagini_output_format)

        # Export indagini lineari data in mdb or sqlite
        # Add as subtask to avoid concurrent db writes
        export_sln_task = ExportSitiLineariTask(self.exported_project_path, self.indagini_output_format)
        export_spu_task.addSubTask(export_sln_task, [], QgsTask.SubTaskDependency.ParentDependsOnSubTask)
        QgsApplication.taskManager().addTask(export_spu_task)
        self._tasks.append(export_spu_task)

        # Export project files (attachments, plots, etc.)
        export_files_task = ExportProjectFilesTask(self.exported_project_path)
        QgsApplication.taskManager().addTask(export_files_task)
        self._tasks.append(export_files_task)

    def _on_shapefile_export_complete(self, table_name: str, path: Path):
        """Handle successful shapefile export."""
        self.file_logger.info(f"Exported {table_name} to {path}")

        # Load the exported layer and fix field types
        try:
            layer = QgsVectorLayer(str(path), str(path.stem), "ogr")

            # Fix integer fields
            for layer_name, fields in STANDARD_SHAPEFILES_INT_FIELDS.items():
                if table_name == layer_name:
                    for field_name in fields:
                        self._change_field_type(layer, field_name, QMetaType.Type.Int)
                    break

            # Fix specific datasets
            if table_name == "sito_puntuale":
                self._rename_field(layer, "id_spu", "ID_SPU")
            elif table_name == "sito_lineare":
                self._rename_field(layer, "id_sln", "ID_SLN")
            elif table_name in ["stab_l1", "stab_l23", "instab_l1", "instab_l23"]:
                self._change_field_type(layer, "LIVELLO", QMetaType.Type.Double)
                if table_name in ["stab_l23", "instab_l23"]:
                    self._extract_file_name_from_path(layer, "SPETTRI")

        except Exception as e:
            self.file_logger.error(f"Error post-processing {table_name}: {e}")

    def _on_shapefile_export_error(self, result, msg: str):
        """Handle shapefile export error."""
        self.file_logger.error(f"Error during export: {msg} - {result}")

    def _on_tasks_progress(self, taskid, progress):
        """Update progress bar based on task manager progress."""
        with contextlib.suppress(Exception):
            remaining_tasks = QgsApplication.taskManager().count()
            completed_tasks = self.total_tasks - remaining_tasks
            if self.completed_tasks == completed_tasks:
                return
            self.completed_tasks = completed_tasks
            progress_percentage = (completed_tasks / self.total_tasks) * 100
            self.progress_bar.setValue(int(progress_percentage))

    def _on_task_status_changed(self, taskid, status):
        """Track failed tasks."""
        if status == QgsTask.TaskStatus.Terminated:
            task = QgsApplication.taskManager().task(taskid)
            if task is not None:
                self.failed_tasks.append(task.description())

    def _on_tasks_completed(self):
        """Handle task completion."""
        if QgsApplication.taskManager().countActiveTasks() > 0:
            return

        if len(self.failed_tasks) == 0:
            msg = self.tr("Data exported successfully")
            level = Qgis.MessageLevel.Success
        else:
            msg = self.tr("Data export completed with errors. Check the log for details.")
            level = Qgis.MessageLevel.Warning

        self.file_logger.info(f"{'#' * 15} {msg}")

        self.iface.messageBar().clearWidgets()  # type: ignore
        log_text = self.log_file_path.read_text(encoding="utf-8") if self.log_file_path else ""
        self.iface.messageBar().pushMessage(  # type: ignore
            "MzS Tools",
            msg,
            log_text if log_text else "...",
            level=level,
            duration=0,
        )

        self._disconnect_signals()
        self._cleanup_logger()

    def cancel_tasks(self):
        """Cancel all export tasks."""
        self.file_logger.warning(f"{'#' * 15} Data export cancelled. Terminating all tasks")

        self._disconnect_signals()

        QgsApplication.taskManager().cancelAll()

        self.iface.messageBar().clearWidgets()  # type: ignore
        self.iface.messageBar().pushMessage(  # type: ignore
            "MzS Tools", self.tr("Data export cancelled!"), level=Qgis.MessageLevel.Warning
        )

        self._cleanup_logger()

    def _disconnect_signals(self):
        """Safely disconnect all task manager signals."""
        with contextlib.suppress(RuntimeError):
            QgsApplication.taskManager().progressChanged.disconnect(self._on_tasks_progress)
        with contextlib.suppress(RuntimeError):
            QgsApplication.taskManager().statusChanged.disconnect(self._on_task_status_changed)
        with contextlib.suppress(RuntimeError):
            QgsApplication.taskManager().allTasksFinished.disconnect(self._on_tasks_completed)

    def _cleanup_logger(self):
        """Remove and close the per-run file handler."""
        if self.file_handler:
            self.file_logger.removeHandler(self.file_handler)
            self.file_handler.close()
            self.file_handler = None

    def _rename_field(self, layer, field_name: str, new_name: str):
        """Rename a field in a vector layer."""
        for field in layer.fields():
            if field.name() == field_name:
                self.file_logger.debug(f"Renaming {field.name()} to {new_name}")
                with edit(layer):
                    layer.renameAttribute(layer.fields().lookupField(field_name), new_name)
                break

    def _change_field_type(self, layer, field_name: str, field_type):
        """Change the data type of a field in a vector layer."""
        self.file_logger.debug(f"Changing field type for field '{field_name}'")

        field_idx = layer.fields().lookupField(field_name)
        if field_idx == -1:
            self.file_logger.error(f"Field '{field_name}' not found in layer")
            return

        temp_field_name = "temp"

        temp_field = QgsField()
        temp_field.setName(temp_field_name)
        temp_field.setType(field_type)

        new_field = QgsField()
        new_field.setName(field_name)
        new_field.setType(field_type)

        with edit(layer):
            layer.addAttribute(temp_field)
            layer.updateFields()

            temp_field_idx = layer.fields().lookupField(temp_field_name)

            for feature in layer.getFeatures():
                layer.changeAttributeValue(feature.id(), temp_field_idx, feature[field_name])

        with edit(layer):
            layer.deleteAttribute(field_idx)
            layer.updateFields()

            layer.addAttribute(new_field)
            layer.updateFields()

            new_field_idx = layer.fields().lookupField(field_name)
            temp_field_idx = layer.fields().lookupField(temp_field_name)

            for feature in layer.getFeatures():
                layer.changeAttributeValue(feature.id(), new_field_idx, feature[temp_field_name])

            layer.deleteAttribute(temp_field_idx)

        self.file_logger.debug(f"Successfully changed field type for '{field_name}'")

    def _extract_file_name_from_path(self, layer, field_name: str):
        """Extract file names from path strings in a field."""
        self.file_logger.debug(f"Extracting file name from field '{field_name}'")

        field_idx = layer.fields().lookupField(field_name)
        if field_idx == -1:
            self.file_logger.error(f"Field '{field_name}' not found in layer")
            return

        layer.startEditing()

        features_updated = 0
        for feature in layer.getFeatures():
            path_value = feature[field_name]

            if not path_value:
                continue

            try:
                file_name = Path(path_value).name
                feature.setAttribute(field_idx, file_name)
                layer.updateFeature(feature)
                features_updated += 1
            except Exception as e:
                self.file_logger.error(f"Error extracting filename from '{path_value}': {e}")

        success = layer.commitChanges()

        if success:
            self.file_logger.info(f"Successfully updated {features_updated} features in field '{field_name}'")
        else:
            self.file_logger.error(f"Failed to commit changes to layer: {layer.commitErrors()}")
            layer.rollBack()

    def tr(self, message: str) -> str:
        return QCoreApplication.translate(self.__class__.__name__, message)
