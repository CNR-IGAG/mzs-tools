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

from mzs_tools.gui.dlg_fix_layers import DlgFixLayers


@pytest.mark.display
def test_dlg_fix_layers_gui(qtbot, gui_timeout, qgis_iface, monkeypatch):
    """Test PluginInfo dialog."""
    dialog = DlgFixLayers()
    qtbot.addWidget(dialog)
    assert dialog is not None

    dialog.show()

    assert dialog.isVisible()
    assert dialog.ok_button.isEnabled() is False

    dialog.chk_editing_layers.setChecked(True)
    qtbot.wait(int(gui_timeout / 2))
    assert dialog.ok_button.isEnabled() is True
    dialog.chk_editing_layers.setChecked(False)
    assert dialog.ok_button.isEnabled() is False

    dialog.chk_layout_layers.setChecked(True)
    qtbot.wait(int(gui_timeout / 2))
    assert dialog.ok_button.isEnabled() is True
    dialog.chk_layout_layers.setChecked(False)
    assert dialog.ok_button.isEnabled() is False

    dialog.chk_base_layers.setChecked(True)
    qtbot.wait(int(gui_timeout / 2))
    assert dialog.ok_button.isEnabled() is True
    dialog.chk_base_layers.setChecked(False)
    assert dialog.ok_button.isEnabled() is False

    qtbot.wait(int(gui_timeout / 2))

    from qgis.PyQt.QtWidgets import QMessageBox

    monkeypatch.setattr(QMessageBox, "exec", lambda x: QMessageBox.StandardButton.Yes)
    monkeypatch.setattr(dialog.prj_manager, "add_default_layers", Mock())

    dialog.chk_layout_layers.setChecked(True)
    dialog.accept()
    dialog.prj_manager.add_default_layers.assert_called_once_with(  # type: ignore
        add_base_layers=False, add_editing_layers=False, add_layout_groups=True
    )

    dialog.prj_manager.add_default_layers.reset_mock()  # type: ignore
    dialog.chk_layout_layers.setChecked(False)
    dialog.chk_base_layers.setChecked(True)
    dialog.accept()
    dialog.prj_manager.add_default_layers.assert_called_once_with(  # type: ignore
        add_base_layers=True, add_editing_layers=False, add_layout_groups=False
    )

    dialog.prj_manager.add_default_layers.reset_mock()  # type: ignore
    dialog.chk_layout_layers.setChecked(False)
    dialog.chk_base_layers.setChecked(False)
    dialog.chk_editing_layers.setChecked(True)
    # when replacing editing layers, the project must be reloaded to refresh the relation editor widgets
    monkeypatch.setattr(qgis_iface, "addProject", Mock(), raising=False)
    monkeypatch.setattr(dialog.prj_manager, "backup_qgis_project", Mock())
    monkeypatch.setattr(dialog.prj_manager, "current_project", Mock(), raising=False)
    dialog.accept()
    dialog.prj_manager.add_default_layers.assert_called_once_with(  # type: ignore
        add_base_layers=False, add_editing_layers=True, add_layout_groups=False
    )
    dialog.prj_manager.backup_qgis_project.assert_called_once()  # type: ignore
    dialog.prj_manager.current_project.write.assert_called_once()  # type: ignore
    qgis_iface.addProject.assert_called_once()

    # click ok but then select No in the confirmation dialog
    dialog.prj_manager.add_default_layers.reset_mock()  # type: ignore
    monkeypatch.setattr(QMessageBox, "exec", lambda x: QMessageBox.StandardButton.No)
    dialog.accept()
    dialog.prj_manager.add_default_layers.assert_not_called()  # type: ignore
