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

import filecmp
import logging
import shutil
import sqlite3
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from packaging.version import parse as parse_version
from qgis.core import QgsTask
from qgis.PyQt.QtCore import QCoreApplication
from qgis.utils import spatialite_connect

from ..__about__ import __base_version__
from ..core.mzs_project_manager import MzSProjectManager

# tables copied from the source projects, in insertion order (parents before children)
MERGE_TABLES = (
    "sito_puntuale",
    "indagini_puntuali",
    "parametri_puntuali",
    "curve",
    "hvsr",
    "sito_lineare",
    "indagini_lineari",
    "parametri_lineari",
    "stab_l1",
    "instab_l1",
    "isosub_l1",
    "stab_l23",
    "instab_l23",
    "isosub_l23",
    "geoidr",
    "epuntuali",
    "elineari",
    "forme",
    "instab_geotec",
    "geotec",
)

# tables whose text IDs are preserved from the source projects
ID_TABLES = (
    "sito_puntuale",
    "indagini_puntuali",
    "parametri_puntuali",
    "sito_lineare",
    "indagini_lineari",
    "parametri_lineari",
)

# INSERT triggers that would rebuild the preserved IDs: dropped while copying each source
BYPASSED_TRIGGERS = (
    "ins_data_s_point",
    "ins_data_s_line",
    "ins_data_i_point",
    "ins_data_i_line",
    "ins_data_p_point",
    "ins_data_p_line",
)

# (table, field) pairs containing paths of files stored in the Allegati folder
ATTACHMENT_FIELDS = [
    ("indagini_puntuali", "doc_ind"),
    ("indagini_lineari", "doc_ind"),
    ("parametri_puntuali", "tab_curve"),
    ("stab_l1", "SPETTRI"),
    ("instab_l1", "SPETTRI"),
    ("stab_l23", "SPETTRI"),
    ("instab_l23", "SPETTRI"),
    ("instab_geotec", "SPETTRI"),
]

ATTACHMENT_DIRS = ("Altro", "Documenti", "Plot", "Spettri")

# (child table, child pkey column, parent table, text id column)
PKEY_RELATIONS = (
    ("indagini_puntuali", "pkey_spu", "sito_puntuale", "id_spu"),
    ("parametri_puntuali", "pkey_indpu", "indagini_puntuali", "id_indpu"),
    ("curve", "pkey_parpu", "parametri_puntuali", "id_parpu"),
    ("indagini_lineari", "pkey_sln", "sito_lineare", "id_sln"),
    ("parametri_lineari", "pkey_indln", "indagini_lineari", "id_indln"),
)


def _tr(message: str) -> str:
    return QCoreApplication.translate("MergeProjects", message)


@dataclass
class SourceProject:
    """An existing single-municipality MzS Tools project to be merged."""

    path: Path
    cod_istat: str | None = None
    comune: str | None = None
    version: str | None = None
    issue: str | None = None

    @property
    def db_path(self) -> Path:
        return self.path / "db" / "indagini.sqlite"


def scan_source_projects(folder: Path) -> list[SourceProject]:
    """Find the MzS Tools projects in the direct subfolders of ``folder`` and check if they can be merged.

    Projects that cannot be merged have the ``issue`` attribute set.
    """
    candidates = sorted(
        (p for p in folder.iterdir() if p.is_dir() and (p / "db" / "indagini.sqlite").is_file()),
        key=lambda p: p.name,
    )

    sources: list[SourceProject] = []
    for path in candidates:
        source = SourceProject(path=path)
        sources.append(source)

        version_file = path / "progetto" / "versione.txt"
        if not version_file.is_file():
            source.issue = _tr("missing progetto/versione.txt")
            continue
        source.version = version_file.read_text().strip()
        if parse_version(source.version) != parse_version(__base_version__):
            source.issue = _tr("project version {v}: open and update it with MzS Tools {base} first").format(
                v=source.version, base=__base_version__
            )
            continue

        try:
            conn = sqlite3.connect(f"file:{source.db_path}?mode=ro", uri=True)
            try:
                rows = conn.execute("SELECT cod_istat, comune FROM comune_progetto").fetchall()
            finally:
                conn.close()
        except Exception as e:
            source.issue = _tr("database error: {e}").format(e=e)
            continue

        if not rows:
            source.issue = _tr("municipality not set (comune_progetto is empty)")
        elif len(rows) > 1:
            source.issue = _tr("already a multi-municipality project")
        else:
            source.cod_istat, source.comune = rows[0]

    counts = Counter(s.cod_istat for s in sources if s.issue is None)
    for source in sources:
        if source.issue is None and counts[source.cod_istat] > 1:
            source.issue = _tr("duplicate municipality {cod_istat}").format(cod_istat=source.cod_istat)

    return sources


class MergeProjectsTask(QgsTask):
    """Copy the data of several MzS Tools projects into the current (newly created, multi-municipality) project.

    Survey IDs (id_spu, id_indpu, ...) are preserved, attachments are copied (renaming conflicting files) and the
    metadata records are copied. The current project must be created with ``create_merged_project``.
    """

    def __init__(self, sources: list[SourceProject]):
        super().__init__("MzS Tools - merge projects", QgsTask.Flag.CanCancel)

        self.sources = sources
        self.prj_manager = MzSProjectManager.instance()
        self.logger = logging.getLogger("mzs_tools.tasks.merge_projects")
        self.exception: Exception | None = None
        self.counts: dict[str, int] = dict.fromkeys(MERGE_TABLES, 0)
        self.max_src_seq: dict[str, int] = dict.fromkeys(ID_TABLES, 0)

    def run(self) -> bool:
        self.logger.info(f"{'#' * 15} Starting task {self.description()}")
        try:
            conn = spatialite_connect(str(self.prj_manager.db_path))
        except Exception as e:
            self.exception = e
            return False

        try:
            conn.isolation_level = None

            placeholders = ", ".join("?" for _ in BYPASSED_TRIGGERS)
            trigger_sql = dict(
                conn.execute(
                    f"SELECT name, sql FROM sqlite_master WHERE type = 'trigger' AND name IN ({placeholders})",  # nosec B608
                    BYPASSED_TRIGGERS,
                ).fetchall()
            )
            missing = [name for name in BYPASSED_TRIGGERS if name not in trigger_sql]
            if missing:
                raise RuntimeError(f"Missing triggers in the project database: {missing}")

            sources = sorted(self.sources, key=lambda s: s.cod_istat or "")
            for i, source in enumerate(sources):
                if self.isCanceled():
                    self.logger.warning("Task cancelled")
                    return False
                self._merge_source(conn, source, trigger_sql)
                self.setProgress((i + 1) / len(sources) * 95)

            conn.execute("BEGIN")
            for child, pkey, parent, text_id in PKEY_RELATIONS:
                conn.execute(
                    f'UPDATE "{child}" SET "{pkey}" = (SELECT p.pkuid FROM "{parent}" p '  # nosec B608
                    f'WHERE p."{text_id}" = "{child}"."{text_id}") WHERE "{pkey}" IS NOT NULL'  # nosec B608
                )
            # make sure new records get a pkuid higher than every preserved ID suffix
            for table in ID_TABLES:
                cur = conn.execute(
                    "UPDATE sqlite_sequence SET seq = MAX(seq, ?) WHERE name = ?", (self.max_src_seq[table], table)
                )
                if cur.rowcount == 0:
                    conn.execute(
                        "INSERT INTO sqlite_sequence (name, seq) VALUES (?, ?)", (table, self.max_src_seq[table])
                    )
            conn.execute("COMMIT")
        except Exception as e:
            if conn.in_transaction:
                conn.execute("ROLLBACK")
            self.exception = e
            return False
        finally:
            conn.close()

        for table, count in self.counts.items():
            self.logger.info(f"{table}: {count} records merged")
        self.setProgress(100)
        return True

    def _merge_source(self, conn, source: SourceProject, trigger_sql: dict[str, str]) -> None:
        """Copy the data of a single source project in its own transaction."""
        self.logger.info(f"Merging project {source.path} ({source.cod_istat} - {source.comune})")
        attached = False
        try:
            rename_map = self._copy_attachments(source)

            conn.execute("ATTACH DATABASE ? AS src", (str(source.db_path),))
            attached = True

            placeholders = ", ".join("?" for _ in ID_TABLES)
            src_seq = dict(
                conn.execute(
                    f"SELECT name, seq FROM src.sqlite_sequence WHERE name IN ({placeholders})",  # nosec B608
                    ID_TABLES,
                ).fetchall()
            )
            for table in ID_TABLES:
                self.max_src_seq[table] = max(self.max_src_seq[table], src_seq.get(table) or 0)

            conn.execute("BEGIN")
            for name in BYPASSED_TRIGGERS:
                conn.execute(f'DROP TRIGGER "{name}"')

            prev_max = {
                table: conn.execute(f'SELECT COALESCE(MAX(pkuid), 0) FROM main."{table}"').fetchone()[0]  # nosec B608
                for table in {t for t, _ in ATTACHMENT_FIELDS}
            }

            for table in MERGE_TABLES:
                try:
                    cols = self._common_columns(conn, table, exclude=("pkuid",))
                    col_list = ", ".join(f'"{c}"' for c in cols)
                    cur = conn.execute(
                        f'INSERT INTO main."{table}" ({col_list}) SELECT {col_list} FROM src."{table}" ORDER BY pkuid'  # nosec B608
                    )
                except Exception as e:
                    raise RuntimeError(f"{table}: {e}") from e
                self.counts[table] += cur.rowcount
                self.logger.debug(f"{table}: {cur.rowcount} records copied")

            try:
                cols = self._common_columns(conn, "metadati")
                col_list = ", ".join(f'"{c}"' for c in cols)
                conn.execute(f"INSERT INTO main.metadati ({col_list}) SELECT {col_list} FROM src.metadati")  # nosec B608
            except Exception as e:
                raise RuntimeError(f"metadati: {e}") from e

            for old, new in rename_map.items():
                for table, col in ATTACHMENT_FIELDS:
                    conn.execute(
                        f'UPDATE main."{table}" SET "{col}" = ? WHERE "{col}" = ? AND pkuid > ?',  # nosec B608
                        (new, old, prev_max[table]),
                    )

            for name in BYPASSED_TRIGGERS:
                conn.execute(trigger_sql[name])
            conn.execute("COMMIT")
            conn.execute("DETACH DATABASE src")
            attached = False
        except Exception as e:
            if conn.in_transaction:
                conn.execute("ROLLBACK")
            if attached:
                conn.execute("DETACH DATABASE src")
            raise RuntimeError(f"{source.path.name}: {e}") from e

    @staticmethod
    def _common_columns(conn, table: str, exclude: tuple[str, ...] = ()) -> list[str]:
        main_cols = [row[1] for row in conn.execute(f'PRAGMA main.table_info("{table}")')]
        src_cols = {row[1] for row in conn.execute(f'PRAGMA src.table_info("{table}")')}
        return [c for c in main_cols if c in src_cols and c not in exclude]

    def _copy_attachments(self, source: SourceProject) -> dict[str, str]:
        """Copy the attachments of a source project into the merged project.

        Returns:
            dict[str, str]: mapping of the renamed attachment paths (``./Allegati/...`` form), old -> new
        """
        src_allegati = source.path / "Allegati"
        dst_allegati = self.prj_manager.project_path / "Allegati"
        rename_map: dict[str, str] = {}

        for dir_name in ATTACHMENT_DIRS:
            src_dir = src_allegati / dir_name
            if not src_dir.is_dir():
                continue
            for src_file in sorted(src_dir.rglob("*")):
                if not src_file.is_file():
                    continue
                rel = src_file.relative_to(src_allegati)
                dst_file = dst_allegati / rel
                dst_file.parent.mkdir(parents=True, exist_ok=True)

                if not dst_file.exists():
                    shutil.copy2(src_file, dst_file)
                    continue
                if filecmp.cmp(src_file, dst_file, shallow=False):
                    continue

                # same name, different content: rename the copied file
                new_dst = dst_file.with_name(f"{source.cod_istat}_{dst_file.name}")
                n = 0
                while new_dst.exists() and not filecmp.cmp(src_file, new_dst, shallow=False):
                    n += 1
                    new_dst = dst_file.with_name(f"{source.cod_istat}_{dst_file.stem}_{n}{dst_file.suffix}")
                if not new_dst.exists():
                    shutil.copy2(src_file, new_dst)

                new_rel = new_dst.relative_to(dst_allegati)
                rename_map["./Allegati/" + rel.as_posix()] = "./Allegati/" + new_rel.as_posix()
                self.logger.info(f"Attachment {rel.as_posix()} renamed to {new_rel.as_posix()}")

        return rename_map

    def finished(self, result: bool) -> None:
        if self.exception:
            self.logger.error(f"Task {self.description()} failed: {self.exception}")
        elif result:
            self.logger.info(f"Task {self.description()} completed")
