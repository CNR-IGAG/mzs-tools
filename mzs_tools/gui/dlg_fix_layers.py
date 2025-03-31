from pathlib import Path

from qgis.PyQt import uic
from qgis.PyQt.QtCore import QCoreApplication, Qt
from qgis.PyQt.QtWidgets import QDialog, QDialogButtonBox, QMessageBox
from qgis.utils import iface

from ..core.mzs_project_manager import MzSProjectManager
from ..plugin_utils.logging import MzSToolsLogger

FORM_CLASS, _ = uic.loadUiType(Path(__file__).parent / f"{Path(__file__).stem}.ui")


class DlgFixLayers(QDialog, FORM_CLASS):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setupUi(self)
        self.iface = iface

        self.log = MzSToolsLogger.log
        self.prj_manager = MzSProjectManager.instance()

        self.cancel_button = self.button_box.button(QDialogButtonBox.StandardButton.Cancel)
        self.ok_button = self.button_box.button(QDialogButtonBox.StandardButton.Ok)

        self.ok_button.setEnabled(False)

        self.chk_editing_layers.stateChanged.connect(self.validate_input)
        self.chk_layout_layers.stateChanged.connect(self.validate_input)
        self.chk_base_layers.stateChanged.connect(self.validate_input)

        self.accepted.connect(self.replace_layers)

    def validate_input(self):
        if (
            self.chk_editing_layers.isChecked()
            or self.chk_layout_layers.isChecked()
            or self.chk_base_layers.isChecked()
        ):
            self.ok_button.setEnabled(True)
        else:
            self.ok_button.setEnabled(False)

    def replace_layers(self):
        selected_groups = []
        if self.chk_editing_layers.isChecked():
            selected_groups.append(self.tr("Editing"))
        if self.chk_layout_layers.isChecked():
            selected_groups.append(self.tr("Print Layouts"))
        if self.chk_base_layers.isChecked():
            selected_groups.append(self.tr("Base"))

        self.log("Request to replace layers in groups: " + ", ".join(selected_groups))

        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Icon.Question)
        msg_box.setWindowTitle(self.tr("MzS Tools - Fix/Replace Layers"))
        msg = self.tr("The layers in the following groups will be replaced:")
        grp_list_txt = "\n".join(selected_groups)
        msg_box.setText(f"{msg}\n\n{grp_list_txt}\n")
        msg_box.setInformativeText(self.tr("Do you want to proceed?"))
        msg_box.setDetailedText(
            self.tr(
                "An MzS Tools project requires certain settings and specific layers to function properly.\n"
                "If some problems are detected in the current project, it is possible to replace the required layers with the default ones.\n"
                "The process will not modify data currently stored in the database in any way, "
                "only the selected QGIS layer groups will be replaced and all data will be preserved."
            )
        )
        msg_box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        msg_box.setDefaultButton(QMessageBox.StandardButton.Yes)

        response = msg_box.exec()
        if response == QMessageBox.StandardButton.Yes:
            self.prj_manager.add_default_layers(
                add_base_layers=self.chk_base_layers.isChecked(),
                add_editing_layers=self.chk_editing_layers.isChecked(),
                add_layout_groups=self.chk_layout_layers.isChecked(),
            )
            if self.chk_editing_layers.isChecked():
                # the project must be reloaded after adding the default relations to refresh the relation editor widgets
                self.prj_manager.backup_qgis_project()
                self.log("Saving and reloading the project after replacing the editing layers.", log_level=4)
                self.prj_manager.current_project.write()
                iface.addProject(str(self.prj_manager.current_project.absoluteFilePath()))
            self.log("The layer replacement process has been completed successfully.", log_level=3, push=True)
            return
        else:
            self.log("Canceled the layer replacement process.", log_level=4)
            return

    def tr(self, message: str) -> str:
        return QCoreApplication.translate(self.__class__.__name__, message)
