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

from unittest.mock import Mock

import pytest

from mzs_tools.gui.dlg_import_data import DlgImportData, DlgMdbPassword


@pytest.mark.display
def test_dlg_import_data_gui(monkeypatch, qtbot, gui_timeout, tmp_path):
    """Test DlgImportData dialog."""

    gui_timeout = int(gui_timeout / 2)

    # Ignore input dir validation for this test
    monkeypatch.setattr(DlgImportData, "check_mdb_connection", lambda self, x: True)

    dialog = DlgImportData()
    qtbot.addWidget(dialog)
    assert dialog is not None
    assert dialog.ok_button.isEnabled() is False
    assert dialog.group_box_content.isVisible() is False

    dialog.show()

    assert dialog.isVisible()
    assert dialog.input_dir_widget.lineEdit().text() == ""

    # Simulate selecting a directory
    dialog.input_dir_widget.lineEdit().setText("/non/existent/path")
    # With non existent path group_box_content should remain hidden
    assert dialog.group_box_content.isVisible() is False
    assert dialog.ok_button.isEnabled() is False

    qtbot.wait(gui_timeout)

    dialog.input_dir_widget.lineEdit().setText(str(tmp_path))
    # With existent path but not validated group_box_content should remain hidden and radio buttons disabled
    assert dialog.group_box_content.isVisible() is False
    assert dialog.radio_button_mdb.isEnabled() is False
    assert dialog.radio_button_sqlite.isEnabled() is False
    assert dialog.radio_button_csv.isEnabled() is False
    assert dialog.csv_dir_widget.isEnabled() is False
    assert dialog.ok_button.isEnabled() is False

    qtbot.wait(gui_timeout)

    # create "Indagini" subdir to simulate valid project structure
    (tmp_path / "Indagini").mkdir()
    dialog.input_dir_widget.lineEdit().clear()
    dialog.input_dir_widget.lineEdit().setText(str(tmp_path))
    assert dialog.group_box_content.isVisible() is True
    # TODO: ok_button is enabled now but should remain disabled until a radio button or a checkbox is selected
    assert dialog.ok_button.isEnabled() is True
    # no database present (neither MDB nor spatialite)
    assert dialog.radio_button_mdb.isEnabled() is False
    assert dialog.radio_button_sqlite.isEnabled() is False
    # but the CSV option should be enabled
    assert dialog.radio_button_csv.isEnabled() is True
    assert dialog.csv_dir_widget.isEnabled() is False

    # create a dummy MDB file to enable MDB option
    (tmp_path / "Indagini" / "CdI_Tabelle.mdb").touch()
    dialog.input_dir_widget.lineEdit().clear()
    dialog.input_dir_widget.lineEdit().setText(str(tmp_path))
    assert dialog.radio_button_mdb.isEnabled() is True
    # until radio button is selected and "Siti" shapefiles are present, the "Siti" checkboxes should remain disabled
    assert dialog.chk_siti_puntuali.isEnabled() is False
    assert dialog.chk_siti_lineari.isEnabled() is False

    qtbot.wait(gui_timeout)

    (tmp_path / "Indagini" / "Ind_pu.shp").touch()
    (tmp_path / "Indagini" / "Ind_ln.shp").touch()
    dialog.radio_button_mdb.toggle()
    assert dialog.chk_siti_puntuali.isEnabled() is True
    assert dialog.chk_siti_lineari.isEnabled() is True

    qtbot.wait(gui_timeout)

    # create a dummy sqlite file to enable sqlite option
    (tmp_path / "Indagini" / "CdI_Tabelle.sqlite").touch()
    dialog.input_dir_widget.lineEdit().clear()
    dialog.input_dir_widget.lineEdit().setText(str(tmp_path))
    assert dialog.radio_button_sqlite.isEnabled() is True
    dialog.radio_button_sqlite.toggle()
    assert dialog.chk_siti_puntuali.isEnabled() is True
    assert dialog.chk_siti_lineari.isEnabled() is True

    qtbot.wait(gui_timeout)

    # select CSV option
    dialog.radio_button_csv.toggle()
    assert dialog.csv_dir_widget.isEnabled() is True
    assert dialog.chk_siti_puntuali.isEnabled() is False
    assert dialog.chk_siti_lineari.isEnabled() is False
    # TODO: test validate_csv_dir

    qtbot.wait(gui_timeout)


def test_dlg_import_data_check_project_dir(standard_project_path, mdb_deps_available, monkeypatch):
    # monkeypatch DlgMdbPassword.exec() to avoid blocking dialog
    monkeypatch.setattr(DlgMdbPassword, "exec", Mock())

    dialog = DlgImportData()

    result = dialog.check_project_dir(str(standard_project_path))

    # standard project should be importable even when mdb access is not available
    assert result is True

    if mdb_deps_available:
        DlgMdbPassword.exec.reset_mock()
        mdb_connected = dialog.check_mdb_connection(standard_project_path / "Indagini" / "CdI_Tabelle.mdb")

        # If password protected MDB, the password dialog should be shown and connection fail
        assert mdb_connected is False
        assert dialog.radio_button_mdb.isEnabled() is False
        DlgMdbPassword.exec.assert_called_once()

        # swap mdb file to a passwordless one and test again
        DlgMdbPassword.exec.reset_mock()
        mdb_file = standard_project_path / "Indagini" / "CdI_Tabelle.mdb"
        mdb_file.rename(mdb_file.with_suffix(".mdb.bak"))
        (standard_project_path / "Indagini" / "CdI_Tabelle_no_pwd.mdb").rename(mdb_file)
        result = dialog.check_project_dir(str(standard_project_path))
        assert result is True
        assert dialog.radio_button_mdb.isEnabled() is True
        DlgMdbPassword.exec.assert_not_called()

        # restore original mdb file
        mdb_file.rename(standard_project_path / "Indagini" / "CdI_Tabelle_no_pwd.mdb")
        (standard_project_path / "Indagini" / "CdI_Tabelle.mdb.bak").rename(mdb_file)
