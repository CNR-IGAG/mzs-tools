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

import shutil
import sqlite3
import zipfile
from pathlib import Path

import pytest
from qgis.core import QgsApplication, QgsProcessingContext, QgsProcessingFeedback, QgsProject

from mzs_tools.__about__ import __base_version__
from mzs_tools.core.mzs_project_manager import MzSProjectManager
from mzs_tools.processing.provider import MzSToolsProvider

FA_LAYOUT_NAME = "04 - MS23 carta di microzonazione sismica liv2-3 FA"


@pytest.fixture
def mzs_provider(qgis_app):
    provider = MzSToolsProvider()
    QgsApplication.processingRegistry().addProvider(provider)
    yield provider
    QgsApplication.processingRegistry().removeProvider(provider)


def run_algorithm(alg_id: str, params: dict) -> dict:
    alg = QgsApplication.processingRegistry().createAlgorithmById(alg_id)
    assert alg is not None
    results, ok = alg.run(params, QgsProcessingContext(), QgsProcessingFeedback(), catchExceptions=False)
    assert ok
    return results


def read_version(project_dir: Path) -> str:
    return (project_dir / "progetto" / "versione.txt").read_text().strip()


def test_update_project_algorithm_from_2_0_5(mzs_provider, base_project_path_2_0_5):
    project_file = base_project_path_2_0_5 / "progetto_MS.qgz"
    params = {"INPUT": str(project_file), "BACKUP": True}

    results = run_algorithm("mzs_tools:update_project", params)

    assert results["STATUS"] == "updated"
    assert results["FROM_VERSION"] == "2.0.5"
    assert results["TO_VERSION"] == __base_version__
    backup_path = Path(results["BACKUP_PATH"])
    assert backup_path.is_dir()
    assert read_version(backup_path) == "2.0.5"
    assert read_version(base_project_path_2_0_5) == __base_version__

    with sqlite3.connect(base_project_path_2_0_5 / "db" / "indagini.sqlite") as conn:
        row = conn.execute("SELECT db_version FROM mzs_tools_version WHERE id = 1").fetchone()
    assert row[0] == __base_version__

    # the project open in QGIS is untouched
    assert QgsProject.instance().mapLayers() == {}
    assert QgsProject.instance().fileName() == ""

    # the updated project contains the new layout, zoomed on the project municipality
    project = QgsProject()
    assert project.read(str(project_file))
    manager = MzSProjectManager()
    try:
        manager.init_manager(project)
        layout = project.layoutManager().layoutByName(FA_LAYOUT_NAME)
        assert layout is not None
        layer_id = manager.find_layer_by_table_name_role("comune_progetto", "base")
        assert layer_id
        layer = project.mapLayer(layer_id)
        map_item = layout.itemById("mappa_0")
        assert map_item.extent().intersects(layer.extent())

        root = project.layerTreeRoot()
        hidden = [lyr.name() for lyr_id, lyr in project.mapLayers().items() if root.findLayer(lyr_id) is None]
        assert hidden == []
    finally:
        manager.cleanup_db_connection()
        project.clear()

    results = run_algorithm("mzs_tools:update_project", params)
    assert results["STATUS"] == "up_to_date"
    assert results["BACKUP_PATH"] == ""


def test_update_projects_in_folder_algorithm(mzs_provider, base_project_path_2_0_5, tmp_path):
    shutil.copytree(base_project_path_2_0_5, tmp_path / "057001_Accumoli_bis")
    legacy_archive = Path(__file__).parent.parent / "data" / "mzs_projects" / "057001_Accumoli_v1.9.4_new.zip"
    with zipfile.ZipFile(legacy_archive, "r") as zip_ref:
        zip_ref.extractall(tmp_path / "legacy")
    legacy_dir = tmp_path / "legacy" / "057001_Accumoli"
    params = {"INPUT_FOLDER": str(tmp_path), "BACKUP": True}

    results = run_algorithm("mzs_tools:update_projects_in_folder", params)

    assert results["UPDATED_COUNT"] == 2
    assert results["SKIPPED_COUNT"] == 1
    assert results["FAILED_COUNT"] == 0
    assert read_version(legacy_dir) == "1.9.4"

    # backup folders created by the first run are ignored
    results = run_algorithm("mzs_tools:update_projects_in_folder", params)

    assert results["UPDATED_COUNT"] == 0
    assert results["UP_TO_DATE_COUNT"] == 2
    assert results["SKIPPED_COUNT"] == 1
