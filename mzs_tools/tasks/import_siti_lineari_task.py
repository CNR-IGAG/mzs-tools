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
import sqlite3
from datetime import datetime
from pathlib import Path

from qgis.core import QgsTask, QgsVectorLayer
from qgis.utils import spatialite_connect

from ..__about__ import DEBUG_MODE
from ..core.mzs_project_manager import MzSProjectManager
from ..plugin_utils.misc import retry_on_lock
from ..tasks.common_functions import setup_mdb_connection


class ImportSitiLineariTask(QgsTask):
    def __init__(
        self,
        proj_paths: dict,
        data_source: str,
        mdb_password: str | None = None,
        csv_files: dict | None = None,
        adapt_counters: bool = True,
    ):
        super().__init__("Import siti lineari (siti, indagini, parametri)", QgsTask.Flag.CanCancel)

        self.iterations = 0
        self.exception = None

        # the logger is configured in the import data dialog module
        self.logger = logging.getLogger("mzs_tools.tasks.import_data")

        self.data_source = data_source
        self.mdb_password = mdb_password
        self.csv_files = csv_files

        self.prj_manager = MzSProjectManager.instance()
        self.spatialite_db_connection = None
        self.sqlite_db_connection = None
        self.mdb_connection = None

        self.proj_paths = proj_paths
        self.mdb_path = self.proj_paths["CdI_Tabelle.mdb"]["path"]
        self.sqlite_path = self.proj_paths["CdI_Tabelle.sqlite"]["path"]

        self.siti_lineari_shapefile = QgsVectorLayer(str(self.proj_paths["Ind_ln.shp"]["path"]), "Ind_ln", "ogr")
        self.num_siti = self.siti_lineari_shapefile.featureCount()

        # option to adapt the primary keys of the imported data to avoid conflicts with existing data
        self.adapt_counters = adapt_counters

    def run(self):
        self.logger.info(f"{'#' * 15} Starting task {self.description()}")
        if DEBUG_MODE:
            self.logger.warning(f"\n{'#' * 50}\n# Running in DEBUG mode! Data will be DESTROYED! #\n{'#' * 50}")

        self.iterations = 0

        self.logger.info(f"{self.num_siti} siti lineari detected in 'Ind_ln.shp'")

        if self.num_siti == 0:
            self.logger.warning("Shapefile is empty, nothing to do.")
            return True

        try:
            # get features from the shapefile
            features = self.siti_lineari_shapefile.getFeatures()

            self.logger.info(f"Getting data from {self.data_source}")
            if self.data_source == "mdb":
                # setup mdb connection
                try:
                    connected, self.mdb_connection = setup_mdb_connection(self.mdb_path, password=self.mdb_password)
                except Exception as e:
                    self.exception = e
                    return False

                if connected:
                    # prepare data
                    self.sito_lineare_data = self.mdb_connection.get_sito_lineare_data()
                    self.sito_lineare_seq = self.get_sito_lineare_seq()
                    self.indagini_lineari_data = self.mdb_connection.get_indagini_lineari_data()
                    self.indagini_lineari_seq = self.get_indagini_lineari_seq()
                    self.parametri_lineari_data = self.mdb_connection.get_parametri_lineari_data()
                    self.parametri_lineari_seq = self.get_parametri_lineari_seq()

            elif self.data_source == "sqlite":
                self.logger.info("Importing data from SQLite database")

                # Setup SQLite connection
                try:
                    self.sqlite_db_connection = sqlite3.connect(str(self.sqlite_path))
                    self.sqlite_db_connection.row_factory = sqlite3.Row  # This allows accessing columns by name
                except Exception as e:
                    self.logger.error(f"Error connecting to SQLite database: {e}")
                    self.exception = e
                    return False

                # Get data from SQLite tables
                try:
                    # Get sito_lineare data
                    self.logger.debug("Reading sito_lineare data from SQLite")
                    self.sito_lineare_data = self.get_sqlite_sito_lineare_data()
                    self.sito_lineare_seq = self.get_sito_lineare_seq()

                    # Get indagini_lineari data
                    self.logger.debug("Reading indagini_lineari data from SQLite")
                    self.indagini_lineari_data = self.get_sqlite_indagini_lineari_data()
                    self.indagini_lineari_seq = self.get_indagini_lineari_seq()

                    # Get parametri_lineari data
                    self.logger.debug("Reading parametri_lineari data from SQLite")
                    self.parametri_lineari_data = self.get_sqlite_parametri_lineari_data()
                    self.parametri_lineari_seq = self.get_parametri_lineari_seq()
                except Exception as e:
                    self.logger.error(f"Error reading data from SQLite database: {e}")
                    self.exception = e
                    return False

            elif self.data_source == "csv":
                if not self.csv_files:
                    self.logger.error("No CSV files provided!")
                    return False

                # Get data from CSV files
                self.logger.info("Reading data from CSV files")

                # Get sito_lineare data from CSV
                self.sito_lineare_data = {}
                if "sito_lineare" in self.csv_files["lineari"]:
                    try:
                        self.logger.debug(
                            f"Reading sito_lineare data from {self.csv_files['lineari']['sito_lineare']}"
                        )
                        self.sito_lineare_data = self.read_csv_data(
                            "sito_lineare", self.csv_files["lineari"]["sito_lineare"]
                        )
                        self.sito_lineare_seq = self.get_sito_lineare_seq()
                    except Exception as e:
                        self.logger.error(f"Error reading sito_lineare data: {e}")
                        self.exception = e
                        return False

                # Get indagini_lineari data from CSV
                self.indagini_lineari_data = {}
                if "indagini_lineari" in self.csv_files["lineari"]:
                    try:
                        self.logger.debug(
                            f"Reading indagini_lineari data from {self.csv_files['lineari']['indagini_lineari']}"
                        )
                        self.indagini_lineari_data = self.read_csv_data(
                            "indagini_lineari", self.csv_files["lineari"]["indagini_lineari"]
                        )
                        self.indagini_lineari_seq = self.get_indagini_lineari_seq()
                    except Exception as e:
                        self.logger.error(f"Error reading indagini_lineari data: {e}")
                        self.exception = e
                        return False

                # Get parametri_lineari data from CSV
                self.parametri_lineari_data = {}
                if "parametri_lineari" in self.csv_files["lineari"]:
                    try:
                        self.logger.debug(
                            f"Reading parametri_lineari data from {self.csv_files['lineari']['parametri_lineari']}"
                        )
                        self.parametri_lineari_data = self.read_csv_data(
                            "parametri_lineari", self.csv_files["lineari"]["parametri_lineari"]
                        )
                        self.parametri_lineari_seq = self.get_parametri_lineari_seq()
                    except Exception as e:
                        self.logger.error(f"Error reading parametri_lineari data: {e}")
                        self.exception = e
                        return False

            if DEBUG_MODE:
                self.logger.warning(f"{'#' * 15} Deleting all siti_lineari!")
                self.delete_all_siti_lineari()

            for feature in features:  # type: ignore
                self.iterations += 1
                self.setProgress(self.iterations * 100 / self.num_siti)

                try:
                    self.logger.debug(f"Processing feature {feature['ID_SLN']}")
                    sito_lineare = self.sito_lineare_data[feature["ID_SLN"]]
                except KeyError:
                    self.logger.warning(f"ID_SLN {feature['ID_SLN']} not found in {self.data_source}, skipping")
                    continue

                geometry = feature.geometry()
                # Skip features with no geometry
                if geometry.isNull():
                    self.logger.warning(f"Feature {feature['ID_SLN']} has no geometry, skipping feature.")
                    continue
                # Drop Z values
                if geometry.get().is3D():
                    self.logger.warning(f"Feature {feature['ID_SLN']} is 3D. Z value will be dropped.")
                    geometry.get().dropZValue()
                    feature.setGeometry(geometry)
                # Convert multilinestring to linestring, warn if multiple parts are present
                if geometry.isMultipart():
                    parts = geometry.asGeometryCollection()
                    if len(parts) > 1:
                        self.logger.warning(f"Feature {feature['ID_SLN']} is multipart, taking first part only.")
                    geometry = parts[0]
                    feature.setGeometry(geometry)

                sito_lineare["geom"] = feature.geometry().asWkt()

                # avoid CHECK constraint errors
                if not sito_lineare["Aquota"]:
                    sito_lineare["Aquota"] = None  # type: ignore
                if not sito_lineare["Bquota"]:
                    sito_lineare["Bquota"] = None  # type: ignore

                # change counters when data is already present
                sito_lineare_source_pkey = sito_lineare["pkey_sln"]
                if self.adapt_counters and self.sito_lineare_seq > 0:
                    new_pkey_sln = int(sito_lineare["pkey_sln"]) + self.sito_lineare_seq
                    self.logger.debug(f"pkey_sln: {sito_lineare['pkey_sln']} -> {new_pkey_sln}")
                    sito_lineare["pkey_sln"] = new_pkey_sln  # type: ignore
                    sito_lineare["ID_SLN"] = (
                        sito_lineare["ubicazione_prov"]
                        + sito_lineare["ubicazione_com"]
                        + "L"
                        + str(sito_lineare["pkey_sln"])
                    )

                # add import note
                sito_lineare["note_sito"] = (
                    f"[MzS Tools] Dati del sito, indagini e parametri correlati importati da {self.data_source} in data {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n{sito_lineare['note_sito']}"
                )

                try:
                    self.insert_sito_lineare(sito_lineare)
                except Exception as e:
                    self.logger.error(f"Error inserting sito_lineare {sito_lineare['ID_SLN']}: {e}")
                    continue

                ############################################################
                # insert indagini_lineari
                current_pkey_sln = sito_lineare_source_pkey if self.adapt_counters else sito_lineare["pkey_sln"]

                filtered_indagini = {
                    key: value for key, value in self.indagini_lineari_data.items() if str(key[0]) == current_pkey_sln
                }
                # self.log(f"pkey_spu: {current_spu_id} - Filtered elements: {filtered_indagini}")

                for key, value in filtered_indagini.items():
                    # self.log(f"Inserting indagine puntuale - Key: {key}, Value: {value}")
                    # add ID_SPU to the data
                    value["ID_SLN"] = sito_lineare["ID_SLN"]
                    # turn empty strings into None to avoid CHECK constraint errors
                    for k in value.keys():  # noqa: SIM118
                        if value[k] == "":
                            value[k] = None  # type: ignore
                    # change counters when data is already present
                    indagine_lineare_source_pkey = value["pkey_indln"]
                    indagine_lineare_source_id_indln = value["ID_INDLN"]
                    if self.adapt_counters and self.indagini_lineari_seq > 0:
                        value["pkey_indln"] = int(value["pkey_indln"]) + self.indagini_lineari_seq  # type: ignore
                        value["ID_INDLN"] = value["ID_SLN"] + value["tipo_ind"] + str(value["pkey_indln"])

                    # copy and adapt attachments
                    try:
                        if value["doc_ind"]:  # noqa: SIM102
                            # self.log(f"Copying attachment {value['doc_ind']}")
                            if (
                                self.proj_paths["Documenti"]["path"]
                                and Path(self.proj_paths["Documenti"]["path"]).exists()
                            ):
                                new_file_name = self.copy_attachment(
                                    value["doc_ind"], indagine_lineare_source_id_indln, value["ID_INDLN"]
                                )
                                if new_file_name:
                                    value["doc_ind"] = "./Allegati/Documenti/" + new_file_name
                    except Exception as e:
                        self.logger.warning(f"Error copying indagine lineare attachment {value['doc_ind']}: {e}")

                    try:
                        self.insert_indagine_lineare(value)
                    except Exception as e:
                        self.logger.error(f"Error inserting indagine lineare {value['ID_INDLN']}: {e}")
                        continue

                    ############################################################
                    # insert parametri_lineari
                    current_pkey_indln = indagine_lineare_source_pkey if self.adapt_counters else value["pkey_indln"]
                    current_idindln = value["ID_INDLN"]

                    filtered_parametri = {
                        key: value
                        for key, value in self.parametri_lineari_data.items()
                        if str(key[0]) == current_pkey_indln
                    }
                    # self.log(f"pkey_indpu: {current_pkey_indpu} - Filtered elements: {filtered_parametri}")

                    for _key, value in filtered_parametri.items():
                        # self.log(f"Inserting parametro puntuale - Key: {key}, Value: {value}")
                        # add ID_INDPU to the data
                        value["ID_INDLN"] = current_idindln

                        # turn empty strings into None to avoid CHECK constraint errors
                        for k in value.keys():  # noqa: SIM118
                            if value[k] == "":
                                value[k] = None  # type: ignore

                        # amend spessore < 0
                        try:
                            if (
                                value["prof_top"]
                                and value["prof_bot"]
                                and (float(value["prof_top"]) > float(value["prof_bot"]))
                            ):
                                self.logger.warning(f"prof_top > prof_bot in {value['ID_PARLN']}, check prof values!")
                                # one of prof_bot or prof_top is probably wrong, set prof_bot to none to avoid further errors
                                value["prof_bot"] = None  # type: ignore
                            if value["spessore"] and float(value["spessore"]) < 0:
                                self.logger.warning(f"Negative spessore in {value['ID_PARLN']}, check prof values!")
                                value["spessore"] = None  # type: ignore
                                # one of prof_bot or prof_top is probably wrong, set prof_bot to none to avoid further errors
                                value["prof_bot"] = None  # type: ignore
                        except Exception as e:
                            self.logger.warning(f"Error checking spessore in {value['ID_PARLN']}: {e}")

                        # change counters when data is already present
                        # parametro_lineare_source_pkey = value["pkey_parpu"]
                        if self.adapt_counters and self.parametri_lineari_seq > 0:
                            value["pkey_parln"] = int(value["pkey_parln"]) + self.parametri_lineari_seq  # type: ignore
                            value["ID_PARLN"] = value["ID_PARLN"] + value["tipo_parln"] + str(value["pkey_parln"])

                        try:
                            self.insert_parametro_lineare(value)
                        except Exception as e:
                            self.logger.error(f"Error inserting parametro lineare {value['ID_PARLN']}: {e}")
                            continue

                # check isCanceled() to handle cancellation
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

    @retry_on_lock()
    def insert_sito_lineare(self, data: dict):
        """Insert a new 'sito_lineare' record into the database."""
        conn = self.get_spatialite_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                """INSERT INTO sito_lineare (pkuid, id_sln, mod_identcoord, desc_modcoord, aquota, bquota, data_sito,
                note_sito, geom)
                        VALUES(:pkey_sln, :ID_SLN, :mod_identcoord, :desc_modcoord, :Aquota, :Bquota, :data_sito,
                        :note_sito, GeomFromText(:geom, 32633));""",
                data,
            )
            conn.commit()
        finally:
            cursor.close()

    @retry_on_lock()
    def delete_all_siti_lineari(self):
        """Delete all 'sito_lineare' records from the database."""
        conn = self.get_spatialite_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("DELETE FROM sito_lineare;")
            conn.commit()
        finally:
            cursor.close()

    @retry_on_lock()
    def get_sito_lineare_seq(self):
        conn = self.get_spatialite_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''SELECT seq FROM sqlite_sequence WHERE name="sito_lineare"''')
            data = cursor.fetchall()
            return data[0][0] if data else 0
        finally:
            cursor.close()

    @retry_on_lock()
    def get_indagini_lineari_seq(self):
        conn = self.get_spatialite_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''SELECT seq FROM sqlite_sequence WHERE name="indagini_lineari"''')
            data = cursor.fetchall()
            return data[0][0] if data else 0
        finally:
            cursor.close()

    @retry_on_lock()
    def get_parametri_lineari_seq(self):
        conn = self.get_spatialite_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''SELECT seq FROM sqlite_sequence WHERE name="parametri_lineari"''')
            data = cursor.fetchall()
            return data[0][0] if data else 0
        finally:
            cursor.close()

    @retry_on_lock()
    def insert_indagine_lineare(self, data: dict):
        conn = self.get_spatialite_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                """INSERT INTO indagini_lineari (pkuid, id_sln, classe_ind, tipo_ind, id_indln, id_indlnex, arch_ex,
                note_indln, data_ind, doc_pag, doc_ind)
                        VALUES(:pkey_indln, :ID_SLN, :classe_ind, :tipo_ind, :ID_INDLN, :id_indlnex, :arch_ex,
                        :note_indln, :data_ind, :doc_pag, :doc_ind);""",
                data,
            )
            conn.commit()
        finally:
            cursor.close()

    @retry_on_lock()
    def insert_parametro_lineare(self, data: dict):
        conn = self.get_spatialite_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                """INSERT INTO parametri_lineari (pkuid, id_indln, tipo_parln, id_parln, prof_top, prof_bot, spessore,
                quota_slm_top, quota_slm_bot, valore, attend_mis, note_par, data_par)
                        VALUES(:pkey_parln, :ID_INDLN, :tipo_parln, :ID_PARLN, :prof_top, :prof_bot, :spessore,
                        :quota_slm_top, :quota_slm_bot, :valore, :attend_mis, :note_par, :data_par);""",
                data,
            )
            conn.commit()
        finally:
            cursor.close()

    def get_spatialite_db_connection(self):
        if not self.spatialite_db_connection:
            self.spatialite_db_connection = spatialite_connect(str(self.prj_manager.db_path))
        return self.spatialite_db_connection

    def copy_attachment(self, attachment_file_name: str, old_id: str, new_id: str):
        # check file exists
        file_path = self.proj_paths["Documenti"]["path"] / attachment_file_name
        if not Path(file_path).exists():
            # recursively scan in subfolders
            parent_dir = self.proj_paths["Documenti"]["path"]
            attachment_filename = Path(attachment_file_name).name
            found = False

            for path in parent_dir.glob("**/*"):
                if path.is_file() and path.name == attachment_filename:
                    self.logger.info(f"Found attachment {attachment_filename} in {path}")
                    file_path = path
                    found = True
                    break

            if not found:
                self.logger.warning(f"Attachment {file_path} not found, skipping")
                return None
        # copy in the project folder
        dest_path = self.prj_manager.project_path / "Allegati" / "Documenti"  # type: ignore

        # if a new ID has been assigned to the indagine or parametro, add it to the file name
        new_file_name = None
        if old_id != new_id:
            new_file_name = f"{new_id}_[{file_path.stem}]{file_path.suffix}"

        if (new_file_name and (dest_path / new_file_name).exists()) or (dest_path / attachment_file_name).exists():
            self.logger.debug(f"Attachment {attachment_file_name} already exists in {dest_path}, skipping")
            return new_file_name or attachment_file_name

        if new_file_name:
            shutil.copy(file_path, dest_path / new_file_name)
        else:
            shutil.copy(file_path, dest_path)

        self.logger.debug(
            f"Attachment {attachment_file_name} copied to project folder {'as ' + new_file_name if new_file_name else ''}"
        )
        return new_file_name or attachment_file_name

    def get_sqlite_sito_lineare_data(self):
        """Get sito_lineare data from SQLite database"""
        data = {}
        cursor = self.sqlite_db_connection.cursor()
        try:
            cursor.execute("""
                SELECT pkey_sln, ID_SLN, ubicazione_prov, ubicazione_com, Acoord_X, Acoord_Y,
                    Bcoord_X, Bcoord_Y, mod_identcoord, desc_modcoord, Aquota, Bquota,
                    data_sito, note_sito
                FROM sito_lineare
            """)

            rows = cursor.fetchall()
            for row in rows:
                row_dict = {
                    "pkey_sln": str(row["pkey_sln"]),
                    "ID_SLN": row["ID_SLN"],
                    "ubicazione_prov": row["ubicazione_prov"] or "",
                    "ubicazione_com": row["ubicazione_com"] or "",
                    "Acoord_X": row["Acoord_X"],
                    "Acoord_Y": row["Acoord_Y"],
                    "Bcoord_X": row["Bcoord_X"],
                    "Bcoord_Y": row["Bcoord_Y"],
                    "mod_identcoord": row["mod_identcoord"] or "",
                    "desc_modcoord": row["desc_modcoord"] or "",
                    "Aquota": row["Aquota"],
                    "Bquota": row["Bquota"],
                    "data_sito": row["data_sito"] or "",
                    "note_sito": row["note_sito"] or "",
                }
                data[row["ID_SLN"]] = row_dict

            self.logger.info(f"Read {len(data)} records from sito_lineare in SQLite")
            return data
        finally:
            cursor.close()

    def get_sqlite_indagini_lineari_data(self):
        """Get indagini_lineari data from SQLite database"""
        data = {}
        cursor = self.sqlite_db_connection.cursor()
        try:
            cursor.execute("""
                SELECT pkey_sln, pkey_indln, classe_ind, tipo_ind, ID_INDLN, id_indlnex,
                    arch_ex, note_indln, data_ind, doc_pag, doc_ind, id_sln
                FROM indagini_lineari
            """)

            rows = cursor.fetchall()
            for row in rows:
                row_dict = {
                    "pkey_sln": str(row["pkey_sln"]),
                    "pkey_indln": str(row["pkey_indln"]),
                    "classe_ind": row["classe_ind"] or "",
                    "tipo_ind": row["tipo_ind"] or "",
                    "ID_INDLN": row["ID_INDLN"],
                    "id_indlnex": row["id_indlnex"] or "",
                    "arch_ex": row["arch_ex"] or "",
                    "note_indln": row["note_indln"] or "",
                    "data_ind": row["data_ind"] or "",
                    "doc_pag": row["doc_pag"] or "",
                    "doc_ind": row["doc_ind"] or "",
                    "id_sln": row["id_sln"] or "",
                }
                data[(str(row["pkey_sln"]), row["ID_INDLN"])] = row_dict

            self.logger.info(f"Read {len(data)} records from indagini_lineari in SQLite")
            return data
        finally:
            cursor.close()

    def get_sqlite_parametri_lineari_data(self):
        """Get parametri_lineari data from SQLite database"""
        data = {}
        cursor = self.sqlite_db_connection.cursor()
        try:
            cursor.execute("""
                SELECT pkey_indln, pkey_parln, tipo_parln, ID_PARLN, prof_top, prof_bot,
                    spessore, quota_slm_top, quota_slm_bot, valore, attend_mis,
                    note_par, data_par, id_indln
                FROM parametri_lineari
            """)

            rows = cursor.fetchall()
            for row in rows:
                row_dict = {
                    "pkey_indln": str(row["pkey_indln"]),
                    "pkey_parln": str(row["pkey_parln"]),
                    "tipo_parln": row["tipo_parln"] or "",
                    "ID_PARLN": row["ID_PARLN"],
                    "prof_top": row["prof_top"],
                    "prof_bot": row["prof_bot"],
                    "spessore": row["spessore"],
                    "quota_slm_top": row["quota_slm_top"],
                    "quota_slm_bot": row["quota_slm_bot"],
                    "valore": row["valore"],
                    "attend_mis": row["attend_mis"] or "",
                    "note_par": row["note_par"] or "",
                    "data_par": row["data_par"] or "",
                    "id_indln": row["id_indln"] or "",
                }
                data[(str(row["pkey_indln"]), row["ID_PARLN"])] = row_dict

            self.logger.info(f"Read {len(data)} records from parametri_lineari in SQLite")
            return data
        finally:
            cursor.close()

    def read_csv_data(self, table_type, file_path):
        """
        Read data from CSV file and convert it to the same format as get_* methods in AccessDbConnection

        Args:
            table_type: Type of table ('sito_lineare', 'indagini_lineari', 'parametri_lineari')
            file_path: Path to the CSV file

        Returns:
            Dictionary with data from CSV file in the same format as get_* methods in AccessDbConnection
        """
        import csv

        # Expected field names for each table type (case insensitive)
        expected_fields = {
            "sito_lineare": {
                "pkuid": "pkey_sln",
                "pkey_sln": "pkey_sln",
                "id_sln": "ID_SLN",
                "ubicazione_prov": "ubicazione_prov",
                "ubicazione_com": "ubicazione_com",
                "acoord_x": "Acoord_X",
                "acoord_y": "Acoord_Y",
                "bcoord_x": "Bcoord_X",
                "bcoord_y": "Bcoord_Y",
                "mod_identcoord": "mod_identcoord",
                "desc_modcoord": "desc_modcoord",
                "aquota": "Aquota",
                "bquota": "Bquota",
                "data_sito": "data_sito",
                "note_sito": "note_sito",
            },
            "indagini_lineari": {
                "pkey_sln": "pkey_sln",
                "pkey_indln": "pkey_indln",
                "classe_ind": "classe_ind",
                "tipo_ind": "tipo_ind",
                "id_indln": "ID_INDLN",
                "id_indlnex": "id_indlnex",
                "arch_ex": "arch_ex",
                "note_indln": "note_indln",
                "data_ind": "data_ind",
                "doc_pag": "doc_pag",
                "doc_ind": "doc_ind",
            },
            "parametri_lineari": {
                "pkey_indln": "pkey_indln",
                "pkey_parln": "pkey_parln",
                "tipo_parln": "tipo_parln",
                "id_parln": "ID_PARLN",
                "prof_top": "prof_top",
                "prof_bot": "prof_bot",
                "spessore": "spessore",
                "quota_slm_top": "quota_slm_top",
                "quota_slm_bot": "quota_slm_bot",
                "valore": "valore",
                "attend_mis": "attend_mis",
                "note_par": "note_par",
                "data_par": "data_par",
            },
        }

        # Required fields for each table type (to create key)
        required_fields = {
            "sito_lineare": ["ID_SLN"],
            "indagini_lineari": ["pkey_sln", "ID_INDLN"],
            "parametri_lineari": ["pkey_indln", "ID_PARLN"],
        }

        # Numeric fields that should be converted
        numeric_fields = [
            "pkey_sln",
            "pkey_indln",
            "pkey_parln",
            "prof_top",
            "prof_bot",
            "spessore",
            "Aquota",
            "Bquota",
            "quota_slm_top",
            "quota_slm_bot",
        ]

        # Result container
        data = {}

        try:
            with open(file_path, encoding="utf-8") as csvfile:
                # Try to auto-detect the delimiter
                sample = csvfile.read(1024)
                csvfile.seek(0)
                delimiter = "," if sample.count(",") > sample.count(";") else ";"

                reader = csv.reader(csvfile, delimiter=delimiter)

                # Read header row and map column indices
                header_row = next(reader)
                header_map = {}

                # Create case-insensitive mapping from header names to column indices
                for idx, field in enumerate(header_row):
                    field_lower = field.lower().strip()
                    if field_lower in expected_fields[table_type]:
                        header_map[expected_fields[table_type][field_lower]] = idx

                # Log found and missing fields
                found_fields = list(header_map.keys())
                missing_fields = [f for f in required_fields[table_type] if f not in header_map]

                self.logger.debug(f"CSV field mapping: {header_map}")

                if missing_fields:
                    self.logger.warning(f"Missing required fields in {table_type} CSV: {missing_fields}")
                    if any(f for f in required_fields[table_type] if f not in found_fields):
                        raise ValueError(f"CSV file is missing required fields: {missing_fields}")

                # Process the data rows
                for row in reader:
                    if not row or all(cell == "" for cell in row):
                        continue  # Skip empty rows

                    # Create a dictionary for this row
                    row_dict = {}

                    # Map CSV columns to dict keys using header_map
                    for field, idx in header_map.items():
                        if idx < len(row):
                            # Convert empty strings to empty strings (not None) to match AccessDbConnection output
                            value = row[idx].strip() if row[idx] else ""
                            row_dict[field] = value
                        else:
                            row_dict[field] = ""

                    # Convert numeric values for internal use (but keep them as strings for output)
                    numeric_values = {}
                    for field in numeric_fields:
                        if field in row_dict and row_dict[field]:
                            try:
                                # Replace comma with dot for decimal numbers
                                value = str(row_dict[field]).replace(",", ".")
                                numeric_values[field] = float(value)
                                # Convert to int if it's an integer
                                if numeric_values[field].is_integer():
                                    numeric_values[field] = int(numeric_values[field])
                            except (ValueError, AttributeError) as e:
                                self.logger.debug(
                                    f"Could not convert field {field} value '{row_dict[field]}' to number: {e}"
                                )

                    # Create key for dictionary based on table type
                    try:
                        if table_type == "sito_lineare":
                            key = row_dict["ID_SLN"]
                            data[key] = row_dict
                        elif table_type == "indagini_lineari":
                            # Use the same key format as AccessDbConnection (pkey_sln, ID_INDLN)
                            key = (row_dict["pkey_sln"], row_dict["ID_INDLN"])
                            data[key] = row_dict
                        elif table_type == "parametri_lineari":
                            # Use the same key format as AccessDbConnection (pkey_indln, ID_PARLN)
                            key = (row_dict["pkey_indln"], row_dict["ID_PARLN"])
                            data[key] = row_dict
                    except KeyError as e:
                        self.logger.warning(f"Skipping row due to missing required key field: {e}")
                        continue

                self.logger.info(f"Read {len(data)} records from {table_type} CSV file")
                return data

        except Exception as e:
            self.logger.error(f"Error reading CSV file {file_path}: {e}")
            raise e
