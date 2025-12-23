from unittest.mock import Mock

from qgis.PyQt.QtWidgets import QMessageBox

from mzs_tools.gui.dlg_create_project import DlgCreateProject


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


def test_open_dlg_create_project(plugin, qgis_iface, monkeypatch, qgis_new_project):
    """Test the open_dlg_create_project action callback."""
    plugin_instance = plugin(qgis_iface)

    # simulate user cancelling the dialog
    # monkeypatch the exec method of the dialog and return False
    monkeypatch.setattr(DlgCreateProject, "exec", lambda self: False)
    monkeypatch.setattr(plugin_instance.prj_manager, "create_project", Mock())
    plugin_instance.open_dlg_create_project()
    assert plugin_instance.dlg_create_project is not None
    # create_project should not be called
    plugin_instance.prj_manager.create_project.assert_not_called()

    # simulate user accepting the dialog
    # monkeypatch the exec method of the dialog and return True
    monkeypatch.setattr(DlgCreateProject, "exec", lambda self: True)
    plugin_instance.open_dlg_create_project()
    assert plugin_instance.dlg_create_project is not None
    # create_project should be called once
    plugin_instance.prj_manager.create_project.assert_called_once()

    # if import_data is True, dependency_manager.check_python_dependencies() should be called
    monkeypatch.setattr(plugin_instance, "dependency_manager", Mock())
    # prevent QmessageBox from blocking the test
    monkeypatch.setattr(QMessageBox, "information", lambda *args, **kwargs: None)
    # prevent import dialog from opening
    monkeypatch.setattr(plugin_instance, "open_dlg_import_data", Mock())
    plugin_instance.open_dlg_create_project(import_data=True)
    plugin_instance.dependency_manager.check_python_dependencies.assert_called_once()
    # open_dlg_import_data should be called once
    plugin_instance.open_dlg_import_data.assert_called_once()

    # simulate an exception in create_project
    def raise_exception(*args, **kwargs):
        raise Exception("Test exception")

    monkeypatch.setattr(plugin_instance.prj_manager, "create_project", raise_exception)
    # prevent QmessageBox from blocking the test
    monkeypatch.setattr(QMessageBox, "critical", lambda *args, **kwargs: None)
    plugin_instance.open_dlg_create_project()
    assert plugin_instance.dlg_create_project is not None
