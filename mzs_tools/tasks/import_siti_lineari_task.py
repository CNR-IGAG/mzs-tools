import logging
import shutil
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
        mdb_password: str = None,
        adapt_counters: bool = True,
    ):
        super().__init__("Import siti lineari (siti, indagini, parametri)", QgsTask.CanCancel)

        self.iterations = 0
        self.exception = None

        # the logger is configured in the import data dialog module
        self.logger = logging.getLogger("mzs_tools.tasks.import_data")

        self.data_source = data_source
        self.mdb_password = mdb_password

        self.prj_manager = MzSProjectManager.instance()
        self.spatialite_db_connection = None
        self.mdb_connection = None

        self.proj_paths = proj_paths
        self.mdb_path = self.proj_paths["CdI_Tabelle.mdb"]["path"]

        self.siti_lineari_shapefile = QgsVectorLayer(str(self.proj_paths["Ind_ln.shp"]["path"]), "Ind_ln", "ogr")
        self.num_siti = self.siti_lineari_shapefile.featureCount()

        # option to adapt the primary keys of the imported data to avoid conflicts with existing data
        self.adapt_counters = adapt_counters

    def run(self):
        self.logger.info(f"{'#' * 15} Starting task {self.description()}")
        if DEBUG_MODE:
            self.logger.warning(f"\n{'#' * 50}\n# Running in DEBUG mode! Data will be DESTROYED! #\n{'#' * 50}")

        self.iterations = 0

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

            else:
                # TODO: get data from csv
                pass

            if DEBUG_MODE:
                self.logger.warning(f"{'#' * 15} Deleting all siti_lineari!")
                self.delete_all_siti_lineari()

            for feature in features:
                self.iterations += 1
                self.setProgress(self.iterations * 100 / self.num_siti)

                try:
                    self.logger.debug(f"Processing feature {feature['ID_SLN']}")
                    sito_lineare = self.sito_lineare_data[feature["ID_SLN"]]
                except KeyError:
                    self.logger.warning(f"ID_SLN {feature['ID_SLN']} not found in {self.data_source}, skipping")
                    continue

                sito_lineare["geom"] = feature.geometry().asWkt()
                geometry = feature.geometry()
                # Convert to single part
                if geometry.isMultipart():
                    parts = geometry.asGeometryCollection()
                    geometry = parts[0]
                    # if len(parts) > 1:
                    #     self.set_log_message.emit(
                    #         "Geometry from layer %s is multipart with more than one part: taking first part only"
                    #         % (vector_layer.name())
                    #     )
                    sito_lineare["geom"] = geometry.asWkt()
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

                # avoid CHECK constraint errors
                if not sito_lineare["Aquota"]:
                    sito_lineare["Aquota"] = None
                if not sito_lineare["Bquota"]:
                    sito_lineare["Bquota"] = None

                # change counters when data is already present
                sito_lineare_source_pkey = sito_lineare["pkey_sln"]
                if self.adapt_counters and self.sito_lineare_seq > 0:
                    new_pkey_sln = int(sito_lineare["pkey_sln"]) + self.sito_lineare_seq
                    self.logger.debug(f"pkey_sln: {sito_lineare['pkey_sln']} -> {new_pkey_sln}")
                    sito_lineare["pkey_sln"] = new_pkey_sln
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
                    for k in value.keys():
                        if value[k] == "":
                            value[k] = None
                    # change counters when data is already present
                    indagine_lineare_source_pkey = value["pkey_indln"]
                    indagine_lineare_source_id_indln = value["ID_INDLN"]
                    if self.adapt_counters and self.indagini_lineari_seq > 0:
                        value["pkey_indln"] = int(value["pkey_indln"]) + self.indagini_lineari_seq
                        value["ID_INDLN"] = value["ID_SLN"] + value["tipo_ind"] + str(value["pkey_indln"])

                    # copy and adapt attachments
                    try:
                        if value["doc_ind"]:
                            # self.log(f"Copying attachment {value['doc_ind']}")
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

                    for key, value in filtered_parametri.items():
                        # self.log(f"Inserting parametro puntuale - Key: {key}, Value: {value}")
                        # add ID_INDPU to the data
                        value["ID_INDLN"] = current_idindln

                        # turn empty strings into None to avoid CHECK constraint errors
                        for k in value.keys():
                            if value[k] == "":
                                value[k] = None

                        # change counters when data is already present
                        # parametro_lineare_source_pkey = value["pkey_parpu"]
                        if self.adapt_counters and self.parametri_lineari_seq > 0:
                            value["pkey_parln"] = int(value["pkey_parln"]) + self.parametri_lineari_seq
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
        with self.get_spatialite_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """INSERT INTO sito_lineare (pkuid, id_sln, mod_identcoord, desc_modcoord, aquota, bquota, data_sito,
                note_sito, geom) 
                        VALUES(:pkey_sln, :ID_SLN, :mod_identcoord, :desc_modcoord, :Aquota, :Bquota, :data_sito,
                        :note_sito, GeomFromText(:geom, 32633));""",
                data,
            )
            conn.commit()
            cursor.close()

    # def delete_sito_puntuale(self, pkuid: int):
    #     """Delete a 'sito_puntuale' record from the database."""
    #     with self.get_spatialite_db_connection() as conn:
    #         cursor = conn.cursor()
    #         cursor.execute("DELETE FROM sito_puntuale WHERE pkuid = :pkuid;", {"pkuid": pkuid})
    #         conn.commit()
    #         cursor.close()

    @retry_on_lock()
    def delete_all_siti_lineari(self):
        """Delete all 'sito_lineare' records from the database."""
        with self.get_spatialite_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM sito_lineare;")
            conn.commit()
            cursor.close()

    @retry_on_lock()
    def get_sito_lineare_seq(self):
        with self.get_spatialite_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''SELECT seq FROM sqlite_sequence WHERE name="sito_lineare"''')
            data = cursor.fetchall()
            cursor.close()
        return data[0][0] if data else 0

    @retry_on_lock()
    def get_indagini_lineari_seq(self):
        with self.get_spatialite_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''SELECT seq FROM sqlite_sequence WHERE name="indagini_lineari"''')
            data = cursor.fetchall()
            cursor.close()
        return data[0][0] if data else 0

    @retry_on_lock()
    def get_parametri_lineari_seq(self):
        with self.get_spatialite_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''SELECT seq FROM sqlite_sequence WHERE name="parametri_lineari"''')
            data = cursor.fetchall()
            cursor.close()
        return data[0][0] if data else 0

    @retry_on_lock()
    def insert_indagine_lineare(self, data: dict):
        with self.get_spatialite_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """INSERT INTO indagini_lineari (pkuid, id_sln, classe_ind, tipo_ind, id_indln, id_indlnex, arch_ex,
                note_indln, data_ind, doc_pag, doc_ind)
                        VALUES(:pkey_indln, :ID_SLN, :classe_ind, :tipo_ind, :ID_INDLN, :id_indlnex, :arch_ex,
                        :note_indln, :data_ind, :doc_pag, :doc_ind);""",
                data,
            )
            conn.commit()
            cursor.close()

    @retry_on_lock()
    def insert_parametro_lineare(self, data: dict):
        with self.get_spatialite_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """INSERT INTO parametri_lineari (pkuid, id_indln, tipo_parln, id_parln, prof_top, prof_bot, spessore,
                quota_slm_top, quota_slm_bot, valore, attend_mis, note_par, data_par)
                        VALUES(:pkey_parln, :ID_INDLN, :tipo_parln, :ID_PARLN, :prof_top, :prof_bot, :spessore,
                        :quota_slm_top, :quota_slm_bot, :valore, :attend_mis, :note_par, :data_par);""",
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
