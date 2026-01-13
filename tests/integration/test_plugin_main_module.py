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

from pathlib import Path
from unittest.mock import Mock

from qgis.PyQt.QtWidgets import QFileDialog, QMessageBox

from mzs_tools.gui.dlg_create_project import DlgCreateProject
from mzs_tools.gui.dlg_metadata_edit import DlgMetadataEdit


def test_add_action_method(plugin, qgis_iface, qgis_app):
    """Test the add_action method."""
    plugin_instance = plugin(qgis_iface)

    # Mock callback
    mock_callback = Mock()

    # Add an action
    action = plugin_instance.add_action(
        icon_path=qgis_app.getThemeIcon("mActionHelp.svg"),
        text="Test Action",
        whats_this="This is a test action",
        callback=mock_callback,
        enabled_flag=True,
        add_to_menu=False,  # Don't add to menu for test
        add_to_toolbar=True,
    )

    # Verify action was created
    assert action is not None
    assert action.text() == "Test Action"
    assert action.isEnabled() is True
    # Verify action was added to toolbar (when add_to_toolbar=True)
    toolbar_actions = plugin_instance.toolbar.actions()
    assert action in toolbar_actions


def test_on_new_project_action(plugin, qgis_iface, monkeypatch, qgis_new_project):
    """Test the on_new_project_action action callback."""
    plugin_instance = plugin(qgis_iface)

    # simulate user cancelling the dialog
    # monkeypatch the exec method of the dialog and return False
    monkeypatch.setattr(DlgCreateProject, "exec", lambda self: False)
    monkeypatch.setattr(plugin_instance.prj_manager, "create_project", Mock())
    plugin_instance.on_new_project_action()
    assert plugin_instance.dlg_create_project is not None
    # create_project should not be called
    plugin_instance.prj_manager.create_project.assert_not_called()

    # simulate user accepting the dialog
    # monkeypatch the exec method of the dialog and return True
    monkeypatch.setattr(DlgCreateProject, "exec", lambda self: True)
    plugin_instance.on_new_project_action()
    assert plugin_instance.dlg_create_project is not None
    # create_project should be called once
    plugin_instance.prj_manager.create_project.assert_called_once()

    # if import_data is True, dependency_manager.check_python_dependencies() should be called
    monkeypatch.setattr(plugin_instance, "dependency_manager", Mock())
    # prevent QmessageBox from blocking the test
    monkeypatch.setattr(QMessageBox, "information", lambda *args, **kwargs: None)
    # prevent import dialog from opening
    monkeypatch.setattr(plugin_instance, "on_import_data_action", Mock())
    plugin_instance.on_new_project_action(import_data=True)
    plugin_instance.dependency_manager.check_python_dependencies.assert_called_once()
    # on_import_data_action should be called once
    plugin_instance.on_import_data_action.assert_called_once()

    # simulate an exception in create_project
    def raise_exception(*args, **kwargs):
        raise Exception("Test exception")

    monkeypatch.setattr(plugin_instance.prj_manager, "create_project", raise_exception)
    # prevent QmessageBox from blocking the test
    monkeypatch.setattr(QMessageBox, "critical", lambda *args, **kwargs: None)
    plugin_instance.on_new_project_action()
    assert plugin_instance.dlg_create_project is not None


def test_on_export_data_action(plugin, qgis_iface, monkeypatch):
    """Test the on_export_data_action action callback."""
    plugin_instance = plugin(qgis_iface)

    # monkeypatch the DlgExportData to prevent opening the actual dialog
    monkeypatch.setattr(plugin_instance, "dlg_export_data", Mock(spec=plugin_instance.dlg_export_data))

    # simulate all dependencies are met
    monkeypatch.setattr(plugin_instance.dependency_manager, "check_python_dependencies", lambda: True)

    # dialog should not be opened if no mzs tools project is loaded
    monkeypatch.setattr(plugin_instance.prj_manager, "is_mzs_project", False)
    plugin_instance.on_export_data_action()
    plugin_instance.dlg_export_data.exec.assert_not_called()

    monkeypatch.setattr(plugin_instance.prj_manager, "is_mzs_project", True)
    plugin_instance.on_export_data_action()
    plugin_instance.dlg_export_data.exec.assert_called_once()


def test_on_import_data_action(plugin, qgis_iface, monkeypatch):
    """Test the on_import_data_action action callback."""
    plugin_instance = plugin(qgis_iface)

    # monkeypatch the DlgImportData to prevent opening the actual dialog
    monkeypatch.setattr(plugin_instance, "dlg_import_data", Mock(spec=plugin_instance.dlg_import_data))

    # simulate all dependencies are met
    monkeypatch.setattr(plugin_instance.dependency_manager, "check_python_dependencies", lambda: True)

    # dialog should not be opened if no mzs tools project is loaded
    monkeypatch.setattr(plugin_instance.prj_manager, "is_mzs_project", False)
    plugin_instance.on_import_data_action()
    plugin_instance.dlg_import_data.exec.assert_not_called()

    # simulate a project with no indagini data
    def mock_count_indagini_data(mock_count=0):
        tables = [
            "sito_puntuale",
            "indagini_puntuali",
            "parametri_puntuali",
            "curve",
            "sito_lineare",
            "indagini_lineari",
            "parametri_lineari",
        ]

        result = {}
        for table in tables:
            result[table] = [mock_count, mock_count]
        return result

    monkeypatch.setattr(plugin_instance.prj_manager, "count_indagini_data", lambda x=0: mock_count_indagini_data(x))
    monkeypatch.setattr(plugin_instance.prj_manager, "is_mzs_project", True)
    plugin_instance.on_import_data_action()
    plugin_instance.dlg_import_data.exec.assert_called_once()

    # simulate a project with some indagini data
    monkeypatch.setattr(plugin_instance.prj_manager, "count_indagini_data", lambda x=10: mock_count_indagini_data(x))
    # monkeypatch QMessageBox to prevent blocking the test
    monkeypatch.setattr(QMessageBox, "warning", lambda *args, **kwargs: None)
    plugin_instance.on_import_data_action()

    # when missing dependencies, _show_missing_dependencies_dialog should be called
    monkeypatch.setattr(plugin_instance.dependency_manager, "check_python_dependencies", lambda: False)
    monkeypatch.setattr(plugin_instance, "_show_missing_dependencies_dialog", Mock())
    plugin_instance.on_import_data_action()
    plugin_instance._show_missing_dependencies_dialog.assert_called_once()


def test_on_add_default_layers_action(plugin, qgis_iface, monkeypatch):
    """Test the on_add_default_layers_action action callback."""
    plugin_instance = plugin(qgis_iface)

    # monkeypatch the DlgExportData to prevent opening the actual dialog
    monkeypatch.setattr(plugin_instance, "dlg_fix_layers", Mock())

    # dialog should not be opened if no mzs tools project is loaded
    monkeypatch.setattr(plugin_instance.prj_manager, "is_mzs_project", False)
    plugin_instance.on_add_default_layers_action()
    plugin_instance.dlg_fix_layers.exec.assert_not_called()

    monkeypatch.setattr(plugin_instance.prj_manager, "is_mzs_project", True)
    plugin_instance.on_add_default_layers_action()
    plugin_instance.dlg_fix_layers.exec.assert_called_once()


def test_on_help_action(plugin, qgis_iface, monkeypatch):
    """Test the on_help_action action callback."""
    plugin_instance = plugin(qgis_iface)

    # monkeypatch the DlgPluginInfo to prevent opening the actual dialog
    monkeypatch.setattr(plugin_instance, "dlg_plugin_info", Mock())

    plugin_instance.on_help_action()
    plugin_instance.dlg_plugin_info.exec.assert_called_once()


def test_on_load_ogc_services_action(plugin, qgis_iface, monkeypatch):
    """Test the on_load_ogc_services_action action callback."""
    plugin_instance = plugin(qgis_iface)

    # monkeypatch the DlgLoadOGCServices to prevent opening the actual dialog
    monkeypatch.setattr(plugin_instance, "dlg_load_ogc_services", Mock())

    plugin_instance.on_load_ogc_services_action()
    plugin_instance.dlg_load_ogc_services.exec.assert_called_once()


def test_on_edit_metadata_action(plugin, qgis_iface, monkeypatch):
    """Test the on_edit_metadata_action action callback."""
    plugin_instance = plugin(qgis_iface)

    # simulate no mzs tools project loaded
    monkeypatch.setattr(plugin_instance.prj_manager, "is_mzs_project", False)
    plugin_instance.on_edit_metadata_action()
    assert plugin_instance.dlg_metadata_edit is None

    # simulate mzs tools project loaded
    monkeypatch.setattr(plugin_instance.prj_manager, "is_mzs_project", True)

    # monkeypatch the DlgMetadataEdit to prevent opening the actual dialog
    monkeypatch.setattr(plugin_instance, "dlg_metadata_edit", None)
    monkeypatch.setattr(DlgMetadataEdit, "__init__", lambda self, parent: None)
    monkeypatch.setattr(DlgMetadataEdit, "exec", lambda self: True)
    monkeypatch.setattr(DlgMetadataEdit, "save_data", Mock())

    plugin_instance.on_edit_metadata_action()
    assert plugin_instance.dlg_metadata_edit is not None
    plugin_instance.dlg_metadata_edit.save_data.assert_called_once()


def test_on_dependency_manager_action(plugin, qgis_iface, monkeypatch):
    """Test the on_dependency_manager_action action callback."""
    plugin_instance = plugin(qgis_iface)

    # Mock check_mdb_connection with successful result
    mock_result = {"deps_ok": True, "jvm_ok": True, "connected": True}
    monkeypatch.setattr("mzs_tools.mzs_tools.check_mdb_connection", lambda x: mock_result)
    monkeypatch.setattr(QMessageBox, "information", lambda *args, **kwargs: None)

    plugin_instance.on_dependency_manager_action()
    # Should call QMessageBox.information for success

    # Mock check_mdb_connection with failed connection
    mock_result = {"deps_ok": True, "jvm_ok": True, "connected": False}
    monkeypatch.setattr("mzs_tools.mzs_tools.check_mdb_connection", lambda x: mock_result)
    monkeypatch.setattr(QMessageBox, "warning", lambda *args, **kwargs: None)

    plugin_instance.on_dependency_manager_action()
    # Should call QMessageBox.warning for failure

    # Mock check_mdb_connection with missing dependencies
    mock_result = {"deps_ok": False, "jvm_ok": False, "connected": False}
    monkeypatch.setattr("mzs_tools.mzs_tools.check_mdb_connection", lambda x: mock_result)
    monkeypatch.setattr(plugin_instance.dependency_manager, "install_python_dependencies", Mock())

    plugin_instance.on_dependency_manager_action()
    # Should call install_python_dependencies when deps_ok is False
    plugin_instance.dependency_manager.install_python_dependencies.assert_called_once_with(interactive=True)


def test_on_check_attachments_action(plugin, qgis_iface, monkeypatch):
    """Test the on_check_attachments_action action callback."""
    plugin_instance = plugin(qgis_iface)

    # Dialog should not be opened if no mzs tools project is loaded
    monkeypatch.setattr(plugin_instance.prj_manager, "is_mzs_project", False)
    mock_dialog_init = Mock()
    monkeypatch.setattr("mzs_tools.mzs_tools.DlgManageAttachments", mock_dialog_init)
    plugin_instance.on_check_attachments_action()
    # DlgManageAttachments should not be instantiated
    mock_dialog_init.assert_not_called()

    # Dialog should be opened if mzs tools project is loaded
    monkeypatch.setattr(plugin_instance.prj_manager, "is_mzs_project", True)
    mock_dialog = Mock()
    mock_dialog_init = Mock(return_value=mock_dialog)
    monkeypatch.setattr("mzs_tools.mzs_tools.DlgManageAttachments", mock_dialog_init)

    plugin_instance.on_check_attachments_action()
    # DlgManageAttachments should be instantiated and exec called
    mock_dialog_init.assert_called_once()
    mock_dialog.exec.assert_called_once()


def test_on_backup_project_action(plugin, qgis_iface, monkeypatch, tmp_path):
    """Test the on_backup_project_action action callback."""
    plugin_instance = plugin(qgis_iface)

    # Action should not run if no mzs tools project is loaded
    monkeypatch.setattr(plugin_instance.prj_manager, "is_mzs_project", False)
    monkeypatch.setattr(plugin_instance.prj_manager, "backup_project", Mock())
    plugin_instance.on_backup_project_action()
    # Should return early without calling backup_project
    plugin_instance.prj_manager.backup_project.assert_not_called()

    # Simulate user cancelling the file dialog
    monkeypatch.setattr(plugin_instance.prj_manager, "is_mzs_project", True)
    project_path = tmp_path / "test_project"
    project_path.mkdir()
    monkeypatch.setattr(plugin_instance.prj_manager, "project_path", project_path)
    monkeypatch.setattr(QFileDialog, "getExistingDirectory", lambda *args, **kwargs: "")
    plugin_instance.on_backup_project_action()
    plugin_instance.prj_manager.backup_project.assert_not_called()

    # Simulate user selecting the same directory as the project
    monkeypatch.setattr(QFileDialog, "getExistingDirectory", lambda *args, **kwargs: str(project_path))
    monkeypatch.setattr(QMessageBox, "warning", lambda *args, **kwargs: None)
    plugin_instance.on_backup_project_action()
    # backup_project should not be called when selecting same directory

    # Simulate user selecting a directory that contains an existing MzS project
    existing_mzs_dir = tmp_path / "existing_mzs_project"
    existing_mzs_dir.mkdir()
    (existing_mzs_dir / "db").mkdir()
    (existing_mzs_dir / "db" / "indagini.sqlite").touch()
    monkeypatch.setattr(QFileDialog, "getExistingDirectory", lambda *args, **kwargs: str(existing_mzs_dir))
    plugin_instance.on_backup_project_action()
    # backup_project should not be called when directory contains existing project

    # Simulate successful backup
    backup_dir = tmp_path / "backup"
    backup_dir.mkdir()
    monkeypatch.setattr(QFileDialog, "getExistingDirectory", lambda *args, **kwargs: str(backup_dir))
    monkeypatch.setattr(plugin_instance.prj_manager, "backup_project", Mock(return_value=backup_dir / "backup"))
    plugin_instance.on_backup_project_action()
    plugin_instance.prj_manager.backup_project.assert_called_once_with(Path(str(backup_dir)))

    # Simulate exception during backup
    def raise_exception(*args, **kwargs):
        raise Exception("Test exception")

    monkeypatch.setattr(plugin_instance.prj_manager, "backup_project", raise_exception)
    monkeypatch.setattr(QMessageBox, "critical", lambda *args, **kwargs: None)
    plugin_instance.on_backup_project_action()
    # Should handle exception gracefully


def test_on_backup_db_action(plugin, qgis_iface, monkeypatch, tmp_path):
    """Test the on_backup_db_action action callback."""
    plugin_instance = plugin(qgis_iface)

    # Action should not run if no mzs tools project is loaded
    monkeypatch.setattr(plugin_instance.prj_manager, "is_mzs_project", False)
    monkeypatch.setattr(plugin_instance.prj_manager, "backup_database", Mock())
    plugin_instance.on_backup_db_action()
    plugin_instance.prj_manager.backup_database.assert_not_called()

    # Simulate successful backup
    monkeypatch.setattr(plugin_instance.prj_manager, "is_mzs_project", True)
    backup_path = tmp_path / "backup.sqlite"
    monkeypatch.setattr(plugin_instance.prj_manager, "backup_database", Mock(return_value=backup_path))
    plugin_instance.on_backup_db_action()
    plugin_instance.prj_manager.backup_database.assert_called_once()

    # Simulate exception during backup
    def raise_exception(*args, **kwargs):
        raise Exception("Test exception")

    monkeypatch.setattr(plugin_instance.prj_manager, "backup_database", raise_exception)
    monkeypatch.setattr(QMessageBox, "critical", lambda *args, **kwargs: None)
    plugin_instance.on_backup_db_action()
    # Should handle exception gracefully


def test_on_load_default_print_layouts_action(plugin, qgis_iface, monkeypatch):
    """Test the on_load_default_print_layouts_action action callback."""
    plugin_instance = plugin(qgis_iface)

    # Action should not run if no mzs tools project is loaded
    monkeypatch.setattr(plugin_instance.prj_manager, "is_mzs_project", False)
    monkeypatch.setattr(plugin_instance.prj_manager, "load_print_layouts", Mock())
    plugin_instance.on_load_default_print_layouts_action()
    plugin_instance.prj_manager.load_print_layouts.assert_not_called()

    # Simulate user declining the confirmation dialog
    monkeypatch.setattr(plugin_instance.prj_manager, "is_mzs_project", True)
    monkeypatch.setattr(QMessageBox, "question", lambda *args, **kwargs: QMessageBox.StandardButton.No)
    plugin_instance.on_load_default_print_layouts_action()
    plugin_instance.prj_manager.load_print_layouts.assert_not_called()

    # Simulate user accepting the confirmation dialog
    monkeypatch.setattr(QMessageBox, "question", lambda *args, **kwargs: QMessageBox.StandardButton.Yes)
    monkeypatch.setattr(plugin_instance.prj_manager, "backup_print_layouts", Mock())
    plugin_instance.on_load_default_print_layouts_action()
    plugin_instance.prj_manager.backup_print_layouts.assert_called_once_with(
        backup_label="backup", backup_timestamp=True
    )
    plugin_instance.prj_manager.load_print_layouts.assert_called_once()


def test_on_check_project_action(plugin, qgis_iface, monkeypatch):
    """Test the on_check_project_action action callback."""
    plugin_instance = plugin(qgis_iface)

    # Action should not run if no mzs tools project is loaded
    monkeypatch.setattr(plugin_instance.prj_manager, "is_mzs_project", False)
    monkeypatch.setattr(plugin_instance.prj_manager, "check_project_structure", Mock())
    plugin_instance.on_check_project_action()
    # Should return early without calling check_project_structure
    plugin_instance.prj_manager.check_project_structure.assert_not_called()

    # Set up for MzS project loaded
    monkeypatch.setattr(plugin_instance.prj_manager, "is_mzs_project", True)

    # Test with no project issues - should show information message
    plugin_instance.prj_manager.project_issues = []

    # Mock check_project_structure to do nothing (avoid actual implementation)
    monkeypatch.setattr(plugin_instance.prj_manager, "check_project_structure", lambda: None)
    mock_info = Mock()
    monkeypatch.setattr(QMessageBox, "information", mock_info)

    plugin_instance.on_check_project_action()
    # Verify information message was shown when no issues
    mock_info.assert_called_once()

    # Test with project issues - should call report_project_issues
    plugin_instance.prj_manager.project_issues = ["Issue 1", "Issue 2"]

    monkeypatch.setattr(plugin_instance.prj_manager, "check_project_structure", lambda: None)
    mock_report = Mock()
    monkeypatch.setattr(plugin_instance, "report_project_issues", mock_report)

    plugin_instance.on_check_project_action()
    # Verify report_project_issues was called when there are issues
    mock_report.assert_called_once()
