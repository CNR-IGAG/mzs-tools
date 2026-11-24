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

"""Create MzS Tools projects from standard SM projects on detached QgsProject instances (used by the processing
algorithms)."""

import logging
import os
import re
import shutil
import sqlite3
import tempfile
from collections import Counter
from collections.abc import Iterator
from contextlib import closing, contextmanager
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from qgis.core import QgsProcessingException, QgsProcessingFeedback, QgsProject, QgsVectorLayer
from qgis.PyQt.QtCore import QCoreApplication

from ..__about__ import __version__
from ..core.mzs_project_manager import MzSProjectManager
from ..tasks.access_db_connection import AccessDbConnection
from ..tasks.import_shapefile_task import ImportShapefileTask
from ..tasks.import_siti_lineari_task import ImportSitiLineariTask
from ..tasks.import_siti_puntuali_task import ImportSitiPuntualiTask
from ..tasks.standard_project import build_standard_project_paths, find_csv_files

IMPORT_STATUS_CREATED = "created"
IMPORT_STATUS_SKIPPED = "skipped"

# the index matches the options of the INDAGINI_SOURCE algorithm parameter
INDAGINI_SOURCES = ("auto", "sqlite", "mdb", "csv")

# the logger the import tasks write to
IMPORT_LOGGER_NAME = "mzs_tools.tasks.import_data"


def tr(message: str) -> str:
    return QCoreApplication.translate("StandardProjectImport", message)


@dataclass
class StandardProjectImportResult:
    standard_project: Path
    status: str  # one of the IMPORT_STATUS_* constants
    project_path: Path | None
    cod_istat: str
    indagini_source: str  # "sqlite" | "mdb" | "csv" | "" (no survey data imported)
    log_file: Path | None
    message: str  # user-facing (translated) summary


def find_standard_projects(root: Path, exclude: Path | None = None) -> list[Path]:
    """Recursively find standard projects (folders with an 'Indagini' subfolder) in root.

    The exclude folder and MzS Tools projects (folders containing db/indagini.sqlite) are not scanned.
    """
    exclude_resolved = exclude.resolve() if exclude is not None else None
    projects = []
    for current, dirs, _files in os.walk(root):
        current_path = Path(current)
        if any(d.lower() == "indagini" for d in dirs):
            projects.append(current_path)
            dirs[:] = []
            continue
        dirs[:] = [
            d
            for d in dirs
            if (exclude_resolved is None or (current_path / d).resolve() != exclude_resolved)
            and not (current_path / d / "db" / "indagini.sqlite").is_file()
        ]
    return sorted(projects)


def load_comuni_names() -> dict[str, str]:
    """Return the municipality names by ISTAT code, from the MzS Tools database template."""
    with tempfile.TemporaryDirectory() as tmp:
        MzSProjectManager.extract_database_template(tmp)
        with closing(sqlite3.connect(Path(tmp) / "indagini.sqlite")) as conn:
            return dict(conn.execute("SELECT cod_istat, comune FROM comuni").fetchall())


def detect_cod_istat(paths: dict, feedback: QgsProcessingFeedback) -> str | None:
    """Detect the ISTAT code from the IDs of the survey sites (the first 6 digits of ID_SPU/ID_SLN)."""
    counts: Counter[str] = Counter()
    for shp_name, field_name in (("Ind_pu.shp", "ID_SPU"), ("Ind_ln.shp", "ID_SLN")):
        shp_path = paths[shp_name]["path"]
        if not shp_path:
            continue
        layer = QgsVectorLayer(str(shp_path), "", "ogr")
        if not layer.isValid():
            continue
        field_idx = layer.fields().lookupField(field_name)
        if field_idx == -1:
            continue
        for feature in layer.getFeatures():
            # NULL values never match
            match = re.match(r"^(\d{6})", str(feature.attribute(field_idx)))
            if match:
                counts[match.group(1)] += 1

    if not counts:
        return None
    code = counts.most_common(1)[0][0]
    if len(counts) > 1:
        feedback.pushWarning(
            tr("Several ISTAT codes found in the survey sites, using the most frequent one") + f": {code}"
        )
    return code


def resolve_indagini_source(
    requested: str,
    paths: dict,
    csv_dir: Path | None,
    mdb_password: str | None,
    feedback: QgsProcessingFeedback,
) -> tuple[str | None, dict | None]:
    """Choose the survey data source.

    Returns:
        (source, csv_files): source is None when no survey data can be imported in "auto" mode; csv_files is the
        dict returned by find_csv_files() for the "csv" source, None otherwise.

    Raises:
        QgsProcessingException: if an explicitly requested source is not available.
    """
    mdb_reason = ""
    csv_files = None

    def sqlite_available() -> bool:
        return bool(paths["CdI_Tabelle.sqlite"]["path"])

    def mdb_available() -> bool:
        nonlocal mdb_reason
        mdb_path = paths["CdI_Tabelle.mdb"]["path"]
        if not mdb_path:
            return False
        try:
            conn = AccessDbConnection(str(mdb_path), password=mdb_password)
            connected = conn.open()
            if connected:
                conn.close()
            return bool(connected)
        except Exception as e:
            mdb_reason = str(e) or e.__class__.__name__
            return False

    def csv_available() -> bool:
        nonlocal csv_files
        if csv_dir is None or not csv_dir.is_dir():
            return False
        found = find_csv_files(csv_dir)
        if "sito_puntuale" in found["puntuali"] or "sito_lineare" in found["lineari"]:
            csv_files = found
            return True
        return False

    checks = {"sqlite": sqlite_available, "mdb": mdb_available, "csv": csv_available}

    if requested == "auto":
        for source, available in checks.items():
            if available():
                feedback.pushInfo(tr("Survey data source") + f": {source}")
                return source, csv_files
            if source == "mdb" and mdb_reason:
                feedback.pushWarning(tr("Access database not available") + f": {mdb_reason}")
        if paths["Ind_pu.shp"]["path"] or paths["Ind_ln.shp"]["path"]:
            feedback.pushWarning(tr("No survey data source found: survey sites are not imported."))
        return None, None

    if not checks[requested]():
        msg = tr("Survey data source not available") + f": {requested}"
        if requested == "mdb" and mdb_reason:
            msg += f" ({mdb_reason})"
        raise QgsProcessingException(msg)
    return requested, csv_files


class _FeedbackLogHandler(logging.Handler):
    """Forward the import log records to the processing feedback."""

    def __init__(self, feedback: QgsProcessingFeedback):
        super().__init__()
        self.feedback = feedback

    def emit(self, record: logging.LogRecord) -> None:
        msg = self.format(record)
        if record.levelno >= logging.ERROR:
            self.feedback.reportError(msg, fatalError=False)
        elif record.levelno >= logging.WARNING:
            self.feedback.pushWarning(msg)
        else:
            self.feedback.pushInfo(msg)


@contextmanager
def _import_log(
    project_dir: Path, feedback: QgsProcessingFeedback, standard_project: Path, source: str | None
) -> Iterator[Path]:
    """Log the import tasks to Allegati/log/data_import_<timestamp>.log and to the processing feedback."""
    logger = logging.getLogger(IMPORT_LOGGER_NAME)
    log_file = project_dir / "Allegati" / "log" / f"data_import_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.log"
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
    feedback_handler = _FeedbackLogHandler(feedback)
    old_level = logger.level

    logger.addHandler(file_handler)
    logger.addHandler(feedback_handler)
    logger.setLevel(logging.INFO)
    try:
        logger.info(f"MzS Tools version {__version__} - Data import log")
        logger.info(f"Importing data from {standard_project} using {source} for Indagini data")
        logger.info("############### Data import started")
        yield log_file
    finally:
        for handler in (file_handler, feedback_handler):
            logger.removeHandler(handler)
            handler.close()
        logger.setLevel(old_level)


def import_standard_project(
    standard_project: Path,
    output_dir: Path,
    *,
    cod_istat: str | None,
    indagini_source: str,
    mdb_password: str | None,
    csv_dir: Path | None,
    study_author: str | None,
    author_email: str | None,
    comuni_names: dict[str, str],
    feedback: QgsProcessingFeedback,
) -> StandardProjectImportResult:
    """Create a new MzS Tools project in output_dir and import all the data found in a standard project.

    Raises:
        QgsProcessingException: if the project cannot be created or the data import fails (the created project is
            kept when only the data import fails).
    """
    paths = build_standard_project_paths(standard_project)
    if paths["Indagini"]["path"] is None:
        raise QgsProcessingException(
            tr("Not a standard project ('Indagini' folder not found)") + f": {standard_project}"
        )

    code = cod_istat.strip() if cod_istat and cod_istat.strip() else detect_cod_istat(paths, feedback)
    if code is None:
        raise QgsProcessingException(
            tr("Cannot detect the ISTAT code from the survey sites (ID_SPU/ID_SLN): set it explicitly.")
        )
    if code not in comuni_names:
        raise QgsProcessingException(tr("Unknown ISTAT code") + f": {code}")
    comune_name = comuni_names[code]

    project_dir = output_dir / f"{code}_{MzSProjectManager.sanitize_comune_name(comune_name)}"
    if project_dir.exists():
        return StandardProjectImportResult(
            standard_project,
            IMPORT_STATUS_SKIPPED,
            None,
            code,
            "",
            None,
            tr("Output project folder already exists") + f": {project_dir}",
        )

    if csv_dir is None:
        csv_dir = next((d for d in standard_project.iterdir() if d.is_dir() and d.name.lower() == "csv"), None)
    # resolved before creating the project, so that an unavailable source leaves nothing on disk
    source, csv_files = resolve_indagini_source(indagini_source, paths, csv_dir, mdb_password, feedback)

    project = QgsProject()
    manager = MzSProjectManager()
    try:
        manager.create_project(
            comune_name, code, study_author or None, author_email or None, str(output_dir), project=project
        )
    except Exception as e:
        manager.cleanup_db_connection()
        project.clear()
        if project_dir.exists():
            shutil.rmtree(project_dir)
        raise QgsProcessingException(tr("Project creation failed") + f": {e}") from e

    try:
        # reload the saved project, as the GUI does after creating a new project
        manager.cleanup_db_connection()
        project.clear()
        if not project.read(str(project_dir / "progetto_MS.qgz")):
            raise QgsProcessingException(tr("Cannot read project") + f" {project_dir}: {project.error()}")
        manager.init_manager(project)
        if manager.db_manager is None:
            raise QgsProcessingException(tr("Cannot connect to the project database."))

        tasks = []
        for shp_name, csv_series, sito_prefix, task_class in (
            ("Ind_pu.shp", "puntuali", "sito_puntuale", ImportSitiPuntualiTask),
            ("Ind_ln.shp", "lineari", "sito_lineare", ImportSitiLineariTask),
        ):
            if (
                paths[shp_name]["path"] and source and (source != "csv" or sito_prefix in csv_files[csv_series])  # type: ignore[index]
            ):
                tasks.append(
                    task_class(
                        paths, data_source=source, mdb_password=mdb_password, csv_files=csv_files, prj_manager=manager
                    )
                )
        for name, data in paths.items():
            if "table" in data and data["path"] is not None:
                tasks.append(ImportShapefileTask(paths, name, prj_manager=manager))

        failed: list[str] = []
        with _import_log(project_dir, feedback, standard_project, source) as log_file:
            logger = logging.getLogger(IMPORT_LOGGER_NAME)
            for task in tasks:
                if feedback.isCanceled():
                    raise QgsProcessingException(tr("Import cancelled."))
                # run synchronously: finished() is not called, as it re-raises the task exception
                if task.run():
                    logger.info(f"Task {task.description()} completed with {task.iterations} iterations")
                else:
                    logger.error(f"Task {task.description()} failed: {task.exception}")
                    failed.append(f"{task.description()}: {task.exception}")

        if failed:
            raise QgsProcessingException(
                tr("Data import completed with errors. Check the log for details.")
                + f" {log_file}\n"
                + "\n".join(failed)
            )

        return StandardProjectImportResult(
            standard_project,
            IMPORT_STATUS_CREATED,
            project_dir,
            code,
            source or "",
            log_file,
            tr("Project created in {0} with data imported from {1}.").format(project_dir, standard_project),
        )
    finally:
        # release SQLite handles before the next project
        manager.cleanup_db_connection()
        project.clear()
