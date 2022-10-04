import csv
import os
import shutil
import sqlite3
import re

from qgis.core import *
from qgis.gui import *
from qgis.PyQt import QtGui, uic
from qgis.PyQt.QtCore import *
from qgis.PyQt.QtGui import *
from qgis.utils import *
from ..constants import *
from .abstract_worker import AbstractWorker, UserAbortedNotification


# FOR TESTING ONLY!!!
# When testing export: only import a few features to make the testing process faster
TESTING = False


class ImportWorker(AbstractWorker):
    '''Worker class handling data import from existing project'''

    def __init__(self, proj_abs_path, in_dir, tab_dir, map_registry_instance):
        AbstractWorker.__init__(self)
        # self.steps = steps
        self.proj_abs_path = proj_abs_path
        self.in_dir = in_dir
        self.tab_dir = tab_dir
        self.map_registry_instance = map_registry_instance

        self.current_step = 1
        self.check_sito_p = True
        self.check_sito_l = True

        self.db_path = os.path.join(self.proj_abs_path, "db", "indagini.sqlite")

        self.current_trig_name = None
        self.current_trig_table = None
        self.current_trig_sql = None

    def drop_trigger(self, lyr_name):
        tab_name = LAYER_DB_TAB[lyr_name]
        self.set_log_message.emit(f'Dropping {tab_name} insert trigger...')

        conn = sqlite3.connect(self.db_path)

        try:
            cur = conn.cursor()

            res = cur.execute(f"SELECT name, tbl_name, sql FROM sqlite_master WHERE type = 'trigger' AND name like 'ins_data%' AND tbl_name = '{tab_name}'")
            if res is not None:
                self.current_trig_name, self.current_trig_table, self.current_trig_sql = res.fetchone()

                cur.execute(f"DROP TRIGGER {self.current_trig_name}")
                cur.close()
                conn.commit()
            else:
                self.current_trig_name = self.current_trig_table = self.current_trig_sql = None

        # except:
        #     self.set_log_message.emit('ERRRRRROEREE...')
        #     cur.execute("rollback")
        finally:
            conn.close()

    def update_values_and_restore_trigger(self, lyr_name):
        self.set_log_message.emit(f'Updating {lyr_name} values and restoring insert trigger...')

        conn = sqlite3.connect(self.db_path)
        conn.text_factory = lambda x: str(x, 'utf-8', 'ignore')
        conn.enable_load_extension(True)
        conn.execute('SELECT load_extension("mod_spatialite")')
        
        try:
            cur = conn.cursor()
            self.set_log_message.emit(f'current_trig_sql: {self.current_trig_sql}')
            
            # update table data
            if lyr_name == "Siti puntuali":
                trig_queries_list = SITO_PUNTUALE_INS_TRIG_QUERIES.split(";")
            elif lyr_name == "Siti lineari":
                trig_queries_list = SITO_LINEARE_INS_TRIG_QUERIES.split(";")
            else:
                # re.BLACKMAGIC
                search_res = re.search("BEGIN(.*)(?=^END|\Z)", self.current_trig_sql, re.DOTALL)
                trig_queries = search_res.group(1)
                trig_queries_list = trig_queries.split(";")

            for query in trig_queries_list:
                if query:
                    self.set_log_message.emit(f'executing query: {query}')
                    cur.execute(query)

            # restore trigger
            cur.execute(self.current_trig_sql)
            
            cur.close()
            conn.commit()

        # except:
        #     self.set_log_message.emit('ERRRRRROEREE...')
        #     cur.execute("rollback")
        finally:
            conn.close()


    def work(self):
        path_tabelle = os.path.join(self.proj_abs_path, "Allegati", "Altro")
        z_list = []

        # calculate steps
        total_steps = len(POSIZIONE) + 5

        # step 1 (preparing data)
        ###############################################
        self.set_message.emit('Creating folders...')

        if os.path.exists(os.path.join(path_tabelle, "Indagini")):
            shutil.rmtree(os.path.join(path_tabelle, "Indagini"))

        os.makedirs(os.path.join(path_tabelle, "Indagini"))
        self.copy_files(os.path.join(self.in_dir, "Indagini"),
                        os.path.join(path_tabelle, "Indagini"))

        for nome_tab in LISTA_TAB:
            if os.path.exists(os.path.join(path_tabelle, nome_tab)):
                os.remove(os.path.join(path_tabelle, nome_tab))

        self.set_log_message.emit('Folder structure -> OK\n')

        self.set_message.emit('Copying tables...')
        self.copy_files(self.tab_dir, path_tabelle)

        # end step 1
        if self.killed:
            raise UserAbortedNotification('USER Killed')
        self.current_step = self.current_step + 1
        self.progress.emit(int(self.current_step * 100/total_steps))
        
        # step 2 (inserting features)
        ###############################################
        for chiave, valore in list(POSIZIONE.items()):

            if not os.path.exists(os.path.join(self.in_dir, valore[0], valore[1] + ".shp")):
                self.set_log_message.emit(
                    "'" + chiave + "' shapefile does not exist!\n")
                continue

            sourceLYR = QgsVectorLayer(os.path.join(
                self.in_dir, valore[0], valore[1] + ".shp"), valore[1], 'ogr')
            destLYR = self.map_registry_instance.mapLayersByName(chiave)[0]

            commonFields = self.attribute_adaptor(destLYR, sourceLYR)

            self.drop_trigger(chiave)

            if chiave == "Siti puntuali":
                if os.path.exists(os.path.join(path_tabelle, 'Sito_Puntuale.txt')):
                    self.insert_siti(sourceLYR, os.path.join(
                        path_tabelle, 'Sito_Puntuale.txt'), "puntuale")
                    self.set_message.emit(
                        "'" + chiave + "' shapefile has been copied!")
                    self.set_log_message.emit(
                        "'" + chiave + "' shapefile has been copied!\n")
                    z_list.append("Sito_Puntuale")
                else:
                    self.set_log_message.emit(
                        "Table 'Sito_Puntuale.txt' does not exist!\n")
                    self.check_sito_p = False

            elif chiave == "Siti lineari":
                if os.path.exists(os.path.join(path_tabelle, 'Sito_Lineare.txt')):
                    self.insert_siti(sourceLYR, os.path.join(
                        path_tabelle, 'Sito_Lineare.txt'), "lineare")
                    self.set_message.emit(
                        "'" + chiave + "' shapefile has been copied!")
                    self.set_log_message.emit(
                        "'" + chiave + "' shapefile has been copied!\n")
                    z_list.append("Sito_Lineare")
                else:
                    self.set_log_message.emit(
                        "Table 'Sito_Lineare.txt' does not exist!\n")
                    self.check_sito_l = False

            elif chiave == "Zone stabili liv 2" or chiave == "Zone instabili liv 2":
                sourceFeatures = sourceLYR.getFeatures(
                    QgsFeatureRequest(QgsExpression(" \"LIVELLO\" = 2 ")))
                self.set_message.emit(
                    "'" + chiave + "' shapefile has been copied!")
                self.set_log_message.emit(
                    "'" + chiave + "' shapefile has been copied!\n")
                self.calc_layer(sourceFeatures, destLYR, commonFields)

            elif chiave == "Zone stabili liv 3" or chiave == "Zone instabili liv 3":
                sourceFeatures = sourceLYR.getFeatures(
                    QgsFeatureRequest(QgsExpression(" \"LIVELLO\" = 3 ")))
                self.set_message.emit(
                    "'" + chiave + "' shapefile has been copied!")
                self.set_log_message.emit(
                    "'" + chiave + "' shapefile has been copied!\n")
                self.calc_layer(sourceFeatures, destLYR, commonFields)

            elif chiave == "Comune del progetto":
                pass
            else:
                # self.drop_trigger(chiave)

                sourceFeatures = sourceLYR.getFeatures()
                self.set_message.emit(
                    "'" + chiave + "' shapefile has been copied!")
                self.set_log_message.emit(
                    "'" + chiave + "' shapefile has been copied!\n")
                self.calc_layer(sourceFeatures, destLYR, commonFields)

                # if self.current_trig_sql is not None:
                #     self.update_values_and_restore_trigger(chiave)

            # restore insert trigger
            if self.current_trig_sql is not None:
                self.update_values_and_restore_trigger(chiave)

            if self.killed:
                break

            self.current_step = self.current_step + 1
            self.progress.emit(int(self.current_step * 100/total_steps))

        # end for
        if self.killed:
            raise UserAbortedNotification('USER Killed')

##		self.set_log_message.emit('Insert features -> OK\n')
        # end inserting features

        # step 3 (inserting indagini_puntuali and related data)
        #######################################################
        if self.check_sito_p is True and os.path.exists(os.path.join(path_tabelle, "Indagini_Puntuali.txt")):
            z_list.append("Indagini_Puntuali")
            self.drop_trigger("Indagini puntuali")
            self.insert_table("indagini_puntuali",
                              os.path.join(
                                  path_tabelle, "Indagini_Puntuali.txt"))
            if self.current_trig_sql is not None:
                self.update_values_and_restore_trigger("Indagini puntuali")
            self.set_log_message.emit(
                "'Indagini_Puntuali' table has been copied!\n")

            if os.path.exists(os.path.join(path_tabelle, "Parametri_Puntuali.txt")):
                z_list.append("Parametri_Puntuali")
                self.drop_trigger("Parametri puntuali")
                self.insert_table(
                    "parametri_puntuali", os.path.join(path_tabelle, "Parametri_Puntuali.txt"))
                if self.current_trig_sql is not None:
                    self.update_values_and_restore_trigger("Parametri puntuali")
                self.set_log_message.emit(
                    "'Parametri_Puntuali' table has been copied!\n")

                if os.path.exists(os.path.join(path_tabelle, "Curve.txt")):
                    z_list.append("Curve")
                    self.insert_table(
                        "curve", os.path.join(path_tabelle, "Curve.txt"))
                    self.set_log_message.emit(
                        "'Curve' table has been copied!\n")

        # end inserting indagini puntuali
        if self.killed:
            raise UserAbortedNotification('USER Killed')
        self.current_step = self.current_step + 1
        self.progress.emit(int(self.current_step * 100/total_steps))

        # step 4 (inserting indagini lineari and related data)
        ######################################################
        if self.check_sito_l is True and os.path.exists(os.path.join(path_tabelle, "Indagini_Lineari.txt")):
            z_list.append("Indagini_Lineari")
            self.drop_trigger("Indagini lineari")
            self.insert_table("indagini_lineari", os.path.join(
                path_tabelle, "Indagini_Lineari.txt"))
            if self.current_trig_sql is not None:
                self.update_values_and_restore_trigger("Indagini lineari")
            self.set_log_message.emit(
                "'Indagini_Lineari' table has been copied!\n")

            if os.path.exists(os.path.join(path_tabelle, "Parametri_Lineari.txt")):
                z_list.append("Parametri_Lineari")
                self.drop_trigger("Parametri lineari")
                self.insert_table(
                    "parametri_lineari", os.path.join(
                        path_tabelle, "Parametri_Lineari.txt"))
                if self.current_trig_sql is not None:
                    self.update_values_and_restore_trigger("Parametri lineari")
                self.set_log_message.emit(
                    "'Parametri_Lineari' table has been copied!\n")

        if self.check_sito_p is False:
            self.set_log_message.emit(
                "'Ind_pu' layer and/or 'Sito_Puntuale' table are not present! The correlated surveys and parameters tables will not be copied!\n\n")

        if self.check_sito_l is False:
            self.set_log_message.emit(
                "'Ind_ln' layer and/or 'Sito_Lineare' table are not present! The correlated surveys and parameters tables will not be copied!\n\n")

        if self.check_sito_p is True and self.check_sito_l is True:
            tab_mancanti = list(set(LISTA_TAB) - set(z_list))
            for t_lost in tab_mancanti:
                self.set_log_message.emit(
                    "'" + t_lost + "' table does not exist!\n")

        # end inserting indagini lineari
        if self.killed:
            raise UserAbortedNotification('USER Killed')

        self.current_step = self.current_step + 1
        self.progress.emit(int(self.current_step * 100/total_steps))

        # step 5 (miscellaneous files and cleanup)
        ###############################################
        self.set_message.emit('Adding miscellaneous files...')

        dizio_folder = {
            "Plot": ["OLD_Plot", os.path.join(self.proj_abs_path, "Allegati", "Plot"), os.path.join(self.in_dir, "Plot")],
            "Documenti": ["OLD_Documenti", os.path.join(self.proj_abs_path, "Allegati", "Documenti"), os.path.join(self.in_dir, "Indagini", "Documenti")],
            "Spettri": ["OLD_Spettri", os.path.join(self.proj_abs_path, "Allegati", "Spettri"), os.path.join(self.in_dir, "MS23", "Spettri")]
        }

        for chiave_fold, valore_fold in list(dizio_folder.items()):
            self.set_message.emit("Copying '" + chiave_fold + "' folder")
            QgsMessageLog.logMessage("Copying: %s - %s" %
                                     (chiave_fold, valore_fold))
            if os.path.exists(valore_fold[2]):
                _folder = os.path.join(
                    self.proj_abs_path, "Allegati", chiave_fold)
                QgsMessageLog.logMessage("_folder: %s" % _folder)
                if os.path.exists(_folder):
                    shutil.rmtree(_folder)
                    shutil.copytree(valore_fold[2], valore_fold[1])
                else:
                    QgsMessageLog.logMessage("ELSE _folder: %s -> %s" % (os.path.join(self.in_dir, chiave_fold),
                                                                         os.path.join(self.proj_abs_path,
                                                                                      "Allegati", chiave_fold)))
                    shutil.copytree(os.path.join(self.in_dir, chiave_fold),
                                    os.path.join(self.proj_abs_path,
                                                 "Allegati", chiave_fold))
                self.set_log_message.emit(
                    "Folder '" + chiave_fold + " has been copied!\n")
            else:
                self.set_log_message.emit(
                    "Folder '" + chiave_fold + "' does not exist!")

            if self.killed:
                break

        self.set_message.emit('Final cleanup...')
        shutil.rmtree(os.path.join(self.proj_abs_path, "Allegati", "Altro"))
        os.makedirs(os.path.join(self.proj_abs_path, "Allegati", "Altro"))

        # end miscellaneous files and cleanup
        if self.killed:
            raise UserAbortedNotification('USER Killed')

        self.current_step = self.current_step + 1
        self.progress.emit(int(self.current_step * 100 / total_steps))

        return 'Import completed!'

    def attribute_adaptor(self, targetLayer, sourceLayer):
        targetLayerFields = []
        sourceLayerFields = []
        primaryKeyList = []

        for index in targetLayer.dataProvider().pkAttributeIndexes():
            primaryKeyList.append(
                targetLayer.dataProvider().fields().at(index).name())

        for field in sourceLayer.dataProvider().fields().toList():
            sourceLayerFields.append(field.name())

        for field in targetLayer.dataProvider().fields().toList():
            targetLayerFields.append(field.name())

        commonFields = list(set(sourceLayerFields) & set(targetLayerFields))
        commonFields = list(set(commonFields)-set(primaryKeyList))

        return commonFields

    def attribute_fill(self, qgsFeature, targetLayer, commonFields):

        featureFields = {}

        for field in qgsFeature.fields().toList():
            if field.name() == "desc_modco":
                featureFields["desc_modcoord"] = qgsFeature[field.name()]
            elif field.name() == "mod_identc":
                featureFields["mod_identcoord"] = qgsFeature[field.name()]
            elif field.name() == "ub_prov":
                featureFields["ubicazione_prov"] = qgsFeature[field.name()]
            elif field.name() == "ub_com":
                featureFields["ubicazione_com"] = qgsFeature[field.name()]
            elif field.name() == "ID_SPU":
                featureFields["id_spu"] = qgsFeature[field.name()]
            elif field.name() == "ID_SLN":
                featureFields["id_sln"] = qgsFeature[field.name()]
            else:
                featureFields[field.name()] = qgsFeature[field.name()]

        qgsFeature.setFields(targetLayer.dataProvider().fields())
        if commonFields:
            for fieldName in commonFields:
                qgsFeature[fieldName] = featureFields[fieldName]

        return qgsFeature

    def calc_layer(self, sourceFeatures, destLYR, commonFields):

        featureList = []
        for feature in sourceFeatures:
            geom = feature.geometry()
            if geom:
                err = geom.validateGeometry()
                if not err:
                    modifiedFeature = self.attribute_fill(
                        feature, destLYR, commonFields)
                    featureList.append(modifiedFeature)
                else:
                    self.set_log_message.emit(
                        "  Geometry error (feature %d will not be copied)\n" % (feature.id()+1))

        # data_provider = destLYR.dataProvider()
        current_feature = 1

        # data_provider.addFeatures(featureList)
        destLYR.startEditing()
        for f in featureList:
            self.set_message.emit(destLYR.name(
            ) + ": inserting feature " + str(current_feature) + "/" + str(len(featureList)))
            # data_provider.addFeatures([f])
            
            destLYR.addFeatures([f])            

            current_feature = current_feature + 1

            if self.killed:
                destLYR.rollBack()
                break

        destLYR.commitChanges()

        if self.killed:
            raise UserAbortedNotification('USER Killed')

    def insert_siti(self, vector_layer, txt_table, sito_type):

        if sito_type == "puntuale":
            id_field_name = "ID_SPU"
            tab_name = "sito_puntuale"
        elif sito_type == "lineare":
            id_field_name = "ID_SLN"
            tab_name = "sito_lineare"

        path_db = os.path.join(self.proj_abs_path, "db", "indagini.sqlite")
        dict_sito = {}
        conn = sqlite3.connect(path_db)
        conn.text_factory = lambda x: str(x, 'utf-8', 'ignore')
        conn.enable_load_extension(True)

        try:
            conn.execute('SELECT load_extension("mod_spatialite")')
            cur = conn.cursor()

            cur.execute("begin")

            # drop insert trigger to speed up import process
            # TODO: causes QGIS crash
            # cur.execute("DROP TRIGGER ins_data_s_point" if tab_name == "sito_puntuale" else "DROP TRIGGER ins_data_s_line")

            with open(txt_table, 'r') as table:
                dr = csv.DictReader(table, delimiter=';', quotechar='"')
                current_feature = 1
                row_num = len(list(dr))
                # restart reading file after line count
                table.seek(0)
                next(dr)
                for i in dr:
                    self.set_message.emit(
                        "Sito %s: inserting feature %s/%s" % (sito_type, str(current_feature), str(row_num)))

                    # transform empty strings to None to circumvent db CHECKs
                    for k in i:
                        if i[k] == "":
                            i[k] = None

                    # populate dict_sito and get geom from vector layer
                    for key in list(i.keys()):
                        dict_sito[key] = i[key]
                        if key == id_field_name:
                            exp = '"{field_name}" = \'{field_value}\''.format(
                                field_name=id_field_name, field_value=dict_sito[id_field_name])
                            req = QgsFeatureRequest(QgsExpression(exp))
                            feature = next(vector_layer.getFeatures(req))
                            geometry = feature.geometry()

                            # Convert to single part
                            if geometry.isMultipart():
                                parts = geometry.asGeometryCollection()
                                geometry = parts[0]
                                if len(parts) > 1:
                                    self.set_log_message.emit(
                                        'Geometry from layer %s is multipart with more than one part: taking first part only - %s' % (vector_layer.name(), geom))

                            geom = geometry.asWkt()
                            if not geometry.isGeosValid():
                                self.set_log_message.emit(
                                    'Wrong geometry from layer %s, expression: %s: %s' % (vector_layer.name(), exp, geom))
                            if geometry.isNull():
                                self.set_log_message.emit(
                                    'Null geometry from layer %s, expression: %s: %s' % (vector_layer.name(), exp, geom))

                    if sito_type == "puntuale":
                        try:
                            cur.execute(
                                "INSERT INTO sito_puntuale (id_spu, geom) VALUES (?, GeomFromText(?, 32633))", (dict_sito["ID_SPU"], geom))
                            lastid = cur.lastrowid
                            cur.execute('''UPDATE sito_puntuale SET pkuid = ?, indirizzo = ?, mod_identcoord = ?,
                                desc_modcoord = ?, quota_slm = ?, modo_quota = ?, data_sito = ?, note_sito = ?
                                WHERE pkuid = ?;''',  (dict_sito["pkey_spu"], dict_sito["indirizzo"], dict_sito["mod_identcoord"],
                                                       dict_sito["desc_modcoord"], dict_sito["quota_slm"], dict_sito["modo_quota"],
                                                       dict_sito["data_sito"], dict_sito["note_sito"], lastid))
                        except Exception as ex:
                            self.set_log_message.emit(
                                "Error inserting geometry in sito_puntuale %s: %s - %s" % (dict_sito["ID_SPU"], geom, str(ex)))
                    elif sito_type == "lineare":
                        try:
                            cur.execute(
                                "INSERT INTO sito_lineare (id_sln, geom) VALUES (?, GeomFromText(?, 32633))", (dict_sito["ID_SLN"], geom))
                            lastid = cur.lastrowid
                            cur.execute('''UPDATE sito_lineare SET pkuid = ?, mod_identcoord = ?,
                                desc_modcoord = ?, aquota = ?, bquota = ?, data_sito = ?, note_sito = ?
                                WHERE pkuid = ?;''',  (dict_sito["pkey_sln"], dict_sito["mod_identcoord"],
                                                       dict_sito["desc_modcoord"], dict_sito["Aquota"], dict_sito["Bquota"],
                                                       dict_sito["data_sito"], dict_sito["note_sito"], lastid))
                        except Exception as ex:
                            self.set_log_message.emit(
                                "Error inserting geometry in sito_lineare %s: %s - %s" % (dict_sito["ID_SLN"], geom, str(ex)))

                    current_feature = current_feature + 1
                    if self.killed or (TESTING and current_feature > 10):
                        break

            # restore insert trigger
            # TODO: causes QGIS crash
            # cur.execute(self.ins_data_s_point if tab_name == "sito_puntuale" else self.ins_data_s_line)

            # conn.commit()
            cur.execute("commit")

            # check if spatial index needs rebuild
            cur.execute('SELECT RecoverSpatialIndex(?, ?)', (tab_name, 'geom'))

            cur.close()
        # except:
        #     cur.execute("rollback")
        finally:
            conn.close()

    def insert_table(self, db_table, txt_table):

        # indagini_puntuali
        insert_indpu = """
			INSERT INTO indagini_puntuali
				(pkuid, id_spu, classe_ind, tipo_ind, id_indpu,
				id_indpuex, arch_ex, note_ind, prof_top, prof_bot,
				spessore, quota_slm_top, quota_slm_bot, data_ind,
				doc_pag, doc_ind,pkey_spu)
			VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)"""
        select_id_spu = "SELECT pkuid, id_spu FROM sito_puntuale WHERE pkuid = ?"
        update_indpu_fkey = "UPDATE indagini_puntuali SET id_spu = ? WHERE pkuid = ?"

        # parametri_puntuali
        insert_parpu = """
			INSERT INTO parametri_puntuali
				(pkuid, id_indpu, tipo_parpu, id_parpu, prof_top, prof_bot,
				spessore, quota_slm_top, quota_slm_bot, valore, attend_mis,
				tab_curve, note_par, data_par,pkey_indpu)
			VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)"""
        select_id_indpu = "SELECT pkuid, id_indpu FROM indagini_puntuali WHERE pkuid = ?"
        update_parpu_fkey = "UPDATE parametri_puntuali SET id_indpu = ? WHERE pkuid = ?"

        # curve
        insert_curve = """
			INSERT INTO curve (pkuid, id_parpu, cond_curve, varx, vary,pkey_parpu)
				VALUES (?,?,?,?,?,?);"""
        select_id_parpu = "SELECT pkuid, id_parpu FROM parametri_puntuali WHERE pkuid = ?"
        update_curve_fkey = "UPDATE curve SET id_parpu = ? WHERE pkuid = ?"

        # indagini_lineari
        insert_indln = """
			INSERT INTO indagini_lineari
				(pkuid, id_sln, classe_ind, tipo_ind, id_indln, id_indlnex,
				arch_ex, note_indln, data_ind, doc_pag, doc_ind,pkey_sln)
			VALUES (?,?,?,?,?,?,?,?,?,?,?,?)"""
        select_id_sln = "SELECT pkuid, id_sln FROM sito_lineare WHERE pkuid = ?"
        update_indln_fkey = "UPDATE indagini_lineari SET id_sln = ? WHERE pkuid = ?"

        # parametri_lineari
        insert_parln = """
			INSERT INTO parametri_lineari
				(pkuid, id_indln, tipo_parln, id_parln, prof_top, prof_bot,
				spessore, quota_slm_top, quota_slm_bot, valore, attend_mis,
				note_par, data_par,pkey_indln)
			VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)"""
        select_id_indln = "SELECT pkuid, id_indln FROM indagini_lineari WHERE pkuid = ?"
        update_parln_fkey = "UPDATE parametri_lineari SET id_indln = ? WHERE pkuid = ?"

        path_db = os.path.join(self.proj_abs_path, "db", "indagini.sqlite")
        conn = sqlite3.connect(path_db)
        conn.text_factory = lambda x: str(x, 'utf-8', 'ignore')
        try:
            cur = conn.cursor()

            cur.execute("begin")

            with open(txt_table, 'r') as table:
                dr = csv.DictReader(table, delimiter=';', quotechar='"')
                current_record = 1
                row_num = len(list(dr))
                # restart reading file after line count
                table.seek(0)
                next(dr)
                for i in dr:

                    self.set_message.emit(
                        "Table %s: inserting record %s/%s" % (db_table, str(current_record), str(row_num)))

                    # transform empty strings to None to circumvent db CHECKs
                    for k in i:
                        if i[k] == "":
                            i[k] = None

                    if db_table == "indagini_puntuali":
                        to_db = (i['pkey_indpu'], i['pkey_spu'], i['classe_ind'], i['tipo_ind'], i['ID_INDPU'], i['id_indpuex'], i['arch_ex'], i['note_ind'],
                                 i['prof_top'], i['prof_bot'], i['spessore'], i['quota_slm_top'], i['quota_slm_bot'], i['data_ind'], i['doc_pag'], i['doc_ind'], i['pkey_spu'])
                        fkey = i['pkey_spu']
                        insert_sql = insert_indpu
                        select_parent_sql = select_id_spu
                        update_sql = update_indpu_fkey
                    elif db_table == "parametri_puntuali":
                        to_db = (i['pkey_parpu'], i['pkey_indpu'], i['tipo_parpu'], i['ID_PARPU'], i['prof_top'], i['prof_bot'], i['spessore'],
                                 i['quota_slm_top'], i['quota_slm_bot'], i['valore'], i['attend_mis'], i['tab_curve'], i['note_par'], i['data_par'], i['pkey_indpu'])
                        fkey = i['pkey_indpu']
                        insert_sql = insert_parpu
                        select_parent_sql = select_id_indpu
                        update_sql = update_parpu_fkey
                    elif db_table == "curve":
                        to_db = (i['pkey_curve'], i['pkey_parpu'],
                                 i['cond_curve'], i['varx'], i['vary'], i['pkey_parpu'])
                        fkey = i['pkey_parpu']
                        insert_sql = insert_curve
                        select_parent_sql = select_id_parpu
                        update_sql = update_curve_fkey
                    elif db_table == "indagini_lineari":
                        to_db = (i['pkey_indln'], i['pkey_sln'], i['classe_ind'], i['tipo_ind'], i['ID_INDLN'], i['id_indlnex'],
                                 i['arch_ex'], i['note_indln'], i['data_ind'], i['doc_pag'], i['doc_ind'], i['pkey_sln'])
                        fkey = i['pkey_sln']
                        insert_sql = insert_indln
                        select_parent_sql = select_id_sln
                        update_sql = update_indln_fkey
                    elif db_table == "parametri_lineari":
                        to_db = (i['pkey_parln'], i['pkey_indln'], i['tipo_parln'], i['ID_PARLN'], i['prof_top'], i['prof_bot'], i['spessore'],
                                 i['quota_slm_top'], i['quota_slm_bot'], i['valore'], i['attend_mis'], i['note_par'], i['data_par'], i['pkey_indln'])
                        fkey = i['pkey_indln']
                        insert_sql = insert_parln
                        select_parent_sql = select_id_indln
                        update_sql = update_parln_fkey

                    try:
                        cur.execute(insert_sql, to_db)
                        id_last_insert = cur.lastrowid
                        cur.execute(select_parent_sql, (fkey,))
                        id_parent = cur.fetchone()[1]
                        cur.execute(update_sql, (id_parent, id_last_insert))
                    except Exception as ex:
                        self.set_log_message.emit(
                            "Error inserting table %s SQL: %s" % (str(ex), insert_sql))

                    current_record = current_record + 1
                    if self.killed or (TESTING and current_record > 10):
                        break

            # conn.commit()
            cur.execute("commit")
            cur.close()
        # except:
        #     cur.execute("rollback")
        finally:
            conn.close()

    def calc_join(self, orig_tab, link_tab, temp_field, link_field, orig_field):

        path_db = os.path.join(self.proj_abs_path, "db", "indagini.sqlite")

        joinObject = QgsVectorJoinInfo()
        joinObject.joinLayerId = link_tab.id()
        joinObject.joinFieldName = 'pkuid'
        joinObject.targetFieldName = temp_field
        joinObject.memoryCache = True
        orig_tab.addJoin(joinObject)

        context = QgsExpressionContext()
        scope = QgsExpressionContextScope()
        context.appendScope(scope)

        expression = QgsExpression(link_field)
        expression.prepare(orig_tab.pendingFields())

        try:
            conn = sqlite3.connect(path_db)
            conn.text_factory = lambda x: str(x, 'utf-8', 'ignore')
            cur = conn.cursor()

            for feature in orig_tab.getFeatures():
                scope.setFeature(feature)
                value = expression.evaluate(context)
                if value is None:
                    pass
                else:
                    nome_tab = LAYER_DB_TAB[orig_tab.name()]
#					 cur.execute("UPDATE %s SET %s  = %s WHERE pkuid = %s;" % nome_tab, orig_field, value, str(feature['pkuid']))
                    cur.execute("UPDATE ? SET ?  = ? WHERE pkuid = ?",
                                (nome_tab, orig_field, value, str(feature['pkuid'])))

            conn.commit()
        except Exception as ex:
            # error will be forwarded upstream
            raise ex
        finally:
            conn.close()

        orig_tab.removeJoin(link_tab.id())

    def copy_files(self, src, dest):
        for file_name in os.listdir(src):
            full_file_name = os.path.join(src, file_name)
            if (os.path.isfile(full_file_name)):
                shutil.copy(full_file_name, dest)
