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

import webbrowser
from pathlib import Path

from qgis.PyQt import uic
from qgis.PyQt.QtCore import QCoreApplication, Qt
from qgis.PyQt.QtWidgets import QDialog, QDialogButtonBox, QFileDialog, QListWidgetItem, QMessageBox

from ..core.mzs_project_manager import MzSProjectManager
from ..tasks.merge_projects_task import SourceProject, scan_source_projects

FORM_CLASS, _ = uic.loadUiType(Path(__file__).parent / f"{Path(__file__).stem}.ui")

HELP_URL = "https://mzs-tools.readthedocs.io/it/latest/plugin/altri_strumenti.html#unione-di-progetti"


class DlgMergeProjects(QDialog, FORM_CLASS):
    def __init__(self, parent=None):
        """Constructor."""
        super().__init__(parent)
        self.setupUi(self)

        self.input_dir_widget.setOptions(QFileDialog.Option.ShowDirsOnly)
        self.output_dir_widget.setOptions(QFileDialog.Option.ShowDirsOnly)

        self.help_button = self.button_box.button(QDialogButtonBox.StandardButton.Help)
        self.cancel_button = self.button_box.button(QDialogButtonBox.StandardButton.Cancel)
        self.ok_button = self.button_box.button(QDialogButtonBox.StandardButton.Ok)
        self.ok_button.setEnabled(False)

        self.connect_signals()

    def connect_signals(self):
        self.ok_button.clicked.connect(self.accept)
        self.cancel_button.clicked.connect(self.reject)
        self.help_button.clicked.connect(lambda: webbrowser.open(HELP_URL))
        self.input_dir_widget.lineEdit().textChanged.connect(self.scan_input_dir)
        self.projects_list_widget.itemChanged.connect(self.validate_input)
        self.output_dir_widget.lineEdit().textChanged.connect(self.validate_input)
        self.project_name_line_edit.textChanged.connect(self.validate_input)

    def showEvent(self, e):
        super().showEvent(e)
        self.validate_input()

    def scan_input_dir(self):
        self.projects_list_widget.clear()
        input_dir = self.input_dir_widget.lineEdit().text()
        if input_dir and Path(input_dir).is_dir():
            self.projects_list_widget.blockSignals(True)
            try:
                for project in scan_source_projects(Path(input_dir)):
                    if project.issue is None:
                        item = QListWidgetItem(f"{project.cod_istat} - {project.comune} ({project.path.name})")
                        item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                        item.setCheckState(Qt.CheckState.Checked)
                    else:
                        item = QListWidgetItem(f"{project.path.name} - {project.issue}")
                        item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEnabled & ~Qt.ItemFlag.ItemIsUserCheckable)
                    item.setData(Qt.ItemDataRole.UserRole, project)
                    self.projects_list_widget.addItem(item)
            finally:
                self.projects_list_widget.blockSignals(False)
        self.validate_input()

    def selected_projects(self) -> list[SourceProject]:
        projects = []
        for i in range(self.projects_list_widget.count()):
            item = self.projects_list_widget.item(i)
            if item.flags() & Qt.ItemFlag.ItemIsUserCheckable and item.checkState() == Qt.CheckState.Checked:
                projects.append(item.data(Qt.ItemDataRole.UserRole))
        return projects

    def output_dir(self) -> str:
        return self.output_dir_widget.lineEdit().text()

    def project_name(self) -> str:
        return self.project_name_line_edit.text().strip()

    def validate_input(self):
        output_dir = self.output_dir()
        name = self.project_name()
        if len(self.selected_projects()) >= 2 and name and output_dir and Path(output_dir).is_dir():
            if (Path(output_dir) / MzSProjectManager.sanitize_comune_name(name)).exists():
                msg = self.tr(
                    "A folder with this project name already exists in the output directory. Choose a different name."
                )
                QMessageBox.warning(None, self.tr("Warning"), msg)
                self.project_name_line_edit.clear()
                return
            self.ok_button.setEnabled(True)
        else:
            self.ok_button.setEnabled(False)

    def tr(self, message):
        return QCoreApplication.translate("MergeProjects", message)
