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

from functools import partial
from pathlib import Path
from typing import cast

from qgis.core import QgsApplication, QgsAuthMethodConfig
from qgis.gui import QgisInterface
from qgis.PyQt import uic
from qgis.PyQt.QtCore import QCoreApplication, Qt, QUrl
from qgis.PyQt.QtGui import QDesktopServices
from qgis.PyQt.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QLabel,
    QLineEdit,
    QVBoxLayout,
)
from qgis.utils import iface

from ..core.mzs_project_manager import MzSProjectManager
from ..plugin_utils.logging import MzSToolsLogger
from ..tasks.access_db_connection import AccessDbConnection, JVMError, MdbAuthError
from ..tasks.import_data_task_manager import ImportDataTaskManager
from ..tasks.standard_project import (
    LINEARI_CSV_SERIES,
    PUNTUALI_CSV_SERIES,
    build_standard_project_paths,
    find_csv_files,
)

FORM_CLASS, _ = uic.loadUiType(Path(__file__).parent / f"{Path(__file__).stem}.ui")


class DlgImportData(QDialog, FORM_CLASS):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setupUi(self)
        self.iface: QgisInterface = cast(QgisInterface, iface)

        self.log = MzSToolsLogger.log

        self.prj_manager = MzSProjectManager.instance()

        self.help_button = self.button_box.button(QDialogButtonBox.StandardButton.Help)
        self.cancel_button = self.button_box.button(QDialogButtonBox.StandardButton.Cancel)
        self.ok_button = self.button_box.button(QDialogButtonBox.StandardButton.Ok)

        self.ok_button.setText(self.tr("Start import"))
        self.ok_button.setEnabled(False)
        self.radio_button_mdb.setEnabled(False)
        self.radio_button_csv.setEnabled(False)
        self.radio_button_sqlite.setEnabled(False)
        self.csv_dir_widget.setEnabled(False)

        self.input_dir_widget.lineEdit().textChanged.connect(self.validate_input)

        self.radio_button_mdb.toggled.connect(self.enable_csv_selection)
        self.radio_button_mdb.toggled.connect(self.validate_input)
        self.radio_button_csv.toggled.connect(self.enable_csv_selection)
        self.radio_button_csv.toggled.connect(self.validate_input)
        self.radio_button_sqlite.toggled.connect(self.enable_csv_selection)
        self.radio_button_sqlite.toggled.connect(self.validate_input)

        self.csv_dir_widget.lineEdit().textChanged.connect(self.validate_input)
        self.csv_files_found = None

        self.group_box_content.setVisible(False)
        self.label_mdb_msg.setText("")
        self.label_mdb_msg.setVisible(False)

        self.help_button.pressed.connect(
            partial(QDesktopServices.openUrl, QUrl("https://cnr-igag.github.io/mzs-tools/plugin/importazione.html"))
        )

        self.input_path = None
        self.reset_sequences = False
        self.standard_proj_paths = None
        self.shapefile_checkboxes: dict[str, QCheckBox] = {
            "Elineari.shp": self.chk_elineari,
            "Epuntuali.shp": self.chk_epuntuali,
            "Forme.shp": self.chk_forme,
            "Geotec.shp": self.chk_geotec,
            "Geoidr.shp": self.chk_geoidr,
            "Instab_geotec.shp": self.chk_instab_geotec,
            "Ind_pu.shp": self.chk_siti_puntuali,
            "Ind_ln.shp": self.chk_siti_lineari,
            "MS1-Instab.shp": self.chk_ms1_instab,
            "MS1-Isosub.shp": self.chk_ms1_isosub,
            "MS1-Stab.shp": self.chk_ms1_stab,
            "MS23-Instab.shp": self.chk_ms23_instab,
            "MS23-Isosub.shp": self.chk_ms23_isosub,
            "MS23-Stab.shp": self.chk_ms23_stab,
        }

        self.mdb_password = None

        self.accepted.connect(self.start_import_tasks)

        self.import_data_task_manager: ImportDataTaskManager | None = None

    def showEvent(self, e):
        super().showEvent(e)
        self.input_dir_widget.lineEdit().setText("")

    def validate_input(self):
        if not self.validate_input_dir():
            self.log("Input path is not valid", log_level=1)
            self.ok_button.setEnabled(False)
            return False

        if (
            not self.radio_button_mdb.isChecked()
            and not self.radio_button_csv.isChecked()
            and not self.radio_button_sqlite.isChecked()
        ):
            self.log("No data source selected", log_level=1)
            self.chk_siti_puntuali.setEnabled(False)
            self.chk_siti_puntuali.setChecked(False)
            self.chk_siti_lineari.setEnabled(False)
            self.chk_siti_lineari.setChecked(False)
        else:
            self.validate_input_dir()

        if self.radio_button_csv.isChecked() and not self.validate_csv_dir():
            self.log("CSV directory is not valid", log_level=1)
            self.ok_button.setEnabled(False)
            self.chk_siti_puntuali.setEnabled(False)
            self.chk_siti_puntuali.setChecked(False)
            self.chk_siti_lineari.setEnabled(False)
            self.chk_siti_lineari.setChecked(False)
            return False

        self.ok_button.setEnabled(True)

    def validate_input_dir(self):
        input_dir = self.input_dir_widget.lineEdit().text()

        if not input_dir or not Path(input_dir).exists():
            self.group_box_content.setVisible(False)

            # https://stackoverflow.com/questions/1731620/is-there-a-way-to-have-all-radion-buttons-be-unchecked
            self.radio_button_mdb.setAutoExclusive(False)
            self.radio_button_mdb.setChecked(False)
            self.radio_button_mdb.setAutoExclusive(True)

            self.radio_button_mdb.setEnabled(False)

            self.radio_button_sqlite.setAutoExclusive(False)
            self.radio_button_sqlite.setChecked(False)
            self.radio_button_sqlite.setAutoExclusive(True)

            self.radio_button_sqlite.setEnabled(False)

            self.radio_button_csv.setAutoExclusive(False)
            self.radio_button_csv.setChecked(False)
            self.radio_button_csv.setAutoExclusive(True)

            self.radio_button_csv.setEnabled(False)

            self.label_mdb_msg.setVisible(False)
            return False

        if self.check_project_dir(input_dir):
            self.radio_button_csv.setEnabled(True)
            self.group_box_content.setVisible(True)
            self.input_path = Path(input_dir)
            self.label_mdb_msg.setVisible(True)

            return True

        self.input_path = None
        self.label_mdb_msg.setVisible(False)

    def enable_csv_selection(self):
        self.csv_dir_widget.setEnabled(self.radio_button_csv.isChecked())

    def validate_csv_dir(self):
        csv_dir = self.csv_dir_widget.lineEdit().text()
        if not csv_dir or not Path(csv_dir).exists():
            return False

        self.csv_files_found = find_csv_files(Path(csv_dir))
        has_sito_puntuale = "sito_puntuale" in self.csv_files_found["puntuali"]
        has_sito_lineare = "sito_lineare" in self.csv_files_found["lineari"]

        # Enable/disable checkboxes based on what was found
        if has_sito_puntuale:
            self.chk_siti_puntuali.setEnabled(True)
            self.chk_siti_puntuali.setChecked(True)
        else:
            self.chk_siti_puntuali.setEnabled(False)
            self.chk_siti_puntuali.setChecked(False)

        if has_sito_lineare:
            self.chk_siti_lineari.setEnabled(True)
            self.chk_siti_lineari.setChecked(True)
        else:
            self.chk_siti_lineari.setEnabled(False)
            self.chk_siti_lineari.setChecked(False)

        # At least one of sito_puntuale or sito_lineare must be present
        has_required_files = has_sito_puntuale or has_sito_lineare

        if has_required_files:
            status_msg = []
            if "sito_puntuale" in self.csv_files_found["puntuali"]:
                status_msg.append(
                    f"Found {len(self.csv_files_found['puntuali'])}/{len(PUNTUALI_CSV_SERIES)} puntuali files"
                )
            if "sito_lineare" in self.csv_files_found["lineari"]:
                status_msg.append(
                    f"Found {len(self.csv_files_found['lineari'])}/{len(LINEARI_CSV_SERIES)} lineari files"
                )

            self.log(f"CSV validation: {', '.join(status_msg)}", log_level=4)
        else:
            self.log("CSV validation failed: missing required files (sito_puntuale or sito_lineare)", log_level=1)

        return has_required_files

    def check_project_dir(self, input_dir):
        if not Path(input_dir).exists():
            self.log(self.tr("Project folder does not exist"), log_level=4)
            self.standard_proj_paths = None
            return False

        self.standard_proj_paths = build_standard_project_paths(Path(input_dir))
        for name, checkbox in self.shapefile_checkboxes.items():
            checkbox.setEnabled(bool(self.standard_proj_paths[name]["path"]))
            checkbox.setChecked(bool(self.standard_proj_paths[name]["path"]))

        if not self.standard_proj_paths["Indagini"]["path"]:
            self.log(self.tr("Project folder does not contain 'Indagini' subfolder"), log_level=1)
            return False

        cdi_tabelle_mdb_path = self.standard_proj_paths["CdI_Tabelle.mdb"]["path"]
        if not cdi_tabelle_mdb_path:
            self.label_mdb_msg.setText(self.tr("[File not found]"))
            self.radio_button_mdb.setEnabled(False)
        else:
            connected = self.check_mdb_connection(cdi_tabelle_mdb_path)
            self.radio_button_mdb.setEnabled(connected)

        cdi_tabelle_sqlite_path = self.standard_proj_paths["CdI_Tabelle.sqlite"]["path"]
        if not cdi_tabelle_sqlite_path:
            self.radio_button_sqlite.setEnabled(False)
        else:
            self.radio_button_sqlite.setEnabled(True)

        return True

    def check_mdb_connection(self, mdb_path, password=None):
        connected = False
        mdb_conn = None
        try:
            mdb_conn = AccessDbConnection(mdb_path, password=password)
            connected = mdb_conn.open()
        except ImportError as e:
            self.log(f"{e}. Use 'qpip' QGIS plugin to install dependencies.", log_level=2)
            self.label_mdb_msg.setText(f"[{e}]")
        except JVMError as e:
            self.log(f"{e}", log_level=2)
            self.label_mdb_msg.setText(f"[{e} - check your Java JVM installation]")
        except MdbAuthError as e:
            self.log(f"{e}", log_level=1)
            if password is None:
                # check if the password was saved in the QGIS auth manager
                authManager = QgsApplication.authManager()
                stored_config_id = self.retrieve_auth_config_by_name("MzS Tools CdI_Tabelle.mdb password")
                if stored_config_id:
                    config = QgsAuthMethodConfig()
                    success = authManager.loadAuthenticationConfig(stored_config_id, config, full=True)
                    if success and "password" in config.configMap():
                        self.log(f"Loaded stored password from config id: {stored_config_id}", log_level=4)
                        return self.check_mdb_connection(mdb_path, password=config.configMap()["password"])
            else:
                # password was stored but it's incorrect, remove it
                authManager = QgsApplication.authManager()
                stored_config_id = self.retrieve_auth_config_by_name("MzS Tools CdI_Tabelle.mdb password")
                if stored_config_id:
                    authManager.removeAuthenticationConfig(stored_config_id)
                    self.log(f"Removed invalid auth config with id: {stored_config_id}", log_level=4)

            dialog = DlgMdbPassword(self)
            dialog.exec()
            if dialog.result() == QDialog.DialogCode.Accepted:
                # self.log(f"Password: {dialog.input.text()}", log_level=4)
                if dialog.input.text() and dialog.save_password:
                    authManager = QgsApplication.authManager()
                    config = QgsAuthMethodConfig()
                    config.setMethod("Basic")
                    config.setName("MzS Tools CdI_Tabelle.mdb password")
                    config.setConfig("password", dialog.input.text())
                    authManager.storeAuthenticationConfig(config)
                    self.log(f"Password saved in QGIS auth manager: {config.id()}", log_level=4)
                return self.check_mdb_connection(mdb_path, password=dialog.input.text())
            # dialog rejected
            self.label_mdb_msg.setText(f"[{e}]")
        except Exception as e:
            self.log(f"{e}", log_level=2)
            self.label_mdb_msg.setText(self.tr("[Connection failed]"))
        finally:
            if connected:
                mdb_conn.close()
                msg_connected = self.tr("Connection established")
                msg_pwd = self.tr(" with password")
                self.label_mdb_msg.setText(f"[{msg_connected}{msg_pwd if password else ''}]")
                self.mdb_password = password

        return connected

    def retrieve_auth_config_by_name(self, name):
        authManager = QgsApplication.authManager()
        for id, config in authManager.availableAuthMethodConfigs().items():
            if config.name() == name:
                return id
        return None

    def start_import_tasks(self):
        if not self.prj_manager.project_path or not self.input_path:
            self.log("Project path or input path not set", log_level=2)
            return

        # Determine the indagini data source
        indagini_data_source = None
        if self.radio_button_mdb.isChecked():
            indagini_data_source = "mdb"
        elif self.radio_button_sqlite.isChecked():
            indagini_data_source = "sqlite"
        elif self.radio_button_csv.isChecked():
            indagini_data_source = "csv"
        else:
            self.log("No import source selected", log_level=1)

        import_spu = self.chk_siti_puntuali.isEnabled() and self.chk_siti_puntuali.isChecked()
        import_sln = self.chk_siti_lineari.isEnabled() and self.chk_siti_lineari.isChecked()

        selected_shapefiles = [
            name
            for name, checkbox in self.shapefile_checkboxes.items()
            if "table" in self.standard_proj_paths[name] and checkbox.isEnabled() and checkbox.isChecked()
        ]

        self.import_data_task_manager = ImportDataTaskManager(
            standard_proj_paths=self.standard_proj_paths,
            input_path=self.input_path,
            indagini_data_source=indagini_data_source,
            mdb_password=self.mdb_password,
            csv_files_found=self.csv_files_found,
            reset_sequences=self.reset_sequences,
            import_spu=import_spu,
            import_sln=import_sln,
            selected_shapefiles=selected_shapefiles,
            debug_mode=self.chk_debug_logging.isChecked(),
        )
        self.import_data_task_manager.start_import_tasks()

    def tr(self, message: str) -> str:
        return QCoreApplication.translate(self.__class__.__name__, message)


# class CustomDialog(QDialog):
#     def __init__(self, parent=None):
#         super().__init__()
#         self.setWindowTitle("Select auth config")

#         QBtn = QDialogButtonBox.Ok | QDialogButtonBox.Cancel
#         self.buttonBox = QDialogButtonBox(QBtn)
#         self.buttonBox.accepted.connect(self.accept)
#         self.buttonBox.rejected.connect(self.reject)

#         self.auth_config_selector = QgsAuthConfigSelect(self)
#         self.auth_config_selector.selectedConfigIdChanged.connect(self.get_config_id)

#         self.layout = QVBoxLayout()

#         message = QLabel("Select the auth config containing the credentials")

#         self.layout.addWidget(message)
#         self.layout.addWidget(self.auth_config_selector)
#         self.layout.addWidget(self.buttonBox)
#         self.setLayout(self.layout)

#         self.config_id = None

#     def get_config_id(self):
#         self.config_id = self.auth_config_selector.configId()


class DlgMdbPassword(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(self.tr("Enter database password"))

        self.layout: QVBoxLayout = QVBoxLayout()

        self.label = QLabel(self.tr("A password is required to access CdI_Tabelle.mdb"))
        self.layout.addWidget(self.label)

        self.input = QLineEdit()
        self.input.setEchoMode(QLineEdit.EchoMode.Password)
        self.layout.addWidget(self.input)

        self.chkbox_save = QCheckBox(self.tr("Save password in QGIS auth manager"))
        self.chkbox_save.setCheckState(Qt.CheckState.Checked)
        self.chkbox_save.stateChanged.connect(self.on_chkbox_save_state_changed)
        self.layout.addWidget(self.chkbox_save)

        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)  # type: ignore
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        self.layout.addWidget(self.button_box)

        self.setLayout(self.layout)

        self.save_password = True
        self.password = None

    def on_chkbox_save_state_changed(self, state):
        self.save_password = state == Qt.CheckState.Checked

    def tr(self, message: str) -> str:
        return QCoreApplication.translate(self.__class__.__name__, message)
