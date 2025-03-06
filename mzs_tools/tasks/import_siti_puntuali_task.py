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


class ImportSitiPuntualiTask(QgsTask):
    def __init__(
        self,
        proj_paths: dict,
        data_source: str,
        mdb_password: str = None,
        csv_files: dict = None,
        adapt_counters: bool = True,
    ):
        super().__init__("Import siti puntuali (siti, indagini, parametri, curve)", QgsTask.CanCancel)

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

        self.siti_puntuali_shapefile = QgsVectorLayer(str(self.proj_paths["Ind_pu.shp"]["path"]), "Ind_pu", "ogr")
        self.num_siti = self.siti_puntuali_shapefile.featureCount()

        # option to adapt the primary keys of the imported data to avoid conflicts with existing data
        self.adapt_counters = adapt_counters

    def run(self):
        self.logger.info(f"{'#' * 15} Starting task {self.description()}")
        if DEBUG_MODE:
            self.logger.warning(f"\n{'#' * 50}\n# Running in DEBUG MODE! Data will be DESTROYED! #\n{'#' * 50}")

        self.iterations = 0

        self.logger.info(f"{self.num_siti} siti puntuali detected in 'Ind_pu.shp'")

        if self.num_siti == 0:
            self.logger.warning("Shapefile is empty, nothing to do.")
            return True

        try:
            # get features from the shapefile
            features = self.siti_puntuali_shapefile.getFeatures()

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
                    self.sito_puntuale_data = self.mdb_connection.get_sito_puntuale_data()
                    self.sito_puntuale_seq = self.get_sito_puntuale_seq()
                    self.indagini_puntuali_data = self.mdb_connection.get_indagini_puntuali_data()
                    self.indagini_puntuali_seq = self.get_indagini_puntuali_seq()
                    self.parametri_puntuali_data = self.mdb_connection.get_parametri_puntuali_data()
                    self.parametri_puntuali_seq = self.get_parametri_puntuali_seq()
                    self.curve_data = self.mdb_connection.get_curve_data()
                    self.curve_seq = self.get_curve_seq()

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
                    # Get sito_puntuale data
                    self.logger.debug("Reading sito_puntuale data from SQLite")
                    self.sito_puntuale_data = self.get_sqlite_sito_puntuale_data()
                    self.sito_puntuale_seq = self.get_sito_puntuale_seq()

                    # Get indagini_puntuali data
                    self.logger.debug("Reading indagini_puntuali data from SQLite")
                    self.indagini_puntuali_data = self.get_sqlite_indagini_puntuali_data()
                    self.indagini_puntuali_seq = self.get_indagini_puntuali_seq()

                    # Get parametri_puntuali data
                    self.logger.debug("Reading parametri_puntuali data from SQLite")
                    self.parametri_puntuali_data = self.get_sqlite_parametri_puntuali_data()
                    self.parametri_puntuali_seq = self.get_parametri_puntuali_seq()

                    # Get curve data
                    self.logger.debug("Reading curve data from SQLite")
                    self.curve_data = self.get_sqlite_curve_data()
                    self.curve_seq = self.get_curve_seq()
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

                # Get sito_puntuale data from CSV
                self.sito_puntuale_data = {}
                if "sito_puntuale" in self.csv_files["puntuali"]:
                    try:
                        self.logger.debug(
                            f"Reading sito_puntuale data from {self.csv_files['puntuali']['sito_puntuale']}"
                        )
                        self.sito_puntuale_data = self.read_csv_data(
                            "sito_puntuale", self.csv_files["puntuali"]["sito_puntuale"]
                        )
                        self.sito_puntuale_seq = self.get_sito_puntuale_seq()
                    except Exception as e:
                        self.logger.error(f"Error reading sito_puntuale data: {e}")
                        self.exception = e
                        return False

                # Get indagini_puntuali data from CSV
                self.indagini_puntuali_data = {}
                if "indagini_puntuali" in self.csv_files["puntuali"]:
                    try:
                        self.logger.debug(
                            f"Reading indagini_puntuali data from {self.csv_files['puntuali']['indagini_puntuali']}"
                        )
                        self.indagini_puntuali_data = self.read_csv_data(
                            "indagini_puntuali", self.csv_files["puntuali"]["indagini_puntuali"]
                        )
                        self.indagini_puntuali_seq = self.get_indagini_puntuali_seq()
                    except Exception as e:
                        self.logger.error(f"Error reading indagini_puntuali data: {e}")
                        self.exception = e
                        return False

                # Get parametri_puntuali data from CSV
                self.parametri_puntuali_data = {}
                if "parametri_puntuali" in self.csv_files["puntuali"]:
                    try:
                        self.logger.debug(
                            f"Reading parametri_puntuali data from {self.csv_files['puntuali']['parametri_puntuali']}"
                        )
                        self.parametri_puntuali_data = self.read_csv_data(
                            "parametri_puntuali", self.csv_files["puntuali"]["parametri_puntuali"]
                        )
                        self.parametri_puntuali_seq = self.get_parametri_puntuali_seq()
                    except Exception as e:
                        self.logger.error(f"Error reading parametri_puntuali data: {e}")
                        self.exception = e
                        return False

                # Get curve data from CSV
                self.curve_data = {}
                if "curve" in self.csv_files["puntuali"]:
                    try:
                        self.logger.debug(f"Reading curve data from {self.csv_files['puntuali']['curve']}")
                        self.curve_data = self.read_csv_data("curve", self.csv_files["puntuali"]["curve"])
                        self.curve_seq = self.get_curve_seq()
                    except Exception as e:
                        self.logger.error(f"Error reading curve data: {e}")
                        self.exception = e
                        return False

            if DEBUG_MODE:
                self.logger.warning(f"{'#' * 15} Deleting all siti_puntuali!")
                self.delete_all_siti_puntuali()

            for feature in features:
                self.iterations += 1
                self.setProgress(self.iterations * 100 / self.num_siti)

                try:
                    self.logger.debug(f"Processing feature {feature['ID_SPU']}")
                    sito_puntuale = self.sito_puntuale_data[feature["ID_SPU"]]
                except KeyError:
                    self.logger.warning(f"ID_SPU {feature['ID_SPU']} not found in {self.data_source}, skipping")
                    continue

                sito_puntuale["geom"] = feature.geometry().asWkt()
                # geometry = feature.geometry()
                # # Convert to single part
                # if geometry.isMultipart():
                #     parts = geometry.asGeometryCollection()
                #     geometry = parts[0]
                #     if len(parts) > 1:
                #         self.set_log_message.emit(
                #             "Geometry from layer %s is multipart with more than one part: taking first part only"
                #             % (vector_layer.name())
                #         )
                # geom = geometry.asWkt()
                # if not geometry.isGeosValid():
                #     self.set_log_message.emit(
                #         "Wrong geometry from layer %s, expression: %s: %s"
                #         % (vector_layer.name(), exp, geom)
                #     )
                # if geometry.isNull():
                #     self.set_log_message.emit(
                #         "Null geometry from layer %s, expression: %s: %s"
                #         % (vector_layer.name(), exp, geom)
                #     )

                # adapt counters when data is already present
                sito_puntuale_source_pkey = sito_puntuale["pkey_spu"]
                if self.adapt_counters and self.sito_puntuale_seq > 0:
                    new_pkey_spu = int(sito_puntuale["pkey_spu"]) + self.sito_puntuale_seq
                    self.logger.debug(f"pkey_spu: {sito_puntuale['pkey_spu']} -> {new_pkey_spu}")
                    sito_puntuale["pkey_spu"] = new_pkey_spu
                    sito_puntuale["ID_SPU"] = (
                        sito_puntuale["ubicazione_prov"]
                        + sito_puntuale["ubicazione_com"]
                        + "P"
                        + str(sito_puntuale["pkey_spu"])
                    )

                # add import note
                sito_puntuale["note_sito"] = (
                    f"[MzS Tools] Dati del sito, indagini e parametri correlati importati da {self.data_source} in data {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n{sito_puntuale['note_sito']}"
                )

                try:
                    self.insert_sito_puntuale(sito_puntuale)
                except Exception as e:
                    self.logger.error(f"Error inserting sito_puntuale {sito_puntuale['ID_SPU']}: {e}")
                    continue

                ############################################################
                # insert indagini_puntuali
                current_pkey_spu = sito_puntuale_source_pkey if self.adapt_counters else sito_puntuale["pkey_spu"]

                filtered_indagini = {
                    key: value for key, value in self.indagini_puntuali_data.items() if str(key[0]) == current_pkey_spu
                }
                # self.logger.debug(f"pkey_spu: {current_pkey_spu} - Filtered elements: {filtered_indagini}")

                for key, value in filtered_indagini.items():
                    # self.log(f"Inserting indagine puntuale - Key: {key}, Value: {value}")
                    # add ID_SPU to the data
                    value["ID_SPU"] = sito_puntuale["ID_SPU"]
                    # turn empty strings into None to avoid CHECK constraint errors
                    for k in value.keys():
                        if value[k] == "":
                            value[k] = None
                    # change counters when data is already present
                    indagine_puntuale_source_pkey = value["pkey_indpu"]
                    indagine_puntuale_source_id_indpu = value["ID_INDPU"]
                    if self.adapt_counters and self.indagini_puntuali_seq > 0:
                        value["pkey_indpu"] = int(value["pkey_indpu"]) + self.indagini_puntuali_seq
                        value["ID_INDPU"] = value["ID_SPU"] + value["tipo_ind"] + str(value["pkey_indpu"])

                    # copy and adapt attachments
                    try:
                        if value["doc_ind"]:
                            # self.log(f"Copying attachment {value['doc_ind']}")
                            new_file_name = self.copy_attachment(
                                value["doc_ind"], indagine_puntuale_source_id_indpu, value["ID_INDPU"]
                            )
                            if new_file_name:
                                value["doc_ind"] = "./Allegati/Documenti/" + new_file_name
                    except Exception as e:
                        self.logger.warning(f"Error copying indagine puntuale attachment {value['doc_ind']}: {e}")

                    try:
                        self.insert_indagine_puntuale(value)
                    except Exception as e:
                        self.logger.error(f"Error inserting indagine puntuale {value['ID_INDPU']}: {e}")
                        continue

                    ############################################################
                    # insert parametri_puntuali
                    current_pkey_indpu = indagine_puntuale_source_pkey if self.adapt_counters else value["pkey_indpu"]
                    current_idindpu = value["ID_INDPU"]

                    filtered_parametri = {
                        key: value
                        for key, value in self.parametri_puntuali_data.items()
                        if str(key[0]) == current_pkey_indpu
                    }
                    # self.log(f"pkey_indpu: {current_pkey_indpu} - Filtered elements: {filtered_parametri}")

                    for key, value in filtered_parametri.items():
                        # self.log(f"Inserting parametro puntuale - Key: {key}, Value: {value}")
                        # add ID_INDPU to the data
                        value["ID_INDPU"] = current_idindpu
                        # add valore_appoggio if valore is not a number
                        value["valore_appoggio"] = None
                        try:
                            int(value["valore"].strip().replace(",", "."))
                        except ValueError:
                            try:
                                float(value["valore"].strip().replace(",", "."))
                            except ValueError:
                                value["valore_appoggio"] = value["valore"]
                        # turn empty strings into None to avoid CHECK constraint errors
                        for k in value.keys():
                            if value[k] == "":
                                value[k] = None

                        # change counters when data is already present
                        parametro_puntuale_source_pkey = value["pkey_parpu"]
                        parametro_puntuale_source_id_parpu = value["ID_PARPU"]
                        if self.adapt_counters and self.parametri_puntuali_seq > 0:
                            value["pkey_parpu"] = int(value["pkey_parpu"]) + self.parametri_puntuali_seq
                            value["ID_PARPU"] = value["ID_INDPU"] + value["tipo_parpu"] + str(value["pkey_parpu"])

                        # copy and adapt attachments
                        try:
                            if value["tab_curve"]:
                                # self.log(f"Copying tab_curve {value['tab_curve']}")
                                new_file_name = self.copy_attachment(
                                    value["tab_curve"], parametro_puntuale_source_id_parpu, value["ID_PARPU"]
                                )
                                if new_file_name:
                                    value["tab_curve"] = "./Allegati/Documenti/" + new_file_name
                        except Exception as e:
                            self.logger.warning(f"Error copying parametro attachment {value['tab_curve']}: {e}")

                        try:
                            self.insert_parametro_puntuale(value)
                        except Exception as e:
                            self.logger.error(f"Error inserting parametro puntuale {value['ID_PARPU']}: {e}")
                            continue

                        ############################################################
                        # insert curve
                        current_pkey_parpu = (
                            parametro_puntuale_source_pkey if self.adapt_counters else value["pkey_parpu"]
                        )
                        current_idparpu = value["ID_PARPU"]
                        filtered_curve = {
                            key: value for key, value in self.curve_data.items() if str(key[0]) == current_pkey_parpu
                        }
                        # self.log(f"pkey_parpu: {current_pkey_parpu} - Filtered elements: {filtered_curve}")
                        for key, value in filtered_curve.items():
                            # self.log(f"Inserting curve - Key: {key}, Value: {value}")
                            # add ID_PARPU to the data
                            value["ID_PARPU"] = current_idparpu
                            # turn empty strings into None to avoid CHECK constraint errors
                            for k in value.keys():
                                if value[k] == "":
                                    value[k] = None

                            # change counters when data is already present
                            if self.adapt_counters and self.curve_seq > 0:
                                value["pkey_curve"] = int(value["pkey_curve"]) + self.curve_seq

                            try:
                                self.insert_curve(value)
                            except Exception as e:
                                self.logger.error(f"Error inserting 'curve' value {value['pkey_curve']}: {e}")
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
                self.logger.debug("Closing SQLite connection...")
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
    def insert_sito_puntuale(self, data: dict):
        """Insert a new 'sito_puntuale' record into the database."""
        with self.get_spatialite_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """INSERT INTO sito_puntuale (pkuid, id_spu, indirizzo, mod_identcoord, desc_modcoord,
                        quota_slm, modo_quota, data_sito, note_sito, geom) 
                        VALUES(:pkey_spu, :ID_SPU, :indirizzo, :mod_identcoord, :desc_modcoord,
                        :quota_slm, :modo_quota, :data_sito, :note_sito, GeomFromText(:geom, 32633));""",
                data,
            )
            conn.commit()
            cursor.close()

    @retry_on_lock()
    def delete_sito_puntuale(self, pkuid: int):
        """Delete a 'sito_puntuale' record from the database."""
        with self.get_spatialite_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM sito_puntuale WHERE pkuid = :pkuid;", {"pkuid": pkuid})
            conn.commit()
            cursor.close()

    @retry_on_lock()
    def delete_all_siti_puntuali(self):
        """Delete all 'sito_puntuale' records from the database."""
        with self.get_spatialite_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM sito_puntuale;")
            conn.commit()
            cursor.close()

    @retry_on_lock()
    def get_sito_puntuale_seq(self):
        with self.get_spatialite_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''SELECT seq FROM sqlite_sequence WHERE name="sito_puntuale"''')
            data = cursor.fetchall()
            cursor.close()
        return data[0][0] if data else 0

    @retry_on_lock()
    def get_indagini_puntuali_seq(self):
        with self.get_spatialite_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''SELECT seq FROM sqlite_sequence WHERE name="indagini_puntuali"''')
            data = cursor.fetchall()
            cursor.close()
        return data[0][0] if data else 0

    @retry_on_lock()
    def get_parametri_puntuali_seq(self):
        with self.get_spatialite_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''SELECT seq FROM sqlite_sequence WHERE name="parametri_puntuali"''')
            data = cursor.fetchall()
            cursor.close()
        return data[0][0] if data else 0

    @retry_on_lock()
    def get_curve_seq(self):
        with self.get_spatialite_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''SELECT seq FROM sqlite_sequence WHERE name="curve"''')
            data = cursor.fetchall()
            cursor.close()
        return data[0][0] if data else 0

    @retry_on_lock()
    def insert_indagine_puntuale(self, data: dict):
        with self.get_spatialite_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """INSERT INTO indagini_puntuali (pkuid, id_spu, classe_ind, tipo_ind, id_indpu, id_indpuex, arch_ex,
                note_ind, prof_top, prof_bot, spessore, quota_slm_top, quota_slm_bot, data_ind, doc_pag, doc_ind)
                        VALUES(:pkey_indpu, :ID_SPU, :classe_ind, :tipo_ind, :ID_INDPU, :id_indpuex, :arch_ex,
                        :note_ind, :prof_top, :prof_bot, :spessore, :quota_slm_top, :quota_slm_bot, :data_ind,
                        :doc_pag, :doc_ind);""",
                data,
            )
            conn.commit()
            cursor.close()

    @retry_on_lock()
    def insert_parametro_puntuale(self, data: dict):
        with self.get_spatialite_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """INSERT INTO parametri_puntuali (pkuid, id_indpu, tipo_parpu, id_parpu, prof_top, prof_bot, spessore,
                quota_slm_top, quota_slm_bot, valore, attend_mis, tab_curve, note_par, data_par, valore_appoggio)
                        VALUES(:pkey_parpu, :ID_INDPU, :tipo_parpu, :ID_PARPU, :prof_top, :prof_bot, :spessore,
                        :quota_slm_top, :quota_slm_bot, :valore, :attend_mis, :tab_curve, :note_par, :data_par,
                        :valore_appoggio);""",
                data,
            )
            conn.commit()
            cursor.close()

    @retry_on_lock()
    def insert_curve(self, data: dict):
        with self.get_spatialite_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """INSERT INTO curve (pkuid, id_parpu, cond_curve, varx, vary)
                        VALUES(:pkey_curve, :ID_PARPU, :cond_curve, :varx, :vary);""",
                data,
            )
            conn.commit()
            cursor.close()

    def get_spatialite_db_connection(self):
        if not self.spatialite_db_connection:
            self.spatialite_db_connection = spatialite_connect(str(self.prj_manager.db_path))
        return self.spatialite_db_connection

    def copy_attachment(self, attachment_file_name: str, old_id: str, new_id: str):
        # check file exists
        file_path = self.proj_paths["Documenti"]["path"] / attachment_file_name
        if not Path(file_path).exists():
            self.logger.warning(f"Attachment {file_path} not found, skipping")
            return None
        # copy in the project folder
        dest_path = self.prj_manager.project_path / "Allegati" / "Documenti"

        # if a new ID has been assigned to the indagine or parametro, add it to the file name
        new_file_name = None
        if old_id != new_id:
            new_file_name = f"{new_id}_[{file_path.stem}]{file_path.suffix}"

        if new_file_name:
            shutil.copy(file_path, dest_path / new_file_name)
        else:
            shutil.copy(file_path, dest_path)

        self.logger.debug(
            f"Attachment {attachment_file_name} copied to project folder {'as ' + new_file_name if new_file_name else ''}"
        )
        return new_file_name or attachment_file_name

    def get_sqlite_sito_puntuale_data(self):
        """Get sito_puntuale data from SQLite database"""
        data = {}
        cursor = self.sqlite_db_connection.cursor()
        cursor.execute("""
            SELECT pkey_spu, ID_SPU, ubicazione_prov, ubicazione_com, indirizzo, 
                coord_X, coord_Y, mod_identcoord, desc_modcoord, quota_slm, 
                modo_quota, data_sito, note_sito
            FROM sito_puntuale
        """)

        rows = cursor.fetchall()
        for row in rows:
            row_dict = {
                "pkey_spu": str(row["pkey_spu"]),
                "ID_SPU": row["ID_SPU"],
                "ubicazione_prov": row["ubicazione_prov"],
                "ubicazione_com": row["ubicazione_com"],
                "indirizzo": row["indirizzo"] or "",
                "coord_X": str(row["coord_X"]) if row["coord_X"] is not None else "",
                "coord_Y": str(row["coord_Y"]) if row["coord_Y"] is not None else "",
                "mod_identcoord": row["mod_identcoord"] or "",
                "desc_modcoord": row["desc_modcoord"] or "",
                "quota_slm": str(row["quota_slm"]) if row["quota_slm"] is not None else "",
                "modo_quota": row["modo_quota"] or "",
                "data_sito": row["data_sito"] or "",
                "note_sito": row["note_sito"] or "",
            }
            data[row["ID_SPU"]] = row_dict

        self.logger.info(f"Read {len(data)} records from sito_puntuale in SQLite")
        return data

    def get_sqlite_indagini_puntuali_data(self):
        """Get indagini_puntuali data from SQLite database"""
        data = {}
        cursor = self.sqlite_db_connection.cursor()
        cursor.execute("""
            SELECT pkey_spu, pkey_indpu, classe_ind, tipo_ind, ID_INDPU, id_indpuex,
                arch_ex, note_ind, prof_top, prof_bot, spessore, quota_slm_top, 
                quota_slm_bot, data_ind, doc_pag, doc_ind, id_spu
            FROM indagini_puntuali
        """)

        rows = cursor.fetchall()
        for row in rows:
            row_dict = {
                "pkey_spu": str(row["pkey_spu"]),
                "pkey_indpu": str(row["pkey_indpu"]),
                "classe_ind": row["classe_ind"] or "",
                "tipo_ind": row["tipo_ind"] or "",
                "ID_INDPU": row["ID_INDPU"],
                "id_indpuex": row["id_indpuex"] or "",
                "arch_ex": row["arch_ex"] or "",
                "note_ind": row["note_ind"] or "",
                "prof_top": str(row["prof_top"]) if row["prof_top"] is not None else "",
                "prof_bot": str(row["prof_bot"]) if row["prof_bot"] is not None else "",
                "spessore": str(row["spessore"]) if row["spessore"] is not None else "",
                "quota_slm_top": str(row["quota_slm_top"]) if row["quota_slm_top"] is not None else "",
                "quota_slm_bot": str(row["quota_slm_bot"]) if row["quota_slm_bot"] is not None else "",
                "data_ind": row["data_ind"] or "",
                "doc_pag": row["doc_pag"] or "",
                "doc_ind": row["doc_ind"] or "",
                "id_spu": row["id_spu"] or "",
            }
            data[(str(row["pkey_spu"]), row["ID_INDPU"])] = row_dict

        self.logger.info(f"Read {len(data)} records from indagini_puntuali in SQLite")
        return data

    def get_sqlite_parametri_puntuali_data(self):
        """Get parametri_puntuali data from SQLite database"""
        data = {}
        cursor = self.sqlite_db_connection.cursor()
        cursor.execute("""
            SELECT pkey_indpu, pkey_parpu, tipo_parpu, ID_PARPU, prof_top, prof_bot,
                spessore, quota_slm_top, quota_slm_bot, valore, attend_mis, 
                tab_curve, note_par, data_par, id_indpu
            FROM parametri_puntuali
        """)

        rows = cursor.fetchall()
        for row in rows:
            row_dict = {
                "pkey_indpu": str(row["pkey_indpu"]),
                "pkey_parpu": str(row["pkey_parpu"]),
                "tipo_parpu": row["tipo_parpu"] or "",
                "ID_PARPU": row["ID_PARPU"],
                "prof_top": str(row["prof_top"]) if row["prof_top"] is not None else "",
                "prof_bot": str(row["prof_bot"]) if row["prof_bot"] is not None else "",
                "spessore": str(row["spessore"]) if row["spessore"] is not None else "",
                "quota_slm_top": str(row["quota_slm_top"]) if row["quota_slm_top"] is not None else "",
                "quota_slm_bot": str(row["quota_slm_bot"]) if row["quota_slm_bot"] is not None else "",
                "valore": row["valore"] or "",
                "attend_mis": row["attend_mis"] or "",
                "tab_curve": row["tab_curve"] or "",
                "note_par": row["note_par"] or "",
                "data_par": row["data_par"] or "",
                "id_indpu": row["id_indpu"] or "",
            }
            data[(str(row["pkey_indpu"]), row["ID_PARPU"])] = row_dict

        self.logger.info(f"Read {len(data)} records from parametri_puntuali in SQLite")
        return data

    def get_sqlite_curve_data(self):
        """Get curve data from SQLite database"""
        data = {}
        cursor = self.sqlite_db_connection.cursor()
        cursor.execute("""
            SELECT pkey_parpu, pkey_curve, cond_curve, varx, vary, id_parpu
            FROM curve
        """)

        rows = cursor.fetchall()
        for row in rows:
            row_dict = {
                "pkey_parpu": str(row["pkey_parpu"]),
                "pkey_curve": str(row["pkey_curve"]),
                "cond_curve": row["cond_curve"] or "",
                "varx": str(row["varx"]) if row["varx"] is not None else "",
                "vary": str(row["vary"]) if row["vary"] is not None else "",
                "id_parpu": row["id_parpu"] or "",
            }
            data[(str(row["pkey_parpu"]), str(row["pkey_curve"]))] = row_dict

        self.logger.info(f"Read {len(data)} records from curve in SQLite")
        return data

    def read_csv_data(self, table_type, file_path):
        """
        Read data from CSV file and convert it to the same format as get_* methods in AccessDbConnection

        Args:
            table_type: Type of table ('sito_puntuale', 'indagini_puntuali', 'parametri_puntuali', 'curve')
            file_path: Path to the CSV file

        Returns:
            Dictionary with data from CSV file in the same format as get_* methods in AccessDbConnection
        """
        import csv

        # Expected field names for each table type (case insensitive)
        expected_fields = {
            "sito_puntuale": {
                "pkuid": "pkey_spu",
                "pkey_spu": "pkey_spu",
                "id_spu": "ID_SPU",
                "ubicazione_prov": "ubicazione_prov",
                "ubicazione_com": "ubicazione_com",
                "indirizzo": "indirizzo",
                "coord_x": "coord_X",
                "coord_y": "coord_Y",
                "mod_identcoord": "mod_identcoord",
                "desc_modcoord": "desc_modcoord",
                "quota_slm": "quota_slm",
                "modo_quota": "modo_quota",
                "data_sito": "data_sito",
                "note_sito": "note_sito",
            },
            "indagini_puntuali": {
                "pkey_spu": "pkey_spu",
                "pkey_indpu": "pkey_indpu",
                "classe_ind": "classe_ind",
                "tipo_ind": "tipo_ind",
                "id_indpu": "ID_INDPU",
                "id_indpuex": "id_indpuex",
                "arch_ex": "arch_ex",
                "note_ind": "note_ind",
                "prof_top": "prof_top",
                "prof_bot": "prof_bot",
                "spessore": "spessore",
                "quota_slm_top": "quota_slm_top",
                "quota_slm_bot": "quota_slm_bot",
                "data_ind": "data_ind",
                "doc_pag": "doc_pag",
                "doc_ind": "doc_ind",
            },
            "parametri_puntuali": {
                "pkey_indpu": "pkey_indpu",
                "pkey_parpu": "pkey_parpu",
                "tipo_parpu": "tipo_parpu",
                "id_parpu": "ID_PARPU",
                "prof_top": "prof_top",
                "prof_bot": "prof_bot",
                "spessore": "spessore",
                "quota_slm_top": "quota_slm_top",
                "quota_slm_bot": "quota_slm_bot",
                "valore": "valore",
                "attend_mis": "attend_mis",
                "tab_curve": "tab_curve",
                "note_par": "note_par",
                "data_par": "data_par",
            },
            "curve": {
                "pkey_parpu": "pkey_parpu",
                "pkey_curve": "pkey_curve",
                "cond_curve": "cond_curve",
                "varx": "varx",
                "vary": "vary",
            },
        }

        # Required fields for each table type (to create key)
        required_fields = {
            "sito_puntuale": ["ID_SPU"],
            "indagini_puntuali": ["pkey_spu", "ID_INDPU"],
            "parametri_puntuali": ["pkey_indpu", "ID_PARPU"],
            "curve": ["pkey_parpu", "pkey_curve"],
        }

        # Numeric fields that should be converted
        numeric_fields = [
            "pkey_spu",
            "pkey_indpu",
            "pkey_parpu",
            "pkey_curve",
            "prof_top",
            "prof_bot",
            "spessore",
            "quota_slm",
            "quota_slm_top",
            "quota_slm_bot",
            "varx",
            "vary",
        ]

        # Result container
        data = {}

        try:
            with open(file_path, "r", encoding="utf-8") as csvfile:
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
                        if table_type == "sito_puntuale":
                            key = row_dict["ID_SPU"]
                            data[key] = row_dict
                        elif table_type == "indagini_puntuali":
                            # Use the same key format as AccessDbConnection (pkey_spu, ID_INDPU)
                            key = (row_dict["pkey_spu"], row_dict["ID_INDPU"])
                            data[key] = row_dict
                        elif table_type == "parametri_puntuali":
                            # Use the same key format as AccessDbConnection (pkey_indpu, ID_PARPU)
                            key = (row_dict["pkey_indpu"], row_dict["ID_PARPU"])
                            data[key] = row_dict
                        elif table_type == "curve":
                            # Use the same key format as AccessDbConnection (pkey_parpu, pkey_curve)
                            key = (row_dict["pkey_parpu"], row_dict["pkey_curve"])
                            data[key] = row_dict
                    except KeyError as e:
                        self.logger.warning(f"Skipping row due to missing required key field: {e}")
                        continue

                self.logger.info(f"Read {len(data)} records from {table_type} CSV file")
                return data

        except Exception as e:
            self.logger.error(f"Error reading CSV file {file_path}: {e}")
            raise e
