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

from unittest.mock import MagicMock, patch

import pytest
from qgis.core import QgsMessageLog
from qgis.gui import QgsMessageBar
from qgis.PyQt.QtWidgets import QWidget

from mzs_tools.__about__ import __title__
from mzs_tools.plugin_utils.logging import MzSToolsLogger


def test_basic_log(monkeypatch):
    """Test basic logging functionality"""
    test_message = "Test message"
    monkeypatch.setattr(QgsMessageLog, "logMessage", MagicMock())
    MzSToolsLogger.log(message=test_message)

    QgsMessageLog.logMessage.assert_called_once_with(message=test_message, tag=__title__, notifyUser=False, level=0)


def test_push_message(monkeypatch, qgis_iface):
    """Test push message to message bar"""
    test_message = "Push test message"
    msgbar = qgis_iface.messageBar()
    monkeypatch.setattr(msgbar, "pushMessage", MagicMock())
    MzSToolsLogger.log(message=test_message, push=True)

    msgbar.pushMessage.assert_called_once()


def test_debug_mode(monkeypatch):
    """Test debug mode behavior"""
    with patch("mzs_tools.plugin_utils.settings.PlgOptionsManager.get_plg_settings") as mock_settings:
        mock_settings.return_value.debug_mode = False

        monkeypatch.setattr(QgsMessageLog, "logMessage", MagicMock())

        # Debug message should not be logged in non-debug mode
        MzSToolsLogger.log(message="Info message", log_level=4)
        QgsMessageLog.logMessage.assert_not_called()

        # Warning should be logged regardless of debug mode
        MzSToolsLogger.log(message="Warning message", log_level=1)
        QgsMessageLog.logMessage.assert_called_once_with(
            message="Warning message", tag=__title__, notifyUser=False, level=1
        )


def test_message_conversion(monkeypatch):
    """Test non-string message conversion"""
    test_number = 12345
    monkeypatch.setattr(QgsMessageLog, "logMessage", MagicMock())
    MzSToolsLogger.log(message=test_number)  # type: ignore

    QgsMessageLog.logMessage.assert_called_once_with(message="12345", tag=__title__, notifyUser=False, level=0)

    # simulate conversion failure
    class BadStr:
        def __str__(self):
            raise Exception("Bad conversion")

    bad_message = BadStr()
    MzSToolsLogger.log(message=bad_message)  # type: ignore


def test_button_functionality(monkeypatch, qgis_iface):
    """Test button creation and functionality"""
    test_message = "Button test"
    monkeypatch.setattr(QgsMessageLog, "logMessage", MagicMock())
    msgbar = qgis_iface.messageBar()
    monkeypatch.setattr(msgbar, "createMessage", MagicMock(), raising=False)
    monkeypatch.setattr(msgbar, "pushWidget", MagicMock(), raising=False)
    button_callback = MagicMock()

    MzSToolsLogger.log(
        message=test_message, push=True, button=True, button_text="Click me", button_connect=button_callback
    )

    QgsMessageLog.logMessage.assert_called_once_with(message="Button test", tag=__title__, notifyUser=True, level=0)


@pytest.mark.display
def test_parent_widget_message_bar(qtbot, gui_timeout):
    """Test using parent widget's message bar"""
    test_message = "Parent widget test"

    widget = QWidget()
    qtbot.addWidget(widget)
    message_bar = QgsMessageBar(widget)
    qtbot.addWidget(message_bar)

    MzSToolsLogger.log(message=test_message, push=True, parent_location=widget, duration=5)

    widget.show()

    # Message should be pushed to parent's message bar
    assert widget.findChild(type(message_bar)) is not None

    qtbot.wait(gui_timeout)
