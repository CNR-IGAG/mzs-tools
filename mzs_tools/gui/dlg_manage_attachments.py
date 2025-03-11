from pathlib import Path

from mzs_tools.tasks.attachments_task_manager import AttachmentsTaskManager
from qgis.PyQt import uic
from qgis.PyQt.QtWidgets import QDialog


FORM_CLASS, _ = uic.loadUiType(Path(__file__).parent / f"{Path(__file__).stem}.ui")


class DlgManageAttachments(QDialog, FORM_CLASS):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setupUi(self)

        self.manager = None

        self.accepted.connect(self.on_accepted)

    def on_accepted(self):
        self.manager = AttachmentsTaskManager(self.chk_prepend_ids.isChecked())
        self.manager.start_manage_attachments_task()
