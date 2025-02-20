import logging
import shutil
from functools import partial
from pathlib import Path

from qgis.core import (
    Qgis,
    QgsApplication,
    QgsField,
    QgsVectorLayer,
    QgsVectorLayerExporterTask,
    edit,
)
from qgis.gui import QgsMessageBarItem
from qgis.PyQt import QtCore, uic
from qgis.PyQt.QtCore import QCoreApplication, Qt, QVariant
from qgis.PyQt.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QProgressBar,
    QPushButton,
)
from qgis.utils import iface

from mzs_tools.__about__ import DIR_PLUGIN_ROOT, __version__
from mzs_tools.core.mzs_project_manager import MzSProjectManager
from mzs_tools.plugin_utils.logging import MzSToolsLogger
from mzs_tools.tasks.access_db_connection import AccessDbConnection, JVMError
from mzs_tools.tasks.export_siti_puntuali_task import ExportSitiPuntualiTask

FORM_CLASS, _ = uic.loadUiType(Path(__file__).parent / f"{Path(__file__).stem}.ui")


class DlgExportData(QDialog, FORM_CLASS):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setupUi(self)
        self.iface = iface

        self.log = MzSToolsLogger.log

        # DEBUG MODE: all existent data will be deleted before importing new data!
        ########################
        self.debug_mode = True
        ########################

        # setup proper python logger to be used in tasks with file-based logging
        self.file_logger: logging.Logger = logging.getLogger("mzs_tools.tasks.export_data")
        if not self.file_logger.hasHandlers():
            handler = MzSToolsLogger()
            self.file_logger.addHandler(handler)

        self.prj_manager = MzSProjectManager.instance()

        self.help_button = self.button_box.button(QDialogButtonBox.Help)
        self.cancel_button = self.button_box.button(QDialogButtonBox.Cancel)
        self.ok_button = self.button_box.button(QDialogButtonBox.Ok)

        self.ok_button.setText(self.tr("Start export"))
        self.ok_button.setEnabled(False)
        self.radio_button_mdb.setEnabled(False)

        self.output_dir_widget.lineEdit().textChanged.connect(self.validate_input)
        self.radio_button_mdb.toggled.connect(self.validate_input)

        self.label_mdb_msg.setText("")
        self.label_mdb_msg.setVisible(True)

        self.output_path = None
        self.standard_proj_paths = None

        self.accepted.connect(self.start_export_tasks)

        self.indagini_output_format = None

        # test mdb connection
        cdi_tabelle_path = DIR_PLUGIN_ROOT / "data" / "CdI_Tabelle_4.2.mdb"
        connected = self.check_mdb_connection(cdi_tabelle_path)
        if connected:
            self.radio_button_mdb.setEnabled(True)

        self.total_tasks = 0
        self.completed_tasks = 0

    def showEvent(self, e):
        super().showEvent(e)
        self.output_dir_widget.lineEdit().setText("")

    def validate_input(self):
        if not self.validate_output_dir():
            self.log("Output path is not valid", log_level=1)
            self.ok_button.setEnabled(False)
            return False

        if not self.radio_button_mdb.isChecked() and not self.radio_button_sqlite.isChecked():
            self.log("No data source selected", log_level=1)
            return False

        self.ok_button.setEnabled(True)

    def validate_output_dir(self):
        output_dir = self.output_dir_widget.lineEdit().text()

        if not output_dir or not Path(output_dir).exists():
            return False

        self.output_path = Path(output_dir)
        return True

    def check_mdb_connection(self, mdb_path):
        connected = False
        mdb_conn = None
        try:
            mdb_conn = AccessDbConnection(mdb_path)
            connected = mdb_conn.open()
        except ImportError as e:
            self.log(f"{e}. Use 'qpip' QGIS plugin to install dependencies.", log_level=2)
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
            if connected:
                mdb_conn.close()
                self.label_mdb_msg.setText(self.tr("[Connection established]"))
                self.radio_button_mdb.setToolTip("")

        return connected

    def start_export_tasks(self):
        # setup file-based logging
        timestamp = QtCore.QDateTime.currentDateTime().toString("yyyy-MM-dd_hh-mm-ss")
        filename = f"data_export_{timestamp}.log"
        self.log_file_path = self.prj_manager.project_path / "Allegati" / "log" / filename
        self.file_handler = logging.FileHandler(self.log_file_path, encoding="utf-8")
        self.file_logger.addHandler(self.file_handler)
        formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
        self.file_handler.setFormatter(formatter)
        self.file_logger.setLevel(logging.DEBUG if self.chk_debug_logging.isChecked() else logging.INFO)
        self.file_logger.info(f"MzS Tools version {__version__} - Data export log")
        self.file_logger.info(f"Log file: {self.log_file_path}")
        self.file_logger.info("############### Data export started")

        if self.radio_button_mdb.isChecked():
            self.indagini_output_format = "mdb"
        elif self.radio_button_sqlite.isChecked():
            self.indagini_output_format = "sqlite"
        else:
            self.log("No import source selected", log_level=1)

        # create output directory
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

        # copy the mdb file to the output directory
        cdi_tabelle_path = DIR_PLUGIN_ROOT / "data" / "CdI_Tabelle_4.2.mdb"
        shutil.copy(cdi_tabelle_path, exported_project_path / "Indagini" / "CdI_Tabelle.mdb")

        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximum(100)
        self.progress_bar.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.progress_msg: QgsMessageBarItem = self.iface.messageBar().createMessage(
            "MzS Tools", self.tr("Data export in progress...")
        )
        self.progress_msg.layout().addWidget(self.progress_bar)

        cancel_button = QPushButton()
        cancel_button.setText("Cancel")
        cancel_button.clicked.connect(self.cancel_tasks)
        self.progress_msg.layout().addWidget(cancel_button)

        self.iface.messageBar().pushWidget(self.progress_msg, Qgis.Info)

        QgsApplication.taskManager().progressChanged.connect(self.on_tasks_progress)
        # QgsApplication.taskManager().countActiveTasksChanged.connect(self.on_tasks_completed)

        # weird behavior: the signal is not emitted when the last task is finished, but
        # when *every* task is finished
        QgsApplication.taskManager().allTasksFinished.connect(self.on_tasks_completed)

        # table - shapefile mapping
        shapefile_mapping = {
            "comuni": "BasiDati/comuni_istat.shp",
            "comune_progetto": "BasiDati/comune_progetto.shp",
            "elineari": "GeoTec/Elineari.shp",
            "epuntuali": "GeoTec/Epuntuali.shp",
            "forme": "GeoTec/Forme.shp",
            "geoidr": "GeoTec/Geoidr.shp",
            "geotec": "GeoTec/Geotec.shp",
            "instab_geotec": "GeoTec/Instab_geotec.shp",
            "sito_puntuale": "Indagini/Ind_pu.shp",
            "sito_lineare": "Indagini/Ind_ln.shp",
            "instab_l1": "MS1/Instab.shp",
            "isosub_l1": "MS1/Isosub.shp",
            "stab_l1": "MS1/Stab.shp",
            "instab_l23": "MS23/Instab.shp",
            "isosub_l23": "MS23/Isosub.shp",
            "stab_l23": "MS23/Stab.shp",
        }

        # create tasks to export shapefiles
        for table_name, shapefile_name in shapefile_mapping.items():
            layer_id = self.prj_manager.find_layer_by_table_name_role(table_name, "editing")
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
                task.errorOccurred.connect(
                    partial(self.file_logger.error, f"Error exporting {table_name} to {shapefile_name}")
                )
                self.file_logger.info(f"Starting task to export {table_name} to {shapefile_name}")
                QgsApplication.taskManager().addTask(task)
                # task.hold()
                # QTimer.singleShot(count * 1000, lambda: task.unhold())

        self.export_siti_puntuali_task = ExportSitiPuntualiTask(
            exported_project_path, self.indagini_output_format, self.debug_mode
        )
        QgsApplication.taskManager().addTask(self.export_siti_puntuali_task)

        self.total_tasks = QgsApplication.taskManager().count()

    def on_shapefile_export_complete(self, table_name, path: Path):
        self.file_logger.info(f"Exported {table_name} to {path}")

        # modify specific datasets
        if table_name == "sito_puntuale":
            self.rename_field(QgsVectorLayer(str(path), str(path.stem), "ogr"), "id_spu", "ID_SPU")
        elif table_name == "sito_lineare":
            self.rename_field(QgsVectorLayer(str(path), str(path.stem), "ogr"), "id_sln", "ID_SLN")
        elif table_name in ["isosub_l1", "isosub_l23"]:
            # for some absurd reason, the field "Quota" must be a string
            self.change_field_type(QgsVectorLayer(str(path), str(path.stem), "ogr"), "Quota", QVariant.Int)
        elif table_name in ["stab_l1", "stab_l23", "instab_l1", "instab_l23"]:
            # for some absurd reason, the field "LIVELLO" must be a double
            self.change_field_type(QgsVectorLayer(str(path), str(path.stem), "ogr"), "LIVELLO", QVariant.Double)

    def on_tasks_progress(self, taskid, progress):
        # self.progress_bar.setValue(int(progress))
        remaining_tasks = QgsApplication.taskManager().count()
        completed_tasks = self.total_tasks - remaining_tasks
        if self.completed_tasks == completed_tasks:
            return
        self.completed_tasks = completed_tasks
        progress_percentage = (completed_tasks / self.total_tasks) * 100
        self.progress_bar.setValue(int(progress_percentage))

    def on_tasks_completed(self):
        # adding on the 'allTasksFinished' weirdness, QgsApplication.taskManager().countActiveTasks()
        # will return 0 as soon as the *first* task is finished, so we need to use count() instead,
        # count() is weird too, it returns 1 when the last task is finished instead of 0
        # self.log(f"active: {QgsApplication.taskManager().countActiveTasks()}")
        # self.log(f"count: {QgsApplication.taskManager().count()}")
        if QgsApplication.taskManager().count() == 1:
            self.file_logger.info(f"{"#"*15} Data exported successfully.")
            self.iface.messageBar().clearWidgets()
            # load log file
            log_text = self.log_file_path.read_text(encoding="utf-8")
            self.iface.messageBar().pushMessage(
                "MzS Tools",
                self.tr("Data exported successfully"),
                log_text if log_text else "...",
                level=Qgis.Success,
                duration=0,
            )
            # QgsApplication.taskManager().countActiveTasksChanged.disconnect(self.on_tasks_completed)
            QgsApplication.taskManager().allTasksFinished.disconnect(self.on_tasks_completed)
            QgsApplication.taskManager().progressChanged.disconnect(self.on_tasks_progress)

            self.file_logger.removeHandler(self.file_handler)

    def cancel_tasks(self):
        self.file_logger.warning(f"{"#"*15} Data export cancelled. Terminating all tasks")
        QgsApplication.taskManager().allTasksFinished.disconnect(self.on_tasks_completed)
        QgsApplication.taskManager().progressChanged.disconnect(self.on_tasks_progress)
        # QgsApplication.taskManager().countActiveTasksChanged.disconnect(self.set_progress_msg)
        QgsApplication.taskManager().cancelAll()

        self.iface.messageBar().clearWidgets()
        self.iface.messageBar().pushMessage("MzS Tools", self.tr("Data export cancelled!"), level=Qgis.Warning)

        self.iface.mapCanvas().refreshAllLayers()

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
        # TODO: there should be a quicker/proper way to do this
        # TODO: DeprecationWarning: QgsField constructor is deprecated
        self.file_logger.debug(f"Changing field type for field '{field_name}'")
        layer.startEditing()
        layer.dataProvider().addAttributes([QgsField("new_col", field_type)])
        layer.commitChanges()

        layer.startEditing()
        for feature in layer.getFeatures():
            feature.setAttribute(feature.fields().lookupField("new_col"), feature[field_name])
            layer.updateFeature(feature)
        layer.commitChanges()

        layer.startEditing()
        layer.dataProvider().deleteAttributes([layer.fields().lookupField(field_name)])
        layer.dataProvider().addAttributes([QgsField(field_name, field_type)])
        layer.commitChanges()

        layer.startEditing()
        for feature in layer.getFeatures():
            feature.setAttribute(feature.fields().lookupField(field_name), feature["new_col"])
            layer.updateFeature(feature)
        layer.commitChanges()

        layer.startEditing()
        layer.dataProvider().deleteAttributes([layer.fields().lookupField("new_col")])
        layer.commitChanges()
