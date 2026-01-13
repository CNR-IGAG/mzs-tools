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

import importlib
from unittest.mock import Mock

from qgis.core import QgsSettings


def test_plugin_init(qgis_iface, monkeypatch):
    """Test that the QGIS plugin initializes without errors."""

    # mock qgis_iface.projectRead signal
    # qgis_iface.projectRead = Mock()
    # using Mock directly would influence other tests using the qgis_iface fixture
    # monkeypatch is cleaner as it only affects this test
    monkeypatch.setattr(qgis_iface, "projectRead", Mock(), raising=False)

    mod = importlib.import_module("mzs_tools.mzs_tools")
    main_class = mod.MzSTools
    main_class = main_class(qgis_iface)  # execute __init__

    assert main_class is not None
    assert hasattr(main_class, "initGui")
    assert hasattr(main_class, "unload")
    assert hasattr(main_class, "log")
    assert hasattr(main_class, "prj_manager")


def test_plugin_init_with_fixture(plugin, qgis_iface):
    """Test that the QGIS plugin initializes without errors using the plugin fixture."""
    plugin_instance = plugin(qgis_iface)  # execute __init__

    assert plugin_instance is not None
    assert hasattr(plugin_instance, "initGui")
    assert hasattr(plugin_instance, "unload")
    assert hasattr(plugin_instance, "log")
    assert hasattr(plugin_instance, "prj_manager")

    assert plugin_instance.toolbar is not None
    assert plugin_instance.toolbar.objectName() == "MzSTools"


def test_plugin_init_with_locale_it(plugin, qgis_iface, monkeypatch):
    """Test that the QGIS plugin initializes with Italian locale without errors."""

    monkeypatch.setattr(
        QgsSettings,
        "value",
        lambda self, key, defaultValue=None, type=None: "it" if key == "locale/userLocale" else defaultValue,
    )

    plugin_instance = plugin(qgis_iface)

    assert plugin_instance is not None
    # quick test of translations
    assert plugin_instance.tr("MzSTools") == "MzSTools"  # plugin name should not be translated
    assert plugin_instance.tr("New project") == "Nuovo progetto"


def test_plugin_initGui_and_unload(plugin, qgis_iface, monkeypatch):
    """Test that the plugin's initGui and unload methods can be called without errors."""
    plugin_instance = plugin(qgis_iface)

    # monkeypatch qgis_iface missing methods used in initGui
    monkeypatch.setattr(qgis_iface, "addPluginToDatabaseMenu", Mock(), raising=False)
    monkeypatch.setattr(qgis_iface, "removePluginDatabaseMenu", Mock(), raising=False)
    monkeypatch.setattr(qgis_iface, "pluginHelpMenu", Mock(), raising=False)
    monkeypatch.setattr(qgis_iface, "registerOptionsWidgetFactory", Mock(), raising=False)
    monkeypatch.setattr(qgis_iface, "unregisterOptionsWidgetFactory", Mock(), raising=False)

    # Call initGui
    plugin_instance.initGui()

    assert len(plugin_instance.actions) > 0
    action_texts = [action.text() for action in plugin_instance.actions]
    assert plugin_instance.tr("New project") in action_texts

    # Call unload
    plugin_instance.unload()

    # plugin_instance should not have toolbar anymore
    assert not hasattr(plugin_instance, "toolbar")


# def test_check_project_read_signal(plugin, qgis_iface, monkeypatch):
#     """Test that the plugin connects to the projectRead signal without errors."""
#     # monkeypatch qgis_iface.projectRead to be a Mock
#     # monkeypatch.setattr(qgis_iface, "projectRead", Mock(), raising=False)

#     plugin_instance = plugin(qgis_iface)

#     # Ensure that the projectRead signal's connect method was called
#     plugin_instance.check_project()
