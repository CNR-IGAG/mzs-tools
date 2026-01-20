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

import logging
import shutil
from pathlib import Path

from qgis.core import QgsTask

from ..core.mzs_project_manager import MzSProjectManager


class ExportProjectFilesTask(QgsTask):
    def __init__(self, exported_project_path: Path):
        super().__init__("Export project files (attachments, plots, etc.)", QgsTask.Flag.CanCancel)

        self.iterations = 0
        self.exception = None

        # the logger is configured in the import data dialog module
        self.logger = logging.getLogger("mzs_tools.tasks.export_data")

        self.prj_manager = MzSProjectManager.instance()
        self.exported_project_path = exported_project_path

    def run(self):
        if not self.prj_manager.project_path or not self.exported_project_path:
            self.logger.error("Project path or exported project path is not set")
            return False

        self.logger.info(f"{'#' * 15} Starting task {self.description()}")
        self.iterations = 0

        try:
            # copy attachments
            self.logger.debug("Copying indagini attachments (Indagini/Documenti)...")
            orig_path = self.prj_manager.project_path / "Allegati" / "Documenti"
            dest_path = self.exported_project_path / "Indagini" / "Documenti"
            shutil.copytree(orig_path, dest_path, dirs_exist_ok=True)
            self.iterations += 1
            if self.isCanceled():
                return False

            # copy plots
            self.logger.debug("Copying plots (Indagini/Plots)...")
            orig_path = self.prj_manager.project_path / "Allegati" / "Plot"
            dest_path = self.exported_project_path / "Plot"
            shutil.copytree(orig_path, dest_path, dirs_exist_ok=True)
            self.iterations += 1
            if self.isCanceled():
                return False

            # copy spettri
            self.logger.debug("Copying spettri (Indagini/Spettri)...")
            orig_path = self.prj_manager.project_path / "Allegati" / "Spettri"
            dest_path = self.exported_project_path / "MS23" / "Spettri"
            shutil.copytree(orig_path, dest_path, dirs_exist_ok=True)
            self.iterations += 1
            if self.isCanceled():
                return False

        except Exception as e:
            self.exception = e
            return False

        return True

    def finished(self, result):
        if result:
            self.logger.info(f"Task {self.description()} completed with {self.iterations} iterations")
        else:
            if self.exception is None:
                self.logger.warning(f"Task {self.description()} was canceled")
            else:
                self.logger.error(f"Task {self.description()} failed: {self.exception}")
                raise self.exception

    def cancel(self):
        self.logger.warning(f"Task {self.description()} was canceled")
        super().cancel()
