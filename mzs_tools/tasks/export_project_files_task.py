import logging
import shutil
from pathlib import Path

from qgis.core import QgsTask

from mzs_tools.core.mzs_project_manager import MzSProjectManager


class ExportProjectFilesTask(QgsTask):
    def __init__(
        self,
        exported_project_path: Path,
        debug: bool = False,
    ):
        super().__init__("Export project files (attachments, plots, etc.)", QgsTask.CanCancel)

        self.iterations = 0
        self.exception = None

        # the logger is configured in the import data dialog module
        self.logger = logging.getLogger("mzs_tools.tasks.export_data")

        self.prj_manager = MzSProjectManager.instance()
        self.exported_project_path = exported_project_path

        self.debug = debug

    def run(self):
        self.logger.info(f"{'#'*15} Starting task {self.description()}")

        self.iterations = 0

        try:
            # copy attachments
            self.logger.debug("Copying indagini attachments (Indagini/Documenti)...")
            orig_path = self.prj_manager.project_path / "Allegati" / "Documenti"
            dest_path = self.exported_project_path / "Indagini" / "Documenti"
            shutil.copytree(orig_path, dest_path, dirs_exist_ok=True)
            self.iterations += 1

            # copy plots
            self.logger.debug("Copying plots (Indagini/Plots)...")
            orig_path = self.prj_manager.project_path / "Allegati" / "Plot"
            dest_path = self.exported_project_path / "Plot"
            shutil.copytree(orig_path, dest_path, dirs_exist_ok=True)
            self.iterations += 1

            # copy spettri
            self.logger.debug("Copying spettri (Indagini/Spettri)...")
            orig_path = self.prj_manager.project_path / "Allegati" / "Spettri"
            dest_path = self.exported_project_path / "MS23" / "Spettri"
            shutil.copytree(orig_path, dest_path, dirs_exist_ok=True)
            self.iterations += 1

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
