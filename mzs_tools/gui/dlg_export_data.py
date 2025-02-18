import logging
from pathlib import Path
import shutil

from qgis.core import Qgis, QgsApplication, QgsAuthMethodConfig, QgsTask, QgsVectorLayerExporterTask
from qgis.gui import QgsMessageBarItem
from qgis.PyQt import QtCore, uic
from qgis.PyQt.QtCore import QCoreApplication, Qt
from qgis.PyQt.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QLabel,
    QLineEdit,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
)
from qgis.utils import iface

from mzs_tools.__about__ import DIR_PLUGIN_ROOT, __version__
from mzs_tools.core.mzs_project_manager import MzSProjectManager
from mzs_tools.plugin_utils.logging import MzSToolsLogger
from mzs_tools.plugin_utils.misc import get_path_for_name
from mzs_tools.tasks.access_db_connection import AccessDbConnection, JVMError, MdbAuthError
from mzs_tools.tasks.import_shapefile_task import ImportShapefileTask
from mzs_tools.tasks.import_siti_lineari_task import ImportSitiLineariTask
from mzs_tools.tasks.import_siti_puntuali_task import ImportSitiPuntualiTask

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

        # test mdb connection
        cdi_tabelle_path = DIR_PLUGIN_ROOT / "data" / "CdI_Tabelle_4.2.mdb"
        connected = self.check_mdb_connection(cdi_tabelle_path)
        if connected:
            self.radio_button_mdb.setEnabled(True)

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
        # create output directory
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

        layer_id = self.prj_manager.find_layer_by_table_name_role("sito_puntuale", "editing")
        if layer_id:
            layer = self.prj_manager.current_project.mapLayer(layer_id)

            # export shapefiles
            task = QgsVectorLayerExporterTask(
                layer,
                str(exported_project_path / "Indagini" / "Ind_pu.shp"),
                "ogr",
                layer.crs(),
                options={"driverName": "ESRI Shapefile"},
            )
            QgsApplication.taskManager().addTask(task)
