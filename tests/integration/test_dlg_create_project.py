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

from pathlib import Path

import pytest
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtWidgets import QCompleter, QMessageBox

from mzs_tools.gui.dlg_create_project import DlgCreateProject


def test_dlg_create_project_init():
    dialog = DlgCreateProject()
    assert dialog is not None


@pytest.mark.display
def test_dlg_create_project_comune_completer(qtbot, gui_timeout):
    dialog = DlgCreateProject()
    qtbot.addWidget(dialog)

    dialog.show()

    # comune_line_edit.setText() does not trigger the completer, so we use qtbot to simulate key presses
    comune = "rom"
    for char in comune:
        qtbot.wait(100)
        qtbot.keyClick(dialog.comune_line_edit, char)

    # Get completion model
    completer = dialog.comune_line_edit.completer()
    assert isinstance(completer, QCompleter)
    assert completer.caseSensitivity() == Qt.CaseSensitivity.CaseInsensitive
    model = completer.completionModel()
    assert model.rowCount() > 0

    results = [model.data(model.index(i, 0)) for i in range(model.rowCount())]
    assert "Roma (Roma - Lazio)" in results
    assert "Monopoli (Bari - Puglia)" not in results

    dialog.comune_line_edit.setText("")

    comune = "monopo"
    for char in comune:
        qtbot.wait(100)
        qtbot.keyClick(dialog.comune_line_edit, char)

    # Verify "Monopoli" is in completions
    found = False
    for i in range(model.rowCount()):
        if "Monopoli" in model.data(model.index(i, 0)):
            found = True
            # Simulate selection of completion
            completer.activated.emit(model.data(model.index(i, 0)))
            break
    assert found

    assert dialog.comune_line_edit.text() == "Monopoli (Bari - Puglia)"
    assert dialog.cod_istat_line_edit.text() == "072030"

    qtbot.wait(gui_timeout)


@pytest.mark.display
def test_dlg_create_project_validate_input(qtbot, monkeypatch, tmp_path, gui_timeout):
    """Test the validate_input method of DlgCreateProject."""
    dialog = DlgCreateProject()
    qtbot.addWidget(dialog)
    dialog.show()

    # Initially, ok button should be disabled
    assert dialog.ok_button.isEnabled() is False

    # Fill in some fields
    dialog.comune_line_edit.setText("roma")
    dialog.cod_istat_line_edit.setText("058091")
    dialog.study_author_line_edit.setText("Mario Rossi")
    dialog.author_email_line_edit.setText("asdf@qwer.com")
    dialog.output_dir_widget.lineEdit().setText("/nonexistent_directory")
    dialog.validate_input()
    # ok button should still be disabled because output directory does not exist
    assert dialog.ok_button.isEnabled() is False

    dialog.output_dir_widget.lineEdit().setText(str(tmp_path))
    dialog.validate_input()
    # ok button should be enabled now
    assert dialog.ok_button.isEnabled() is True
    qtbot.wait(gui_timeout)

    # Test the case where the project directory already exists
    # in this case validate_input() removes output_dir_widget text and returns

    # monkeypatch Path.exists to return True
    monkeypatch.setattr(Path, "exists", lambda x: True)

    # monkeypatch QMessageBox.warning to prevent modal dialog
    # https://pytest-qt.readthedocs.io/en/4.3.0/note_dialogs.html
    monkeypatch.setattr(QMessageBox, "warning", lambda *args, **kwargs: None)

    dialog.validate_input()
    assert dialog.output_dir_widget.lineEdit().text() == ""
    assert dialog.ok_button.isEnabled() is False

    qtbot.wait(gui_timeout)
