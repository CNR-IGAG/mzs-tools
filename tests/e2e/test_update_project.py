from unittest.mock import Mock

import pytest
from pytest_qgis import MockMessageBar
from qgis.core import QgsProject

from mzs_tools.__about__ import __base_version__


@pytest.mark.skip("Not implemented yet")
def test_update_project_from_1x(
    qtbot,
    plugin,
    qgis_iface,
    monkeypatch,
):
    """Test updating a project from version 1.x to the current version."""
    pass


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

    assert plugin_instance.prj_manager.is_mzs_project is True
    assert plugin_instance.prj_manager.project_updateable is True

    monkeypatch.setattr(MockMessageBar, "clearWidgets", lambda x: None, raising=False)
    monkeypatch.setattr(MockMessageBar, "createMessage", lambda x, y, z: Mock(), raising=False)
    monkeypatch.setattr(MockMessageBar, "pushWidget", lambda x, y, z: Mock(), raising=False)
    monkeypatch.setattr(MockMessageBar, "popWidget", lambda x, y: Mock(), raising=False)

    plugin_instance.update_current_project()

    assert plugin_instance.prj_manager.project_updateable is False
    assert plugin_instance.prj_manager.project_version == __base_version__

    project.clear()
