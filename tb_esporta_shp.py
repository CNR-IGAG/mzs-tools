# -*- coding: utf-8 -*-
#-------------------------------------------------------------------------------
# Name:		tb_esporta_shp.py
# Author:	  Tarquini E.
# Created:	 08-02-2018
#-------------------------------------------------------------------------------

from PyQt4 import QtGui, uic
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from qgis.utils import *
from qgis.core import *
from qgis.gui import *
import os, sys, webbrowser, shutil, zipfile, sqlite3, constants

FORM_CLASS, _ = uic.loadUiType(os.path.join(
	os.path.dirname(__file__), 'tb_esporta_shp.ui'))


class esporta_shp(QtGui.QDialog, FORM_CLASS):

	def __init__(self, parent=None):
		"""Constructor."""
		self.iface = iface
		super(esporta_shp, self).__init__(parent)
		self.setupUi(self)
		self.plugin_dir = os.path.dirname(__file__)

	def esporta_prog(self):
		self.help_button.clicked.connect(lambda: webbrowser.open('https://www.youtube.com/watch?v=dYcMZSpu6HA&t=2s'))
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
		attend_mis, note_par, data_par FROM A.parametri_lineari;"""]

		self.dir_output.clear()
		self.alert_text.hide()
		self.button_box.setEnabled(False)
		self.dir_output.textChanged.connect(self.disableButton)

		self.show()
		result = self.exec_()
		if result:

			try:
				in_dir = QgsProject.instance().readPath("./")
				out_dir = self.dir_output.text()
				if os.path.exists(out_dir):
					input_name = out_dir + os.sep + "progetto_shapefile"
					output_name = out_dir + os.sep + in_dir.split("/")[-1]
					zip_ref = zipfile.ZipFile(self.plugin_dir + os.sep + "data" + os.sep + "progetto_shapefile.zip", 'r')
					zip_ref.extractall(out_dir)
					zip_ref.close()
					os.rename(input_name, output_name)

					root = QgsProject.instance().layerTreeRoot()
					root.addGroup("Validazione")

					for chiave, valore in constants.POSIZIONE.iteritems():
						sourceLYR = QgsMapLayerRegistry.instance().mapLayersByName(chiave)[0]
						QgsVectorFileWriter.writeAsVectorFormat(sourceLYR ,output_name + os.sep + valore[0] + os.sep + valore[1],"utf-8",None,"ESRI Shapefile")
						selected_layer = QgsVectorLayer(output_name + os.sep + valore[0] + os.sep + valore[1] + ".shp", valore[1], 'ogr')
						if chiave == "Zone stabili liv 2" or chiave == "Zone instabili liv 2" or chiave == "Zone stabili liv 3" or chiave == "Zone instabili liv 3":
							pass
						if chiave == "Siti lineari" or chiave == "Siti puntuali":
							self.esporta([0, ['id_spu','id_sln']], selected_layer)
						else:
							self.esporta([1, ['pkuid']], selected_layer)

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

					if os.path.exists(in_dir + os.sep + "allegati" + os.sep + "Plot"):
						shutil.copytree(in_dir + os.sep + "allegati" + os.sep + "Plot", output_name + os.sep + "Plot")
					if os.path.exists(in_dir + os.sep + "allegati" + os.sep + "Documenti"):
						shutil.copytree(in_dir + os.sep + "allegati" + os.sep + "Documenti", output_name + os.sep + "Indagini" + os.sep + "Documenti")
					if os.path.exists(in_dir + os.sep + "allegati" + os.sep + "Spettri"):
						shutil.copytree(in_dir + os.sep + "allegati" + os.sep + "Spettri", output_name + os.sep + "MS23" + os.sep + "Spettri")
					if os.path.exists(in_dir + os.sep + "allegati" + os.sep + "altro"):
						shutil.copytree(in_dir + os.sep + "allegati" + os.sep + "altro", output_name + os.sep + "altro")

					for file_name in os.listdir(in_dir + os.sep + "allegati"):
						if file_name.endswith(".txt"):
							shutil.copyfile(in_dir + os.sep + "allegati" + os.sep + file_name, output_name + os.sep + file_name)

					dir_gdb = output_name + os.sep + "Indagini" + os.sep + "CdI_Tabelle.sqlite"
					orig_gdb =  in_dir + os.sep + "db" + os.sep + "indagini.sqlite"
					conn = sqlite3.connect(dir_gdb)
					sql = """ATTACH '""" + orig_gdb + """' AS A;"""
					conn.execute(sql)
					for query in LISTA_QUERY:
						conn.execute(query)
						conn.commit()
					conn.close()
					QMessageBox.information(None, u'INFORMATION!', u"The project has been exported!")

				else:
					QMessageBox.warning(None, u'WARNING!', u"The selected directory does not exist!")

			except Exception as z:
				QMessageBox.critical(None, u'ERROR!', u'Error:\n"' + str(z) + '"')

	def disableButton(self):
		conteggio = 0
		check_campi = [self.dir_output.text()]
		check_value = []

		layers = self.iface.legendInterface().layers()
		for layer in layers:
			if layer.name() in constants.LISTA_LAYER:
				conteggio += 1

		for x in check_campi:
			if len(x) > 0:
				value_campi = 1
				check_value.append(value_campi)
			else:
				value_campi = 0
				check_value.append(value_campi)
		campi = sum(check_value)

		if conteggio > 23 and campi > 0:
			self.button_box.setEnabled(True)
			self.alert_text.hide()
		elif conteggio > 23 and campi == 0:
			self.button_box.setEnabled(False)
			self.alert_text.hide()
		else:
			self.button_box.setEnabled(False)
			self.alert_text.show()

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
