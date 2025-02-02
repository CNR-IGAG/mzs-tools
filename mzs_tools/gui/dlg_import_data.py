from pathlib import Path

import jpype
import jpype.imports
from jpype.types import *  # noqa: F403
from qgis.core import QgsApplication, QgsAuthMethodConfig
from qgis.gui import QgsAuthConfigSelect
from qgis.PyQt import uic
from qgis.PyQt.QtCore import QCoreApplication, QSettings, Qt
from qgis.PyQt.QtGui import QIcon, QPixmap
from qgis.PyQt.QtWidgets import (
    QAction,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMessageBox,
    QVBoxLayout,
)
from qgis.utils import iface

from mzs_tools.core.access_db_connection import AccessDbConnection
from mzs_tools.plugin_utils.logging import MzSToolsLogger

FORM_CLASS, _ = uic.loadUiType(Path(__file__).parent / f"{Path(__file__).stem}.ui")


class DlgImportData(QDialog, FORM_CLASS):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.log = MzSToolsLogger().log
        self.setupUi(self)

        self.help_button = self.button_box.button(QDialogButtonBox.Help)
        self.cancel_button = self.button_box.button(QDialogButtonBox.Cancel)
        self.ok_button = self.button_box.button(QDialogButtonBox.Ok)

        self.radio_button_mdb.setEnabled(False)
        self.radio_button_csv.setEnabled(False)
        self.csv_dir_widget.setEnabled(False)

        self.input_dir_widget.lineEdit().textChanged.connect(self.validate_input_dir)

        self.radio_button_mdb.toggled.connect(self.enable_csv_selection)
        self.radio_button_csv.toggled.connect(self.enable_csv_selection)

        self.group_box_content.setVisible(False)

    def showEvent(self, e):
        super().showEvent(e)

        # self.radio_button_mdb.setEnabled(True)

    def validate_input_dir(self):
        input_dir = self.input_dir_widget.lineEdit().text()

        if not input_dir:
            self.group_box_content.setVisible(False)

            # https://stackoverflow.com/questions/1731620/is-there-a-way-to-have-all-radion-buttons-be-unchecked
            self.radio_button_mdb.setAutoExclusive(False)
            self.radio_button_mdb.setChecked(False)
            self.radio_button_mdb.setAutoExclusive(True)

            self.radio_button_mdb.setEnabled(False)

            self.radio_button_csv.setAutoExclusive(False)
            self.radio_button_csv.setChecked(False)
            self.radio_button_csv.setAutoExclusive(True)

            self.radio_button_csv.setEnabled(False)

            return

        mdb_path = Path(input_dir) / "Indagini" / "CdI_Tabelle.mdb"
        if mdb_path.exists():
            self.check_mdb_connection(mdb_path)
        else:
            self.radio_button_mdb.setText("CdI_Tabelle.mdb [File non trovato]")
            self.radio_button_mdb.setEnabled(False)

        if self.check_project_dir(input_dir):
            self.radio_button_csv.setEnabled(True)
            self.group_box_content.setVisible(True)

    def enable_csv_selection(self):
        self.csv_dir_widget.setEnabled(self.radio_button_csv.isChecked())

    def check_project_dir(self, input_dir):
        if not Path(input_dir).exists():
            self.log("La cartella selezionata non esiste", log_level=2)
            return False

        if not (Path(input_dir) / "Indagini").exists():
            self.log("La cartella selezionata non contiene la cartella 'Indagini'", log_level=2)
            return False

        # etc...

        return True

    def check_mdb_connection(self, mdb_path, password=None):
        mdb_conn = AccessDbConnection(mdb_path, password=password)

        connected = False
        try:
            connected = mdb_conn.open()
        except Exception as e:
            if not jpype.isJVMStarted():
                self.radio_button_mdb.setText("CdI_Tabelle.mdb [Errore JVM]")
                self.radio_button_mdb.setEnabled(False)
                return False
            from net.ucanaccess.exception import AuthenticationException  # type: ignore

            if isinstance(e.getCause(), AuthenticationException):
                # title = "Enter database password"
                # label = "A password is required to access the database"
                # text = ""
                # mode = QLineEdit.Password
                # password, ok = QInputDialog.getText(self, title, label, mode, text)
                # if ok:
                #     return self.check_mdb_connection(mdb_path, password=password)
                dialog = CustomDialog(self)
                dialog.exec_()
                if dialog.result() == QDialog.Accepted:
                    self.log(f"Selected auth config: {dialog.config_id}", log_level=4)
                    if dialog.config_id:
                        authManager = QgsApplication.authManager()
                        config = QgsAuthMethodConfig()
                        success = authManager.loadAuthenticationConfig(dialog.config_id, config, full=True)
                        if success:
                            return self.check_mdb_connection(mdb_path, password=config.configMap()["password"])

                self.radio_button_mdb.setText("CdI_Tabelle.mdb [Password richiesta]")
            else:
                self.radio_button_mdb.setText("CdI_Tabelle.mdb [Connessione non riuscita]")
                self.radio_button_mdb.setEnabled(False)
            return False

        if connected:
            self.radio_button_mdb.setText("CdI_Tabelle.mdb [Connessione riuscita]")
            self.radio_button_mdb.setEnabled(True)
            mdb_conn.close()


class CustomDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__()
        self.setWindowTitle("Select auth config")

        QBtn = QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        self.buttonBox = QDialogButtonBox(QBtn)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)

        self.auth_config_selector = QgsAuthConfigSelect(self)
        self.auth_config_selector.selectedConfigIdChanged.connect(self.get_config_id)

        self.layout = QVBoxLayout()

        message = QLabel("Select the auth config containing the credentials")

        self.layout.addWidget(message)
        self.layout.addWidget(self.auth_config_selector)
        self.layout.addWidget(self.buttonBox)
        self.setLayout(self.layout)

        self.config_id = None

    def get_config_id(self):
        self.config_id = self.auth_config_selector.configId()
