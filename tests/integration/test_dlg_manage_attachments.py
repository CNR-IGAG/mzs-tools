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

from mzs_tools.gui.dlg_manage_attachments import DlgManageAttachments


@pytest.mark.display
def test_dlg_manage_attachments_gui(qtbot, gui_timeout):
    """Test DlgManageAttachments dialog."""
    dialog = DlgManageAttachments()
    qtbot.addWidget(dialog)
    assert dialog is not None
    assert dialog.chk_prepend_ids is not None

    dialog.show()

    assert dialog.isVisible()

    qtbot.wait(gui_timeout)
