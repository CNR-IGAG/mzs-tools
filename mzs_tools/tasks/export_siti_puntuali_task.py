import logging
from pathlib import Path

from qgis.core import QgsTask
from qgis.utils import spatialite_connect

from ..core.mzs_project_manager import MzSProjectManager
from ..tasks.common_functions import setup_mdb_connection


class ExportSitiPuntualiTask(QgsTask):
    def __init__(self, exported_project_path: Path, data_source: str):
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

        self.tot_steps = 10

    def run(self):
        self.logger.info(f"{'#' * 15} Starting task {self.description()}")

        self.iterations = 0

        try:
            # prepare data
            self.logger.debug("Getting metadata data...")
            self.metadata_data = self.get_metadata_data()
            self._advance_progress()
            self.logger.debug("Getting sito_puntuale data...")
            self.sito_puntuale_data = self.get_sito_puntuale_data()
            self._advance_progress()
            self.logger.debug("Getting indagini_puntuali data...")
            self.indagini_puntuali_data = self.get_indagini_puntuali_data()
            self._advance_progress()
            self.logger.debug("Getting parametri_puntuali data...")
            self.parametri_puntuali_data = self.get_parametri_puntuali_data()
            self._advance_progress()
            self.logger.debug("Getting curve data...")
            self.curve_data = self.get_curve_data()
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

                # insert metadata first...
                self.logger.debug("Inserting metadata in mdb...")
                insert_errors = self.mdb_connection.insert_metadata(self.metadata_data)
                if insert_errors:
                    self.logger.warning(
                        f"Errors occurred during metadata insertion, the following records have been discarded: {insert_errors}"
                    )
                self._advance_progress()
                if self.isCanceled():
                    return False

                # insert siti, parametri, indagini, curve
                self.logger.debug("Inserting siti_puntuali data in mdb...")
                insert_errors = self.mdb_connection.insert_siti_puntuali(self.sito_puntuale_data)
                if insert_errors:
                    self.logger.warning(
                        f"Errors occurred during siti_puntuali data insertion, the following records have been discarded: {insert_errors}"
                    )
                self._advance_progress()
                if self.isCanceled():
                    return False

                self.logger.debug("Inserting indagini_puntuali data in mdb...")
                insert_errors = self.mdb_connection.insert_indagini_puntuali(self.indagini_puntuali_data)
                if insert_errors:
                    self.logger.warning(
                        f"Errors occurred during indagini_puntuali data insertion, the following records have been discarded: {insert_errors}"
                    )
                self._advance_progress()
                if self.isCanceled():
                    return False

                self.logger.debug("Inserting parametri_puntuali data in mdb...")
                insert_errors = self.mdb_connection.insert_parametri_puntuali(self.parametri_puntuali_data)
                if insert_errors:
                    self.logger.warning(
                        f"Errors occurred during parametri_puntuali data insertion, the following records have been discarded: {insert_errors}"
                    )
                self._advance_progress()
                if self.isCanceled():
                    return False

                self.logger.debug("Inserting curve data in mdb...")
                insert_errors = self.mdb_connection.insert_curve(self.curve_data)
                if insert_errors:
                    self.logger.warning(
                        f"Errors occurred during curve data insertion, the following records have been discarded: {insert_errors}"
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

    def get_indagini_puntuali_data(self):
        with self.get_spatialite_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """SELECT sp.pkuid, ip.pkuid, classe_ind, tipo_ind, id_indpu, id_indpuex, arch_ex, note_ind, prof_top,
                prof_bot, spessore, quota_slm_top, quota_slm_bot, data_ind, doc_pag, substr(doc_ind, instr(doc_ind,
                sp.id_spu), length(doc_ind) +1) AS doc_ind, sp.id_spu FROM indagini_puntuali ip JOIN sito_puntuale sp ON
                ip.id_spu = sp.id_spu"""
            )
            data = cursor.fetchall()
            cursor.close()
        return data

    def get_parametri_puntuali_data(self):
        with self.get_spatialite_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """SELECT ip.pkuid, pp.pkuid, tipo_parpu, id_parpu, pp.prof_top, pp.prof_bot, pp.spessore,
                pp.quota_slm_top, pp.quota_slm_bot, valore, attend_mis, substr(tab_curve, instr(tab_curve, ip.id_indpu),
                length(tab_curve) +1) AS tab_curve, note_par, data_par, ip.id_indpu FROM parametri_puntuali pp JOIN
                indagini_puntuali ip ON pp.id_indpu = ip.id_indpu"""
            )
            data = cursor.fetchall()
            cursor.close()
        return data

    def get_curve_data(self):
        with self.get_spatialite_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """SELECT pp.pkuid, c.pkuid, cond_curve, varx, vary FROM curve c JOIN parametri_puntuali pp ON
                c.id_parpu = pp.id_parpu"""
            )
            data = cursor.fetchall()
            cursor.close()
        return data

    def get_metadata_data(self):
        with self.get_spatialite_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """SELECT id_metadato, liv_gerarchico, resp_metadato_nome,
                    resp_metadato_email, resp_metadato_sito, data_metadato, srs_dati, proprieta_dato_nome, proprieta_dato_email, proprieta_dato_sito, data_dato, ruolo, desc_dato,
                    formato, tipo_dato, contatto_dato_nome, contatto_dato_email, contatto_dato_sito, keywords, keywords_inspire, limitazione, vincoli_accesso, vincoli_fruibilita,
                    vincoli_sicurezza, scala, categoria_iso, estensione_ovest, estensione_est, estensione_sud, estensione_nord, formato_dati, distributore_dato_nome,
                    distributore_dato_telefono, distributore_dato_email, distributore_dato_sito, url_accesso_dato, funzione_accesso_dato, precisione, genealogia
                FROM metadati"""
            )
            data = cursor.fetchall()
            cursor.close()
        return data
