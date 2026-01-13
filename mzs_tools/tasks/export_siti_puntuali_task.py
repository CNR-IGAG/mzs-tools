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
import sqlite3
from pathlib import Path

from qgis.core import QgsTask
from qgis.utils import spatialite_connect

from ..core.mzs_project_manager import MzSProjectManager
from ..tasks.common_functions import setup_mdb_connection


class ExportSitiPuntualiTask(QgsTask):
    def __init__(self, exported_project_path: Path, data_source: str):
        super().__init__("Export siti puntuali (siti, indagini, parametri, curve)", QgsTask.Flag.CanCancel)

        self.iterations = 0
        self.exception = None

        # the logger is configured in the import data dialog module
        self.logger = logging.getLogger("mzs_tools.tasks.export_data")

        self.data_source = data_source

        self.prj_manager = MzSProjectManager.instance()
        self.spatialite_db_connection = None
        self.mdb_connection = None
        self.sqlite_db_connection = None

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

            elif self.data_source == "sqlite":
                # setup sqlite connection
                self.logger.debug("Setting up sqlite connection...")
                try:
                    self.sqlite_db_connection = self.get_sqlite_db_connection()
                except Exception as e:
                    self.exception = e
                    return False

            # insert metadata first...
            self.logger.debug("Inserting metadata...")
            insert_errors = (
                self.mdb_connection.insert_metadata(self.metadata_data)
                if self.data_source == "mdb"
                else self.insert_metadata(self.metadata_data)
            )
            if insert_errors:
                self.logger.warning(
                    f"Errors occurred during metadata insertion, the following records have been discarded: {insert_errors}"
                )
            self._advance_progress()
            if self.isCanceled():
                return False

            # insert siti, parametri, indagini, curve
            self.logger.debug("Inserting siti_puntuali data...")
            insert_errors = (
                self.mdb_connection.insert_siti_puntuali(self.sito_puntuale_data)
                if self.data_source == "mdb"
                else self.insert_siti_puntuali(self.sito_puntuale_data)
            )
            if insert_errors:
                self.logger.warning(
                    f"Errors occurred during siti_puntuali data insertion, the following records have been discarded: {insert_errors}"
                )
            self._advance_progress()
            if self.isCanceled():
                return False

            self.logger.debug("Inserting indagini_puntuali data...")
            insert_errors = (
                self.mdb_connection.insert_indagini_puntuali(self.indagini_puntuali_data)
                if self.data_source == "mdb"
                else self.insert_indagini_puntuali(self.indagini_puntuali_data)
            )
            if insert_errors:
                self.logger.warning(
                    f"Errors occurred during indagini_puntuali data insertion, the following records have been discarded: {insert_errors}"
                )
            self._advance_progress()
            if self.isCanceled():
                return False

            self.logger.debug("Inserting parametri_puntuali data...")
            insert_errors = (
                self.mdb_connection.insert_parametri_puntuali(self.parametri_puntuali_data)
                if self.data_source == "mdb"
                else self.insert_parametri_puntuali(self.parametri_puntuali_data)
            )
            if insert_errors:
                self.logger.warning(
                    f"Errors occurred during parametri_puntuali data insertion, the following records have been discarded: {insert_errors}"
                )
            self._advance_progress()
            if self.isCanceled():
                return False

            self.logger.debug("Inserting curve data...")
            insert_errors = (
                self.mdb_connection.insert_curve(self.curve_data)
                if self.data_source == "mdb"
                else self.insert_curve(self.curve_data)
            )
            if insert_errors:
                self.logger.warning(
                    f"Errors occurred during curve data insertion, the following records have been discarded: {insert_errors}"
                )
            self._advance_progress()
            if self.isCanceled():
                return False

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
            if self.sqlite_db_connection:
                self.logger.debug("Closing sqlite connection...")
                self.sqlite_db_connection.close()

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

    def get_sqlite_db_connection(self):
        if not self.sqlite_db_connection:
            self.sqlite_db_connection = sqlite3.connect(
                str(self.exported_project_path / "Indagini" / "CdI_Tabelle.sqlite")
            )
        return self.sqlite_db_connection

    def get_sito_puntuale_data(self):
        conn = self.get_spatialite_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                """SELECT pkuid, id_spu, ubicazione_prov, ubicazione_com, indirizzo, coord_x, coord_y, mod_identcoord,
                    desc_modcoord, quota_slm, modo_quota, data_sito, note_sito FROM sito_puntuale"""
            )
            data = cursor.fetchall()
            return data
        finally:
            cursor.close()

    def insert_siti_puntuali(self, data):
        """Export 'sito_puntuale' data in sqlite db."""
        insert_errors = []
        for row in data:
            try:
                self.sqlite_db_connection.execute(
                    """
                    INSERT INTO sito_puntuale (pkey_spu, ID_SPU, ubicazione_prov, ubicazione_com, indirizzo, coord_X,
                    coord_Y, mod_identcoord, desc_modcoord, quota_slm, modo_quota, data_sito, note_sito) VALUES(?, ?,
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        row[0],
                        row[1],
                        row[2],
                        row[3],
                        row[4],
                        row[5],
                        row[6],
                        row[7],
                        row[8],
                        row[9],
                        row[10],
                        row[11] if row[11] else None,  # data_sito - no empty strings
                        row[12],
                    ),
                )
                self.sqlite_db_connection.commit()
            except Exception as e:
                insert_errors.append((row[1], e))
                continue
        return insert_errors

    def get_indagini_puntuali_data(self):
        # doc_ind: to strip the path from the document name:
        # - find the position of the id_spu in the string
        # - get the substring from that position to the end of the string
        # - if id_spu was not added to the file name, try to remove the './Allegati/Documenti/' part
        conn = self.get_spatialite_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                """SELECT sp.pkuid, ip.pkuid, classe_ind, tipo_ind, id_indpu, id_indpuex, arch_ex, note_ind, prof_top,
                prof_bot, spessore, quota_slm_top, quota_slm_bot, data_ind, doc_pag, replace(substr(doc_ind, instr(doc_ind,
                sp.id_spu), length(doc_ind) +1), './Allegati/Documenti/', '') AS doc_ind, sp.id_spu FROM
                indagini_puntuali ip JOIN sito_puntuale sp ON ip.id_spu = sp.id_spu"""
            )
            data = cursor.fetchall()
            return data
        finally:
            cursor.close()

    def insert_indagini_puntuali(self, data):
        """Export 'indagini_puntuali' data in sqlite db."""
        insert_errors = []
        for row in data:
            try:
                self.sqlite_db_connection.execute(
                    """
                    INSERT INTO indagini_puntuali (pkey_spu, pkey_indpu, classe_ind, tipo_ind, ID_INDPU, id_indpuex,
                    arch_ex, note_ind, prof_top, prof_bot, spessore, quota_slm_top, quota_slm_bot, data_ind, doc_pag,
                    doc_ind, id_spu) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        row[0],
                        row[1],
                        row[2],
                        row[3],
                        row[4],
                        row[5],
                        row[6],
                        row[7],
                        row[8],
                        row[9],
                        row[10],
                        row[11],
                        row[12],
                        row[13] if row[13] else None,  # data_ind - no empty strings
                        row[14],
                        row[15],
                        row[16],
                    ),
                )
                self.sqlite_db_connection.commit()
            except Exception as e:
                insert_errors.append((row[4], e))
                continue
        return insert_errors

    def get_parametri_puntuali_data(self):
        # tab_curve: to strip the path from the document name:
        # - find the position of the id_indpu in the string
        # - get the substring from that position to the end of the string
        # - if id_indpu was not added to the file name, try to remove the './Allegati/Documenti/' part
        conn = self.get_spatialite_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                """SELECT ip.pkuid, pp.pkuid, tipo_parpu, id_parpu, pp.prof_top, pp.prof_bot, pp.spessore,
                pp.quota_slm_top, pp.quota_slm_bot, valore, attend_mis, replace(substr(tab_curve, instr(tab_curve, ip.id_indpu),
                length(tab_curve) +1), './Allegati/Documenti/', '') AS tab_curve, note_par, data_par, ip.id_indpu FROM
                parametri_puntuali pp JOIN indagini_puntuali ip ON pp.id_indpu = ip.id_indpu"""
            )
            data = cursor.fetchall()
            return data
        finally:
            cursor.close()

    def insert_parametri_puntuali(self, data):
        """Export 'parametri_puntuali' data in sqlite db."""
        insert_errors = []
        for row in data:
            try:
                self.sqlite_db_connection.execute(
                    """
                    INSERT INTO parametri_puntuali (pkey_indpu, pkey_parpu, tipo_parpu, ID_PARPU, prof_top, prof_bot,
                    spessore, quota_slm_top, quota_slm_bot, valore, attend_mis, tab_curve, note_par, data_par,
                    id_indpu) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        row[0],
                        row[1],
                        row[2],
                        row[3],
                        row[4],
                        row[5],
                        row[6],
                        row[7],
                        row[8],
                        row[9],
                        row[10],
                        row[11],
                        row[12],
                        row[13] if row[13] else None,  # data_par - no empty strings
                        row[14],
                    ),
                )
                self.sqlite_db_connection.commit()
            except Exception as e:
                insert_errors.append((row[3], e))
                continue
        return insert_errors

    def get_curve_data(self):
        conn = self.get_spatialite_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                """SELECT pp.pkuid, c.pkuid, cond_curve, varx, vary, pp.id_parpu FROM curve c JOIN parametri_puntuali pp ON
                c.id_parpu = pp.id_parpu"""
            )
            data = cursor.fetchall()
            return data
        finally:
            cursor.close()

    def insert_curve(self, data):
        """Export 'curve' data in sqlite db."""
        insert_errors = []
        for row in data:
            try:
                self.sqlite_db_connection.execute(
                    """
                    INSERT INTO curve (pkey_parpu, pkey_curve, cond_curve, varx, vary, id_parpu) VALUES(?, ?, ?, ?, ?, ?)
                    """,
                    (
                        row[0],
                        row[1],
                        row[2],
                        row[3],
                        row[4],
                        row[5],
                    ),
                )
                self.sqlite_db_connection.commit()
            except Exception as e:
                insert_errors.append((row[1], e))
                continue
        return insert_errors

    def get_metadata_data(self):
        conn = self.get_spatialite_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                """SELECT id_metadato, liv_gerarchico, resp_metadato_nome,
                    resp_metadato_email, resp_metadato_sito, data_metadato, srs_dati, proprieta_dato_nome, proprieta_dato_email, proprieta_dato_sito, data_dato, ruolo, desc_dato,
                    formato, tipo_dato, contatto_dato_nome, contatto_dato_email, contatto_dato_sito, keywords, keywords_inspire, limitazione, vincoli_accesso, vincoli_fruibilita,
                    vincoli_sicurezza, scala, categoria_iso, estensione_ovest, estensione_est, estensione_sud, estensione_nord, formato_dati, distributore_dato_nome,
                    distributore_dato_telefono, distributore_dato_email, distributore_dato_sito, url_accesso_dato, funzione_accesso_dato, precisione, genealogia
                FROM metadati"""
            )
            data = cursor.fetchall()
            return data
        finally:
            cursor.close()

    def insert_metadata(self, data):
        """Export 'metadata' data in sqlite db."""
        insert_errors = []
        for row in data:
            try:
                self.sqlite_db_connection.execute(
                    """
                    INSERT INTO metadati (id_metadato, liv_gerarchico, resp_metadato_nome, resp_metadato_email,
                    resp_metadato_sito, data_metadato, srs_dati, proprieta_dato_nome, proprieta_dato_email,
                    proprieta_dato_sito, data_dato, ruolo, desc_dato, formato, tipo_dato, contatto_dato_nome,
                    contatto_dato_email, contatto_dato_sito, keywords, keywords_inspire, limitazione, vincoli_accesso,
                    vincoli_fruibilita, vincoli_sicurezza, scala, categoria_iso, estensione_ovest, estensione_est,
                    estensione_sud, estensione_nord, formato_dati, distributore_dato_nome, distributore_dato_telefono,
                    distributore_dato_email, distributore_dato_sito, url_accesso_dato, funzione_accesso_dato,
                    precisione, genealogia) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        row[0],
                        row[1],
                        row[2],
                        row[3],
                        row[4],
                        row[5] if row[5] else None,
                        row[6],
                        row[7],
                        row[8],
                        row[9],
                        row[10] if row[10] else None,
                        row[11],
                        row[12],
                        row[13],
                        row[14],
                        row[15],
                        row[16],
                        row[17],
                        row[18],
                        row[19],
                        row[20],
                        row[21],
                        row[22],
                        row[23],
                        row[24],
                        row[25],
                        row[26],
                        row[27],
                        row[28],
                        row[29],
                        row[30],
                        row[31],
                        row[32],
                        row[33],
                        row[34],
                        row[35],
                        row[36],
                        row[37],
                        row[38],
                    ),
                )
                self.sqlite_db_connection.commit()
            except Exception as e:
                insert_errors.append((row[0], e))
                continue
        return insert_errors
