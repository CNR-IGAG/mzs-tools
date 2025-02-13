from datetime import datetime
from pathlib import Path
import shutil

from qgis.core import QgsTask, QgsVectorLayer
from qgis.utils import spatialite_connect

from mzs_tools.core.mzs_project_manager import MzSProjectManager
from mzs_tools.plugin_utils.logging import MzSToolsLogger
from mzs_tools.plugin_utils.misc import retry_on_lock
from mzs_tools.tasks.common_functions import setup_mdb_connection


class ImportSitiPuntualiTask(QgsTask):
    def __init__(
        self,
        proj_paths: dict,
        data_source: str,
        mdb_password: str = None,
        adapt_counters: bool = True,
    ):
        super().__init__("Import siti puntuali (siti, indagini, parametri, curve)", QgsTask.CanCancel)

        self.iterations = 0
        self.exception = None

        self.log = MzSToolsLogger().log

        self.data_source = data_source
        self.mdb_password = mdb_password

        self.prj_manager = MzSProjectManager.instance()
        self.spatialite_db_connection = None
        self.mdb_connection = None

        self.proj_paths = proj_paths
        self.mdb_path = self.proj_paths["CdI_Tabelle.mdb"]["path"]

        self.siti_puntuali_shapefile = QgsVectorLayer(str(self.proj_paths["Ind_pu.shp"]["path"]), "Ind_pu", "ogr")
        self.num_siti = self.siti_puntuali_shapefile.featureCount()

        # option to adapt the primary keys of the imported data to avoid conflicts with existing data
        self.adapt_counters = adapt_counters

    def run(self):
        self.log(f"Starting task {self.description()}")
        self.iterations = 0

        try:
            # get features from the shapefile
            features = self.siti_puntuali_shapefile.getFeatures()

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

            else:
                # TODO: get data from csv
                pass

            # TODO: testing only
            self.log("Deleting all siti_puntuali", log_level=1)
            self.delete_all_siti_puntuali()

            for feature in features:
                self.iterations += 1
                # self.log(f"{self.iterations} / {self.num_siti}")
                self.setProgress(self.iterations * 100 / self.num_siti)
                # self.log(f"ID_SPU: {feature['ID_SPU']} - {self.progress()}")

                # take sito_puntuale data from db or csv
                if self.data_source == "mdb":
                    try:
                        sito_puntuale = self.sito_puntuale_data[feature["ID_SPU"]]
                        # self.log(f"Data from mdb: {sito_puntuale}")
                    except KeyError:
                        self.log(f"ID_SPU {feature['ID_SPU']} not found in mdb, skipping", log_level=1)
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

                    # change counters when data is already present
                    sito_puntuale_source_pkey = sito_puntuale["pkey_spu"]
                    if self.adapt_counters and self.sito_puntuale_seq > 0:
                        sito_puntuale["pkey_spu"] = int(sito_puntuale["pkey_spu"]) + self.sito_puntuale_seq
                        sito_puntuale["ID_SPU"] = (
                            sito_puntuale["ubicazione_prov"]
                            + sito_puntuale["ubicazione_com"]
                            + "P"
                            + str(sito_puntuale["pkey_spu"])
                        )

                    # add import note
                    sito_puntuale["note_sito"] = (
                        f"[MzS Tools] Dati del sito, indagini e parametri correlati importati da database Access in data {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n{sito_puntuale["note_sito"]}"
                    )

                    try:
                        self.insert_sito_puntuale(sito_puntuale)
                    except Exception as e:
                        self.log(f"Error inserting sito_puntuale {sito_puntuale['ID_SPU']}: {e}", log_level=2)
                        continue

                    ############################################################
                    # insert indagini_puntuali
                    current_pkey_spu = sito_puntuale_source_pkey if self.adapt_counters else sito_puntuale["pkey_spu"]

                    filtered_indagini = {
                        key: value
                        for key, value in self.indagini_puntuali_data.items()
                        if str(key[0]) == current_pkey_spu
                    }
                    # self.log(f"pkey_spu: {current_spu_id} - Filtered elements: {filtered_indagini}")

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
                            self.log(
                                f"Error copying indagine puntuale attachment {value['doc_ind']}: {e}", log_level=1
                            )

                        try:
                            self.insert_indagine_puntuale(value)
                        except Exception as e:
                            self.log(f"Error inserting indagine puntuale {value['ID_INDPU']}: {e}", log_level=2)
                            continue

                        ############################################################
                        # insert parametri_puntuali
                        current_pkey_indpu = (
                            indagine_puntuale_source_pkey if self.adapt_counters else value["pkey_indpu"]
                        )
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
                                self.log(f"Error copying parametro attachment {value['tab_curve']}: {e}", log_level=1)

                            try:
                                self.insert_parametro_puntuale(value)
                            except Exception as e:
                                self.log(f"Error inserting parametro puntuale {value['ID_PARPU']}: {e}", log_level=2)
                                continue

                            ############################################################
                            # insert curve
                            current_pkey_parpu = (
                                parametro_puntuale_source_pkey if self.adapt_counters else value["pkey_parpu"]
                            )
                            current_idparpu = value["ID_PARPU"]
                            filtered_curve = {
                                key: value
                                for key, value in self.curve_data.items()
                                if str(key[0]) == current_pkey_parpu
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
                                    self.log(f"Error inserting 'curve' value {value['pkey_curve']}: {e}", log_level=2)
                                    continue

                # check isCanceled() to handle cancellation
                if self.isCanceled():
                    return False

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
            self.log(f"Task {self.description()} completed with {self.iterations} iterations")
        else:
            if self.exception is None:
                self.log(f"Task {self.description()} was canceled", log_level=1)
            else:
                self.log(f"Task {self.description()} failed: {self.exception}", log_level=2)

                raise self.exception

    def cancel(self):
        self.log(f"Task {self.description()} was canceled", log_level=1)
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
            self.log(f"Attachment {file_path} not found, skipping", log_level=1)
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

        # self.log(f"Attachment {attachment_file_name} copied to project folder", log_level=4)
        return new_file_name or attachment_file_name
