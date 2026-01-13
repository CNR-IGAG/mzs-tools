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

import pytest

from mzs_tools.__about__ import __version__
from mzs_tools.gui.dlg_info import DlgPluginInfo


@pytest.mark.display
def test_dlg_info_gui(qtbot, gui_timeout):
    """Test PluginInfo dialog."""
    dialog = DlgPluginInfo()
    qtbot.addWidget(dialog)
    assert dialog is not None
    assert dialog.markdown_available is not None
    assert dialog.label_info is not None
    assert dialog.label_license is not None
    assert dialog.label_credits is not None
    assert dialog.label_changelog is not None
    assert dialog.button_manual is not None
    assert dialog.button_github is not None
    assert dialog.buttonBox is not None

    if dialog.markdown_available:
        assert dialog.label_credits.textFormat() == 3
        assert dialog.label_changelog.textFormat() == 3

    dialog.show()

    assert dialog.isVisible()
    # version label is set in showEvent()
    assert dialog.label_version.text() == f"Version {__version__}"

    qtbot.wait(gui_timeout)
