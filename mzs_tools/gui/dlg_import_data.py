import logging
from pathlib import Path

from qgis.core import Qgis, QgsApplication, QgsAuthMethodConfig, QgsTask
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

from ..__about__ import __version__
from ..core.mzs_project_manager import MzSProjectManager
from ..plugin_utils.logging import MzSToolsLogger
from ..plugin_utils.misc import get_path_for_name
from ..tasks.access_db_connection import AccessDbConnection, JVMError, MdbAuthError
from ..tasks.import_shapefile_task import ImportShapefileTask
from ..tasks.import_siti_lineari_task import ImportSitiLineariTask
from ..tasks.import_siti_puntuali_task import ImportSitiPuntualiTask

FORM_CLASS, _ = uic.loadUiType(Path(__file__).parent / f"{Path(__file__).stem}.ui")


class DlgImportData(QDialog, FORM_CLASS):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setupUi(self)
        self.iface = iface

        self.log = MzSToolsLogger.log

        # setup proper python logger to be used in tasks with file-based logging
        self.file_logger: logging.Logger = logging.getLogger("mzs_tools.tasks.import_data")
        if not self.file_logger.hasHandlers():
            handler = MzSToolsLogger()
            self.file_logger.addHandler(handler)

        self.prj_manager = MzSProjectManager.instance()

        self.help_button = self.button_box.button(QDialogButtonBox.Help)
        self.cancel_button = self.button_box.button(QDialogButtonBox.Cancel)
        self.ok_button = self.button_box.button(QDialogButtonBox.Ok)

        self.ok_button.setText(self.tr("Start import"))
        self.ok_button.setEnabled(False)
        self.radio_button_mdb.setEnabled(False)
        self.radio_button_csv.setEnabled(False)
        self.csv_dir_widget.setEnabled(False)

        self.input_dir_widget.lineEdit().textChanged.connect(self.validate_input)

        self.radio_button_mdb.toggled.connect(self.enable_csv_selection)
        self.radio_button_mdb.toggled.connect(self.validate_input)
        self.radio_button_csv.toggled.connect(self.enable_csv_selection)
        self.radio_button_csv.toggled.connect(self.validate_input)

        self.csv_dir_widget.lineEdit().textChanged.connect(self.validate_input)

        self.group_box_content.setVisible(False)
        self.label_mdb_msg.setText("")
        self.label_mdb_msg.setVisible(False)

        self.input_path = None
        self.reset_sequences = False
        self.standard_proj_paths = None

        self.accepted.connect(self.start_import_tasks)

        self.failed_tasks = []

    def showEvent(self, e):
        super().showEvent(e)
        self.input_dir_widget.lineEdit().setText("")

    def validate_input(self):
        if not self.validate_input_dir():
            self.log("Input path is not valid", log_level=1)
            self.ok_button.setEnabled(False)
            return False

        if not self.radio_button_mdb.isChecked() and not self.radio_button_csv.isChecked():
            self.log("No data source selected", log_level=1)
            self.chk_siti_puntuali.setEnabled(False)
            self.chk_siti_puntuali.setChecked(False)
            self.chk_siti_lineari.setEnabled(False)
            self.chk_siti_lineari.setChecked(False)
        else:
            self.validate_input_dir()

        if self.radio_button_csv.isChecked():
            if not self.validate_csv_dir():
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

        # TODO: check if the CSV directory contains the required files

        return True

    def check_project_dir(self, input_dir):
        if not Path(input_dir).exists():
            self.log(self.tr("Project folder does not exist"), log_level=4)
            self.standard_proj_paths = None
            return False

        self.standard_proj_paths = {
            "GeoTec": {"parent": None, "path": None, "checkbox": None},
            "Elineari.shp": {"parent": "GeoTec", "path": None, "checkbox": self.chk_elineari, "table": "elineari"},
            "Epuntuali.shp": {"parent": "GeoTec", "path": None, "checkbox": self.chk_epuntuali, "table": "epuntuali"},
            "Forme.shp": {"parent": "GeoTec", "path": None, "checkbox": self.chk_forme, "table": "forme"},
            "Geotec.shp": {"parent": "GeoTec", "path": None, "checkbox": self.chk_geotec, "table": "geotec"},
            "Geoidr.shp": {"parent": "GeoTec", "path": None, "checkbox": self.chk_geoidr, "table": "geoidr"},
            "Instab_geotec.shp": {
                "parent": "GeoTec",
                "path": None,
                "checkbox": self.chk_instab_geotec,
                "table": "instab_geotec",
            },
            "Indagini": {"parent": None, "path": None, "checkbox": None},
            "Documenti": {"parent": "Indagini", "path": None, "checkbox": None},
            "CdI_Tabelle.mdb": {"parent": "Indagini", "path": None, "checkbox": None},
            "Ind_pu.shp": {"parent": "Indagini", "path": None, "checkbox": self.chk_siti_puntuali},
            "Ind_ln.shp": {"parent": "Indagini", "path": None, "checkbox": self.chk_siti_lineari},
            "MS1": {"parent": None, "path": None, "checkbox": None},
            "MS1-Instab.shp": {"parent": "MS1", "path": None, "checkbox": self.chk_ms1_instab, "table": "instab_l1"},
            "MS1-Isosub.shp": {"parent": "MS1", "path": None, "checkbox": self.chk_ms1_isosub, "table": "isosub_l1"},
            "MS1-Stab.shp": {"parent": "MS1", "path": None, "checkbox": self.chk_ms1_stab, "table": "stab_l1"},
            "MS23": {"parent": None, "path": None, "checkbox": None},
            "MS23-Instab.shp": {
                "parent": "MS23",
                "path": None,
                "checkbox": self.chk_ms23_instab,
                "table": "instab_l23",
            },
            "MS23-Isosub.shp": {
                "parent": "MS23",
                "path": None,
                "checkbox": self.chk_ms23_isosub,
                "table": "isosub_l23",
            },
            "MS23-Stab.shp": {"parent": "MS23", "path": None, "checkbox": self.chk_ms23_stab, "table": "stab_l23"},
            "Spettri": {"parent": "MS23", "path": None, "checkbox": None},
            "Plot": {"parent": None, "path": None, "checkbox": None},
        }

        for name, data in self.standard_proj_paths.items():
            parent_path = Path(input_dir) if not data["parent"] else Path(input_dir) / data["parent"]
            data["path"] = get_path_for_name(parent_path, name.split("-")[1] if "-" in name else name)
            # self.log(f"{name}: {data['path']}", log_level=4)
            if data["checkbox"]:
                # self.log(f"Enabling checkbox for {name}", log_level=4)
                data["checkbox"].setEnabled(True if data["path"] else False)
                data["checkbox"].setChecked(True if data["path"] else False)

        # self.log(f"Standard project paths: {self.standard_proj_paths}", log_level=4)

        if not self.standard_proj_paths["Indagini"]["path"]:
            self.log(self.tr("Project folder does not contain 'Indagini' subfolder"), log_level=1)
            return False

        cdi_tabelle_path = self.standard_proj_paths["CdI_Tabelle.mdb"]["path"]
        if not cdi_tabelle_path:
            self.label_mdb_msg.setText(self.tr("[File not found]"))
            self.radio_button_mdb.setEnabled(False)
        else:
            connected = self.check_mdb_connection(cdi_tabelle_path)
            self.radio_button_mdb.setEnabled(connected)

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
            self.label_mdb_msg.setText(self.tr("[Connection failed]"))
        finally:
            if connected:
                mdb_conn.close()
                self.label_mdb_msg.setText(self.tr(f"[Connection {'with password' if password else ''} established]"))
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

        # make sure document paths exist
        allegati_paths = ["Altro", "Documenti", "log", "Plot", "Spettri"]
        for sub_dir in allegati_paths:
            sub_dir_path = self.prj_manager.project_path / "Allegati" / sub_dir
            sub_dir_path.mkdir(parents=True, exist_ok=True)

        # setup file-based logging
        timestamp = QtCore.QDateTime.currentDateTime().toString("yyyy-MM-dd_hh-mm-ss")
        filename = f"data_import_{timestamp}.log"
        self.log_file_path = self.prj_manager.project_path / "Allegati" / "log" / filename
        self.file_handler = logging.FileHandler(self.log_file_path, encoding="utf-8")
        self.file_logger.addHandler(self.file_handler)
        formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
        self.file_handler.setFormatter(formatter)
        self.file_logger.setLevel(logging.DEBUG if self.chk_debug_logging.isChecked() else logging.INFO)
        self.file_logger.info(f"MzS Tools version {__version__} - Data import log")
        self.file_logger.info(f"Log file: {self.log_file_path}")
        self.file_logger.info("############### Data import started")

        indagini_data_source = None
        if self.radio_button_mdb.isChecked():
            indagini_data_source = "mdb"
        elif self.radio_button_csv.isChecked():
            indagini_data_source = "csv"
        else:
            self.log("No import source selected", log_level=1)

        # backup database
        backup_path = self.prj_manager.backup_database()
        self.file_logger.info(f"Database backup created at {backup_path}")

        if self.reset_sequences:
            self.file_logger.warning("Resetting Indagini sequences")
            self.prj_manager.reset_indagini_sequences()

        self.file_logger.info(f"Importing data from {self.input_path} using {indagini_data_source} for Indagini data")

        tasks = []
        if self.chk_siti_puntuali.isEnabled() and self.chk_siti_puntuali.isChecked():
            self.import_spu_task = ImportSitiPuntualiTask(
                self.standard_proj_paths,
                data_source=indagini_data_source,
                mdb_password=self.mdb_password,
            )
            # self.import_spu_task.log_msg.connect(self.log_task_msg)
            tasks.append(self.import_spu_task)
        if self.chk_siti_lineari.isEnabled() and self.chk_siti_lineari.isChecked():
            self.import_sln_task = ImportSitiLineariTask(
                self.standard_proj_paths,
                data_source=indagini_data_source,
                mdb_password=self.mdb_password,
            )
            tasks.append(self.import_sln_task)
        self.import_shapefile_tasks = {}
        for name, data in self.standard_proj_paths.items():
            if (
                ".shp" in name
                and "table" in data
                and data["checkbox"]
                and data["checkbox"].isEnabled()
                and data["checkbox"].isChecked()
            ):
                task_name = f"import_shapefile_task_{name}"
                self.import_shapefile_tasks[task_name] = ImportShapefileTask(self.standard_proj_paths, name)
                tasks.append(self.import_shapefile_tasks[task_name])

        if not tasks:
            self.file_logger.warning("No tasks selected for import!")
            return

        selected_tasks = []
        for task in tasks:
            selected_tasks = [task.description() for task in tasks]
        self.file_logger.info(f"Selected tasks: {selected_tasks}")

        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximum(100)
        self.progress_bar.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.progress_msg: QgsMessageBarItem = self.iface.messageBar().createMessage(
            "MzS Tools", self.tr("Data import in progress...")
        )
        self.progress_msg.layout().addWidget(self.progress_bar)

        cancel_button = QPushButton()
        cancel_button.setText("Cancel")
        cancel_button.clicked.connect(self.cancel_tasks)
        self.progress_msg.layout().addWidget(cancel_button)

        self.iface.messageBar().pushWidget(self.progress_msg, Qgis.Info)

        QgsApplication.taskManager().progressChanged.connect(self.on_tasks_progress)
        QgsApplication.taskManager().statusChanged.connect(self.on_task_status_changed)
        QgsApplication.taskManager().allTasksFinished.connect(self.on_tasks_completed)

        if len(tasks) == 1:
            QgsApplication.taskManager().addTask(tasks[0])
            return

        # this way the tasks are independent from each other and run concurrently
        # probably dangerous for db writes
        # for task in tasks:
        #     QgsApplication.taskManager().addTask(task)

        # run the tasks sequentially:
        # every task is a subtask of the previous one and the parent task is dependent on the subtask
        task_count = 0
        first_task = None
        previous_task = None
        for task in tasks:
            task_count += 1
            if task_count == 1:
                first_task = previous_task = task
            else:
                previous_task.addSubTask(task, [], QgsTask.ParentDependsOnSubTask)
                previous_task = task

        QgsApplication.taskManager().addTask(first_task)

    def on_tasks_progress(self, taskid, progress):
        # if there is only one main task with a series of subtasks, progress
        # seems to be reported as the average of all the subtasks' progress
        # task_desc = QgsApplication.taskManager().task(taskid).description()
        # num_tasks_remaining = QgsApplication.taskManager().countActiveTasks()
        # try:
        #     self.progress_msg.setText(f"{task_desc} - {num_tasks_remaining} tasks remaining")
        #     self.progress_bar.setValue(int(progress))
        # except:  # noqa: E722
        #     pass

        # refresh layers every 20%
        if progress % 20 == 0:
            self.iface.mapCanvas().refreshAllLayers()
        self.progress_bar.setValue(int(progress))

    def on_task_status_changed(self, taskid, status):
        if status == QgsTask.Terminated:
            self.failed_tasks.append(QgsApplication.taskManager().task(taskid).description())

    def on_tasks_completed(self):
        if QgsApplication.taskManager().countActiveTasks() > 0:
            return

        if len(self.failed_tasks) == 0:
            msg = self.tr("Data imported successfully")
            level = Qgis.Success
        else:
            msg = self.tr("Data import completed with errors. Check the log for details.")
            level = Qgis.Warning

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
        self.file_logger.warning(f"{'#' * 15} Data import cancelled. Terminating all tasks")
        QgsApplication.taskManager().progressChanged.disconnect(self.on_tasks_progress)
        QgsApplication.taskManager().statusChanged.disconnect(self.on_task_status_changed)
        QgsApplication.taskManager().allTasksFinished.disconnect(self.on_tasks_completed)

        QgsApplication.taskManager().cancelAll()

        self.iface.messageBar().clearWidgets()
        self.iface.messageBar().pushMessage("MzS Tools", self.tr("Data import cancelled!"), level=Qgis.Warning)

        self.iface.mapCanvas().refreshAllLayers()

        self.file_logger.removeHandler(self.file_handler)

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
