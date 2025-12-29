from unittest.mock import patch

import pytest

from mzs_tools.gui.dlg_export_data import DlgExportData
from mzs_tools.tasks.access_db_connection import AccessDbConnection, JVMError


def test_dlg_export_data_init():
    dialog = DlgExportData()
    assert dialog is not None


@pytest.mark.display
def test_dlg_export_data_gui(monkeypatch, qtbot, gui_timeout, tmp_path):
    """Test DlgExportData dialog."""
    dialog = DlgExportData()
    qtbot.addWidget(dialog)
    assert dialog is not None
    assert dialog.ok_button.isEnabled() is False

    assert dialog.mdb_checked is False

    dialog.show()

    assert dialog.isVisible()

    # radio_button_mdb is enabled only when mdb_checked is True
    assert dialog.radio_button_mdb.isEnabled() == dialog.mdb_checked

    qtbot.wait(gui_timeout)

    dialog.mdb_checked = False

    # simulate mdb connection failures
    simulate_mdb_conn_fail(dialog, ImportError, "OK: ImportError")
    qtbot.wait(gui_timeout)
    simulate_mdb_conn_fail(dialog, JVMError, "OK: JVMError")
    qtbot.wait(gui_timeout)
    simulate_mdb_conn_fail(dialog, Exception, "Connection failed")
    qtbot.wait(gui_timeout)

    dialog.hide()
    dialog.show()

    # test dialog validation logic
    dialog.output_dir_widget.lineEdit().setText(str(tmp_path))
    dialog.radio_button_sqlite.setChecked(True)
    assert dialog.ok_button.isEnabled() is True

    if dialog.radio_button_mdb.isEnabled():
        dialog.radio_button_mdb.setChecked(True)
        assert dialog.ok_button.isEnabled() is True

    dialog.output_dir_widget.lineEdit().setText("/nonexistent_directory")
    assert dialog.ok_button.isEnabled() is False

    qtbot.wait(gui_timeout)


def simulate_mdb_conn_fail(dialog, err_class, msg):
    with patch.object(AccessDbConnection, "__init__", side_effect=err_class(msg)):
        # monkeypatch.setattr(dialog, "check_mdb_connection", lambda e: False)
        dialog.hide()
        dialog.show()  # trigger showEvent
        assert dialog.radio_button_mdb.isEnabled() is False
        assert msg in dialog.label_mdb_msg.text()
