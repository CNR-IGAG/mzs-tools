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


class ExportSitiLineariTask(QgsTask):
    def __init__(self, exported_project_path: Path, data_source: str):
        super().__init__("Export siti lineari (siti, indagini, parametri)", QgsTask.Flag.CanCancel)

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

            elif self.data_source == "sqlite":
                # setup sqlite connection
                self.logger.debug("Setting up sqlite connection...")
                try:
                    self.sqlite_db_connection = self.get_sqlite_db_connection()
                except Exception as e:
                    self.exception = e
                    return False

            # insert data in mdb
            self.logger.debug("Inserting siti_lineari data...")
            insert_errors = (
                self.mdb_connection.insert_siti_lineari(self.sito_lineare_data)
                if self.data_source == "mdb"
                else self.insert_siti_lineari(self.sito_lineare_data)
            )
            if insert_errors:
                self.logger.warning(
                    f"Errors occurred during siti_lineari data insertion, the following records have been discarded: {insert_errors}"
                )
            self._advance_progress()
            if self.isCanceled():
                return False

            self.logger.debug("Inserting indagini_lineari data in mdb...")
            insert_errors = (
                self.mdb_connection.insert_indagini_lineari(self.indagini_lineari_data)
                if self.data_source == "mdb"
                else self.insert_indagini_lineari(self.indagini_lineari_data)
            )
            if insert_errors:
                self.logger.warning(
                    f"Errors occurred during indagini_lineari data insertion, the following records have been discarded: {insert_errors}"
                )
            self._advance_progress()
            if self.isCanceled():
                return False

            self.logger.debug("Inserting parametri_lineari data in mdb...")
            insert_errors = (
                self.mdb_connection.insert_parametri_lineari(self.parametri_lineari_data)
                if self.data_source == "mdb"
                else self.insert_parametri_lineari(self.parametri_lineari_data)
            )
            if insert_errors:
                self.logger.warning(
                    f"Errors occurred during parametri_lineari data insertion, the following records have been discarded: {insert_errors}"
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

    def get_sito_lineare_data(self):
        conn = self.get_spatialite_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                """SELECT pkuid, id_sln, ubicazione_prov, ubicazione_com, acoord_x, acoord_y, bcoord_x, bcoord_y,
                mod_identcoord, desc_modcoord, aquota, bquota, data_sito, note_sito FROM sito_lineare"""
            )
            data = cursor.fetchall()
            return data
        finally:
            cursor.close()

    def insert_siti_lineari(self, data):
        """Insert 'sito_lineare' data into the database."""
        insert_errors = []
        for row in data:
            try:
                self.sqlite_db_connection.execute(
                    """
                    INSERT INTO sito_lineare (pkey_sln, ID_SLN, ubicazione_prov, ubicazione_com, Acoord_X, Acoord_Y,
                    Bcoord_X, Bcoord_Y, mod_identcoord, desc_modcoord, Aquota, Bquota, data_sito, note_sito) VALUES(?,
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                        row[11],
                        row[12] if row[12] else None,  # data_sito - no empty strings
                        row[13],
                    ),
                )
                self.sqlite_db_connection.commit()
            except Exception as e:
                insert_errors.append((row[1], e))
                continue
        return insert_errors

    def get_indagini_lineari_data(self):
        # doc_ind: to strip the path from the document name:
        # - find the position of the id_sln in the string
        # - get the substring from that position to the end of the string
        # - if id_sln was not added to the file name, try to remove the './Allegati/Documenti/' part
        conn = self.get_spatialite_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                """SELECT sl.pkuid, il.pkuid, classe_ind, tipo_ind, id_indln, id_indlnex, arch_ex, note_indln,
                data_ind, doc_pag, replace(substr(doc_ind, instr(doc_ind, sl.id_sln), length(doc_ind) +1),
                './Allegati/Documenti/', '') AS doc_ind, sl.id_sln FROM indagini_lineari il JOIN sito_lineare sl ON
                il.id_sln = sl.id_sln"""
            )
            data = cursor.fetchall()
            return data
        finally:
            cursor.close()

    def insert_indagini_lineari(self, data):
        """Insert 'indagini_lineari' data into the database."""
        insert_errors = []
        for row in data:
            try:
                self.sqlite_db_connection.execute(
                    """
                    INSERT INTO indagini_lineari (pkey_sln, pkey_indln, classe_ind, tipo_ind, ID_INDLN, id_indlnex,
                    arch_ex, note_indln, data_ind, doc_pag, doc_ind, id_sln) VALUES(?, ?, ?, ?, ?, ?, ?,
                    ?, ?, ?, ?, ?)""",
                    (
                        row[0],
                        row[1],
                        row[2],
                        row[3],
                        row[4],
                        row[5],
                        row[6],
                        row[7],
                        row[8] if row[8] else None,  # data_sito - no empty strings
                        row[9],
                        row[10],
                        row[11],
                    ),
                )
                self.sqlite_db_connection.commit()
            except Exception as e:
                insert_errors.append((row[4], e))
                continue
        return insert_errors

    def get_parametri_lineari_data(self):
        conn = self.get_spatialite_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                """SELECT il.pkuid, pl.pkuid, tipo_parln, id_parln, prof_top, prof_bot, spessore, quota_slm_top,
                quota_slm_bot, valore, attend_mis, note_par, data_par, il.id_indln FROM parametri_lineari pl JOIN
                indagini_lineari il ON pl.id_indln = il.id_indln"""
            )
            data = cursor.fetchall()
            return data
        finally:
            cursor.close()

    def insert_parametri_lineari(self, data):
        """Insert 'parametri_lineari' data into the database."""
        insert_errors = []
        for row in data:
            try:
                self.sqlite_db_connection.execute(
                    """
                    INSERT INTO parametri_lineari (pkey_indln, pkey_parln, tipo_parln, ID_PARLN, prof_top, prof_bot,
                    spessore, quota_slm_top, quota_slm_bot, valore, attend_mis, note_par, data_par, id_indln)
                    VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
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
                        row[12] if row[12] else None,  # data_sito - no empty strings
                        row[13],
                    ),
                )
                self.sqlite_db_connection.commit()
            except Exception as e:
                insert_errors.append((row[3], e))
                continue
        return insert_errors
