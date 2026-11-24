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
from contextlib import closing
from pathlib import Path

import pytest
from qgis.core import (
    QgsApplication,
    QgsProcessingContext,
    QgsProcessingException,
    QgsProcessingFeedback,
    QgsProject,
)

from mzs_tools.__about__ import __base_version__
from mzs_tools.core.constants import DEFAULT_RELATIONS


def run_algorithm(alg_id: str, params: dict) -> dict:
    alg = QgsApplication.processingRegistry().createAlgorithmById(alg_id)
    assert alg is not None
    results, ok = alg.run(params, QgsProcessingContext(), QgsProcessingFeedback(), catchExceptions=False)
    assert ok
    return results


def count_rows(project_dir: Path, table: str) -> int:
    with closing(sqlite3.connect(project_dir / "db" / "indagini.sqlite")) as conn:
        return conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]


def test_import_standard_project_algorithm(mzs_provider, standard_project_path, tmp_path):
    out = tmp_path / "out"
    out.mkdir()
    params = {"INPUT_FOLDER": str(standard_project_path), "OUTPUT_FOLDER": str(out)}

    results = run_algorithm("mzs_tools:import_standard_project", params)

    project_dir = out / "057001_Accumoli"
    assert results["STATUS"] == "created"
    assert results["COD_ISTAT"] == "057001"
    assert results["INDAGINI_SOURCE"] == "sqlite"
    assert results["PROJECT_PATH"] == str(project_dir)
    assert (project_dir / "progetto" / "versione.txt").read_text().strip() == __base_version__
    log_file = Path(results["LOG_FILE"])
    assert log_file.is_file()
    assert log_file.parent == project_dir / "Allegati" / "log"
    for table in ("sito_puntuale", "sito_lineare", "elineari"):
        assert count_rows(project_dir, table) > 0, table

    # the survey data relations are resolved in the detached project, which opens on the study municipality
    project = QgsProject()
    try:
        assert project.read(str(project_dir / "progetto_MS.qgz"))
        relations = project.relationManager().relations()
        assert set(DEFAULT_RELATIONS) <= set(relations)
        assert all(relations[name].isValid() for name in DEFAULT_RELATIONS)
        comune_layer = next(
            layer
            for layer in project.mapLayers().values()
            if layer.customProperty("mzs_tools/layer_role") == "base" and "comune_progetto" in layer.source()
        )
        view_extent = project.viewSettings().defaultViewExtent()
        comune_extent = comune_layer.extent()
        # the extent is serialized in the project file: compare with a tolerance
        assert [view_extent.xMinimum(), view_extent.yMinimum(), view_extent.xMaximum(), view_extent.yMaximum()] == (
            pytest.approx(
                [
                    comune_extent.xMinimum(),
                    comune_extent.yMinimum(),
                    comune_extent.xMaximum(),
                    comune_extent.yMaximum(),
                ],
                abs=1e-3,
            )
        )
    finally:
        project.clear()

    # the project open in QGIS is not touched
    assert QgsProject.instance().fileName() == ""
    assert QgsProject.instance().mapLayers() == {}

    # an existing output project is never overwritten
    results = run_algorithm("mzs_tools:import_standard_project", params)
    assert results["STATUS"] == "skipped"


def test_import_standard_project_algorithm_csv_fallback(mzs_provider, standard_project_path, tmp_path):
    for name in ("CdI_Tabelle.sqlite", "CdI_Tabelle.mdb", "CdI_Tabelle_no_pwd.mdb"):
        (standard_project_path / "Indagini" / name).unlink()
    out = tmp_path / "out"
    out.mkdir()

    results = run_algorithm(
        "mzs_tools:import_standard_project", {"INPUT_FOLDER": str(standard_project_path), "OUTPUT_FOLDER": str(out)}
    )

    project_dir = Path(results["PROJECT_PATH"])
    assert results["INDAGINI_SOURCE"] == "csv"
    assert count_rows(project_dir, "sito_puntuale") > 0
    assert count_rows(project_dir, "curve") > 0

    # an explicit source that is not available fails before creating anything
    out_sqlite = tmp_path / "out_sqlite"
    out_sqlite.mkdir()
    alg = QgsApplication.processingRegistry().createAlgorithmById("mzs_tools:import_standard_project")
    with pytest.raises(QgsProcessingException):
        alg.run(
            {"INPUT_FOLDER": str(standard_project_path), "OUTPUT_FOLDER": str(out_sqlite), "INDAGINI_SOURCE": 1},
            QgsProcessingContext(),
            QgsProcessingFeedback(),
            catchExceptions=False,
        )
    assert list(out_sqlite.iterdir()) == []


def test_import_standard_projects_in_folder_algorithm(mzs_provider, standard_project_path, tmp_path):
    shutil.copytree(standard_project_path, tmp_path / "more" / "Accumoli_bis")
    (tmp_path / "not_a_project").mkdir()
    # inside the scanned root: must not be scanned
    out = tmp_path / "out"
    out.mkdir()
    params = {"INPUT_FOLDER": str(tmp_path), "OUTPUT_FOLDER": str(out)}

    results = run_algorithm("mzs_tools:import_standard_projects_in_folder", params)

    assert results["CREATED_COUNT"] == 1
    # Accumoli_bis maps to the same output project folder
    assert results["SKIPPED_COUNT"] == 1
    assert results["FAILED_COUNT"] == 0
    assert results["CREATED_PROJECTS"] == str(out / "057001_Accumoli")

    results = run_algorithm("mzs_tools:import_standard_projects_in_folder", params)
    assert results["CREATED_COUNT"] == 0
    assert results["SKIPPED_COUNT"] == 2
