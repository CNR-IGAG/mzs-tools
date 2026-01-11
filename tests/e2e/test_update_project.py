import sqlite3
from pathlib import Path
from typing import Any
from unittest.mock import Mock

from pytest_qgis import MockMessageBar
from qgis.core import QgsProject

from mzs_tools.__about__ import __base_version__, __version__
from mzs_tools.core.constants import DB_MIGRATION_SCRIPTS


def setup_test_environment(plugin_instance: Any, qgis_iface: Any, project_path: Path, monkeypatch: Any) -> tuple:
    """Set up test environment for project update tests.

    Args:
        plugin_instance: The plugin instance
        qgis_iface: QGIS interface mock
        project_path: Path to the project file
        monkeypatch: pytest monkeypatch fixture

    Returns:
        Tuple of (project, project_file)
    """
    project_file = project_path / "progetto_MS.qgz"
    project = QgsProject.instance()

    # Patch plugin methods and interface
    monkeypatch.setattr(plugin_instance, "show_project_update_dialog", lambda: None, raising=False)
    monkeypatch.setattr(qgis_iface, "addProject", Mock(), raising=False)

    # Disable rendering to prevent crashes during project read
    disable_rendering(project, qgis_iface)

    # Open the project
    project.read(str(project_file))

    return project, project_file


def disable_rendering(project: Any, qgis_iface: Any) -> None:
    """Disable map rendering to prevent crashes during tests.

    There is a known issue with QGIS when running tests - the map canvas tries to render even in headless mode,
    leading to labeling engine crashes. This function disables rendering on the map canvas.

    Args:
        project: QGIS project instance
        qgis_iface: QGIS interface mock
    """
    # Disable map canvas rendering if available
    if hasattr(qgis_iface, "mapCanvas") and qgis_iface.mapCanvas():
        canvas = qgis_iface.mapCanvas()
        canvas.setRenderFlag(False)
        canvas.freeze(True)


def patch_message_bar(monkeypatch: Any) -> None:
    """Patch MockMessageBar methods for testing.

    Args:
        monkeypatch: pytest monkeypatch fixture
    """
    monkeypatch.setattr(MockMessageBar, "clearWidgets", lambda x: None, raising=False)
    monkeypatch.setattr(MockMessageBar, "createMessage", lambda x, y, z: Mock(), raising=False)
    monkeypatch.setattr(MockMessageBar, "pushWidget", lambda x, y, z: Mock(), raising=False)
    monkeypatch.setattr(MockMessageBar, "popWidget", lambda x, y: Mock(), raising=False)


def perform_update(
    plugin_instance: Any,
    project: Any,
    project_file: Path,
    qgis_iface: Any,
    monkeypatch: Any,
    reload_project: bool = True,
) -> None:
    """Perform project update and reload.

    Args:
        plugin_instance: The plugin instance
        project: QGIS project instance
        project_file: Path to the project file
        qgis_iface: QGIS interface mock
        monkeypatch: pytest monkeypatch fixture
        reload_project: Whether to reload the project after update (default: True)
    """
    patch_message_bar(monkeypatch)
    plugin_instance.update_current_project()

    if reload_project:
        # Manually load the updated project as addProject is mocked
        qgis_iface.addProject.assert_called_once_with(str(project_file))
        # Ensure rendering is disabled before reading the project
        disable_rendering(project, qgis_iface)
        project.read(str(project_file))

    plugin_instance.check_project()


def verify_update_history(prj_manager: Any, project_version: str, check_history_table_before: bool = True) -> list:
    """Verify database update history and return applied SQL scripts.

    Args:
        prj_manager: Project manager instance
        project_version: Original project version before update
        check_history_table_before: Whether to check history table didn't exist before (default: True)

    Returns:
        List of applied SQL script names
    """
    # Enable row factory to access columns by name
    prj_manager.db.connection.row_factory = sqlite3.Row

    assert prj_manager.db.table_exists("mzs_tools_update_history") is True
    history = prj_manager.db.execute_query("SELECT * FROM mzs_tools_update_history")
    assert len(history) > 0

    sql_scripts_applied = []
    for record in history:
        assert record["from_version"] == project_version
        assert record["to_version"] == __version__
        if record["updated_component"] == "project":
            # Different message for pre-2.0 vs 2.0+ projects
            expected_note = "rebuilding project" if check_history_table_before else "project updated successfully"
            assert expected_note in record["notes"]
        else:
            sql_scripts_applied.append(record["notes"])

    return sql_scripts_applied


def verify_sql_scripts_applied(sql_scripts_applied: list, project_version: str) -> None:
    """Verify that expected SQL migration scripts were applied.

    Args:
        sql_scripts_applied: List of applied SQL script names from history
        project_version: Original project version before update
    """
    expected_scripts = [script for version, script in DB_MIGRATION_SCRIPTS.items() if version > project_version]
    assert len(expected_scripts) == len(sql_scripts_applied)

    if len(expected_scripts) > 0:
        notes_str = " ".join(sql_scripts_applied)
        for script_file in expected_scripts:
            assert script_file in notes_str


def test_update_project_from_0_7(plugin, qgis_iface, prj_manager, base_project_path_0_7, monkeypatch):
    """Test updating a project from version 0.7 to the current version."""
    plugin_instance = plugin(qgis_iface)

    # Setup test environment
    project, project_file = setup_test_environment(plugin_instance, qgis_iface, base_project_path_0_7, monkeypatch)

    # Check initial project state
    plugin_instance.check_project()
    project_version = prj_manager.project_version
    assert project_version == "0.7"
    assert prj_manager.is_mzs_project is True
    assert prj_manager.project_updateable is True
    # verify db < 2.0.0 has no history table
    assert prj_manager.db.table_exists("mzs_tools_update_history") is False

    # Perform update
    perform_update(plugin_instance, project, project_file, qgis_iface, monkeypatch)

    # Verify update results
    assert prj_manager.project_updateable is False
    assert prj_manager.project_version == __base_version__

    # Verify update history and SQL scripts
    sql_scripts_applied = verify_update_history(prj_manager, project_version, check_history_table_before=True)
    verify_sql_scripts_applied(sql_scripts_applied, project_version)


def test_update_project_from_1_0(plugin, qgis_iface, prj_manager, base_project_path_1_0, monkeypatch):
    """Test updating a project from version 1.0 to the current version."""
    plugin_instance = plugin(qgis_iface)

    # Setup test environment
    project, project_file = setup_test_environment(plugin_instance, qgis_iface, base_project_path_1_0, monkeypatch)

    # Check initial project state
    plugin_instance.check_project()
    project_version = prj_manager.project_version
    assert project_version == "1.0"
    assert prj_manager.is_mzs_project is True
    assert prj_manager.project_updateable is True
    # verify db < 2.0.0 has no history table
    assert prj_manager.db.table_exists("mzs_tools_update_history") is False

    # Perform update
    perform_update(plugin_instance, project, project_file, qgis_iface, monkeypatch)

    # Verify update results
    assert prj_manager.project_updateable is False
    assert prj_manager.project_version == __base_version__

    # Verify update history and SQL scripts
    sql_scripts_applied = verify_update_history(prj_manager, project_version, check_history_table_before=True)
    verify_sql_scripts_applied(sql_scripts_applied, project_version)


def test_update_project_from_1_5(plugin, qgis_iface, prj_manager, base_project_path_1_5, monkeypatch):
    """Test updating a project from version 1.5 to the current version."""
    plugin_instance = plugin(qgis_iface)

    # Setup test environment
    project, project_file = setup_test_environment(plugin_instance, qgis_iface, base_project_path_1_5, monkeypatch)

    # Check initial project state
    plugin_instance.check_project()
    project_version = prj_manager.project_version
    assert project_version == "1.5"
    assert prj_manager.is_mzs_project is True
    assert prj_manager.project_updateable is True
    # verify db < 2.0.0 has no history table
    assert prj_manager.db.table_exists("mzs_tools_update_history") is False

    # Perform update
    perform_update(plugin_instance, project, project_file, qgis_iface, monkeypatch)

    # Verify update results
    assert prj_manager.project_updateable is False
    assert prj_manager.project_version == __base_version__

    # Verify update history and SQL scripts
    sql_scripts_applied = verify_update_history(prj_manager, project_version, check_history_table_before=True)
    verify_sql_scripts_applied(sql_scripts_applied, project_version)


def test_update_project_from_1_9_4(plugin, qgis_iface, prj_manager, base_project_path_1_9_4, monkeypatch):
    """Test updating a project from version 1.9.4 to the current version."""
    plugin_instance = plugin(qgis_iface)

    # Setup test environment
    project, project_file = setup_test_environment(plugin_instance, qgis_iface, base_project_path_1_9_4, monkeypatch)

    # Check initial project state
    plugin_instance.check_project()
    project_version = prj_manager.project_version
    assert project_version == "1.9.4"
    assert prj_manager.is_mzs_project is True
    assert prj_manager.project_updateable is True
    # verify db < 2.0.0 has no history table
    assert prj_manager.db.table_exists("mzs_tools_update_history") is False

    # Perform update
    perform_update(plugin_instance, project, project_file, qgis_iface, monkeypatch)

    # Verify update results
    assert prj_manager.project_updateable is False
    assert prj_manager.project_version == __base_version__

    # Verify update history and SQL scripts
    sql_scripts_applied = verify_update_history(prj_manager, project_version, check_history_table_before=True)
    verify_sql_scripts_applied(sql_scripts_applied, project_version)


def test_update_project_from_1_9_4_with_data(
    plugin, qgis_iface, prj_manager, base_project_path_1_9_4_imported, monkeypatch
):
    """Test updating a project from version 1.9.4 to the current version with data."""
    plugin_instance = plugin(qgis_iface)

    # Setup test environment
    project, project_file = setup_test_environment(
        plugin_instance, qgis_iface, base_project_path_1_9_4_imported, monkeypatch
    )

    # Check initial project state
    plugin_instance.check_project()
    project_version = prj_manager.project_version
    assert project_version == "1.9.4"
    assert prj_manager.is_mzs_project is True
    assert prj_manager.project_updateable is True
    # verify db < 2.0.0 has no history table
    assert prj_manager.db.table_exists("mzs_tools_update_history") is False

    # Perform update
    perform_update(plugin_instance, project, project_file, qgis_iface, monkeypatch)

    # Verify update results
    assert prj_manager.project_updateable is False
    assert prj_manager.project_version == __base_version__

    # Verify update history and SQL scripts
    sql_scripts_applied = verify_update_history(prj_manager, project_version, check_history_table_before=True)
    verify_sql_scripts_applied(sql_scripts_applied, project_version)

    # TODO: verify data


def test_update_project_from_2_0_0(plugin, qgis_iface, prj_manager, base_project_path_2_0_0, monkeypatch):
    """Test updating a project from version 2.0.5 to the current version."""
    plugin_instance = plugin(qgis_iface)

    # Setup test environment (no addProject mock needed for 2.0+ projects)
    project_file = base_project_path_2_0_0 / "progetto_MS.qgz"
    project = QgsProject.instance()
    monkeypatch.setattr(plugin_instance, "show_project_update_dialog", lambda: None, raising=False)

    # Disable rendering to prevent crashes
    disable_rendering(project, qgis_iface)
    project.read(str(project_file))

    # Check initial project state
    plugin_instance.check_project()
    project_version = prj_manager.project_version
    assert project_version == "2.0.0"
    assert prj_manager.is_mzs_project is True
    assert prj_manager.project_updateable is True

    # Perform update (no project reload needed for 2.0+ projects)
    perform_update(plugin_instance, project, project_file, qgis_iface, monkeypatch, reload_project=False)

    # Verify update results
    assert prj_manager.project_updateable is False
    assert prj_manager.project_version == __base_version__

    # Verify update history and SQL scripts
    sql_scripts_applied = verify_update_history(prj_manager, project_version, check_history_table_before=False)
    verify_sql_scripts_applied(sql_scripts_applied, project_version)


def test_update_project_from_2_0_5(plugin, qgis_iface, prj_manager, base_project_path_2_0_5, monkeypatch):
    """Test updating a project from version 2.0.5 to the current version."""
    plugin_instance = plugin(qgis_iface)

    # Setup test environment (no addProject mock needed for 2.0+ projects)
    project_file = base_project_path_2_0_5 / "progetto_MS.qgz"
    project = QgsProject.instance()
    monkeypatch.setattr(plugin_instance, "show_project_update_dialog", lambda: None, raising=False)

    # Disable rendering to prevent crashes
    disable_rendering(project, qgis_iface)
    project.read(str(project_file))

    # Check initial project state
    plugin_instance.check_project()
    project_version = prj_manager.project_version
    assert project_version == "2.0.5"
    assert prj_manager.is_mzs_project is True
    assert prj_manager.project_updateable is True

    # Perform update (no project reload needed for 2.0+ projects)
    perform_update(plugin_instance, project, project_file, qgis_iface, monkeypatch, reload_project=False)

    # Verify update results
    assert prj_manager.project_updateable is False
    assert prj_manager.project_version == __base_version__

    # Verify update history and SQL scripts
    sql_scripts_applied = verify_update_history(prj_manager, project_version, check_history_table_before=False)
    verify_sql_scripts_applied(sql_scripts_applied, project_version)
