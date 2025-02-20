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

        self.debug = debug

    def run(self):
        self.logger.info(f"{'#'*15} Starting task {self.description()}")

        self.iterations = 0

        try:
            # prepare data
            self.sito_puntuale_data = self.get_sito_puntuale_data()
            self.iterations += 1
            # self.indagini_puntuali_data = self.prj_manager.get_indagini_puntuali_data()
            # self.parametri_puntuali_data = self.prj_manager.get_parametri_puntuali_data()
            # self.curve_data = self.prj_manager.get_curve_data()

            if self.data_source == "mdb":
                # setup mdb connection
                try:
                    connected, self.mdb_connection = setup_mdb_connection(self.mdb_path)
                except Exception as e:
                    self.exception = e
                    return False

                if not connected:
                    return False

                # insert data in mdb
                self.mdb_connection.insert_siti_puntuali(self.sito_puntuale_data)
                self.iterations += 1

            elif self.data_source == "sqlite":
                # TODO: implement sqlite export
                pass

            # close connections
            if self.mdb_connection:
                self.mdb_connection.close()
            if self.spatialite_db_connection:
                self.spatialite_db_connection.close()

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

    def get_spatialite_db_connection(self):
        if not self.spatialite_db_connection:
            self.spatialite_db_connection = spatialite_connect(str(self.prj_manager.db_path))
        return self.spatialite_db_connection

    def get_sito_puntuale_data(self):
        with self.get_spatialite_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """SELECT pkuid, id_spu, ubicazione_prov, ubicazione_com, indirizzo, coord_x, coord_y, mod_identcoord,
                    desc_modcoord, quota_slm, modo_quota, data_sito, note_sito FROM sito_puntuale"""
            )
            data = cursor.fetchall()
            cursor.close()
        return data
