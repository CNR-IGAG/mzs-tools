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
from contextlib import closing
from pathlib import Path

import pytest
from qgis.core import (
    QgsApplication,
    QgsProcessingContext,
    QgsProcessingFeedback,
    QgsProject,
    QgsVectorLayer,
)
from qgis.PyQt.QtCore import QMetaType


def run_algorithm(alg_id: str, params: dict) -> dict:
    alg = QgsApplication.processingRegistry().createAlgorithmById(alg_id)
    assert alg is not None
    results, ok = alg.run(params, QgsProcessingContext(), QgsProcessingFeedback(), catchExceptions=False)
    assert ok
    return results


def test_export_project_to_standard_algorithm(mzs_provider, base_project_path_current_imported, tmp_path):
    p = base_project_path_current_imported
    out = tmp_path / "out"  # not created: the algorithm creates it
    params = {"INPUT": str(p / "progetto_MS.qgz"), "OUTPUT_FOLDER": str(out)}

    results = run_algorithm("mzs_tools:export_project_to_standard", params)

    export_path = out / "057001_Accumoli_S42_Shapefile"
    assert results["STATUS"] == "exported"
    assert results["COD_ISTAT"] == "057001"
    assert results["EXPORT_PATH"] == str(export_path)
    assert results["OUTPUT_FOLDER"] == str(out)
    log_file = Path(results["LOG_FILE"])
    assert log_file.parent == p / "Allegati" / "log"
    assert log_file.stat().st_size > 0

    for shp in ("GeoTec/Elineari.shp", "BasiDati/comune_progetto.shp", "Indagini/Ind_pu.shp"):
        assert (export_path / shp).is_file(), shp

    ind_pu = QgsVectorLayer(str(export_path / "Indagini" / "Ind_pu.shp"), "Ind_pu", "ogr")
    field_names = ind_pu.fields().names()
    assert "ID_SPU" in field_names
    assert "id_spu" not in field_names
    assert ind_pu.featureCount() > 0

    # integer fields are converted back from the float type written by the exporter
    elineari = QgsVectorLayer(str(export_path / "GeoTec" / "Elineari.shp"), "Elineari", "ogr")
    assert elineari.fields().field("ID_el").type() in (QMetaType.Type.Int, QMetaType.Type.LongLong)

    with closing(sqlite3.connect(export_path / "Indagini" / "CdI_Tabelle.sqlite")) as conn:
        for table in ("sito_puntuale", "sito_lineare"):
            assert conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] > 0, table
    assert any((export_path / "Indagini" / "Documenti").iterdir())

    # the project is exported on a detached QgsProject
    assert QgsProject.instance().fileName() == ""
    assert QgsProject.instance().mapLayers() == {}

    # an existing export folder gets a timestamp suffix
    results = run_algorithm("mzs_tools:export_project_to_standard", params)
    assert results["EXPORT_PATH"].startswith(str(out / "057001_Accumoli_S42_Shapefile_"))


def test_export_project_to_standard_algorithm_outdated(mzs_provider, base_project_path_2_0_5, tmp_path):
    out = tmp_path / "out"
    out.mkdir()
    params = {"INPUT": str(base_project_path_2_0_5 / "progetto_MS.qgz"), "OUTPUT_FOLDER": str(out)}

    results = run_algorithm("mzs_tools:export_project_to_standard", params)

    assert results["STATUS"] == "skipped"
    assert list(out.iterdir()) == []


def test_export_project_to_standard_algorithm_mdb(
    mzs_provider, base_project_path_current_imported, mdb_deps_available, tmp_path
):
    if not mdb_deps_available:
        pytest.skip("Access database dependencies not available")
    params = {
        "INPUT": str(base_project_path_current_imported / "progetto_MS.qgz"),
        "OUTPUT_FOLDER": str(tmp_path / "out"),
        "OUTPUT_FORMAT": 1,
    }

    results = run_algorithm("mzs_tools:export_project_to_standard", params)

    export_path = Path(results["EXPORT_PATH"])
    assert results["STATUS"] == "exported"
    assert (export_path / "Indagini" / "CdI_Tabelle.mdb").is_file()
    assert not (export_path / "Indagini" / "CdI_Tabelle.sqlite").exists()


def test_export_projects_in_folder_to_standard_algorithm(mzs_provider, base_project_path_current_imported, tmp_path):
    shutil.copytree(base_project_path_current_imported, tmp_path / "more" / "copy")
    # an outdated project, which is skipped
    archive = Path(__file__).parents[1] / "data" / "mzs_projects" / "057001_Accumoli_v2.0.5_new.zip"
    with zipfile.ZipFile(archive) as zip_ref:
        zip_ref.extractall(tmp_path / "old")
    out = tmp_path / "out"
    params = {"INPUT_FOLDER": str(tmp_path), "OUTPUT_FOLDER": str(out)}

    results = run_algorithm("mzs_tools:export_projects_in_folder_to_standard", params)

    assert results["EXPORTED_COUNT"] == 2
    assert results["SKIPPED_COUNT"] == 1
    assert results["FAILED_COUNT"] == 0
    assert len(results["EXPORTED_PATHS"].splitlines()) == 2
    assert results["OUTPUT_FOLDER"] == str(out)
    assert len(list(out.iterdir())) == 2
