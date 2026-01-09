import sqlite3
from unittest.mock import Mock

import pytest
from pytest_qgis import MockMessageBar
from qgis.core import QgsProject

from mzs_tools.__about__ import __base_version__, __version__
from mzs_tools.core.constants import DB_MIGRATION_SCRIPTS


def test_update_project_from_1_9_4(
    plugin,
    qgis_iface,
    qgis_new_project,
    base_project_path_1_9_4,
    monkeypatch,
):
    """Test updating a project from version 1.9.4 to the current version."""
    plugin_instance = plugin(qgis_iface)

    project_file = base_project_path_1_9_4 / "progetto_MS.qgz"

    # Create a new project
    project = QgsProject.instance()

    # patch show_project_update_dialog
    monkeypatch.setattr(plugin_instance, "show_project_update_dialog", lambda: None, raising=False)
    # qgis_iface lacks addProject method
    monkeypatch.setattr(qgis_iface, "addProject", Mock(), raising=False)

    # open the project
    project.read(str(project_file))

    # manually run check_project as qgis_iface lacks projectRead signal
    # this will initialize the plugin's project manager
    # prj_manager.init_manager()
    plugin_instance.check_project()
    project_version = plugin_instance.prj_manager.project_version
    assert project_version == "1.9.4"

    assert plugin_instance.prj_manager.is_mzs_project is True
    assert plugin_instance.prj_manager.project_updateable is True

    # verify db < 2.0.0 has no history table
    assert plugin_instance.prj_manager.db.table_exists("mzs_tools_update_history") is False

    # patch message bar and start update
    monkeypatch.setattr(MockMessageBar, "clearWidgets", lambda x: None, raising=False)
    monkeypatch.setattr(MockMessageBar, "createMessage", lambda x, y, z: Mock(), raising=False)
    monkeypatch.setattr(MockMessageBar, "pushWidget", lambda x, y, z: Mock(), raising=False)
    monkeypatch.setattr(MockMessageBar, "popWidget", lambda x, y: Mock(), raising=False)
    plugin_instance.update_current_project()

    # manually load the updated project as addProject is mocked
    qgis_iface.addProject.assert_called_once_with(str(project_file))
    project.read(str(project_file))
    plugin_instance.check_project()

    assert plugin_instance.prj_manager.project_updateable is False
    assert plugin_instance.prj_manager.project_version == __base_version__

    # verify db history and applied sql scripts
    # enable row factory to access columns by name and get the db update history
    plugin_instance.prj_manager.db.connection.row_factory = sqlite3.Row
    assert plugin_instance.prj_manager.db.table_exists("mzs_tools_update_history") is True
    history = plugin_instance.prj_manager.db.execute_query("SELECT * FROM mzs_tools_update_history")
    assert len(history) > 0
    sql_scripts_applied = []
    for record in history:
        assert record["from_version"] == project_version
        assert record["to_version"] == __version__
        if record["updated_component"] == "project":
            assert "rebuilding project" in record["notes"]
        else:
            sql_scripts_applied.append(record["notes"])

    # Check that expected SQL scripts were applied
    expected_scripts = [script for version, script in DB_MIGRATION_SCRIPTS.items() if version > project_version]
    assert len(expected_scripts) == len(sql_scripts_applied)
    if len(expected_scripts) > 0:
        notes_str = " ".join(sql_scripts_applied)
        for script_file in expected_scripts:
            assert script_file in notes_str

    project.clear()


def test_update_project_from_1_9_4_with_data(
    plugin,
    qgis_iface,
    qgis_new_project,
    base_project_path_1_9_4_imported,
    monkeypatch,
):
    """Test updating a project from version 1.9.4 to the current version with data."""
    plugin_instance = plugin(qgis_iface)

    project_file = base_project_path_1_9_4_imported / "progetto_MS.qgz"

    # Create a new project
    project = QgsProject.instance()

    # patch show_project_update_dialog
    monkeypatch.setattr(plugin_instance, "show_project_update_dialog", lambda: None, raising=False)
    # qgis_iface lacks addProject method
    monkeypatch.setattr(qgis_iface, "addProject", Mock(), raising=False)

    # open the project
    project.read(str(project_file))

    # manually run check_project as qgis_iface lacks projectRead signal
    # this will initialize the plugin's project manager
    # prj_manager.init_manager()
    plugin_instance.check_project()
    project_version = plugin_instance.prj_manager.project_version
    assert project_version == "1.9.4"

    assert plugin_instance.prj_manager.is_mzs_project is True
    assert plugin_instance.prj_manager.project_updateable is True

    # verify db < 2.0.0 has no history table
    assert plugin_instance.prj_manager.db.table_exists("mzs_tools_update_history") is False

    # patch message bar and start update
    monkeypatch.setattr(MockMessageBar, "clearWidgets", lambda x: None, raising=False)
    monkeypatch.setattr(MockMessageBar, "createMessage", lambda x, y, z: Mock(), raising=False)
    monkeypatch.setattr(MockMessageBar, "pushWidget", lambda x, y, z: Mock(), raising=False)
    monkeypatch.setattr(MockMessageBar, "popWidget", lambda x, y: Mock(), raising=False)
    plugin_instance.update_current_project()

    # manually load the updated project as addProject is mocked
    qgis_iface.addProject.assert_called_once_with(str(project_file))
    project.read(str(project_file))
    plugin_instance.check_project()

    assert plugin_instance.prj_manager.project_updateable is False
    assert plugin_instance.prj_manager.project_version == __base_version__

    # verify db history and applied sql scripts
    # enable row factory to access columns by name and get the db update history
    plugin_instance.prj_manager.db.connection.row_factory = sqlite3.Row
    assert plugin_instance.prj_manager.db.table_exists("mzs_tools_update_history") is True
    history = plugin_instance.prj_manager.db.execute_query("SELECT * FROM mzs_tools_update_history")
    assert len(history) > 0
    sql_scripts_applied = []
    for record in history:
        assert record["from_version"] == project_version
        assert record["to_version"] == __version__
        if record["updated_component"] == "project":
            assert "rebuilding project" in record["notes"]
        else:
            sql_scripts_applied.append(record["notes"])

    # Check that expected SQL scripts were applied
    expected_scripts = [script for version, script in DB_MIGRATION_SCRIPTS.items() if version > project_version]
    assert len(expected_scripts) == len(sql_scripts_applied)
    if len(expected_scripts) > 0:
        notes_str = " ".join(sql_scripts_applied)
        for script_file in expected_scripts:
            assert script_file in notes_str

    # TODO: verify data

    project.clear()


def test_update_project_from_2_0_5(
    plugin,
    qgis_iface,
    qgis_new_project,
    base_project_path_2_0_5,
    monkeypatch,
):
    """Test updating a project from version 2.0.5 to the current version."""
    plugin_instance = plugin(qgis_iface)

    project_file = base_project_path_2_0_5 / "progetto_MS.qgz"

    # Create a new project
    project = QgsProject.instance()

    # patch show_project_update_dialog
    monkeypatch.setattr(plugin_instance, "show_project_update_dialog", lambda: None, raising=False)

    # open the project
    project.read(str(project_file))

    # manually run check_project as qgis_iface lacks projectRead signal
    # this will initialize the plugin's project manager
    # prj_manager.init_manager()
    plugin_instance.check_project()
    project_version = plugin_instance.prj_manager.project_version
    assert project_version == "2.0.5"

    assert plugin_instance.prj_manager.is_mzs_project is True
    assert plugin_instance.prj_manager.project_updateable is True

    # patch message bar and start update
    monkeypatch.setattr(MockMessageBar, "clearWidgets", lambda x: None, raising=False)
    monkeypatch.setattr(MockMessageBar, "createMessage", lambda x, y, z: Mock(), raising=False)
    monkeypatch.setattr(MockMessageBar, "pushWidget", lambda x, y, z: Mock(), raising=False)
    monkeypatch.setattr(MockMessageBar, "popWidget", lambda x, y: Mock(), raising=False)
    plugin_instance.update_current_project()

    plugin_instance.check_project()

    assert plugin_instance.prj_manager.project_updateable is False
    assert plugin_instance.prj_manager.project_version == __base_version__

    # verify db history and applied sql scripts
    # enable row factory to access columns by name and get the db update history
    plugin_instance.prj_manager.db.connection.row_factory = sqlite3.Row
    assert plugin_instance.prj_manager.db.table_exists("mzs_tools_update_history") is True
    history = plugin_instance.prj_manager.db.execute_query("SELECT * FROM mzs_tools_update_history")
    assert len(history) > 0
    sql_scripts_applied = []
    for record in history:
        assert record["from_version"] == project_version
        assert record["to_version"] == __version__
        if record["updated_component"] == "project":
            assert "project updated successfully" in record["notes"]
        elif record["updated_component"] == "db":
            sql_scripts_applied.append(record["notes"])

    # Check that expected SQL scripts were applied
    expected_scripts = [script for version, script in DB_MIGRATION_SCRIPTS.items() if version > project_version]
    assert len(expected_scripts) == len(sql_scripts_applied)
    if len(expected_scripts) > 0:
        notes_str = " ".join(sql_scripts_applied)
        for script_file in expected_scripts:
            assert script_file in notes_str

    project.clear()
