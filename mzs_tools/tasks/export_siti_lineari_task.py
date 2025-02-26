import logging
from pathlib import Path

from qgis.core import QgsTask
from qgis.utils import spatialite_connect

from ..core.mzs_project_manager import MzSProjectManager
from ..tasks.common_functions import setup_mdb_connection


class ExportSitiLineariTask(QgsTask):
    def __init__(self, exported_project_path: Path, data_source: str):
        super().__init__("Export siti lineari (siti, indagini, parametri)", QgsTask.CanCancel)

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

        self.tot_steps = 6

    def run(self):
        self.logger.info(f"{'#' * 15} Starting task {self.description()}")

        self.iterations = 0

        try:
            # prepare data
            self.logger.debug("Getting sito_lineare data...")
            self.sito_lineare_data = self.get_sito_lineare_data()
            self._advance_progress()
            self.logger.debug("Getting indagini_lineari data...")
            self.indagini_lineari_data = self.get_indagini_lineari_data()
            self._advance_progress()
            self.logger.debug("Getting parametri_lineari data...")
            self.parametri_lineari_data = self.get_parametri_lineari_data()
            self._advance_progress()

            if self.isCanceled():
                return False

            if self.data_source == "mdb":
                # setup mdb connection
                self.logger.debug("Setting up mdb connection...")
                try:
                    connected, self.mdb_connection = setup_mdb_connection(self.mdb_path)
                except Exception as e:
                    self.exception = e
                    return False

                if not connected:
                    return False

                # insert data in mdb
                self.logger.debug("Inserting siti_lineari data in mdb...")
                insert_errors = self.mdb_connection.insert_siti_lineari(self.sito_lineare_data)
                if insert_errors:
                    self.logger.warning(
                        f"Errors occurred during siti_lineari data insertion, the following records have been discarded: {insert_errors}"
                    )
                self._advance_progress()
                if self.isCanceled():
                    return False

                self.logger.debug("Inserting indagini_lineari data in mdb...")
                insert_errors = self.mdb_connection.insert_indagini_lineari(self.indagini_lineari_data)
                if insert_errors:
                    self.logger.warning(
                        f"Errors occurred during indagini_lineari data insertion, the following records have been discarded: {insert_errors}"
                    )
                self._advance_progress()
                if self.isCanceled():
                    return False

                self.logger.debug("Inserting parametri_lineari data in mdb...")
                insert_errors = self.mdb_connection.insert_parametri_lineari(self.parametri_lineari_data)
                if insert_errors:
                    self.logger.warning(
                        f"Errors occurred during parametri_lineari data insertion, the following records have been discarded: {insert_errors}"
                    )
                self._advance_progress()
                if self.isCanceled():
                    return False

            elif self.data_source == "sqlite":
                # TODO: implement sqlite export
                pass

        except Exception as e:
            self.exception = e
            return False

        finally:
            # close connections
            if self.mdb_connection:
                self.logger.debug("Closing mdb connection...")
                self.mdb_connection.close()
            if self.spatialite_db_connection:
                self.logger.debug("Closing spatialite connection...")
                self.spatialite_db_connection.close()

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

    def _advance_progress(self):
        self.iterations += 1
        self.setProgress(self.iterations * 100 / self.tot_steps)

    def get_spatialite_db_connection(self):
        if not self.spatialite_db_connection:
            self.spatialite_db_connection = spatialite_connect(str(self.prj_manager.db_path))
        return self.spatialite_db_connection

    def get_sito_lineare_data(self):
        with self.get_spatialite_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """SELECT pkuid, id_sln, ubicazione_prov, ubicazione_com, acoord_x, acoord_y, bcoord_x, bcoord_y,
                mod_identcoord, desc_modcoord, aquota, bquota, data_sito, note_sito FROM sito_lineare"""
            )
            data = cursor.fetchall()
            cursor.close()
        return data

    def get_indagini_lineari_data(self):
        with self.get_spatialite_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """SELECT sl.pkuid, il.pkuid, classe_ind, tipo_ind, id_indln, id_indlnex, arch_ex, note_indln,
                data_ind, doc_pag, substr(doc_ind, instr(doc_ind, id_indln), length(doc_ind) +1) AS doc_ind
                FROM indagini_lineari il JOIN sito_lineare sl ON il.id_sln = sl.id_sln"""
            )
            data = cursor.fetchall()
            cursor.close()
        return data

    def get_parametri_lineari_data(self):
        with self.get_spatialite_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """SELECT il.pkuid, pl.pkuid, tipo_parln, id_parln, prof_top, prof_bot, spessore, quota_slm_top,
                quota_slm_bot, valore, attend_mis, note_par, data_par FROM parametri_lineari pl JOIN indagini_lineari
                il ON pl.id_indln = il.id_indln"""
            )
            data = cursor.fetchall()
            cursor.close()
        return data
