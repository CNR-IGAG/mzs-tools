# -*- coding: utf-8 -*-
#-------------------------------------------------------------------------------
# Name:		export_workers.py
# Author:   Tarquini E.
# Created:	 18-03-2019
#-------------------------------------------------------------------------------

from PyQt4 import QtGui, uic
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from qgis.utils import *
from qgis.core import *
from qgis.gui import *
import os, sys, webbrowser, shutil, zipfile, sqlite3
from MzSTools.constants import *
from abstract_worker import AbstractWorker, UserAbortedNotification


class ExportWorker(AbstractWorker):
	'''Worker class handling data import from existing project'''

	def __init__(self, in_dir, out_dir, plugin_dir):
		AbstractWorker.__init__(self)
#		 self.steps = steps
		self.in_dir = in_dir
		self.out_dir = out_dir
		self.plugin_dir = plugin_dir

		self.current_step = 1

	def work(self):
		# calculate steps
		total_steps = len(POSIZIONE) + 5

		LISTA_LIV_2_3 = [["Zone stabili liv 3","Zone stabili liv 2","Stab.shp","Stab","ID_z"],
					["Zone instabili liv 3","Zone instabili liv 2","Instab.shp","Instab","ID_i"],
					["Isobate liv 3", "Isobate liv 2","Isosub.shp", "Isosub", "ID_isosub"]]
		LISTA_QUERY = ["""INSERT INTO 'sito_puntuale'(pkey_spu, ubicazione_prov, ubicazione_com, ID_SPU, indirizzo, coord_X, coord_Y,
					mod_identcoord, desc_modcoord, quota_slm, modo_quota, data_sito, note_sito) SELECT pkuid, ubicazione_prov, ubicazione_com,
					id_spu, indirizzo, coord_x, coord_y, mod_identcoord, desc_modcoord, quota_slm, modo_quota, data_sito, note_sito FROM A.sito_puntuale;""",
					"""INSERT INTO 'indagini_puntuali'(pkey_indpu, id_spu, classe_ind, tipo_ind, ID_INDPU, id_indpuex, arch_ex, note_ind, prof_top,
					prof_bot, spessore, quota_slm_top, quota_slm_bot, data_ind, doc_pag, doc_ind) SELECT pkuid, id_spu, classe_ind, tipo_ind, id_indpu,
					id_indpuex, arch_ex, note_ind, prof_top, prof_bot, spessore, quota_slm_top, quota_slm_bot, data_ind, doc_pag, doc_ind FROM A.indagini_puntuali;""",
					"""INSERT INTO 'parametri_puntuali'(pkey_parpu, id_indpu, tipo_parpu, ID_PARPU, prof_top, prof_bot, spessore, quota_slm_top, quota_slm_bot, valore,
					attend_mis, tab_curve, note_par, data_par) SELECT pkuid, id_indpu, tipo_parpu, id_parpu, prof_top, prof_bot, spessore, quota_slm_top, quota_slm_bot,
					valore, attend_mis, tab_curve, note_par, data_par FROM A.parametri_puntuali;""",
					"""INSERT INTO 'curve'(pkey_curve, id_parpu, cond_curve, varx, vary) SELECT pkuid, id_parpu, cond_curve, varx, vary FROM A.curve;""",
					"""INSERT INTO 'sito_lineare'(pkey_sln, ubicazione_prov, ubicazione_com, ID_SLN, Acoord_X, Acoord_Y, Bcoord_X, Bcoord_Y, mod_identcoord, desc_modcoord,
					Aquota, Bquota, data_sito, note_sito) SELECT pkuid, ubicazione_prov, ubicazione_com, id_sln, acoord_x, acoord_y, bcoord_x, bcoord_y, mod_identcoord,
					desc_modcoord, aquota, bquota, data_sito, note_sito FROM A.sito_lineare;""",
					"""INSERT INTO 'indagini_lineari'(pkey_indln, id_sln, classe_ind, tipo_ind, ID_INDLN, id_indlnex, arch_ex, note_indln, data_ind, doc_pag, doc_ind)
					SELECT pkuid, id_sln, classe_ind, tipo_ind, id_indln, id_indlnex, arch_ex, note_indln, data_ind, doc_pag, doc_ind FROM A.indagini_lineari;""",
					"""INSERT INTO 'parametri_lineari'(pkey_parln, id_indln, tipo_parln, ID_PARLN, prof_top, prof_bot, spessore, quota_slm_top, quota_slm_bot, valore,
					attend_mis, note_par, data_par) SELECT pkuid, id_indln, tipo_parln, id_parln, prof_top, prof_bot, spessore, quota_slm_top, quota_slm_bot, valore,
					attend_mis, note_par, data_par FROM A.parametri_lineari;""",
                    """INSERT INTO 'metadati'(id_metadato, liv_gerarchico, resp_metadato_nome, resp_metadato_email, resp_metadato_sito, data_metadato, srs_dati,
                    proprieta_dato_nome, proprieta_dato_email, proprieta_dato_sito, data_dato, ruolo, desc_dato, formato, tipo_dato, contatto_dato_nome, contatto_dato_email,
                    contatto_dato_sito, keywords, keywords_inspire, limitazione, vincoli_accesso, vincoli_fruibilita, vincoli_sicurezza, scala, categoria_iso, estensione_ovest,
                    estensione_est, estensione_sud, estensione_nord, formato_dati, distributore_dato_nome, distributore_dato_telefono, distributore_dato_email,
                    distributore_dato_sito, url_accesso_dato, funzione_accesso_dato, precisione, genealogia) SELECT id_metadato, liv_gerarchico, resp_metadato_nome,
                    resp_metadato_email, resp_metadato_sito, data_metadato, srs_dati, proprieta_dato_nome, proprieta_dato_email, proprieta_dato_sito, data_dato, ruolo, desc_dato,
                    formato, tipo_dato, contatto_dato_nome, contatto_dato_email, contatto_dato_sito, keywords, keywords_inspire, limitazione, vincoli_accesso, vincoli_fruibilita,
                    vincoli_sicurezza, scala, categoria_iso, estensione_ovest, estensione_est, estensione_sud, estensione_nord, formato_dati, distributore_dato_nome,
                    distributore_dato_telefono, distributore_dato_email, distributore_dato_sito, url_accesso_dato, funzione_accesso_dato, precisione, genealogia FROM A.metadati;"""]

		# step 1 (preparing data)
		###############################################
		self.set_message.emit('Creating project...')
		self.set_log_message.emit('Creating project...\n')
		input_name = self.out_dir + os.sep + "progetto_shapefile"
		output_name = self.out_dir + os.sep + self.in_dir.split("/")[-1]
		zip_ref = zipfile.ZipFile(self.plugin_dir + os.sep + "data" + os.sep + "progetto_shapefile.zip", 'r')
		zip_ref.extractall(self.out_dir)
		zip_ref.close()
		os.rename(input_name, output_name)
		self.set_log_message.emit('Done!\n')

		self.current_step = self.current_step + 1
		self.progress.emit(self.current_step * 100/total_steps)

		# step 2 (inserting features)
		###############################################
		self.set_message.emit('Creating shapefiles:')
		self.set_log_message.emit('\nCreating shapefiles:\n')

		for chiave, valore in POSIZIONE.iteritems():
			sourceLYR = QgsMapLayerRegistry.instance().mapLayersByName(chiave)[0]
			QgsVectorFileWriter.writeAsVectorFormat(sourceLYR ,output_name + os.sep + valore[0] + os.sep + valore[1],"utf-8",None,"ESRI Shapefile")
			selected_layer = QgsVectorLayer(output_name + os.sep + valore[0] + os.sep + valore[1] + ".shp", valore[1], 'ogr')
			if chiave == "Zone stabili liv 2" or chiave == "Zone instabili liv 2" or chiave == "Zone stabili liv 3" or chiave == "Zone instabili liv 3":
				pass
			if chiave == "Siti lineari" or chiave == "Siti puntuali":
				self.esporta([0, ['id_spu','id_sln']], selected_layer)
				self.set_message.emit("'" + chiave + "' shapefile has been created!")
				self.set_log_message.emit("  '" + chiave + "' shapefile has been created!\n")
			else:
				self.esporta([1, ['pkuid']], selected_layer)
				self.set_message.emit("'" + chiave + "' shapefile has been created!")
				self.set_log_message.emit("  '" + chiave + "' shapefile has been created!\n")

			if self.killed:
				break

			self.current_step = self.current_step + 1
			self.progress.emit(self.current_step * 100/total_steps)

		# end for
		if self.killed:
			raise UserAbortedNotification('USER Killed')

		for l23_value in LISTA_LIV_2_3:
			sourceLYR_1 = QgsMapLayerRegistry.instance().mapLayersByName(l23_value[0])[0]
			QgsVectorFileWriter.writeAsVectorFormat(sourceLYR_1 ,output_name + os.sep + "MS23" + os.sep + l23_value[2],"utf-8",None,"ESRI Shapefile")
			sourceLYR_2 = QgsMapLayerRegistry.instance().mapLayersByName(l23_value[1])[0]
			MS23_stab = QgsVectorLayer(output_name + os.sep + "MS23" + os.sep + l23_value[2], l23_value[3], 'ogr')
			features = []
			for feature in sourceLYR_2.getFeatures():
				features.append(feature)
			MS23_stab.startEditing()
			data_provider = MS23_stab.dataProvider()
			data_provider.addFeatures(features)
			MS23_stab.commitChanges()
			selected_layer_1 = QgsVectorLayer(output_name + os.sep + "MS23" + os.sep + l23_value[2], l23_value[3], 'ogr')
			self.esporta([1, ['pkuid']], selected_layer_1)
			self.set_message.emit("'" + chiave + "' shapefile has been created!")
			self.set_log_message.emit("  '" + chiave + "' shapefile has been created!\n")

		# end for
		if self.killed:
			raise UserAbortedNotification('USER Killed')

		self.current_step = self.current_step + 1
		self.progress.emit(self.current_step * 100/total_steps)

		# step 3 (miscellaneous files)
		#######################################################
		self.set_message.emit('Adding miscellaneous files...')
		self.set_log_message.emit('\nAdding miscellaneous files...\n')

		if os.path.exists(self.in_dir + os.sep + "allegati" + os.sep + "Plot"):
			self.set_message.emit("Copying 'Plot' folder")
			self.set_log_message.emit("  Copying 'Plot' folder\n")
			shutil.copytree(self.in_dir + os.sep + "allegati" + os.sep + "Plot", output_name + os.sep + "Plot")
		if os.path.exists(self.in_dir + os.sep + "allegati" + os.sep + "Documenti"):
			self.set_message.emit("Copying 'Documenti' folder")
			self.set_log_message.emit("  Copying 'Documenti' folder\n")
			shutil.copytree(self.in_dir + os.sep + "allegati" + os.sep + "Documenti", output_name + os.sep + "Indagini" + os.sep + "Documenti")
		if os.path.exists(self.in_dir + os.sep + "allegati" + os.sep + "Spettri"):
			self.set_message.emit("Copying 'Spettri' folder")
			self.set_log_message.emit("  Copying 'Spettri' folder\n")
			shutil.copytree(self.in_dir + os.sep + "allegati" + os.sep + "Spettri", output_name + os.sep + "MS23" + os.sep + "Spettri")
		if os.path.exists(self.in_dir + os.sep + "allegati" + os.sep + "altro"):
			self.set_message.emit("Copying 'altro' folder")
			self.set_log_message.emit("  Copying 'altro' folder\n")
			shutil.copytree(self.in_dir + os.sep + "allegati" + os.sep + "altro", output_name + os.sep + "altro")

		self.current_step = self.current_step + 1
		self.progress.emit(self.current_step * 100/total_steps)

		for file_name in os.listdir(self.in_dir + os.sep + "allegati"):
			if file_name.endswith(".txt"):
				shutil.copyfile(self.in_dir + os.sep + "allegati" + os.sep + file_name, output_name + os.sep + file_name)

		self.set_message.emit("Creating 'CdI_Tabelle.sqlite'")
		self.set_log_message.emit("\nCreating 'CdI_Tabelle.sqlite'\n")
		dir_gdb = output_name + os.sep + "Indagini" + os.sep + "CdI_Tabelle.sqlite"
		orig_gdb =  self.in_dir + os.sep + "db" + os.sep + "indagini.sqlite"
		conn = sqlite3.connect(dir_gdb)
		sql = """ATTACH '""" + orig_gdb + """' AS A;"""
		conn.execute(sql)
		for query in LISTA_QUERY:
			conn.execute(query)
			conn.commit()
		conn.close()
		self.set_log_message.emit("Done!")
		self.current_step = self.current_step + 1
		self.progress.emit(self.current_step * 100/total_steps)

		return 'Export completed!'

	def esporta(self, list_attr, selected_layer):

		field_ids = []
		fieldnames = set(list_attr[1])
		if list_attr[0] == 0:
			for field in selected_layer.fields():
				if field.name() not in fieldnames:
					field_ids.append(selected_layer.fieldNameIndex(field.name()))
			selected_layer.dataProvider().deleteAttributes(field_ids)
			selected_layer.updateFields()
		elif list_attr[0] == 1:
			for field in selected_layer.fields():
				if field.name() in fieldnames:
					field_ids.append(selected_layer.fieldNameIndex(field.name()))
			selected_layer.dataProvider().deleteAttributes(field_ids)
			selected_layer.updateFields()