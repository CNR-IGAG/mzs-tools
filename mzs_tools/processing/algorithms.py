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

from pathlib import Path

from qgis.core import (
    QgsProcessingAlgorithm,
    QgsProcessingOutputFolder,
    QgsProcessingOutputNumber,
    QgsProcessingOutputString,
    QgsProcessingParameterBoolean,
    QgsProcessingParameterEnum,
    QgsProcessingParameterFile,
    QgsProcessingParameterFolderDestination,
    QgsProcessingParameterString,
)
from qgis.PyQt.QtCore import QCoreApplication

from .project_update import (
    UPDATE_STATUS_SKIPPED,
    UPDATE_STATUS_UP_TO_DATE,
    UPDATE_STATUS_UPDATED,
    find_mzs_projects,
    update_project_file,
)
from .standard_project_export import (
    EXPORT_STATUS_EXPORTED,
    EXPORT_STATUS_SKIPPED,
    INDAGINI_FORMATS,
    check_mdb_available,
    export_project_to_standard,
)
from .standard_project_import import (
    IMPORT_STATUS_CREATED,
    IMPORT_STATUS_SKIPPED,
    INDAGINI_SOURCES,
    find_standard_projects,
    import_standard_project,
    load_comuni_names,
)


class _MzSToolsAlgorithmBase(QgsProcessingAlgorithm):
    def flags(self):
        # the algorithms write QGIS projects, layouts and images: they must run on the main thread
        return super().flags() | QgsProcessingAlgorithm.FlagNoThreading

    def createInstance(self):
        return self.__class__()

    def tr(self, message: str) -> str:
        # pylupdate5 files self.tr() calls under the class that contains them: strings defined in the
        # base classes are looked up through the MRO
        for cls in type(self).__mro__:
            translated = QCoreApplication.translate(cls.__name__, message)
            if translated != message:
                return translated
        return message

    def _add_output_folder_parameter(self, description: str):
        # a destination parameter also adds the OUTPUT_FOLDER output, so that algorithms can be chained in models
        self.addParameter(QgsProcessingParameterFolderDestination("OUTPUT_FOLDER", description))

    def _output_folder(self, parameters, context) -> Path:
        # QGIS does not create the destination folder (e.g. a temporary one)
        folder = Path(self.parameterAsFileOutput(parameters, "OUTPUT_FOLDER", context))
        folder.mkdir(parents=True, exist_ok=True)
        return folder


class _MzSProjectUpdateAlgorithmBase(_MzSToolsAlgorithmBase):
    def group(self):
        return self.tr("Project management")

    def groupId(self):
        return "project_management"

    def _add_backup_parameter(self):
        self.addParameter(
            QgsProcessingParameterBoolean(
                "BACKUP", self.tr("Create a backup copy of the project before updating"), defaultValue=True
            )
        )

    def _common_help(self) -> str:
        return self.tr(
            "Before updating, a backup folder named <project>_backup_v<version>_<timestamp> is created next to each "
            "project. Projects older than 2.0.0 are skipped and must be updated by opening them in QGIS. "
            "The project currently open in QGIS is skipped."
        )


class UpdateProjectAlgorithm(_MzSProjectUpdateAlgorithmBase):
    def name(self):
        return "update_project"

    def displayName(self):
        return self.tr("Update MzS Tools project")

    def shortHelpString(self):
        return (
            self.tr(
                "Update a MzS Tools project (progetto_MS.qgz) to the current plugin version. "
                "Use batch mode to update several projects."
            )
            + " "
            + self._common_help()
        )

    def initAlgorithm(self, config=None):
        self.addParameter(
            QgsProcessingParameterFile(
                "INPUT",
                self.tr("MzS Tools project file (progetto_MS.qgz)"),
                behavior=QgsProcessingParameterFile.File,
                fileFilter="QGIS project (*.qgz *.qgs)",
            )
        )
        self._add_backup_parameter()
        self.addOutput(QgsProcessingOutputString("STATUS", self.tr("Update status")))
        self.addOutput(QgsProcessingOutputString("FROM_VERSION", self.tr("Project version before the update")))
        self.addOutput(QgsProcessingOutputString("TO_VERSION", self.tr("Project version after the update")))
        self.addOutput(QgsProcessingOutputString("BACKUP_PATH", self.tr("Backup folder")))
        self.addOutput(QgsProcessingOutputFolder("OUTPUT_FOLDER", self.tr("Project folder")))

    def processAlgorithm(self, parameters, context, feedback):
        project_file = Path(self.parameterAsFile(parameters, "INPUT", context))
        backup = self.parameterAsBoolean(parameters, "BACKUP", context)

        # failures propagate as QgsProcessingException
        result = update_project_file(project_file, backup, feedback)
        if result.status == UPDATE_STATUS_SKIPPED:
            feedback.reportError(result.message, fatalError=False)
        else:
            feedback.pushInfo(result.message)

        return {
            "STATUS": result.status,
            "FROM_VERSION": result.from_version,
            "TO_VERSION": result.to_version,
            "BACKUP_PATH": str(result.backup_path) if result.backup_path else "",
            "OUTPUT_FOLDER": str(project_file.parent),
        }


class UpdateProjectsInFolderAlgorithm(_MzSProjectUpdateAlgorithmBase):
    def name(self):
        return "update_projects_in_folder"

    def displayName(self):
        return self.tr("Update MzS Tools projects in folder")

    def shortHelpString(self):
        return (
            self.tr(
                "Recursively scan a folder for MzS Tools projects and update each of them to the current plugin "
                "version. Backup folders created by previous updates are ignored."
            )
            + " "
            + self._common_help()
        )

    def initAlgorithm(self, config=None):
        self.addParameter(
            QgsProcessingParameterFile(
                "INPUT_FOLDER",
                self.tr("Root folder to scan for MzS Tools projects"),
                behavior=QgsProcessingParameterFile.Folder,
            )
        )
        self._add_backup_parameter()
        self.addOutput(QgsProcessingOutputNumber("UPDATED_COUNT", self.tr("Updated projects")))
        self.addOutput(QgsProcessingOutputNumber("UP_TO_DATE_COUNT", self.tr("Projects already up to date")))
        self.addOutput(QgsProcessingOutputNumber("SKIPPED_COUNT", self.tr("Skipped projects")))
        self.addOutput(QgsProcessingOutputNumber("FAILED_COUNT", self.tr("Failed projects")))
        self.addOutput(QgsProcessingOutputString("FAILED_PROJECTS", self.tr("Failed project files")))
        self.addOutput(QgsProcessingOutputFolder("OUTPUT_FOLDER", self.tr("Scanned folder")))

    def processAlgorithm(self, parameters, context, feedback):
        folder = Path(self.parameterAsFile(parameters, "INPUT_FOLDER", context))
        backup = self.parameterAsBoolean(parameters, "BACKUP", context)

        counts = {UPDATE_STATUS_UPDATED: 0, UPDATE_STATUS_UP_TO_DATE: 0, UPDATE_STATUS_SKIPPED: 0}
        failed: list[str] = []

        # collected before any update, so that backups created during this run are never visited
        projects = find_mzs_projects(folder)
        if not projects:
            feedback.pushWarning(self.tr("No MzS Tools projects found."))

        for i, p in enumerate(projects):
            if feedback.isCanceled():
                break
            feedback.pushInfo(f"[{i + 1}/{len(projects)}] {p}")
            try:
                result = update_project_file(p, backup, feedback)
            except Exception as e:
                failed.append(str(p))
                feedback.reportError(f"{p}: {e}", fatalError=False)
            else:
                counts[result.status] += 1
                if result.status == UPDATE_STATUS_SKIPPED:
                    feedback.reportError(f"{p}: {result.message}", fatalError=False)
                else:
                    feedback.pushInfo(result.message)
            feedback.setProgress(100 * (i + 1) / len(projects))

        if projects:
            feedback.pushInfo(
                self.tr("Updated: {0}, already up to date: {1}, skipped: {2}, failed: {3}").format(
                    counts[UPDATE_STATUS_UPDATED],
                    counts[UPDATE_STATUS_UP_TO_DATE],
                    counts[UPDATE_STATUS_SKIPPED],
                    len(failed),
                )
            )

        return {
            "UPDATED_COUNT": counts[UPDATE_STATUS_UPDATED],
            "UP_TO_DATE_COUNT": counts[UPDATE_STATUS_UP_TO_DATE],
            "SKIPPED_COUNT": counts[UPDATE_STATUS_SKIPPED],
            "FAILED_COUNT": len(failed),
            "FAILED_PROJECTS": "\n".join(failed),
            "OUTPUT_FOLDER": str(folder),
        }


class _StandardProjectImportAlgorithmBase(_MzSToolsAlgorithmBase):
    def group(self):
        return self.tr("Standard project import")

    def groupId(self):
        return "standard_project_import"

    def _add_common_parameters(self):
        self._add_output_folder_parameter(self.tr("Output folder for the new MzS Tools projects"))
        self.addParameter(
            QgsProcessingParameterEnum(
                "INDAGINI_SOURCE",
                self.tr("Survey data source"),
                options=[
                    self.tr("Auto (SQLite, then Access, then CSV)"),
                    "SQLite (CdI_Tabelle.sqlite)",
                    "Access (CdI_Tabelle.mdb)",
                    "CSV",
                ],
                defaultValue=0,
            )
        )
        self.addParameter(
            QgsProcessingParameterString(
                "MDB_PASSWORD", self.tr("Access database password"), defaultValue="", optional=True
            )
        )
        self.addParameter(
            QgsProcessingParameterString("STUDY_AUTHOR", self.tr("Study author"), defaultValue="", optional=True)
        )
        self.addParameter(
            QgsProcessingParameterString("AUTHOR_EMAIL", self.tr("Author email"), defaultValue="", optional=True)
        )

    def _common_parameter_values(self, parameters, context) -> dict:
        return {
            "indagini_source": INDAGINI_SOURCES[self.parameterAsEnum(parameters, "INDAGINI_SOURCE", context)],
            "mdb_password": self.parameterAsString(parameters, "MDB_PASSWORD", context) or None,
            "study_author": self.parameterAsString(parameters, "STUDY_AUTHOR", context) or None,
            "author_email": self.parameterAsString(parameters, "AUTHOR_EMAIL", context) or None,
        }

    def _common_help(self) -> str:
        return self.tr(
            "The new project is named <ISTAT code>_<Comune>: if a folder with that name already exists in the output "
            "folder, the standard project is skipped. All the shapefiles and survey sites found are imported. "
            "Importing survey data from the Access database (CdI_Tabelle.mdb) requires Java and the MzS Tools Python "
            "dependencies. If the data import fails, the created project is kept and the import log is saved in its "
            "Allegati/log folder."
        )


class ImportStandardProjectAlgorithm(_StandardProjectImportAlgorithmBase):
    def name(self):
        return "import_standard_project"

    def displayName(self):
        return self.tr("Create MzS Tools project from standard project")

    def shortHelpString(self):
        return (
            self.tr(
                "Create a new MzS Tools project from a standard SM project (shapefiles and CdI_Tabelle survey data). "
                "The ISTAT code is detected from the survey site IDs, unless set explicitly. "
                "Use batch mode to import several projects."
            )
            + " "
            + self._common_help()
        )

    def initAlgorithm(self, config=None):
        self.addParameter(
            QgsProcessingParameterFile(
                "INPUT_FOLDER", self.tr("Standard project folder"), behavior=QgsProcessingParameterFile.Folder
            )
        )
        self.addParameter(
            QgsProcessingParameterString(
                "COD_ISTAT",
                self.tr("ISTAT code of the municipality (empty: detect from the survey sites)"),
                defaultValue="",
                optional=True,
            )
        )
        self.addParameter(
            QgsProcessingParameterFile(
                "CSV_FOLDER",
                self.tr("Folder with the survey data CSV files (empty: 'CSV' subfolder of the standard project)"),
                behavior=QgsProcessingParameterFile.Folder,
                optional=True,
            )
        )
        self._add_common_parameters()
        self.addOutput(QgsProcessingOutputString("STATUS", self.tr("Import status")))
        self.addOutput(QgsProcessingOutputString("PROJECT_PATH", self.tr("New project folder")))
        self.addOutput(QgsProcessingOutputString("COD_ISTAT", self.tr("ISTAT code")))
        self.addOutput(QgsProcessingOutputString("INDAGINI_SOURCE", self.tr("Survey data source")))
        self.addOutput(QgsProcessingOutputString("LOG_FILE", self.tr("Import log file")))

    def processAlgorithm(self, parameters, context, feedback):
        csv_folder = self.parameterAsFile(parameters, "CSV_FOLDER", context)
        output_folder = self._output_folder(parameters, context)

        # failures propagate as QgsProcessingException
        result = import_standard_project(
            Path(self.parameterAsFile(parameters, "INPUT_FOLDER", context)),
            output_folder,
            cod_istat=self.parameterAsString(parameters, "COD_ISTAT", context) or None,
            csv_dir=Path(csv_folder) if csv_folder else None,
            comuni_names=load_comuni_names(),
            feedback=feedback,
            **self._common_parameter_values(parameters, context),
        )
        if result.status == IMPORT_STATUS_SKIPPED:
            feedback.reportError(result.message, fatalError=False)
        else:
            feedback.pushInfo(result.message)

        return {
            "STATUS": result.status,
            "PROJECT_PATH": str(result.project_path) if result.project_path else "",
            "COD_ISTAT": result.cod_istat,
            "INDAGINI_SOURCE": result.indagini_source,
            "LOG_FILE": str(result.log_file) if result.log_file else "",
            "OUTPUT_FOLDER": str(output_folder),
        }


class ImportStandardProjectsInFolderAlgorithm(_StandardProjectImportAlgorithmBase):
    def name(self):
        return "import_standard_projects_in_folder"

    def displayName(self):
        return self.tr("Create MzS Tools projects from standard projects in folder")

    def shortHelpString(self):
        return (
            self.tr(
                "Recursively scan a folder for standard SM projects (folders containing an 'Indagini' subfolder) and "
                "create a new MzS Tools project from each of them. The ISTAT code is detected from the survey site "
                "IDs and the survey data CSV files are searched in the 'CSV' subfolder of each standard project. "
                "The output folder and MzS Tools projects are not scanned."
            )
            + " "
            + self._common_help()
        )

    def initAlgorithm(self, config=None):
        self.addParameter(
            QgsProcessingParameterFile(
                "INPUT_FOLDER",
                self.tr("Root folder to scan for standard projects"),
                behavior=QgsProcessingParameterFile.Folder,
            )
        )
        self._add_common_parameters()
        self.addOutput(QgsProcessingOutputNumber("CREATED_COUNT", self.tr("Created projects")))
        self.addOutput(QgsProcessingOutputNumber("SKIPPED_COUNT", self.tr("Skipped projects")))
        self.addOutput(QgsProcessingOutputNumber("FAILED_COUNT", self.tr("Failed projects")))
        self.addOutput(QgsProcessingOutputString("CREATED_PROJECTS", self.tr("New project folders")))
        self.addOutput(QgsProcessingOutputString("FAILED_PROJECTS", self.tr("Failed standard project folders")))

    def processAlgorithm(self, parameters, context, feedback):
        folder = Path(self.parameterAsFile(parameters, "INPUT_FOLDER", context))
        output_folder = self._output_folder(parameters, context)
        common_values = self._common_parameter_values(parameters, context)

        created: list[str] = []
        skipped = 0
        failed: list[str] = []

        # collected before any creation, so that the new projects are never visited
        projects = find_standard_projects(folder, exclude=output_folder)
        if not projects:
            feedback.pushWarning(self.tr("No standard projects found."))

        comuni_names = load_comuni_names()
        for i, p in enumerate(projects):
            if feedback.isCanceled():
                break
            feedback.pushInfo(f"[{i + 1}/{len(projects)}] {p}")
            try:
                result = import_standard_project(
                    p,
                    output_folder,
                    cod_istat=None,
                    csv_dir=None,
                    comuni_names=comuni_names,
                    feedback=feedback,
                    **common_values,
                )
            except Exception as e:
                failed.append(str(p))
                feedback.reportError(f"{p}: {e}", fatalError=False)
            else:
                if result.status == IMPORT_STATUS_CREATED:
                    created.append(str(result.project_path))
                    feedback.pushInfo(result.message)
                else:
                    skipped += 1
                    feedback.reportError(f"{p}: {result.message}", fatalError=False)
            feedback.setProgress(100 * (i + 1) / len(projects))

        if projects:
            feedback.pushInfo(
                self.tr("Created: {0}, skipped: {1}, failed: {2}").format(len(created), skipped, len(failed))
            )

        return {
            "CREATED_COUNT": len(created),
            "SKIPPED_COUNT": skipped,
            "FAILED_COUNT": len(failed),
            "CREATED_PROJECTS": "\n".join(created),
            "FAILED_PROJECTS": "\n".join(failed),
            "OUTPUT_FOLDER": str(output_folder),
        }


class _StandardProjectExportAlgorithmBase(_MzSToolsAlgorithmBase):
    def group(self):
        return self.tr("Standard project export")

    def groupId(self):
        return "standard_project_export"

    def _add_common_parameters(self):
        self._add_output_folder_parameter(self.tr("Output folder for the exported standard projects"))
        self.addParameter(
            QgsProcessingParameterEnum(
                "OUTPUT_FORMAT",
                self.tr("Survey data output format"),
                options=["SQLite (CdI_Tabelle.sqlite)", "Access (CdI_Tabelle.mdb)"],
                defaultValue=0,
            )
        )

    def _indagini_format(self, parameters, context) -> str:
        fmt = INDAGINI_FORMATS[self.parameterAsEnum(parameters, "OUTPUT_FORMAT", context)]
        if fmt == "mdb":
            # raises before anything is written
            check_mdb_available()
        return fmt

    def _common_help(self) -> str:
        return self.tr(
            "The project is exported in a folder named <ISTAT code>_<Comune>_S42_Shapefile inside the output folder "
            "(a timestamp is appended if the folder already exists), with the shapefiles, the CdI_Tabelle survey "
            "database and the attachments required by the SM Standards. Projects that must be updated to the current "
            "MzS Tools version are skipped. Exporting survey data to the Access database (CdI_Tabelle.mdb) requires "
            "Java and the MzS Tools Python dependencies. The export log is saved in the Allegati/log folder of each "
            "project."
        )


class ExportProjectToStandardAlgorithm(_StandardProjectExportAlgorithmBase):
    def name(self):
        return "export_project_to_standard"

    def displayName(self):
        return self.tr("Export MzS Tools project to standard project")

    def shortHelpString(self):
        return (
            self.tr(
                "Export a MzS Tools project (progetto_MS.qgz) to the standard SM project structure. "
                "Use batch mode to export several projects."
            )
            + " "
            + self._common_help()
        )

    def initAlgorithm(self, config=None):
        self.addParameter(
            QgsProcessingParameterFile(
                "INPUT",
                self.tr("MzS Tools project file (progetto_MS.qgz)"),
                behavior=QgsProcessingParameterFile.File,
                fileFilter="QGIS project (*.qgz *.qgs)",
            )
        )
        self._add_common_parameters()
        self.addOutput(QgsProcessingOutputString("STATUS", self.tr("Export status")))
        self.addOutput(QgsProcessingOutputString("EXPORT_PATH", self.tr("Exported standard project folder")))
        self.addOutput(QgsProcessingOutputString("COD_ISTAT", self.tr("ISTAT code")))
        self.addOutput(QgsProcessingOutputString("LOG_FILE", self.tr("Export log file")))

    def processAlgorithm(self, parameters, context, feedback):
        fmt = self._indagini_format(parameters, context)
        output_folder = self._output_folder(parameters, context)

        # failures propagate as QgsProcessingException
        result = export_project_to_standard(
            Path(self.parameterAsFile(parameters, "INPUT", context)),
            output_folder,
            indagini_format=fmt,
            feedback=feedback,
        )
        if result.status == EXPORT_STATUS_SKIPPED:
            feedback.reportError(result.message, fatalError=False)
        else:
            feedback.pushInfo(result.message)

        return {
            "STATUS": result.status,
            "EXPORT_PATH": str(result.export_path) if result.export_path else "",
            "COD_ISTAT": result.cod_istat,
            "LOG_FILE": str(result.log_file) if result.log_file else "",
            "OUTPUT_FOLDER": str(output_folder),
        }


class ExportProjectsInFolderToStandardAlgorithm(_StandardProjectExportAlgorithmBase):
    def name(self):
        return "export_projects_in_folder_to_standard"

    def displayName(self):
        return self.tr("Export MzS Tools projects in folder to standard projects")

    def shortHelpString(self):
        return (
            self.tr(
                "Recursively scan a folder for MzS Tools projects and export each of them to the standard SM project "
                "structure. Backup folders created by project updates are ignored."
            )
            + " "
            + self._common_help()
        )

    def initAlgorithm(self, config=None):
        self.addParameter(
            QgsProcessingParameterFile(
                "INPUT_FOLDER",
                self.tr("Root folder to scan for MzS Tools projects"),
                behavior=QgsProcessingParameterFile.Folder,
            )
        )
        self._add_common_parameters()
        self.addOutput(QgsProcessingOutputNumber("EXPORTED_COUNT", self.tr("Exported projects")))
        self.addOutput(QgsProcessingOutputNumber("SKIPPED_COUNT", self.tr("Skipped projects")))
        self.addOutput(QgsProcessingOutputNumber("FAILED_COUNT", self.tr("Failed projects")))
        self.addOutput(QgsProcessingOutputString("EXPORTED_PATHS", self.tr("Exported standard project folders")))
        self.addOutput(QgsProcessingOutputString("FAILED_PROJECTS", self.tr("Failed project files")))

    def processAlgorithm(self, parameters, context, feedback):
        folder = Path(self.parameterAsFile(parameters, "INPUT_FOLDER", context))
        fmt = self._indagini_format(parameters, context)
        output_folder = self._output_folder(parameters, context)

        exported: list[str] = []
        skipped = 0
        failed: list[str] = []

        # the exported standard projects contain no progetto_MS.qgz, so the output folder needs no exclusion
        projects = find_mzs_projects(folder)
        if not projects:
            feedback.pushWarning(self.tr("No MzS Tools projects found."))

        for i, p in enumerate(projects):
            if feedback.isCanceled():
                break
            feedback.pushInfo(f"[{i + 1}/{len(projects)}] {p}")
            try:
                result = export_project_to_standard(p, output_folder, indagini_format=fmt, feedback=feedback)
            except Exception as e:
                failed.append(str(p))
                feedback.reportError(f"{p}: {e}", fatalError=False)
            else:
                if result.status == EXPORT_STATUS_EXPORTED:
                    exported.append(str(result.export_path))
                    feedback.pushInfo(result.message)
                else:
                    skipped += 1
                    feedback.reportError(f"{p}: {result.message}", fatalError=False)
            feedback.setProgress(100 * (i + 1) / len(projects))

        if projects:
            feedback.pushInfo(
                self.tr("Exported: {0}, skipped: {1}, failed: {2}").format(len(exported), skipped, len(failed))
            )

        return {
            "EXPORTED_COUNT": len(exported),
            "SKIPPED_COUNT": skipped,
            "FAILED_COUNT": len(failed),
            "EXPORTED_PATHS": "\n".join(exported),
            "FAILED_PROJECTS": "\n".join(failed),
            "OUTPUT_FOLDER": str(output_folder),
        }
