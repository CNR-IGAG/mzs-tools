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

"""Update MzS Tools projects on detached QgsProject instances (used by the processing algorithms)."""

import re
from dataclasses import dataclass
from pathlib import Path

from packaging.version import InvalidVersion
from packaging.version import parse as parse_version
from qgis.core import QgsProcessingException, QgsProcessingFeedback, QgsProject
from qgis.PyQt.QtCore import QCoreApplication

from ..core.mzs_project_manager import MzSProjectManager

UPDATE_STATUS_UPDATED = "updated"
UPDATE_STATUS_UP_TO_DATE = "up_to_date"
UPDATE_STATUS_SKIPPED = "skipped"

# matches the folder names created by MzSProjectManager.backup_project()
BACKUP_DIR_RE = re.compile(r"_backup_v.+_\d{4}_\d{2}_\d{2}_\d{2}_\d{2}$")

# older projects are cleared and rebuilt through the map canvas, so they must be opened in QGIS
MIN_DETACHED_UPDATE_VERSION = "2.0.0"


def tr(message: str) -> str:
    return QCoreApplication.translate("ProjectUpdate", message)


@dataclass
class ProjectUpdateResult:
    project_file: Path
    status: str  # one of the UPDATE_STATUS_* constants
    from_version: str  # "" if unknown
    to_version: str  # "" if unknown
    backup_path: Path | None
    message: str  # user-facing (translated) summary


def find_mzs_projects(root: Path) -> list[Path]:
    """Recursively find MzS Tools project files in root, excluding backup copies."""
    projects: dict[Path, Path] = {}
    # .qgz is scanned first, so it wins over .qgs in the same folder
    for name in ("progetto_MS.qgz", "progetto_MS.qgs"):
        for p in root.rglob(name):
            if any(BACKUP_DIR_RE.search(part) for part in p.parent.relative_to(root).parts):
                continue
            if not (p.parent / "db" / "indagini.sqlite").is_file():
                continue
            projects.setdefault(p.parent, p)
    return sorted(projects.values())


def update_project_file(project_file: Path, backup: bool, feedback: QgsProcessingFeedback) -> ProjectUpdateResult:
    """Update a MzS Tools project file to the current plugin version, without loading it in QGIS.

    Raises:
        QgsProcessingException: if the project cannot be read or the update fails.
    """
    project_file = project_file.resolve()
    project_dir = project_file.parent

    def skipped(message: str, from_version: str = "") -> ProjectUpdateResult:
        return ProjectUpdateResult(project_file, UPDATE_STATUS_SKIPPED, from_version, "", None, message)

    open_project_path = QgsProject.instance().absoluteFilePath()
    if open_project_path and Path(open_project_path).resolve() == project_file:
        return skipped(tr("Project is currently open in QGIS: use the MzS Tools update dialog instead."))

    if not (project_dir / "db" / "indagini.sqlite").is_file():
        return skipped(tr("Not an MzS Tools project (db/indagini.sqlite not found)."))

    # pre-check the version (same as MzSProjectManager.check_project_structure()) so that legacy projects are
    # never loaded
    try:
        version = (project_dir / "progetto" / "versione.txt").read_text().strip()
    except OSError as e:
        raise QgsProcessingException(tr("Cannot read project version") + f": {e}") from e

    try:
        too_old = parse_version(version) < parse_version(MIN_DETACHED_UPDATE_VERSION)
    except InvalidVersion as e:
        raise QgsProcessingException(tr("Invalid project version") + f": '{version}'") from e
    if too_old:
        return skipped(
            tr("Projects older than 2.0.0 must be updated by opening them in QGIS with MzS Tools."),
            from_version=version,
        )

    project = QgsProject()
    manager = None
    try:
        if not project.read(str(project_file)):
            raise QgsProcessingException(tr("Cannot read project") + f" {project_file}: {project.error()}")

        manager = MzSProjectManager()
        manager.init_manager(project)
        if manager.db_manager is None:
            raise QgsProcessingException(tr("Cannot connect to the project database."))

        if not manager.project_updateable:
            current_version = manager.project_version or ""
            return ProjectUpdateResult(
                project_file,
                UPDATE_STATUS_UP_TO_DATE,
                current_version,
                current_version,
                None,
                tr("Project is already up to date."),
            )

        from_version = manager.project_version or ""
        backup_path = manager.backup_project() if backup else None
        if backup_path:
            feedback.pushInfo(tr("Project backup saved in") + f" {backup_path}")

        try:
            manager.update_db()
            manager.update_project()
        except Exception as e:
            msg = f"{tr('An error occurred during project update.')} {e}"
            if backup_path:
                msg += f" {tr('Backup')}: {backup_path}"
            raise QgsProcessingException(msg) from e

        # re-read versione.txt and report any remaining issue
        manager.check_project_structure()
        for issue_type, issues in (manager.project_issues or {}).items():
            for issue in issues:
                feedback.pushWarning(f"{issue_type}: {issue}")

        to_version = manager.project_version or ""
        return ProjectUpdateResult(
            project_file,
            UPDATE_STATUS_UPDATED,
            from_version,
            to_version,
            backup_path,
            tr("Project updated from version {0} to version {1}.").format(from_version, to_version),
        )
    finally:
        # release SQLite handles before the next project
        if manager is not None:
            manager.cleanup_db_connection()
        project.clear()
