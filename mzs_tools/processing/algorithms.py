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
    QgsProcessingOutputNumber,
    QgsProcessingOutputString,
    QgsProcessingParameterBoolean,
    QgsProcessingParameterFile,
)
from qgis.PyQt.QtCore import QCoreApplication

from .project_update import (
    UPDATE_STATUS_SKIPPED,
    UPDATE_STATUS_UP_TO_DATE,
    UPDATE_STATUS_UPDATED,
    find_mzs_projects,
    update_project_file,
)


class _MzSProjectUpdateAlgorithmBase(QgsProcessingAlgorithm):
    def group(self):
        return self.tr("Project management")

    def groupId(self):
        return "project_management"

    def flags(self):
        # the update writes QGIS projects, layouts and images: it must run on the main thread
        return super().flags() | QgsProcessingAlgorithm.FlagNoThreading

    def createInstance(self):
        return self.__class__()

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

    def tr(self, message: str) -> str:
        return QCoreApplication.translate(self.__class__.__name__, message)


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
        }
