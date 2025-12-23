import pytest
from qgis.PyQt.QtCore import QTimer
from qgis.PyQt.QtWidgets import QDialog

# sanity checks to verify that qtbot from pytest-qt is working

# mark all tests in this module with "display" marker
pytestmark = pytest.mark.display


def test_show_gui_without_qtbot(gui_timeout):
    dialog = QDialog()
    dialog.show()
    assert dialog.isVisible()
    # manually show gui and close after timeout
    QTimer.singleShot(gui_timeout, dialog.close)  # type: ignore
    # alternative: use qapp (pytest-qt) or qgis_app (pytest-qgis)
    # QTimer.singleShot(gui_timeout, qapp.closeAllWindows)  # or qapp.quit
    dialog.exec()


def test_qtbot(qtbot):
    dialog = QDialog()
    # registering widgets not required but recommended for proper cleanup
    qtbot.addWidget(dialog)
    dialog.show()
    assert dialog.isVisible()
    # dialog not shown, it's automatically and immediately closed by qtbot


def test_qtbot_show_gui(qtbot, gui_timeout):
    dialog = QDialog()
    qtbot.addWidget(dialog)
    dialog.show()
    assert dialog.isVisible()

    # using qtbot.wait to show the dialog for a certain time
    qtbot.wait(gui_timeout)
    # no need to close the dialog, qtbot will do it
    # dialog.close()
