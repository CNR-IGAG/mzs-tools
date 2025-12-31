import pytest

from mzs_tools.gui.dlg_import_data import DlgImportData, DlgMdbPassword


@pytest.mark.display
def test_dlg_import_data_gui(monkeypatch, qtbot, gui_timeout, tmp_path):
    """Test DlgImportData dialog."""
    dialog = DlgImportData()
    qtbot.addWidget(dialog)
    assert dialog is not None
    assert dialog.ok_button.isEnabled() is False

    dialog.show()

    assert dialog.isVisible()

    qtbot.wait(gui_timeout)


def test_import_data_check_project_dir(standard_project_path, monkeypatch):
    dialog = DlgImportData()

    # monkeypatch DlgMdbPassword.exec() to avoid blocking dialog
    monkeypatch.setattr(DlgMdbPassword, "exec", lambda self: None, raising=False)

    result = dialog.check_project_dir(str(standard_project_path))

    # standard project should be importable
    assert result is True
