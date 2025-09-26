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
from qgis.PyQt import QtCore, uic
from qgis.PyQt.QtCore import QCoreApplication, QUrl, QVariant
from qgis.PyQt.QtGui import QDesktopServices
from qgis.PyQt.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QProgressBar,
    QPushButton,
)
from qgis.utils import iface

from ..__about__ import DIR_PLUGIN_ROOT, __version__
from ..core.mzs_project_manager import MzSProjectManager
from ..plugin_utils.logging import MzSToolsLogger
from ..plugin_utils.qt_compat import get_alignment_flag
from ..tasks.access_db_connection import AccessDbConnection, JVMError
from ..tasks.export_project_files_task import ExportProjectFilesTask
from ..tasks.export_siti_lineari_task import ExportSitiLineariTask
from ..tasks.export_siti_puntuali_task import ExportSitiPuntualiTask

FORM_CLASS, _ = uic.loadUiType(Path(__file__).parent / f"{Path(__file__).stem}.ui")


class DlgExportData(QDialog, FORM_CLASS):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setupUi(self)
        self.iface = iface

        self.log = MzSToolsLogger.log

        # setup proper python logger to be used in tasks with file-based logging
        self.file_logger: logging.Logger = logging.getLogger("mzs_tools.tasks.export_data")
        if not self.file_logger.hasHandlers():
            handler = MzSToolsLogger()
            self.file_logger.addHandler(handler)

        self.prj_manager = MzSProjectManager.instance()

        self.help_button = self.button_box.button(QDialogButtonBox.StandardButton.Help)
        self.cancel_button = self.button_box.button(QDialogButtonBox.StandardButton.Cancel)
        self.ok_button = self.button_box.button(QDialogButtonBox.StandardButton.Ok)

        self.ok_button.setText(self.tr("Start export"))
        self.ok_button.setEnabled(False)
        self.radio_button_mdb.setEnabled(False)
        self.radio_button_sqlite.setEnabled(True)

        self.output_dir_widget.lineEdit().textChanged.connect(self.validate_input)
        self.radio_button_mdb.toggled.connect(self.validate_input)
        self.radio_button_sqlite.toggled.connect(self.validate_input)

        self.label_mdb_msg.setText("")
        self.label_mdb_msg.setVisible(True)

        self.help_button.pressed.connect(
            partial(QDesktopServices.openUrl, QUrl("https://cnr-igag.github.io/mzs-tools/plugin/esportazione.html"))
        )

        self.output_path = None
        self.standard_proj_paths = None

        self.accepted.connect(self.start_export_tasks)

        self.indagini_output_format = None

        self.mdb_checked = False

        self.total_tasks = 0
        self.completed_tasks = 0
        self.failed_tasks = []

    def showEvent(self, e):
        super().showEvent(e)
        self.output_dir_widget.lineEdit().setText("")

        if not self.mdb_checked:
            # test mdb connection
            cdi_tabelle_path = DIR_PLUGIN_ROOT / "data" / "CdI_Tabelle_4.2.mdb"
            connected = self.check_mdb_connection(cdi_tabelle_path)
            if connected:
                self.radio_button_mdb.setEnabled(True)
                self.mdb_checked = True

    def validate_input(self):
        """Validate user input and enable/disable the OK button accordingly."""
        # Check output directory
        if not self.validate_output_dir():
            self.log("Output path is not valid", log_level=1)
            self.ok_button.setEnabled(False)
            return False

        # Check if a data source is selected
        if not (self.radio_button_mdb.isChecked() or self.radio_button_sqlite.isChecked()):
            self.log("No data source selected", log_level=1)
            self.ok_button.setEnabled(False)
            return False

        # All validations passed
        self.ok_button.setEnabled(True)
        return True

    def validate_output_dir(self):
        """Validate that the output directory exists."""
        output_dir = self.output_dir_widget.lineEdit().text()

        is_valid = output_dir and Path(output_dir).exists()
        if is_valid:
            self.output_path = Path(output_dir)

        return is_valid

    def check_mdb_connection(self, mdb_path):
        """Test connection to an Access database."""
        connected = False
        mdb_conn = None

        try:
            mdb_conn = AccessDbConnection(mdb_path)
            connected = mdb_conn.open()
            if connected:
                self.label_mdb_msg.setText(self.tr("[Connection established]"))
                self.radio_button_mdb.setToolTip("")

        except ImportError as e:
            error_msg = f"{e}. Use 'qpip' QGIS plugin to install dependencies."
            self.log(error_msg, log_level=2)
            self.label_mdb_msg.setText(f"[{e}]")
            self.radio_button_mdb.setToolTip(
                self.tr("Use 'qpip' QGIS plugin to install dependencies and restart QGIS")
            )
        except JVMError as e:
            self.log(f"{e}", log_level=2)
            self.label_mdb_msg.setText(f"[{e} - check your Java JVM installation]")
        except Exception as e:
            self.log(f"{e}", log_level=2)
            self.label_mdb_msg.setText(self.tr("[Connection failed]"))
        finally:
            if mdb_conn and connected:
                mdb_conn.close()

        return connected

    def setup_logging(self):
        """Setup file-based logging for the export tasks."""
        timestamp = QtCore.QDateTime.currentDateTime().toString("yyyy-MM-dd_hh-mm-ss")
        filename = f"data_export_{timestamp}.log"
        log_dir = self.prj_manager.project_path / "Allegati" / "log"
        log_dir.mkdir(exist_ok=True, parents=True)  # Ensure log directory exists

        self.log_file_path = log_dir / filename
        self.file_handler = logging.FileHandler(self.log_file_path, encoding="utf-8")
        self.file_logger.addHandler(self.file_handler)

        formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
        self.file_handler.setFormatter(formatter)

        debug_mode = self.chk_debug_logging.isChecked()
        self.file_logger.setLevel(logging.DEBUG if debug_mode else logging.INFO)

        self.file_logger.info(f"MzS Tools version {__version__} - Data export log")
        self.file_logger.info(f"Log file: {self.log_file_path}")
        self.file_logger.info("############### Data export started")

    def start_export_tasks(self):
        # Setup file-based logging
        self.setup_logging()

        # Determine output format
        if self.radio_button_mdb.isChecked():
            self.indagini_output_format = "mdb"
        elif self.radio_button_sqlite.isChecked():
            self.indagini_output_format = "sqlite"
        else:
            self.log("No output format selected", log_level=1)
            return

        # Create output directory if it doesn't exist
        self.file_logger.info(f"Output directory: {self.output_path}")
        if not self.output_path.exists():
            self.output_path.mkdir(parents=True)

        # get current project comune
        current_project = self.prj_manager.get_project_comune_data()
        comune_name = self.prj_manager.sanitize_comune_name(current_project.comune)
        exported_project_path = self.output_path / f"{comune_name}_S42_Shapefile"

        if exported_project_path.exists():
            timestamp = QtCore.QDateTime.currentDateTime().toString("yyyy-MM-dd_hh-mm-ss")
            exported_project_path = self.output_path / f"{comune_name}_S42_Shapefile_{timestamp}"

        exported_project_path.mkdir(parents=True, exist_ok=False)
        self.file_logger.info(f"Exported project path: {exported_project_path}")

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
            ms_path = exported_project_path / ms_path
            ms_path.mkdir(parents=True)

        # copy the db file to the output directory
        if self.indagini_output_format == "mdb":
            cdi_tabelle_path = DIR_PLUGIN_ROOT / "data" / "CdI_Tabelle_4.2.mdb"
            shutil.copy(cdi_tabelle_path, exported_project_path / "Indagini" / "CdI_Tabelle.mdb")
        elif self.indagini_output_format == "sqlite":
            cdi_tabelle_path = DIR_PLUGIN_ROOT / "data" / "CdI_Tabelle.sqlite"
            shutil.copy(cdi_tabelle_path, exported_project_path / "Indagini" / "CdI_Tabelle.sqlite")

        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximum(100)
        self.progress_bar.setAlignment(get_alignment_flag("AlignLeft", "AlignVCenter"))
        self.progress_msg: QgsMessageBarItem = self.iface.messageBar().createMessage(
            "MzS Tools", self.tr("Data export in progress...")
        )
        self.progress_msg.layout().addWidget(self.progress_bar)

        cancel_button = QPushButton()
        cancel_button.setText("Cancel")
        cancel_button.clicked.connect(self.cancel_tasks)
        self.progress_msg.layout().addWidget(cancel_button)

        self.iface.messageBar().pushWidget(self.progress_msg, Qgis.MessageLevel.Info)

        QgsApplication.taskManager().progressChanged.connect(self.on_tasks_progress)
        QgsApplication.taskManager().statusChanged.connect(self.on_task_status_changed)
        QgsApplication.taskManager().allTasksFinished.connect(self.on_tasks_completed)

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

        # create tasks to export shapefiles
        for table_name, (shapefile_name, role) in shapefile_mapping.items():
            layer_id = self.prj_manager.find_layer_by_table_name_role(table_name, role)
            if layer_id:
                layer = self.prj_manager.current_project.mapLayer(layer_id)
                path = exported_project_path / shapefile_name
                task = QgsVectorLayerExporterTask(
                    layer,
                    str(path),
                    "ogr",
                    layer.crs(),
                    options={"driverName": "ESRI Shapefile"},
                )
                task.exportComplete.connect(partial(self.on_shapefile_export_complete, table_name, path))
                task.errorOccurred.connect(self.on_shapefile_export_error)

                self.file_logger.info(f"Starting task to export {table_name} to {shapefile_name}")
                QgsApplication.taskManager().addTask(task)

        # export indagini puntuali data in mdb or sqlite
        self.export_siti_puntuali_task = ExportSitiPuntualiTask(exported_project_path, self.indagini_output_format)

        # export indagini lineari data in mdb or sqlite
        # adding this as a subtask of indagini puntuali task to avoid concurrent db writes
        self.export_siti_lineari_task = ExportSitiLineariTask(exported_project_path, self.indagini_output_format)
        # QgsApplication.taskManager().addTask(self.export_siti_lineari_task)
        self.export_siti_puntuali_task.addSubTask(
            self.export_siti_lineari_task, [], QgsTask.SubTaskDependency.ParentDependsOnSubTask
        )
        QgsApplication.taskManager().addTask(self.export_siti_puntuali_task)

        # export project files (attachments, plots, etc.)
        self.export_project_files_task = ExportProjectFilesTask(exported_project_path)
        QgsApplication.taskManager().addTask(self.export_project_files_task)

        self.total_tasks = QgsApplication.taskManager().count()

    def on_shapefile_export_complete(self, table_name, path: Path):
        self.file_logger.info(f"Exported {table_name} to {path}")

        # modify specific datasets
        if table_name == "sito_puntuale":
            self.rename_field(QgsVectorLayer(str(path), str(path.stem), "ogr"), "id_spu", "ID_SPU")
        elif table_name == "sito_lineare":
            self.rename_field(QgsVectorLayer(str(path), str(path.stem), "ogr"), "id_sln", "ID_SLN")
        elif table_name in ["isosub_l1", "isosub_l23"]:
            # "Quota" from float to int
            self.change_field_type(QgsVectorLayer(str(path), str(path.stem), "ogr"), "Quota", QVariant.Int)
        elif table_name in ["stab_l1", "stab_l23", "instab_l1", "instab_l23"]:
            # for some absurd reason, the field "LIVELLO" must be a float
            self.change_field_type(QgsVectorLayer(str(path), str(path.stem), "ogr"), "LIVELLO", QVariant.Double)
            if table_name in ["stab_l23", "instab_l23"]:
                # extract file name from path "SPETTRI"
                self.extract_file_name_from_path(QgsVectorLayer(str(path), str(path.stem), "ogr"), "SPETTRI")

    def on_shapefile_export_error(self, result, msg):
        self.file_logger.error(f"Error during export: {msg} - {result}")

    def on_tasks_progress(self, taskid, progress):
        # self.progress_bar.setValue(int(progress))
        remaining_tasks = QgsApplication.taskManager().count()
        completed_tasks = self.total_tasks - remaining_tasks
        if self.completed_tasks == completed_tasks:
            return
        self.completed_tasks = completed_tasks
        progress_percentage = (completed_tasks / self.total_tasks) * 100
        self.progress_bar.setValue(int(progress_percentage))

    def on_task_status_changed(self, taskid, status):
        if status == QgsTask.TaskStatus.Terminated:
            self.failed_tasks.append(QgsApplication.taskManager().task(taskid).description())

    def on_tasks_completed(self):
        if QgsApplication.taskManager().countActiveTasks() > 0:
            return

        if len(self.failed_tasks) == 0:
            msg = self.tr("Data exported successfully")
            level = Qgis.MessageLevel.Success
        else:
            msg = self.tr("Data export completed with errors. Check the log for details.")
            level = Qgis.MessageLevel.Warning

        self.file_logger.info(f"{'#' * 15} {msg}")
        self.iface.messageBar().clearWidgets()
        # load log file
        log_text = self.log_file_path.read_text(encoding="utf-8")
        self.iface.messageBar().pushMessage(
            "MzS Tools",
            msg,
            log_text if log_text else "...",
            level=level,
            duration=0,
        )

        QgsApplication.taskManager().progressChanged.disconnect(self.on_tasks_progress)
        QgsApplication.taskManager().statusChanged.disconnect(self.on_task_status_changed)
        QgsApplication.taskManager().allTasksFinished.disconnect(self.on_tasks_completed)

        self.file_logger.removeHandler(self.file_handler)

    def cancel_tasks(self):
        self.file_logger.warning(f"{'#' * 15} Data export cancelled. Terminating all tasks")
        QgsApplication.taskManager().progressChanged.disconnect(self.on_tasks_progress)
        QgsApplication.taskManager().statusChanged.disconnect(self.on_task_status_changed)
        QgsApplication.taskManager().allTasksFinished.disconnect(self.on_tasks_completed)

        QgsApplication.taskManager().cancelAll()

        self.iface.messageBar().clearWidgets()
        self.iface.messageBar().pushMessage(
            "MzS Tools", self.tr("Data export cancelled!"), level=Qgis.MessageLevel.Warning
        )

        self.file_logger.removeHandler(self.file_handler)

    def tr(self, message: str) -> str:
        return QCoreApplication.translate(self.__class__.__name__, message)

    def rename_field(self, layer: QgsVectorLayer, field_name: str, new_name: str):
        for field in layer.fields():
            if field.name() == field_name:
                self.file_logger.debug(f"Renaming {field.name()} to {new_name}")
                with edit(layer):
                    layer.renameAttribute(layer.fields().lookupField(field_name), new_name)
                break

    def change_field_type(self, layer, field_name, field_type):
        """
        Change the data type of a field in a vector layer.

        Args:
            layer (QgsVectorLayer): The layer containing the field to modify
            field_name (str): Name of the field to change
            field_type (QVariant.Type): New data type for the field
        """
        self.file_logger.debug(f"Changing field type for field '{field_name}'")

        # Check if the field exists
        field_idx = layer.fields().lookupField(field_name)
        if field_idx == -1:
            self.file_logger.error(f"Field '{field_name}' not found in layer")
            return False

        # Get original field configuration
        # original_field = layer.fields().at(field_idx)
        temp_field_name = "temp"

        # Create new QgsField objects without using deprecated constructor
        temp_field = QgsField()
        temp_field.setName(temp_field_name)
        # TODO: Deprecated since version 3.38: Use the method with a QMetaType.Type argument instead.
        temp_field.setType(field_type)

        new_field = QgsField()
        new_field.setName(field_name)
        # TODO: Deprecated since version 3.38: Use the method with a QMetaType.Type argument instead.
        new_field.setType(field_type)

        # Use edit context manager to handle editing sessions
        with edit(layer):
            # Create a temporary field with desired type
            layer.addAttribute(temp_field)
            layer.updateFields()

            temp_field_idx = layer.fields().lookupField(temp_field_name)

            # Copy values to the temporary field
            for feature in layer.getFeatures():
                layer.changeAttributeValue(feature.id(), temp_field_idx, feature[field_name])

        # Remove original field and add new field with same name but new type
        with edit(layer):
            # Remove the original field
            layer.deleteAttribute(field_idx)
            layer.updateFields()

            # Add new field with original name but new type
            layer.addAttribute(new_field)
            layer.updateFields()

            new_field_idx = layer.fields().lookupField(field_name)
            temp_field_idx = layer.fields().lookupField(temp_field_name)

            # Copy values from temporary field to new field
            for feature in layer.getFeatures():
                layer.changeAttributeValue(feature.id(), new_field_idx, feature[temp_field_name])

            # Remove temporary field
            layer.deleteAttribute(temp_field_idx)

        self.file_logger.debug(f"Successfully changed field type for '{field_name}'")
        return True

    def extract_file_name_from_path(self, layer, field_name):
        """
        Extract file names from path strings stored in a specified field and
        replace the full paths with just the file names.

        Args:
            layer (QgsVectorLayer): The vector layer to process
            field_name (str): The name of the field containing file paths
        """

        self.file_logger.debug(f"Extracting file name from field '{field_name}'")

        # Get field index to check if it exists
        field_idx = layer.fields().lookupField(field_name)
        if field_idx == -1:
            self.file_logger.error(f"Field '{field_name}' not found in layer")
            return

        # Start editing the layer
        layer.startEditing()

        # Process each feature
        features_updated = 0
        for feature in layer.getFeatures():
            path_value = feature[field_name]

            # Skip empty values
            if not path_value:
                continue

            # Extract filename from path
            try:
                # Use Path to extract the filename from the path
                file_name = Path(path_value).name

                # Update the feature with just the filename
                feature.setAttribute(field_idx, file_name)
                layer.updateFeature(feature)
                features_updated += 1
            except Exception as e:
                self.file_logger.error(f"Error extracting filename from '{path_value}': {str(e)}")

        # Commit changes
        success = layer.commitChanges()

        if success:
            self.file_logger.info(f"Successfully updated {features_updated} features in field '{field_name}'")
        else:
            self.file_logger.error(f"Failed to commit changes to layer: {layer.commitErrors()}")
            layer.rollBack()
