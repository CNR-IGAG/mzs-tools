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
