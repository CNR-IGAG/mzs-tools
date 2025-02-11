from functools import partial
from pathlib import Path

from mzs_tools.tasks.import_siti_lineari_task import ImportSitiLineariTask
from qgis.core import Qgis, QgsApplication, QgsAuthMethodConfig
from qgis.gui import QgsMessageBarItem
from qgis.PyQt import uic
from qgis.PyQt.QtCore import Qt, QCoreApplication
from qgis.PyQt.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
)
from qgis.utils import iface

from mzs_tools.tasks.access_db_connection import AccessDbConnection, JVMError, MdbAuthError
from mzs_tools.core.mzs_project_manager import MzSProjectManager
from mzs_tools.plugin_utils.logging import MzSToolsLogger
from mzs_tools.tasks.import_siti_puntuali_task import ImportSitiPuntualiTask

FORM_CLASS, _ = uic.loadUiType(Path(__file__).parent / f"{Path(__file__).stem}.ui")


class DlgImportData(QDialog, FORM_CLASS):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.log = MzSToolsLogger().log
        self.iface = iface
        self.setupUi(self)

        self.prj_manager = MzSProjectManager.instance()

        self.help_button = self.button_box.button(QDialogButtonBox.Help)
        self.cancel_button = self.button_box.button(QDialogButtonBox.Cancel)
        self.ok_button = self.button_box.button(QDialogButtonBox.Ok)

        self.ok_button.setText(self.tr("Start import"))
        self.ok_button.setEnabled(False)
        self.radio_button_mdb.setEnabled(False)
        self.radio_button_csv.setEnabled(False)
        self.csv_dir_widget.setEnabled(False)

        # self.input_dir_widget.lineEdit().textChanged.connect(self.validate_input_dir)
        self.input_dir_widget.lineEdit().textChanged.connect(self.validate_input)

        self.radio_button_mdb.toggled.connect(self.enable_csv_selection)
        self.radio_button_mdb.toggled.connect(self.validate_input)
        self.radio_button_csv.toggled.connect(self.enable_csv_selection)
        self.radio_button_csv.toggled.connect(self.validate_input)

        self.csv_dir_widget.lineEdit().textChanged.connect(self.validate_input)

        self.group_box_content.setVisible(False)
        self.label_mdb_msg.setText("")
        self.label_mdb_msg.setVisible(False)

        # self.check_box_preserve_ids.setChecked(False)

        self.input_path = None

        self.accepted.connect(self.start_import_tasks)

        self.reset_sequences = False

    def showEvent(self, e):
        super().showEvent(e)
        self.input_dir_widget.lineEdit().setText("")

    # def showEvent(self, e):
    #     super().showEvent(e)
    #     self.log(f"showEvent {e}")
    #     indagini_count = self.prj_manager.count_indagini_data()
    #     # self.log(f"Indagini data count: {indagini_count}", log_level=4)
    #     prj_contains_indagini_data = False
    #     sequences_gt_0 = False
    #     for tab, count in indagini_count.items():
    #         # count[0] is the table rows count, count[1] is the sequence for the primary key
    #         if count[0] > 0:
    #             prj_contains_indagini_data = True
    #         if count[1] > 0:
    #             sequences_gt_0 = True

    #     if prj_contains_indagini_data:
    #         title = self.tr("Warning!")
    #         message = self.tr(
    #             "The project already contains 'Indagini' data and/or related data (siti, indagini, parametri, curve)."
    #             "\n\nThe imported data numeric IDs will be different from the original data."
    #             "\n\nTo preserve the original IDs, use a new, empy project, or delete all punctual and linear sites before running the import tool."
    #         )
    #         QMessageBox.warning(self, title, message)
    #         self.reset_sequences = False
    #     else:
    #         self.reset_sequences = sequences_gt_0

    def validate_input(self):
        # if not self.input_path:
        #     self.ok_button.setEnabled(False)
        #     return False
        # if not self.input_path:
        if not self.validate_input_dir():
            self.log("Input path is not valid", log_level=1)
            self.ok_button.setEnabled(False)
            return False

        if not self.radio_button_mdb.isChecked() and not self.radio_button_csv.isChecked():
            self.log("No data source selected", log_level=1)
            self.ok_button.setEnabled(False)
            return False

        if self.radio_button_csv.isChecked():
            if not self.validate_csv_dir():
                self.log("CSV directory is not valid", log_level=1)
                self.ok_button.setEnabled(False)
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

            self.radio_button_csv.setAutoExclusive(False)
            self.radio_button_csv.setChecked(False)
            self.radio_button_csv.setAutoExclusive(True)

            self.radio_button_csv.setEnabled(False)

            self.label_mdb_msg.setVisible(False)
            return False

        # mdb_path = Path(input_dir) / "Indagini" / "CdI_Tabelle.mdb"
        # if mdb_path.exists():
        #     connected = self.check_mdb_connection(mdb_path)
        #     self.radio_button_mdb.setEnabled(connected)
        # else:
        #     self.label_mdb_msg.setText("[File non trovato]")
        #     self.radio_button_mdb.setEnabled(False)

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

        # TODO: check if the CSV directory contains the required files

        return True

    def check_project_dir(self, input_dir):
        if not Path(input_dir).exists():
            self.log(self.tr("Project folder does not exist"), log_level=4)
            return False

        # if not (Path(input_dir) / "Indagini").exists():
        #     self.log("La cartella selezionata non contiene la cartella 'Indagini'", log_level=2)
        #     return False

        # TODO: case_insensitive parameter for pathlib glob() and match() was added only in Python 3.12
        input_path = Path(input_dir).resolve()
        subdirs = [d.name for d in input_path.iterdir() if d.is_dir()]

        indagini_dir = None
        for s in subdirs:
            if s.lower() == "indagini":
                indagini_dir = input_path / s
                break

        if not indagini_dir:
            self.log(self.tr("Project folder does not contain 'Indagini' subfolder"), log_level=1)
            return False

        indagini_files = [f.name for f in indagini_dir.iterdir() if f.is_file()]
        indagini_subdirs = [d.name for d in indagini_dir.iterdir() if d.is_dir()]

        cdi_tabelle_file = None
        for f in indagini_files:
            if f.lower() == "cdi_tabelle.mdb":
                cdi_tabelle_file = indagini_dir / f
                connected = self.check_mdb_connection(cdi_tabelle_file)
                self.radio_button_mdb.setEnabled(connected)

        if not cdi_tabelle_file:
            self.label_mdb_msg.setText("[File non trovato]")
            self.radio_button_mdb.setEnabled(False)

        # TODO: etc...

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
            dialog.exec_()
            if dialog.result() == QDialog.Accepted:
                # self.log(f"Password: {dialog.input.text()}", log_level=4)
                if dialog.input.text():
                    if dialog.save_password:
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
            self.label_mdb_msg.setText("[Connessione non riuscita]")
        finally:
            if connected:
                mdb_conn.close()
                self.label_mdb_msg.setText(f"[Connessione {"con password" if password else ""} riuscita]")
                self.mdb_password = password

        return connected

    def retrieve_auth_config_by_name(self, name):
        authManager = QgsApplication.authManager()
        for id, config in authManager.availableAuthMethodConfigs().items():
            if config.name() == name:
                return id
        return None

    def start_import_tasks(self):
        if not self.input_path:
            self.log("No input path selected", log_level=2)
            return

        data_source = None
        if self.radio_button_mdb.isChecked():
            data_source = "mdb"
        elif self.radio_button_csv.isChecked():
            data_source = "csv"
        else:
            self.log("No import source selected", log_level=2)

        if self.reset_sequences:
            self.log("Resetting indagini sequences", log_level=1)
            self.prj_manager.reset_indagini_sequences()

        self.log(f"Importing data from {self.input_path} using {data_source} for Indagini data")

        # issue n.1: the task does not start if it is not assigned to self
        # https://gis.stackexchange.com/a/435487
        self.import_spu_task = ImportSitiPuntualiTask(
            self.input_path, data_source=data_source, mdb_password=self.mdb_password
        )
        self.import_sln_task = ImportSitiLineariTask(
            self.input_path, data_source=data_source, mdb_password=self.mdb_password
        )

        # self.progress_bar = QProgressBar()
        # self.progress_bar.setMaximum(100)
        # self.progress_bar.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.progress_msg: QgsMessageBarItem = self.iface.messageBar().createMessage(
            "MzS Tools", "Data import in progress..."
        )
        # progress_msg.layout().addWidget(self.progress_bar)

        cancel_button = QPushButton()
        cancel_button.setText("Cancel")
        cancel_button.clicked.connect(self.task_cancelled)
        self.progress_msg.layout().addWidget(cancel_button)

        self.iface.messageBar().pushWidget(self.progress_msg, Qgis.Info)

        # issue n.2: don't use task.progress() - it does not work properly
        # self.task.progressChanged.connect(lambda p: self.log(f"Progress: {p}"))

        # self.import_spu_task.progressChanged.connect(lambda v: self.progress_bar.setValue(int(v)))
        # self.import_sln_task.progressChanged.connect(lambda v: self.progress_bar.setValue(int(v)))
        # self.task.progressChanged.connect(lambda v: progress_msg.setText(f"Import Progress: {int(v)}"))
        # self.import_spu_task.taskCompleted.connect(self.task_completed)
        # self.import_sln_task.taskCompleted.connect(self.task_completed)

        # TODO: does not work
        QgsApplication.taskManager().countActiveTasksChanged.connect(
            # lambda v: progress_msg.setText(f"Data import: {v} tasks active")
            self.set_progress_msg
        )
        # QgsApplication.taskManager().countActiveTasksChanged.connect(
        #     lambda v: self.log(f"Import data: {v} tasks active")
        # )
        QgsApplication.taskManager().allTasksFinished.connect(self.task_completed)

        # self.task.progressChanged.connect(lambda: self.log("Progress"))
        QgsApplication.taskManager().addTask(self.import_spu_task)
        QgsApplication.taskManager().addTask(self.import_sln_task)

        self.close()

    def set_progress_msg(self, num_tasks):
        try:
            self.progress_msg.setText(f"Import Progress: {num_tasks} tasks active")
        except:  # noqa: E722
            pass

    def task_completed(self):
        self.log("Import completed.")
        self.iface.messageBar().clearWidgets()
        self.iface.messageBar().pushMessage(
            "Mzs Tools", "Data imported successfully", "more info", level=Qgis.Success, duration=0
        )
        # QgsApplication.taskManager().countActiveTasksChanged.disconnect(self.set_progress_msg)
        QgsApplication.taskManager().allTasksFinished.disconnect(self.task_completed)

        self.iface.mapCanvas().refreshAllLayers()

    def task_cancelled(self):
        self.log(
            f"Data import cancelled. Terminating {QgsApplication.taskManager().countActiveTasks()} tasks", log_level=1
        )
        QgsApplication.taskManager().allTasksFinished.disconnect(self.task_completed)
        QgsApplication.taskManager().countActiveTasksChanged.disconnect(self.set_progress_msg)
        QgsApplication.taskManager().cancelAll()

        self.iface.messageBar().clearWidgets()
        self.iface.messageBar().pushMessage("Import cancelled", "Data import cancelled", level=Qgis.Warning)

        self.iface.mapCanvas().refreshAllLayers()

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

        self.layout = QVBoxLayout()

        self.label = QLabel(self.tr("A password is required to access CdI_Tabelle.mdb"))
        self.layout.addWidget(self.label)

        self.input = QLineEdit()
        self.input.setEchoMode(QLineEdit.Password)
        self.layout.addWidget(self.input)

        self.chkbox_save = QCheckBox(self.tr("Save password in QGIS auth manager"))
        self.chkbox_save.setCheckState(Qt.Checked)
        self.chkbox_save.stateChanged.connect(self.on_chkbox_save_state_changed)
        self.layout.addWidget(self.chkbox_save)

        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        self.layout.addWidget(self.button_box)

        self.setLayout(self.layout)

        self.save_password = True
        self.password = None

    def on_chkbox_save_state_changed(self, state):
        self.save_password = state == Qt.Checked

    def tr(self, message: str) -> str:
        return QCoreApplication.translate(self.__class__.__name__, message)
