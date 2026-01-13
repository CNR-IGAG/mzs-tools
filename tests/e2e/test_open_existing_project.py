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

from unittest.mock import Mock

from qgis.core import QgsProject
from qgis.PyQt.QtWidgets import QMessageBox

from mzs_tools.__about__ import __base_version__


def test_open_existing_project_current(plugin, qgis_iface, prj_manager, base_project_path_current):
    """
    Test opening an existing QGIS project and verifying its contents.
    """
    plugin_instance = plugin(qgis_iface)

    project_file = base_project_path_current / "progetto_MS.qgz"

    # Create a new project
    project = QgsProject.instance()

    # open the project
    project.read(str(project_file))

    # manually run check_project as qgis_iface lacks projectRead signal
    # this will initialize the plugin's project manager - prj_manager.init_manager()
    plugin_instance.check_project()

    assert prj_manager.is_mzs_project is True
    assert prj_manager.project_updateable is False
    assert prj_manager.project_version == __base_version__

    # check_project() -> init_manager() -> check_project_structure()
    # this verifies that required layers, relations, etc. are present
    # the final report should be empty for a valid updated project
    assert prj_manager.project_issues == {}

    # Optionally, verify specific layers or data in the project
    layers = project.mapLayers().values()
    layer_names = [lyr.name() for lyr in layers]
    assert "Comune del progetto" in layer_names, "Layer not found in reopened project!"


def test_open_existing_project_2_0_5(plugin, qgis_iface, prj_manager, base_project_path_2_0_5, monkeypatch, qtbot):
    """
    Test opening an existing QGIS project created with an older version of the plugin.
    """
    plugin_instance = plugin(qgis_iface)

    project_file = base_project_path_2_0_5 / "progetto_MS.qgz"

    # Create a new project
    project = QgsProject.instance()

    # open the project
    project.read(str(project_file))

    # patch show_project_update_dialog
    monkeypatch.setattr(plugin_instance, "show_project_update_dialog", Mock(), raising=False)

    # manually run check_project as qgis_iface lacks projectRead signal
    # this will initialize the plugin's project manager - prj_manager.init_manager()
    plugin_instance.check_project()

    assert prj_manager.is_mzs_project is True
    assert prj_manager.project_updateable is True
    assert prj_manager.project_version == "2.0.5"

    # an outdated 2.x project should not have issues
    assert prj_manager.project_issues == {}
    # Verify that the update dialog was shown; a QTimer.singleShot is used to delay the dialog call
    # after opening the project, so we need to wait for it
    qtbot.waitUntil(lambda: plugin_instance.show_project_update_dialog.called, timeout=5000)
    plugin_instance.show_project_update_dialog.assert_called_once()


def test_open_existing_project_2_0_0(plugin, qgis_iface, prj_manager, base_project_path_2_0_0, monkeypatch, qtbot):
    """
    Test opening an existing QGIS project created with an older version of the plugin.
    """
    plugin_instance = plugin(qgis_iface)

    project_file = base_project_path_2_0_0 / "progetto_MS.qgz"

    # Create a new project
    project = QgsProject.instance()

    # open the project
    project.read(str(project_file))

    # patch show_project_update_dialog
    monkeypatch.setattr(plugin_instance, "show_project_update_dialog", Mock(), raising=False)

    # manually run check_project as qgis_iface lacks projectRead signal
    # this will initialize the plugin's project manager - prj_manager.init_manager()
    plugin_instance.check_project()

    assert prj_manager.is_mzs_project is True
    assert prj_manager.project_updateable is True
    assert prj_manager.project_version == "2.0.0"

    # an outdated 2.x project should not have issues
    assert prj_manager.project_issues == {}
    # Verify that the update dialog was shown; a QTimer.singleShot is used to delay the dialog call
    # after opening the project, so we need to wait for it
    qtbot.waitUntil(lambda: plugin_instance.show_project_update_dialog.called, timeout=5000)
    plugin_instance.show_project_update_dialog.assert_called_once()


def test_open_existing_project_0_7(plugin, qgis_iface, prj_manager, base_project_path_0_7, monkeypatch, qtbot):
    """
    Test opening an existing QGIS project created with an older version of the plugin.
    """
    plugin_instance = plugin(qgis_iface)

    project_file = base_project_path_0_7 / "progetto_MS.qgz"

    # Create a new project
    project = QgsProject.instance()

    # open the project
    project.read(str(project_file))

    # patch show_project_update_dialog
    monkeypatch.setattr(plugin_instance, "show_project_update_dialog", Mock(), raising=False)

    # manually run check_project as qgis_iface lacks projectRead signal
    # this will initialize the plugin's project manager - prj_manager.init_manager()
    plugin_instance.check_project()

    assert prj_manager.is_mzs_project is True
    assert prj_manager.project_updateable is True
    assert prj_manager.project_version == "0.7"

    # opening an outdated < 2.0.0 project should report multiple issues
    assert prj_manager.project_issues != {}
    # Verify that the update dialog was shown; a QTimer.singleShot is used to delay the dialog call
    # after opening the project, so we need to wait for it
    qtbot.waitUntil(lambda: plugin_instance.show_project_update_dialog.called, timeout=5000)
    plugin_instance.show_project_update_dialog.assert_called_once()


def test_open_existing_project_with_issues(plugin, qgis_iface, prj_manager, base_project_path_current, monkeypatch):
    """
    Test opening an existing QGIS project with (simulated) issues.
    """
    plugin_instance = plugin(qgis_iface)

    project_file = base_project_path_current / "progetto_MS.qgz"

    # Create a new project
    project = QgsProject.instance()

    # open the project
    project.read(str(project_file))

    # Remove a required layer to simulate an issue
    layers = project.mapLayers().values()
    layer_to_remove = None
    for lyr in layers:
        if lyr.name() == "Siti puntuali":
            layer_to_remove = lyr
            break
    if layer_to_remove:
        project.removeMapLayer(layer_to_remove.id())

    # Patch QMessageBox to prevent actual dialog during tests
    monkeypatch.setattr(QMessageBox, "exec", Mock(), raising=False)

    # manually run check_project as qgis_iface lacks projectRead signal
    # this will initialize the plugin's project manager - prj_manager.init_manager()
    plugin_instance.check_project()

    assert prj_manager.is_mzs_project is True
    assert prj_manager.project_updateable is False

    # check_project() -> init_manager() -> check_project_structure()
    # this verifies that required layers, relations, etc. are present
    # check the issues dict is not empty
    assert prj_manager.project_issues != {}
    # expect specific issues about missing layers/relations
    assert len(prj_manager.project_issues.get("layers", [])) > 0
    assert len(prj_manager.project_issues.get("project", [])) > 0
    assert "sito_puntuale" in prj_manager.project_issues.get("layers", [])[0], "Missing layer issue not detected!"
    assert "siti_indagini_puntuali" in prj_manager.project_issues.get("project", [])[0], (
        "Missing relation issue not detected!"
    )

    # Optionally, verify specific layers or data in the project
    layers = project.mapLayers().values()
    layer_names = [lyr.name() for lyr in layers]
    assert "Comune del progetto" in layer_names, "Layer not found in reopened project!"
