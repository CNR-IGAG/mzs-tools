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

"""Export MzS Tools projects to standard SM projects on detached QgsProject instances (used by the processing
algorithms)."""

import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from packaging.version import parse as parse_version
from qgis.core import QgsProcessingException, QgsProcessingFeedback, QgsProject, QgsVectorLayerExporter
from qgis.PyQt.QtCore import QCoreApplication

from ..__about__ import DIR_PLUGIN_ROOT, __base_version__, __version__
from ..core.mzs_project_manager import MzSProjectManager
from ..tasks.access_db_connection import AccessDbConnection
from ..tasks.export_project_files_task import ExportProjectFilesTask
from ..tasks.export_siti_lineari_task import ExportSitiLineariTask
from ..tasks.export_siti_puntuali_task import ExportSitiPuntualiTask
from ..tasks.standard_project import (
    CDI_TABELLE_MDB_TEMPLATE,
    EXPORT_LOGGER_NAME,
    STANDARD_EXPORT_VERSION,
    STANDARD_SHAPEFILE_EXPORTS,
    create_standard_export_folder,
    postprocess_exported_shapefile,
)
from .feedback_log import feedback_file_log
from .project_update import read_project_version

EXPORT_STATUS_EXPORTED = "exported"
EXPORT_STATUS_SKIPPED = "skipped"

# the index matches the options of the OUTPUT_FORMAT algorithm parameter
INDAGINI_FORMATS = ("sqlite", "mdb")


def tr(message: str) -> str:
    return QCoreApplication.translate("StandardProjectExport", message)


@dataclass
class StandardProjectExportResult:
    project_file: Path
    status: str  # one of the EXPORT_STATUS_* constants
    export_path: Path | None
    cod_istat: str  # "" if skipped before reading the project
    log_file: Path | None
    message: str  # user-facing (translated) summary


def check_mdb_available() -> None:
    """Check that the Access database template can be opened (Java and the Python dependencies are available).

    Raises:
        QgsProcessingException: if the Access database cannot be opened.
    """
    path = DIR_PLUGIN_ROOT / "data" / CDI_TABELLE_MDB_TEMPLATE
    conn = AccessDbConnection(str(path))
    try:
        connected = conn.open()
    except Exception as e:
        raise QgsProcessingException(
            tr("Access database not available") + f": {str(e) or e.__class__.__name__}"
        ) from e
    if not connected:
        raise QgsProcessingException(tr("Access database not available") + f": {path}")
    conn.close()


def export_project_to_standard(
    project_file: Path, output_dir: Path, *, indagini_format: str, feedback: QgsProcessingFeedback
) -> StandardProjectExportResult:
    """Export a MzS Tools project to a new standard project folder in output_dir, without loading it in QGIS.

    Args:
        indagini_format: "sqlite" or "mdb", the format of the CdI_Tabelle survey database.

    Raises:
        QgsProcessingException: if the project cannot be read or the export fails (the export folder is kept when
            only some of the data cannot be exported).
    """
    project_file = project_file.resolve()
    project_dir = project_file.parent

    def skipped(message: str, cod_istat: str = "") -> StandardProjectExportResult:
        return StandardProjectExportResult(project_file, EXPORT_STATUS_SKIPPED, None, cod_istat, None, message)

    if not (project_dir / "db" / "indagini.sqlite").is_file():
        return skipped(tr("Not an MzS Tools project (db/indagini.sqlite not found)."))

    # the project is never loaded if it needs an update (the GUI disables the export in this case)
    _version, parsed = read_project_version(project_dir)
    if parsed < parse_version(__base_version__):
        return skipped(
            tr(
                "The project must be updated to the current MzS Tools version before the export: use the "
                "'Update MzS Tools project' algorithm."
            )
        )

    open_project_path = QgsProject.instance().absoluteFilePath()
    if open_project_path and Path(open_project_path).resolve() == project_file:
        feedback.pushWarning(tr("Project is currently open in QGIS: unsaved changes are not exported."))

    project = QgsProject()
    manager = MzSProjectManager()
    try:
        if not project.read(str(project_file)):
            raise QgsProcessingException(tr("Cannot read project") + f" {project_file}: {project.error()}")
        manager.init_manager(project)
        if manager.db_manager is None:
            raise QgsProcessingException(tr("Cannot connect to the project database."))
        comune_data = manager.get_project_comune_data()
        if comune_data is None:
            raise QgsProcessingException(tr("Cannot read the municipality data from the project database."))

        log_file = project_dir / "Allegati" / "log" / f"data_export_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.log"
        failed: list[str] = []
        with feedback_file_log(
            EXPORT_LOGGER_NAME,
            log_file,
            feedback,
            [
                f"MzS Tools version {__version__} - Data export log",
                f"Exporting project {project_file} to {output_dir} using {indagini_format} for Indagini data",
                "############### Data export started",
            ],
        ):
            logger = logging.getLogger(EXPORT_LOGGER_NAME)
            try:
                output_dir.mkdir(parents=True, exist_ok=True)
                export_path = create_standard_export_folder(
                    output_dir,
                    comune_data.cod_istat,
                    comune_data.comune,
                    indagini_format,
                    STANDARD_EXPORT_VERSION,
                    CDI_TABELLE_MDB_TEMPLATE,
                )
            except OSError as e:
                raise QgsProcessingException(tr("Cannot create the export folder") + f": {e}") from e
            logger.info(f"Exported project path: {export_path}")

            for table_name, (shp_name, role) in STANDARD_SHAPEFILE_EXPORTS.items():
                if feedback.isCanceled():
                    raise QgsProcessingException(tr("Export cancelled."))
                layer_id = manager.find_layer_by_table_name_role(table_name, role)
                if not layer_id:
                    logger.warning(f"Layer {table_name} ({role}) not found: not exported")
                    continue
                layer = project.mapLayer(layer_id)
                path = export_path / shp_name
                # same export as QgsVectorLayerExporterTask in the GUI; positional arguments select the CRS overload
                error, error_msg = QgsVectorLayerExporter.exportLayer(
                    layer, str(path), "ogr", layer.crs(), False, {"driverName": "ESRI Shapefile"}
                )
                if error != QgsVectorLayerExporter.NoError:
                    logger.error(f"Error during export of {table_name}: {error_msg}")
                    failed.append(f"{table_name}: {error_msg}")
                    continue
                try:
                    postprocess_exported_shapefile(table_name, path)
                except Exception as e:
                    logger.error(f"Error during post-processing of {table_name}: {e}")
                    failed.append(f"{table_name}: {e}")

            # lineari before puntuali, as in the GUI (where lineari is a subtask of puntuali)
            for task in (
                ExportSitiLineariTask(export_path, indagini_format, prj_manager=manager),
                ExportSitiPuntualiTask(export_path, indagini_format, prj_manager=manager),
                ExportProjectFilesTask(export_path, prj_manager=manager),
            ):
                if feedback.isCanceled():
                    raise QgsProcessingException(tr("Export cancelled."))
                # run synchronously: finished() is not called, as it re-raises the task exception
                if task.run():
                    logger.info(f"Task {task.description()} completed with {task.iterations} iterations")
                else:
                    logger.error(f"Task {task.description()} failed: {task.exception}")
                    failed.append(f"{task.description()}: {task.exception}")

        if failed:
            raise QgsProcessingException(
                tr("Data export completed with errors. Check the log for details.")
                + f" {log_file}\n"
                + "\n".join(failed)
            )

        return StandardProjectExportResult(
            project_file,
            EXPORT_STATUS_EXPORTED,
            export_path,
            comune_data.cod_istat,
            log_file,
            tr("Project exported to {0}.").format(export_path),
        )
    finally:
        # release SQLite handles before the next project
        manager.cleanup_db_connection()
        project.clear()
