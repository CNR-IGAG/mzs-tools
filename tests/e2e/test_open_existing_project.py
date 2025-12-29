"""
Tests for opening and updating existing MzS Tools projects
"""

import zipfile
from pathlib import Path
from unittest.mock import Mock

from pytest_qgis import MockMessageBar
from qgis.core import QgsProject

from mzs_tools.__about__ import __base_version__


def test_open_existing_project(plugin, qgis_app, qgis_iface, qgis_new_project, tmp_path, monkeypatch):
    """
    Test opening an existing QGIS project and verifying its contents.
    """
    plugin_instance = plugin(qgis_iface)

    # Extract the project from zip archive in tests/data directory
    project_archive = Path(__file__).parent.parent / "data" / "mzs_projects" / "095014_Bidonì_v2.0.5.zip"
    with zipfile.ZipFile(project_archive, "r") as zip_ref:
        zip_ref.extractall(tmp_path)

    project_file = tmp_path / "095014_Bidonì" / "progetto_MS.qgz"

    # Create a new project
    project = QgsProject.instance()

    # simulate already updated project by changing versione.txt
    versione_file = project_file.parent / "progetto" / "versione.txt"
    versione_file.write_text("2.0.6")

    # open the project
    project.read(str(project_file))

    # patch show_project_update_dialog
    monkeypatch.setattr(plugin_instance, "show_project_update_dialog", lambda: None, raising=False)

    # manually run check_project as qgis_iface lacks projectRead signal
    # this will initialize the plugin's project manager
    # prj_manager.init_manager()
    plugin_instance.check_project()

    assert plugin_instance.prj_manager.is_mzs_project is True
    assert plugin_instance.prj_manager.project_updateable is False

    # Verify that the layer is present in the reopened project
    layers = project.mapLayers().values()
    layer_names = [lyr.name() for lyr in layers]
    assert "Comune del progetto" in layer_names, "Layer not found in reopened project!"

    versione_file.write_text("2.0.5")

    project.clear()

    project.read(str(project_file))
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
