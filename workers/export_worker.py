# -*- coding: utf-8 -*-
# -------------------------------------------------------------------------------
# Name:		export_workers.py
# Author:   Tarquini E.
# Created:	 18-03-2019
# -------------------------------------------------------------------------------

from __future__ import absolute_import
from qgis.PyQt import QtGui, uic
from qgis.PyQt.QtCore import *
from qgis.PyQt.QtGui import *
from qgis.PyQt.QtWidgets import QMessageBox
from qgis.utils import *
from qgis.core import *
from qgis.gui import *
import os
import sys
import webbrowser
import shutil
import zipfile
import sqlite3
from ..constants import *
from .abstract_worker import AbstractWorker, UserAbortedNotification


class ExportWorker(AbstractWorker):
    """Worker class handling data export to a standard SM study structure"""

    def __init__(self, in_dir, out_dir, plugin_dir):
        AbstractWorker.__init__(self)
        # 		 self.steps = steps
        self.in_dir = in_dir
        self.out_dir = out_dir
        self.plugin_dir = plugin_dir

        self.current_step = 1

    def work(self):
        # calculate steps
        total_steps = len(POSIZIONE) + 5

        LISTA_LIV_2_3 = [
            ["Zone stabili liv 3", "Zone stabili liv 2", "Stab.shp", "Stab", "ID_z"],
            [
                "Zone instabili liv 3",
                "Zone instabili liv 2",
                "Instab.shp",
                "Instab",
                "ID_i",
            ],
            ["Isobate liv 3", "Isobate liv 2", "Isosub.shp", "Isosub", "ID_isosub"],
        ]
        QUERY_DICT = {
            "sito_puntuale": """INSERT INTO 'sito_puntuale'(pkey_spu, ubicazione_prov, ubicazione_com, ID_SPU, indirizzo, coord_X, coord_Y,
                    mod_identcoord, desc_modcoord, quota_slm, modo_quota, data_sito, note_sito) SELECT pkuid, ubicazione_prov, ubicazione_com,
                    id_spu, indirizzo, coord_x, coord_y, mod_identcoord, desc_modcoord, quota_slm, modo_quota, data_sito, note_sito FROM A.sito_puntuale;""",
            "indagini_puntuali": """INSERT INTO 'indagini_puntuali'(pkey_indpu, id_spu, classe_ind, tipo_ind, ID_INDPU, id_indpuex, arch_ex, note_ind, prof_top,
                    prof_bot, spessore, quota_slm_top, quota_slm_bot, data_ind, doc_pag, doc_ind, pkey_spu) SELECT pkuid, id_spu, classe_ind, tipo_ind, id_indpu,
                    id_indpuex, arch_ex, note_ind, prof_top, prof_bot, spessore, quota_slm_top, quota_slm_bot, data_ind, doc_pag, doc_ind, pkey_spu FROM A.indagini_puntuali;""",
            "parametri_puntuali": """INSERT INTO 'parametri_puntuali'(pkey_parpu, id_indpu, tipo_parpu, ID_PARPU, prof_top, prof_bot, spessore, quota_slm_top, quota_slm_bot, valore,
                    attend_mis, tab_curve, note_par, data_par, pkey_indpu) SELECT pkuid, id_indpu, tipo_parpu, id_parpu, prof_top, prof_bot, spessore, quota_slm_top, quota_slm_bot,
                    valore, attend_mis, tab_curve, note_par, data_par, pkey_indpu FROM A.parametri_puntuali;""",
            "curve": """INSERT INTO 'curve'(pkey_curve, id_parpu, cond_curve, varx, vary, pkey_parpu) SELECT pkuid, id_parpu, cond_curve, varx, vary, pkey_parpu FROM A.curve;""",
            "sito_lineare": """INSERT INTO 'sito_lineare'(pkey_sln, ubicazione_prov, ubicazione_com, ID_SLN, Acoord_X, Acoord_Y, Bcoord_X, Bcoord_Y, mod_identcoord, desc_modcoord,
                    Aquota, Bquota, data_sito, note_sito) SELECT pkuid, ubicazione_prov, ubicazione_com, id_sln, acoord_x, acoord_y, bcoord_x, bcoord_y, mod_identcoord,
                    desc_modcoord, aquota, bquota, data_sito, note_sito FROM A.sito_lineare;""",
            "indagini_lineari": """INSERT INTO 'indagini_lineari'(pkey_indln, id_sln, classe_ind, tipo_ind, ID_INDLN, id_indlnex, arch_ex, note_indln, data_ind, doc_pag, doc_ind, pkey_sln)
                    SELECT pkuid, id_sln, classe_ind, tipo_ind, id_indln, id_indlnex, arch_ex, note_indln, data_ind, doc_pag, doc_ind, pkey_sln FROM A.indagini_lineari;""",
            "parametri_lineari": """INSERT INTO 'parametri_lineari'(pkey_parln, id_indln, tipo_parln, ID_PARLN, prof_top, prof_bot, spessore, quota_slm_top, quota_slm_bot, valore,
                    attend_mis, note_par, data_par, pkey_indln) SELECT pkuid, id_indln, tipo_parln, id_parln, prof_top, prof_bot, spessore, quota_slm_top, quota_slm_bot, valore,
                    attend_mis, note_par, data_par, pkey_indln FROM A.parametri_lineari;""",
            "metadati": """INSERT INTO 'metadati'(id_metadato, liv_gerarchico, resp_metadato_nome, resp_metadato_email, resp_metadato_sito, data_metadato, srs_dati,
                    proprieta_dato_nome, proprieta_dato_email, proprieta_dato_sito, data_dato, ruolo, desc_dato, formato, tipo_dato, contatto_dato_nome, contatto_dato_email,
                    contatto_dato_sito, keywords, keywords_inspire, limitazione, vincoli_accesso, vincoli_fruibilita, vincoli_sicurezza, scala, categoria_iso, estensione_ovest,
                    estensione_est, estensione_sud, estensione_nord, formato_dati, distributore_dato_nome, distributore_dato_telefono, distributore_dato_email,
                    distributore_dato_sito, url_accesso_dato, funzione_accesso_dato, precisione, genealogia) SELECT id_metadato, liv_gerarchico, resp_metadato_nome,
                    resp_metadato_email, resp_metadato_sito, data_metadato, srs_dati, proprieta_dato_nome, proprieta_dato_email, proprieta_dato_sito, data_dato, ruolo, desc_dato,
                    formato, tipo_dato, contatto_dato_nome, contatto_dato_email, contatto_dato_sito, keywords, keywords_inspire, limitazione, vincoli_accesso, vincoli_fruibilita,
                    vincoli_sicurezza, scala, categoria_iso, estensione_ovest, estensione_est, estensione_sud, estensione_nord, formato_dati, distributore_dato_nome,
                    distributore_dato_telefono, distributore_dato_email, distributore_dato_sito, url_accesso_dato, funzione_accesso_dato, precisione, genealogia FROM A.metadati;""",
        }

        # step 1 (preparing data)
        ###############################################
        self.set_message.emit("Creating project...")
        self.set_log_message.emit("Creating project...\n")
        input_name = os.path.join(self.out_dir, "progetto_shapefile")
        output_name = os.path.join(self.out_dir, self.in_dir.split("/")[-1])
        zip_ref = zipfile.ZipFile(
            os.path.join(self.plugin_dir, "data", "progetto_shapefile.zip"), "r"
        )
        zip_ref.extractall(self.out_dir)
        zip_ref.close()

        try:
            os.rename(input_name, output_name)
        except Exception as ex:
            QMessageBox.critical(
                iface.mainWindow(), "ERROR!", "Error creating zip file: %s" % ex
            )

        self.set_log_message.emit("Done!\n")

        self.current_step = self.current_step + 1
        self.progress.emit(int(self.current_step * 100 / total_steps))

        # step 2 (inserting features)
        ###############################################
        self.set_message.emit("Creating shapefiles:")
        self.set_log_message.emit("\nCreating shapefiles:\n")

        options = QgsVectorFileWriter.SaveVectorOptions()
        options.driverName = "ESRI Shapefile"
        options.fileEncoding = "utf-8"

        for chiave, valore in list(POSIZIONE.items()):
            sourceLYR = QgsProject.instance().mapLayersByName(chiave)[0]
            # QgsVectorFileWriter.writeAsVectorFormat(
            #    sourceLYR, os.path.join(output_name, valore[0], valore[1]), "utf-8", None, "ESRI Shapefile")

            err, msg = QgsVectorFileWriter.writeAsVectorFormatV2(
                sourceLYR,
                os.path.join(output_name, valore[0], valore[1]),
                QgsProject.instance().transformContext(),
                options,
            )

            if err != QgsVectorFileWriter.NoError:
                self.set_log_message.emit(
                    "Error creating shapefile %s: %s!\n" % (output_name, msg)
                )
                continue

            selected_layer = QgsVectorLayer(
                os.path.join(output_name, valore[0], valore[1] + ".shp"),
                valore[1],
                "ogr",
            )
            if (
                chiave == "Zone stabili liv 2"
                or chiave == "Zone instabili liv 2"
                or chiave == "Zone stabili liv 3"
                or chiave == "Zone instabili liv 3"
            ):
                pass
            if chiave == "Siti lineari" or chiave == "Siti puntuali":
                self.esporta([0, ["id_spu", "id_sln"]], selected_layer)
                self.set_message.emit("'" + chiave + "' shapefile has been created!")
                self.set_log_message.emit(
                    "  '" + chiave + "' shapefile has been created!\n"
                )
            else:
                self.esporta([1, ["pkuid"]], selected_layer)
                self.set_message.emit("'" + chiave + "' shapefile has been created!")
                self.set_log_message.emit(
                    "  '" + chiave + "' shapefile has been created!\n"
                )

            if self.killed:
                break

            self.current_step = self.current_step + 1
            self.progress.emit(int(self.current_step * 100 / total_steps))

        # end for
        if self.killed:
            raise UserAbortedNotification("USER Killed")

        for l23_value in LISTA_LIV_2_3:
            sourceLYR_1 = QgsProject.instance().mapLayersByName(l23_value[0])[0]
            # QgsVectorFileWriter.writeAsVectorFormat(
            #    sourceLYR_1, os.path.join(
            #        output_name, "MS23", l23_value[2]), "utf-8", None, "ESRI Shapefile")

            err, msg = QgsVectorFileWriter.writeAsVectorFormatV2(
                sourceLYR_1,
                os.path.join(output_name, "MS23", l23_value[2]),
                QgsProject.instance().transformContext(),
                options,
            )

            if err != QgsVectorFileWriter.NoError:
                self.set_log_message.emit(
                    "Error creating shapefile %s: %s!\n" % (output_name, msg)
                )
                continue

            sourceLYR_2 = QgsProject.instance().mapLayersByName(l23_value[1])[0]
            MS23_stab = QgsVectorLayer(
                os.path.join(output_name, "MS23", l23_value[2]), l23_value[3], "ogr"
            )
            features = []
            for feature in sourceLYR_2.getFeatures():
                features.append(feature)
            MS23_stab.startEditing()
            data_provider = MS23_stab.dataProvider()
            data_provider.addFeatures(features)
            MS23_stab.commitChanges()
            selected_layer_1 = QgsVectorLayer(
                os.path.join(output_name, "MS23", l23_value[2]), l23_value[3], "ogr"
            )
            self.esporta([1, ["pkuid"]], selected_layer_1)
            self.set_message.emit("'" + chiave + "' shapefile has been created!")
            self.set_log_message.emit(
                "  '" + chiave + "' shapefile has been created!\n"
            )

        # end for
        if self.killed:
            raise UserAbortedNotification("USER Killed")

        self.current_step = self.current_step + 1
        self.progress.emit(int(self.current_step * 100 / total_steps))

        # step 3 (miscellaneous files)
        #######################################################
        self.set_message.emit("Adding miscellaneous files...")
        self.set_log_message.emit("\nAdding miscellaneous files...\n")

        if os.path.exists(os.path.join(self.in_dir, "Allegati", "Plot")):
            self.set_message.emit("Copying 'Plot' folder")
            self.set_log_message.emit("  Copying 'Plot' folder\n")
            shutil.copytree(
                os.path.join(self.in_dir, "Allegati", "Plot"),
                os.path.join(output_name, "Plot"),
            )

        if os.path.exists(os.path.join(self.in_dir, "Allegati", "Documenti")):
            self.set_message.emit("Copying 'Documenti' folder")
            self.set_log_message.emit("  Copying 'Documenti' folder\n")
            shutil.copytree(
                os.path.join(self.in_dir, "Allegati", "Documenti"),
                os.path.join(output_name, "Indagini", "Documenti"),
            )

        if os.path.exists(os.path.join(self.in_dir, "Allegati", "Spettri")):
            self.set_message.emit("Copying 'Spettri' folder")
            self.set_log_message.emit("  Copying 'Spettri' folder\n")
            shutil.copytree(
                os.path.join(self.in_dir, "Allegati", "Spettri"),
                os.path.join(output_name, "MS23", "Spettri"),
            )

        if os.path.exists(os.path.join(self.in_dir, "Allegati", "Altro")):
            self.set_message.emit("Copying 'altro' folder")
            self.set_log_message.emit("  Copying 'altro' folder\n")
            shutil.copytree(
                os.path.join(self.in_dir, "Allegati", "Altro"),
                os.path.join(output_name, "Altro"),
            )

        self.current_step = self.current_step + 1
        self.progress.emit(int(self.current_step * 100 / total_steps))

        for file_name in os.listdir(os.path.join(self.in_dir, "Allegati")):
            if file_name.endswith(".txt"):
                shutil.copyfile(
                    os.path.join(self.in_dir, "Allegati", file_name),
                    os.path.join(output_name, file_name),
                )

        self.set_message.emit("Creating 'CdI_Tabelle.sqlite'")
        self.set_log_message.emit("\nCreating 'CdI_Tabelle.sqlite'\n")
        dir_gdb = os.path.join(output_name, "Indagini", "CdI_Tabelle.sqlite")
        orig_gdb = os.path.join(self.in_dir, "db", "indagini.sqlite")

        conn = sqlite3.connect(dir_gdb)
        sql = """ATTACH '""" + orig_gdb + """' AS A;"""

        try:
            conn.execute(sql)

            for tab_name, insert_query in QUERY_DICT.items():
                cur = conn.cursor()

                trigger_data = cur.execute(
                    f"SELECT name, sql FROM sqlite_master WHERE type = 'trigger' AND name like 'ins_data%' AND tbl_name = '{tab_name}'"
                ).fetchone()

                # drop insert trigger
                if trigger_data:
                    cur.execute(f"DROP TRIGGER {trigger_data[0]}")

                # execute insert query
                conn.execute(insert_query)

                # restore insert trigger
                if trigger_data:
                    cur.execute(trigger_data[1])

                conn.commit()
        finally:
            conn.close()

        self.set_log_message.emit("Done!")
        self.current_step = self.current_step + 1
        self.progress.emit(int(self.current_step * 100 / total_steps))

        return "Export completed!"

    def esporta(self, list_attr, selected_layer):
        field_ids = []
        fieldnames = set(list_attr[1])
        if list_attr[0] == 0:
            for field in selected_layer.fields():
                if field.name() not in fieldnames:
                    field_ids.append(selected_layer.fields().lookupField(field.name()))
            selected_layer.dataProvider().deleteAttributes(field_ids)
            selected_layer.updateFields()
            self.cambia_nome(list_attr, selected_layer)
        elif list_attr[0] == 1:
            for field in selected_layer.fields():
                if field.name() in fieldnames:
                    field_ids.append(selected_layer.fields().lookupField(field.name()))
            selected_layer.dataProvider().deleteAttributes(field_ids)
            selected_layer.updateFields()
            if selected_layer.name() == "Isosub":
                nome_attr = "Quota"
                tipo_attr = QVariant.Int
                self.cambia_tipo(selected_layer, nome_attr, tipo_attr)
            elif selected_layer.name() in ("Stab", "Instab"):
                nome_attr = "LIVELLO"
                tipo_attr = QVariant.Double
                self.cambia_tipo(selected_layer, nome_attr, tipo_attr)

    def cambia_nome(self, list_attr, selected_layer):
        selected_layer.startEditing()
        for field in selected_layer.fields():
            if field.name() in list_attr[1]:
                selected_layer.renameAttribute(
                    selected_layer.fields().lookupField(field.name()),
                    field.name().upper(),
                )
        selected_layer.commitChanges()

    def cambia_tipo(self, selected_layer, nome_attr, tipo_attr):
        selected_layer.startEditing()
        selected_layer.dataProvider().addAttributes([QgsField("new_col_na", tipo_attr)])
        selected_layer.commitChanges()

        selected_layer.startEditing()
        for feature in selected_layer.getFeatures():
            feature.setAttribute(
                feature.fields().lookupField("new_col_na"), feature[nome_attr]
            )
            selected_layer.updateFeature(feature)
        selected_layer.commitChanges()

        selected_layer.startEditing()
        selected_layer.dataProvider().deleteAttributes(
            [selected_layer.fields().lookupField(nome_attr)]
        )
        selected_layer.dataProvider().addAttributes([QgsField(nome_attr, tipo_attr)])
        selected_layer.commitChanges()

        selected_layer.startEditing()
        for feature in selected_layer.getFeatures():
            feature.setAttribute(
                feature.fields().lookupField(nome_attr), feature["new_col_na"]
            )
            selected_layer.updateFeature(feature)
        selected_layer.commitChanges()

        selected_layer.startEditing()
        selected_layer.dataProvider().deleteAttributes(
            [selected_layer.fields().lookupField("new_col_na")]
        )
        selected_layer.commitChanges()
