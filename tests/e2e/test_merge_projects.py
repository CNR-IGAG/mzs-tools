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

"""End-to-end tests for merging several MzS Tools projects into a multi-municipality project."""

import shutil
import sqlite3
import zipfile
from pathlib import Path
from unittest.mock import patch

import pytest
from qgis.core import QgsRectangle
from qgis.utils import spatialite_connect

from mzs_tools.__about__ import __base_version__
from mzs_tools.tasks.merge_projects_task import ID_TABLES, MergeProjectsTask, scan_source_projects

# (child table, parent table, text id column)
ID_RELATIONS = [
    ("indagini_puntuali", "sito_puntuale", "id_spu"),
    ("parametri_puntuali", "indagini_puntuali", "id_indpu"),
    ("hvsr", "indagini_puntuali", "id_indpu"),
    ("curve", "parametri_puntuali", "id_parpu"),
    ("indagini_lineari", "sito_lineare", "id_sln"),
    ("parametri_lineari", "indagini_lineari", "id_indln"),
]

ID_COLUMNS = {
    "sito_puntuale": "id_spu",
    "indagini_puntuali": "id_indpu",
    "parametri_puntuali": "id_parpu",
    "sito_lineare": "id_sln",
    "indagini_lineari": "id_indln",
    "parametri_lineari": "id_parln",
}

COLLISION_DOC = "./Allegati/Documenti/collision.pdf"


def _extract_project(dest: Path) -> Path:
    archive = (
        Path(__file__).parent.parent / "data" / "mzs_projects" / f"057001_Accumoli_v{__base_version__}_imported.zip"
    )
    if not archive.exists():
        pytest.skip("Sample MzS Tools project archive not available")
    with zipfile.ZipFile(archive, "r") as zip_ref:
        zip_ref.extractall(dest)
    return dest / "057001_Accumoli"


def _relabel_to_amatrice(db_path: Path) -> None:
    """Turn a copy of the Accumoli project into an Amatrice (057002) project, using the original triggers."""
    conn = spatialite_connect(str(db_path))
    try:
        conn.execute("DELETE FROM comune_progetto")
        conn.execute(
            """INSERT INTO comune_progetto (cod_regio, cod_prov, "cod_com ", comune, geom, cod_istat, provincia, regione)
            SELECT cod_regio, cod_prov, cod_com, comune, GEOMETRY, cod_istat, provincia, regione
            FROM comuni WHERE cod_istat = '057002'"""
        )
        # the template UPDATE triggers rebuild the IDs with the new municipality / parent prefix
        conn.execute("UPDATE sito_puntuale SET indirizzo = indirizzo")
        conn.execute("UPDATE sito_lineare SET note_sito = note_sito")
        conn.execute("UPDATE indagini_puntuali SET id_spu = '057002' || substr(id_spu, 7)")
        conn.execute("UPDATE parametri_puntuali SET id_indpu = '057002' || substr(id_indpu, 7)")
        conn.execute("UPDATE hvsr SET id_indpu = '057002' || substr(id_indpu, 7)")
        conn.execute("UPDATE curve SET id_parpu = '057002' || substr(id_parpu, 7)")
        conn.execute("UPDATE indagini_lineari SET id_sln = '057002' || substr(id_sln, 7)")
        conn.execute("UPDATE parametri_lineari SET id_indln = '057002' || substr(id_indln, 7)")
        conn.execute("UPDATE metadati SET id_metadato = '057002M1'")
        conn.commit()
    finally:
        conn.close()


def _set_collision_doc(project: Path, content: bytes) -> None:
    (project / "Allegati" / "Documenti" / "collision.pdf").write_bytes(content)
    conn = sqlite3.connect(project / "db" / "indagini.sqlite")
    try:
        conn.execute(
            "UPDATE indagini_puntuali SET doc_ind = ? WHERE pkuid = (SELECT MIN(pkuid) FROM indagini_puntuali)",
            (COLLISION_DOC,),
        )
        conn.commit()
    finally:
        conn.close()


@pytest.fixture
def source_projects(tmp_path) -> tuple[Path, Path]:
    """Two current-version source projects: Accumoli (057001) and a relabeled copy as Amatrice (057002),
    sharing an attachment name with different content."""
    project_a = _extract_project(tmp_path / "sources" / "a")
    project_b = _extract_project(tmp_path / "sources" / "b")
    project_b = project_b.rename(project_b.parent / "057002_Amatrice")

    _relabel_to_amatrice(project_b / "db" / "indagini.sqlite")

    _set_collision_doc(project_a, b"A")
    _set_collision_doc(project_b, b"B")

    return project_a, project_b


def _query(db_path: Path, sql: str, params: tuple = ()) -> list[tuple]:
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        return conn.execute(sql, params).fetchall()
    finally:
        conn.close()


def test_scan_source_projects(tmp_path, source_projects):
    project_a, project_b = source_projects
    sources_dir = tmp_path / "scan"
    sources_dir.mkdir()
    shutil.copytree(project_a, sources_dir / "a")
    shutil.copytree(project_b, sources_dir / "b")

    sources = {s.path.name: s for s in scan_source_projects(sources_dir)}
    assert sources["a"].issue is None and sources["a"].cod_istat == "057001"
    assert sources["b"].issue is None and sources["b"].cod_istat == "057002"
    assert sources["b"].comune == "Amatrice"

    # outdated project version
    shutil.copytree(project_a, sources_dir / "c_old")
    (sources_dir / "c_old" / "progetto" / "versione.txt").write_text("2.0.5")
    sources = {s.path.name: s for s in scan_source_projects(sources_dir)}
    assert "2.0.5" in sources["c_old"].issue
    assert sources["a"].issue is None

    # duplicated municipality: both 057001 entries are flagged
    shutil.copytree(project_a, sources_dir / "d_dup")
    sources = {s.path.name: s for s in scan_source_projects(sources_dir)}
    assert "057001" in sources["a"].issue
    assert "057001" in sources["d_dup"].issue
    assert sources["b"].issue is None


def test_merge_projects(tmp_path, source_projects, prj_manager):
    project_a, project_b = source_projects
    sources_dir = project_a.parent.parent
    sources = sorted(
        (s for s in scan_source_projects(sources_dir / "a") + scan_source_projects(sources_dir / "b")),
        key=lambda s: s.cod_istat,
    )
    assert [s.issue for s in sources] == [None, None]

    with patch("mzs_tools.core.mzs_project_manager.iface") as mock_iface:
        mock_iface.addProject.return_value = True
        mock_iface.mapCanvas.return_value.extent.return_value = QgsRectangle(0, 0, 100, 100)
        merged_path = prj_manager.create_merged_project("merged test", ["057001", "057002"], str(tmp_path / "out"))

    task = MergeProjectsTask(sources)
    assert task.run() is True, task.exception

    merged_db = merged_path / "db" / "indagini.sqlite"
    src_dbs = [project_a / "db" / "indagini.sqlite", project_b / "db" / "indagini.sqlite"]

    # 1. one comune_progetto row per municipality
    assert sorted(r[0] for r in _query(merged_db, "SELECT cod_istat FROM comune_progetto")) == ["057001", "057002"]

    # 2. survey IDs preserved
    for table in ID_TABLES:
        col = ID_COLUMNS[table]
        merged_ids = [r[0] for r in _query(merged_db, f"SELECT {col} FROM {table}")]
        src_ids = [r[0] for db in src_dbs for r in _query(db, f"SELECT {col} FROM {table}")]
        assert len(merged_ids) == len(src_ids), table
        assert set(merged_ids) == set(src_ids), table

    # 3. no orphans
    for child, parent, col in ID_RELATIONS:
        orphans = _query(
            merged_db,
            f"SELECT COUNT(*) FROM {child} c LEFT JOIN {parent} p ON p.{col} = c.{col} WHERE p.{col} IS NULL",
        )[0][0]
        assert orphans == 0, f"{child} -> {parent}"

    # 4. conflicting attachment renamed only for the second project
    allegati = merged_path / "Allegati" / "Documenti"
    assert (allegati / "collision.pdf").read_bytes() == b"A"
    assert (allegati / "057002_collision.pdf").read_bytes() == b"B"
    doc_by_site = dict(
        _query(
            merged_db,
            "SELECT id_spu, doc_ind FROM indagini_puntuali WHERE doc_ind LIKE '%collision.pdf'",
        )
    )
    first_a = _query(src_dbs[0], "SELECT id_spu FROM indagini_puntuali ORDER BY pkuid LIMIT 1")[0][0]
    first_b = _query(src_dbs[1], "SELECT id_spu FROM indagini_puntuali ORDER BY pkuid LIMIT 1")[0][0]
    assert doc_by_site == {first_a: COLLISION_DOC, first_b: "./Allegati/Documenti/057002_collision.pdf"}

    # 5. metadata copied from the sources
    assert {r[0] for r in _query(merged_db, "SELECT id_metadato FROM metadati")} == {"057001M1", "057002M1"}

    max_src_seq = max(
        r[0] for db in src_dbs for r in _query(db, "SELECT seq FROM sqlite_sequence WHERE name = 'sito_puntuale'")
    )

    conn = spatialite_connect(str(merged_db))
    try:
        # 6. new site in Amatrice gets the municipality from its location and a pkuid above the source sequences
        # id_spu is NOT NULL: insert a placeholder, the INSERT trigger overwrites it
        conn.execute(
            "INSERT INTO sito_puntuale (id_spu, geom) "
            "SELECT 'new', PointOnSurface(GEOMETRY) FROM comuni WHERE cod_istat = '057002'"
        )
        pkuid = conn.execute("SELECT MAX(pkuid) FROM sito_puntuale").fetchone()[0]
        ubicazione_com, id_spu = conn.execute(
            "SELECT ubicazione_com, id_spu FROM sito_puntuale WHERE pkuid = ?", (pkuid,)
        ).fetchone()
        assert ubicazione_com == "002"
        assert id_spu == f"057002P{pkuid}"
        assert pkuid > max_src_seq

        # 7. updates do not rebuild the preserved IDs
        pkuid, id_spu = conn.execute(
            "SELECT pkuid, id_spu FROM sito_puntuale WHERE id_spu != ubicazione_prov || ubicazione_com || 'P' || pkuid "
            "ORDER BY pkuid LIMIT 1"
        ).fetchone()
        conn.execute("UPDATE sito_puntuale SET indirizzo = 'x' WHERE pkuid = ?", (pkuid,))
        assert conn.execute("SELECT id_spu FROM sito_puntuale WHERE pkuid = ?", (pkuid,)).fetchone()[0] == id_spu

        pkuid, id_indpu = conn.execute(
            "SELECT pkuid, id_indpu FROM indagini_puntuali WHERE id_indpu != id_spu || tipo_ind || pkuid "
            "ORDER BY pkuid LIMIT 1"
        ).fetchone()
        conn.execute("UPDATE indagini_puntuali SET note_ind = 'x' WHERE pkuid = ?", (pkuid,))
        assert (
            conn.execute("SELECT id_indpu FROM indagini_puntuali WHERE pkuid = ?", (pkuid,)).fetchone()[0] == id_indpu
        )
        conn.commit()
    finally:
        conn.close()

    # 8. multi-municipality project state
    assert prj_manager.is_multi_comune is True
    assert "Progetto multicomunale (2 comuni" in prj_manager.current_project.title()
