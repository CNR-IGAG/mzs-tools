import logging

from qgis.core import Qgis, QgsApplication, QgsTask
from qgis.gui import QgsMessageBarItem
from qgis.PyQt import QtCore
from qgis.PyQt.QtCore import QCoreApplication, Qt
from qgis.PyQt.QtWidgets import (
    QProgressBar,
    QPushButton,
)
from qgis.utils import iface

from ..__about__ import __version__
from ..core.mzs_project_manager import MzSProjectManager
from ..plugin_utils.logging import MzSToolsLogger
from ..plugin_utils.settings import PlgOptionsManager
from .attachments_task import AttachmentsTask


class AttachmentsTaskManager:
    def __init__(self, prepend_ids: bool = True):
        self.iface = iface

        self.prepend_ids = prepend_ids

        self.log = MzSToolsLogger.log

        self.prj_manager = MzSProjectManager.instance()

        self.file_logger: logging.Logger = logging.getLogger("mzs_tools.tasks.attachment_manager")
        if not self.file_logger.hasHandlers():
            handler = MzSToolsLogger()
            self.file_logger.addHandler(handler)

        self.manage_attachments_task = None

        self.task_failed = False

        self.debug = PlgOptionsManager.get_plg_settings().debug_mode

    def start_manage_attachments_task(self):
        # setup file-based logging
        timestamp = QtCore.QDateTime.currentDateTime().toString("yyyy-MM-dd_hh-mm-ss")
        filename = f"attachments_check_{timestamp}.log"
        self.log_file_path = self.prj_manager.project_path / "Allegati" / "log" / filename
        self.file_handler = logging.FileHandler(self.log_file_path, encoding="utf-8")
        self.file_logger.addHandler(self.file_handler)
        formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
        self.file_handler.setFormatter(formatter)
        self.file_logger.setLevel(logging.DEBUG if self.debug else logging.INFO)
        self.file_logger.info(f"MzS Tools version {__version__} - Attachment management log")
        self.file_logger.info(f"Log file: {self.log_file_path}")
        self.file_logger.info("############### Attachments check started")

        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximum(100)
        self.progress_bar.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        progress_msg: QgsMessageBarItem = self.iface.messageBar().createMessage(
            "MzS Tools", self.tr("Attachments check in progress...")
        )
        progress_msg.layout().addWidget(self.progress_bar)

        cancel_button = QPushButton()
        cancel_button.setText(self.tr("Cancel"))
        cancel_button.clicked.connect(self.cancel_tasks)
        progress_msg.layout().addWidget(cancel_button)

        self.iface.messageBar().pushWidget(progress_msg, Qgis.Info)

        # QgsApplication.taskManager().progressChanged.connect(self._on_manage_attachments_task_progress)
        # QgsApplication.taskManager().allTasksFinished.connect(self._on_manage_attachments_task_completed)

        self.manage_attachments_task = AttachmentsTask(prepend_ids=self.prepend_ids)
        self.manage_attachments_task.progressChanged.connect(self._on_manage_attachments_task_progress)
        # self.manage_attachments_task.statusChanged.connect(self._on_manage_attachments_task_status_changed)
        self.manage_attachments_task.taskCompleted.connect(self._on_task_completed)
        self.manage_attachments_task.taskTerminated.connect(self._on_task_terminated)

        QgsApplication.taskManager().addTask(self.manage_attachments_task)

    def _on_manage_attachments_task_progress(self, progress):
        try:
            self.progress_bar.setValue(int(progress))
        except Exception:
            pass

    def _on_manage_attachments_task_status_changed(self, status):
        self.log(f"Task status changed: {status}")
        if status == QgsTask.Terminated:
            self.task_failed = True

    def _on_task_completed(self):
        msg = self.tr("Attachment check completed successfully. Check the log for missing files or other problems.")
        self.file_logger.info(f"{'#' * 15} {msg}")

        self.iface.messageBar().clearWidgets()
        # load log file
        log_text = self.log_file_path.read_text(encoding="utf-8")
        self.iface.messageBar().pushMessage(
            "MzS Tools",
            msg,
            log_text if log_text else "...",
            level=Qgis.Success,
            duration=0,
        )
        self.file_logger.removeHandler(self.file_handler)

    def _on_task_terminated(self):
        msg = self.tr("Attachment check terminated. Check the log for details.")
        self.file_logger.info(f"{'#' * 15} {msg}")

        self.iface.messageBar().clearWidgets()
        # load log file
        log_text = self.log_file_path.read_text(encoding="utf-8")
        self.iface.messageBar().pushMessage(
            "MzS Tools",
            msg,
            log_text if log_text else "...",
            level=Qgis.Critical,
            duration=0,
        )
        self.file_logger.removeHandler(self.file_handler)

    def cancel_tasks(self):
        self.file_logger.warning(f"{'#' * 15} Attachment check cancelled. Terminating all tasks")
        QgsApplication.taskManager().cancelAll()

        self.iface.messageBar().clearWidgets()
        self.iface.messageBar().pushMessage("MzS Tools", self.tr("Attachment check cancelled!"), level=Qgis.Warning)

        self.file_logger.removeHandler(self.file_handler)

    def tr(self, message: str) -> str:
        return QCoreApplication.translate(self.__class__.__name__, message)
