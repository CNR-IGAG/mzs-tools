import logging
import shutil
from datetime import datetime
from pathlib import Path

from qgis.core import QgsTask, QgsVectorLayer, QgsVectorFileWriter
from qgis.utils import spatialite_connect

from mzs_tools.core.mzs_project_manager import MzSProjectManager
from mzs_tools.plugin_utils.misc import retry_on_lock
from mzs_tools.tasks.common_functions import setup_mdb_connection


class ExportSitiPuntualiTask(QgsTask):
    def __init__(
        self,
        exported_project_path: Path,
        data_source: str,
        debug: bool = False,
    ):
        super().__init__("Export siti puntuali (siti, indagini, parametri, curve)", QgsTask.CanCancel)

        self.iterations = 0
        self.exception = None

        # the logger is configured in the import data dialog module
        self.logger = logging.getLogger("mzs_tools.tasks.export_data")

        self.data_source = data_source

        self.prj_manager = MzSProjectManager.instance()
        self.spatialite_db_connection = None
        self.mdb_connection = None

        self.exported_project_path = exported_project_path
        self.mdb_path = self.exported_project_path / "Indagini" / "CdI_Tabelle.mdb"

        self.siti_puntuali_shapefile = None
        self.num_siti = 0

        self.debug = debug

    def run(self):
        self.logger.info(f"{'#'*15} Starting task {self.description()}")
        if self.debug:
            self.logger.warning(f"\n{'#'*50}\n# Running in DEBUG mode! Data will be DESTROYED! #\n{'#'*50}")

        self.iterations = 0

        try:
            pass

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
