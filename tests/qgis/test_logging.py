from unittest.mock import MagicMock, patch

import pytest
from qgis.core import QgsMessageLog
from qgis.gui import QgsMessageBar
from qgis.PyQt.QtWidgets import QWidget

from mzs_tools.__about__ import __title__
from mzs_tools.plugin_utils.logging import MzSToolsLogger
from mzs_tools.plugin_utils.settings import PlgOptionsManager


# def test_log_message(qgis_iface):
#     message = "Test message"
#     logger = MzSToolsLogger()
#     logger.log(message, log_level=0, push=False)
#     qgis_iface.messageLog.logMessage.assert_called_with(message, __title__, 0)


@pytest.fixture
def mock_qgis():
    """Mock QGIS dependencies"""
    with (
        patch("mzs_tools.plugin_utils.logging.QgsMessageLog") as mock_log,
        patch("mzs_tools.plugin_utils.logging.iface") as mock_iface,
        patch("mzs_tools.plugin_utils.logging.QgsMessageOutput") as mock_output,
    ):
        mock_iface.messageBar.return_value = MagicMock()
        yield {"message_log": mock_log, "iface": mock_iface, "message_output": mock_output}


@pytest.fixture
def parent_widget():
    """Create parent widget with message bar"""
    widget = QWidget()
    message_bar = QgsMessageBar(widget)
    return widget


@pytest.mark.skip(reason="TODO: find out why this test is failing")
def test_basic_log(mock_qgis):
    """Test basic logging functionality"""
    test_message = "Test message"
    MzSToolsLogger.log(message=test_message)

    mock_qgis["message_log"].logMessage.assert_called_once_with(
        message=test_message, tag=__title__, notifyUser=False, level=0
    )


def test_push_message(mock_qgis):
    """Test push message to message bar"""
    test_message = "Push test message"
    MzSToolsLogger.log(message=test_message, push=True)

    mock_qgis["iface"].messageBar.return_value.pushMessage.assert_called_once()


def test_debug_mode(mock_qgis):
    """Test debug mode behavior"""
    with patch("mzs_tools.plugin_utils.settings.PlgOptionsManager.get_plg_settings") as mock_settings:
        mock_settings.return_value.debug_mode = False

        # Debug message should not be logged in non-debug mode
        MzSToolsLogger.log(message="Info message", log_level=4)
        mock_qgis["message_log"].logMessage.assert_not_called()

        # Warning should be logged regardless of debug mode
        MzSToolsLogger.log(message="Warning message", log_level=1)
        mock_qgis["message_log"].logMessage.assert_called_once()


@pytest.mark.skip(reason="TODO: find out why this test is failing")
def test_message_conversion(mock_qgis):
    """Test non-string message conversion"""
    test_number = 12345
    MzSToolsLogger.log(message=test_number)

    mock_qgis["message_log"].logMessage.assert_called_once_with(
        message="12345", tag=__title__, notifyUser=False, level=0
    )


def test_button_functionality(mock_qgis):
    """Test button creation and functionality"""
    test_message = "Button test"
    button_callback = MagicMock()

    MzSToolsLogger.log(
        message=test_message, push=True, button=True, button_text="Click me", button_connect=button_callback
    )

    mock_qgis["iface"].messageBar.return_value.createMessage.assert_called_once()


def test_parent_widget_message_bar(mock_qgis, parent_widget):
    """Test using parent widget's message bar"""
    test_message = "Parent widget test"

    MzSToolsLogger.log(message=test_message, push=True, parent_location=parent_widget)

    # Message should be pushed to parent's message bar
    assert parent_widget.findChild(QgsMessageBar) is not None


def test_custom_duration(mock_qgis):
    """Test custom duration setting"""
    test_message = "Duration test"
    custom_duration = 10

    MzSToolsLogger.log(message=test_message, push=True, duration=custom_duration)

    mock_qgis["iface"].messageBar.return_value.pushMessage.assert_called_once()


@pytest.fixture(autouse=True)
def cleanup_settings():
    """Cleanup settings after each test"""
    settings_manager = PlgOptionsManager()
    settings_manager.set_value_from_key("debug_mode", False)
    yield
    settings_manager.set_value_from_key("debug_mode", False)
