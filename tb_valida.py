# -*- coding: utf-8 -*-
#-------------------------------------------------------------------------------
# Name:		tb_valida.py
# Author:	  Tarquini E.
# Created:	 08-02-2018
#-------------------------------------------------------------------------------

from PyQt4 import QtGui, uic
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from qgis.utils import *
from qgis.core import *
from qgis.gui import *
import os, sys, webbrowser, processing, shutil, constants

FORM_CLASS, _ = uic.loadUiType(os.path.join(
	os.path.dirname(__file__), 'tb_valida.ui'))


class valida(QtGui.QDialog, FORM_CLASS):
	def __init__(self, parent=None):
		"""Constructor."""
		self.iface = iface
		super(valida, self).__init__(parent)
		self.setupUi(self)
		self.plugin_dir = os.path.dirname(__file__)

	def controllo(self):
		self.help_button.clicked.connect(lambda: webbrowser.open('https://www.youtube.com/watch?v=zv25F_apEMM&t=3s'))
		DIZIO_LYR = {"Siti puntuali":{u'pkuid':'integer', u'ubicazione_prov':'text', u'ubicazione_com':'text', u'id_spu':'text', u'indirizzo':'text', u'coord_x':'real', u'coord_y':'real', u'mod_identcoord':'text', u'desc_modcoord':'text', u'quota_slm':'real', u'modo_quota':'text', u'data_sito':'text', u'note_sito':'text'},
		"Siti lineari":{u'pkuid':'integer', u'ubicazione_prov':'text', u'ubicazione_com':'text', u'id_sln':'text', u'acoord_x':'real', u'acoord_y':'real', u'bcoord_x':'real', u'bcoord_y':'real', u'mod_identcoord':'text', u'desc_modcoord':'text', u'aquota':'real', u'bquota':'real', u'data_sito':'text', u'note_sito':'text'},
		"Elementi geologici e idrogeologici puntuali":{u'pkuid':'integer', u'Tipo_gi':'text', u'Valore':'real', u'Valore2':'real', u'ID_gi':'integer'}, "Elementi puntuali":{u'pkuid':'integer', u'Tipo_ep':'integer', u'ID_ep':'integer'}, "Elementi lineari":{u'pkuid':'integer', u'Tipo_el':'integer', u'ID_el':'integer'},
		"Forme":{u'pkuid':'integer', u'Tipo_f':'integer', u'ID_f':'integer'}, "Unita' geologico-tecniche":{u'pkuid':'integer', u'Tipo_gt':'text', u'Stato':'integer', u'Gen':'text', u'Tipo_geo':'text', u'ID_gt':'integer'},
		"Instabilita' di versante":{u'pkuid':'integer', u'Tipo_i':'integer', u'FRT':'real', u'FRR':'real', u'IL':'real', u'DISL':'real', u'FA':'real', u'FV':'real', u'Ft':'real', u'FH0105':'real', u'FH0510':'real', u'FH0515':'real', u'FPGA':'real', u'FA0105':'real', u'FA0408':'real', u'FA0711':'real', u'SPETTRI':'text', u'LIVELLO':'integer', u'CAT':'text', u'ID_i':'integer', u'AMB':'text'},
		"Isobate liv 1":{u'pkuid':'integer', u'Quota':'real', u'ID_isosub':'integer'}, "Zone stabili liv 1":{u'pkuid':'integer', u'Tipo_z':'integer', u'FA':'real', u'FV':'real', u'Ft':'real', u'FH0105':'real', u'FH0510':'real', u'FH0515':'real', u'FPGA':'real', u'FA0105':'real', u'FA0408':'real', u'FA0711':'real', u'SPETTRI':'text', u'LIVELLO':'integer', u'CAT':'text', u'ID_z':'integer'},
		"Zone instabili liv 1":{u'pkuid':'integer', u'Tipo_i':'integer', u'FRT':'real', u'FRR':'real', u'IL':'real', u'DISL':'real', u'FA':'real', u'FV':'real', u'Ft':'real', u'FH0105':'real', u'FH0510':'real', u'FH0515':'real', u'FPGA':'real', u'FA0105':'real', u'FA0408':'real', u'FA0711':'real', u'SPETTRI':'text', u'LIVELLO':'integer', u'CAT':'text', u'ID_i':'integer', u'AMB':'text'},
		"Isobate liv 2":{u'pkuid':'integer', u'Quota':'real', u'ID_isosub':'integer'}, "Zone stabili liv 2":{u'pkuid':'integer', u'Tipo_z':'integer', u'FA':'real', u'FV':'real', u'Ft':'real', u'FH0105':'real', u'FH0510':'real', u'FH0515':'real', u'FPGA':'real', u'FA0105':'real', u'FA0408':'real', u'FA0711':'real', u'SPETTRI':'text', u'LIVELLO':'integer', u'CAT':'text', u'ID_z':'integer'},
		"Zone instabili liv 2":{u'pkuid':'integer', u'Tipo_i':'integer', u'FRT':'real', u'FRR':'real', u'IL':'real', u'DISL':'real', u'FA':'real', u'FV':'real', u'Ft':'real', u'FH0105':'real', u'FH0510':'real', u'FH0515':'real', u'FPGA':'real', u'FA0105':'real', u'FA0408':'real', u'FA0711':'real', u'SPETTRI':'text', u'LIVELLO':'integer', u'CAT':'text', u'ID_i':'integer', u'AMB':'text'},
		"Isobate liv 3":{u'pkuid':'integer', u'Quota':'real', u'ID_isosub':'integer'}, "Zone stabili liv 3":{u'pkuid':'integer', u'Tipo_z':'integer', u'FA':'real', u'FV':'real', u'Ft':'real', u'FH0105':'real', u'FH0510':'real', u'FH0515':'real', u'FPGA':'real', u'FA0105':'real', u'FA0408':'real', u'FA0711':'real', u'SPETTRI':'text', u'LIVELLO':'integer', u'CAT':'text', u'ID_z':'integer'},
		"Zone instabili liv 3":{u'pkuid':'integer', u'Tipo_i':'integer', u'FRT':'real', u'FRR':'real', u'IL':'real', u'DISL':'real', u'FA':'real', u'FV':'real', u'Ft':'real', u'FH0105':'real', u'FH0510':'real', u'FH0515':'real', u'FPGA':'real', u'FA0105':'real', u'FA0408':'real', u'FA0711':'real', u'SPETTRI':'text', u'LIVELLO':'integer', u'CAT':'text', u'ID_i':'integer', u'AMB':'text'}}
		SHP_VALIDATORE = ["geotec_self_inters", "stab_1_self_inters", "instab_1_self_inters", "ms1_inters_stab_instab", "stab_2_self_inters", "instab_2_self_inters", "ms2_inters_stab_instab", "stab_3_self_inters", "instab_3_self_inters", "ms3_inters_stab_instab"]

		dir_progetto = QgsProject.instance().fileName()
		indagini_punti = True
		indagini_linee = True
		intersezioni_geotec = True
		intersezioni_ms1 = True
		intersezioni_ms2 = True
		intersezioni_ms3 = True
		self.disableButton()

		self.show()
		result = self.exec_()
		if result:

			try:
				dict_layer = {}
				pathname = QgsProject.instance().readPath("./") + os.sep + "allegati" + os.sep + "log"
				logfile_ita = pathname + os.sep + str(time.strftime("%Y-%m-%d_%H-%M-%S", time.gmtime())) + "_log_controllo.txt"
				logfile_eng = pathname + os.sep + str(time.strftime("%Y-%m-%d_%H-%M-%S", time.gmtime())) + "_validation_log.txt"
				f = open(logfile_ita,'a')
				e = open(logfile_eng,'a')
				f.write("REPORT DI CONTROLLO E VALIDAZIONE:" +"\n----------------------------------\n\n")
				e.write("VALIDATION SUMMARY REPORT:" +"\n------------------------------\n\n")

				if os.path.exists(pathname + os.sep + "analisi"):
					shutil.rmtree(pathname + os.sep + "analisi")
					os.makedirs(pathname + os.sep + "analisi")
				else:
					os.makedirs(pathname + os.sep + "analisi")

				f.write("1) Controllo dei layer di progetto:\n")
				e.write("1) Presence of project layers:\n")

				root = QgsProject.instance().layerTreeRoot()
				added = self.checkLayers(root, dict_layer, DIZIO_LYR)
				if len(added) == 0:
					f.write("   I layer fondamentali del progetto sono tutti presenti!")
					e.write("   The project layers are all present!")
				else:
					f.write("   Mancano i seguenti layer:\n")
					e.write("   The following layers are missing:\n")
					for x in added:
						f.write("	- " + x + "\n")
						e.write("	- " + x + "\n")

				if "Siti puntuali" in added or "Indagini puntuali" in added or "Parametri puntuali" in added or "Curve di riferimento" in added:
					indagini_punti = False
				if "Siti lineari" in added or "Indagini lineari" in added or "Parametri lineari" in added:
					indagini_linee = False
				if "Unita' geologico-tecniche" in added:
					intersezioni_geotec = False
				if "Zone stabili liv 1" in added or "Zone instabili liv 1" in added:
					intersezioni_ms1 = False
				if "Zone stabili liv 2" in added or "Zone instabili liv 2" in added:
					intersezioni_ms2 = False
				if "Zone stabili liv 3" in added or "Zone instabili liv 3" in added:
					intersezioni_ms3 = False

				f.write("\n\n2) Controllo geometrico:\n")
				e.write("\n\n2) Geometric control:\n")

				for nome in constants.LISTA_LAYER:
					if nome in ["Indagini puntuali", "Parametri puntuali", "Curve di riferimento", "Indagini lineari", "Parametri lineari"]:
						pass
					else:
						f.write("   Sto eseguendo il controllo geometrico del layer '" + nome + "'\n")
						e.write("   I am performing geometric validation of the '" + nome + "' layer\n")
						features = QgsMapLayerRegistry.instance().mapLayersByName(nome)[0]
						for feature in features.getFeatures():
							geom = feature.geometry()
							if geom:
								err = geom.validateGeometry()
								if err:
									f.write('	%d individuato errore geometrico (feature %d)\n' % (len(err), feature.id()))
									e.write('	%d identified geometric error (feature %d)\n' % (len(err), feature.id()))
						f.write("   Ho terminato l'analisi del layer '" + nome + "'\n\n")
						e.write("   I finished the analysis of the layer '" + nome + "'\n\n")

				f.write("3) Controllo topologico:\n")
				e.write("3) Topological control:\n")

				f.write("   Sto eseguendo il controllo topologico per il livello 'Carta Geotecnica'...\n")
				e.write("   I am performing topological validation of 'Carta Geotecnica' level...\n")
				if intersezioni_geotec is True:
					processing.runandload("saga:polygonselfintersection", "Unita' geologico-tecniche", "ID_gt", pathname + os.sep + "analisi" + os.sep + "geotec_self_inters.shp")
					self.elab_self_intersect("geotec_self_inters")
					self.remove_record("geotec_self_inters")
					f.write("	Fatto! Il file contenente le auto-intersezioni del layer 'Unita' geologico-tecniche' e' stato salvato nella directory '\\allegati\\log\\analisi\\geotec_self_inters.shp'\n\n")
					e.write("	Done! File containing auto-intersections of 'Unita' geologico-tecniche' layer has been saved in '\\allegati\\log\\analisi\\geotec_self_inters.shp'\n\n")
				else:
					f.write("	Non e' possibile eseguire il controllo topologico in quanto manca/mancano uno o piu' layer!\n\n")
					e.write("	Topological validation can not be performed because one or more layers is/are missing!\n\n")

				f.write("   Sto eseguendo il controllo topologico per il livello 'MS1'...\n")
				e.write("   I am performing topological validation of the 'MS1' level...\n")
				if intersezioni_ms1 is True:
					self.topology_check(pathname + os.sep + "analisi", "Zone stabili liv 1", "Zone instabili liv 1", "ID_z", "ID_i", "stab_1_self_inters", "instab_1_self_inters", "ms1_inters_stab_instab", f, e)
				else:
					f.write("	Non e' possibile eseguire il controllo topologico in quanto manca/mancano uno o piu' layer!\n\n")
					e.write("	Topological validation can not be performed because one or more layers is/are missing!\n\n")

				f.write("   Sto eseguendo il controllo topologico per il livello 'MS2'...\n")
				e.write("   I am performing topological validation of the 'MS2' level...\n")
				if intersezioni_ms2 is True:
					self.topology_check(pathname + os.sep + "analisi", "Zone stabili liv 2", "Zone instabili liv 2", "ID_z", "ID_i", "stab_2_self_inters", "instab_2_self_inters", "ms2_inters_stab_instab", f, e)
				else:
					f.write("	Non e' possibile eseguire il controllo topologico in quanto manca/mancano uno o piu' layer!\n\n")
					e.write("	Topological validation can not be performed because one or more layers is/are missing!\n\n")

				f.write("   Sto eseguendo il controllo topologico per il livello 'MS3'...\n")
				e.write("   I am performing topological validation of the 'MS3' level...\n")
				if intersezioni_ms3 is True:
					self.topology_check(pathname + os.sep + "analisi", "Zone stabili liv 3", "Zone instabili liv 3", "ID_z", "ID_i", "stab_3_self_inters", "instab_3_self_inters", "ms3_inters_stab_instab", f, e)
				else:
					f.write("	Non e' possibile eseguire il controllo topologico in quanto manca/mancano uno o piu' layer!\n\n")
					e.write("	Topological validation can not be performed because one or more layers is/are missing!\n\n")

				f.write("\nAnalisi terminata!")
				e.write("\nAnalysis completed!")
				QMessageBox.information(None, u'INFORMATION!', u"Validation summary report was saved in the project folder '...\\allegati\\log'")

				for layer in iface.mapCanvas().layers():
					if layer.name() in SHP_VALIDATORE:
						feats_count = layer.featureCount()
						if feats_count == 0:
							QgsMapLayerRegistry.instance().removeMapLayer(layer)

				root = QgsProject.instance().layerTreeRoot()
				root.addGroup("Validazione")
				toc = iface.legendInterface()
				groups = toc.groups()
				groupIndex = groups.index("Validazione")
				canvas = iface.mapCanvas()
				layers = canvas.layers()
				for i in layers:
				  if i.name() in SHP_VALIDATORE:
					alayer = i
					toc.moveLayer(i, groupIndex)
				canvas.refresh()

			except IOError:
				QMessageBox.warning(None, u'WARNING!', u"Open a Seismic Microzonation project before starting this tool!")
			except WindowsError:
				QMessageBox.warning(None, u'WARNING!', u"Before running this tool, delete shapefiles for topological validation from the project!")
			except Exception as z:
				QMessageBox.critical(None, u'ERROR!', u'Error:\n"' + str(z) + '"')

	def disableButton(self):

		conteggio = 0

		layers = self.iface.legendInterface().layers()
		for layer in layers:
			if layer.name() in constants.LISTA_LAYER:
				conteggio += 1

		if conteggio > 23:
			self.button_box.setEnabled(True)
			self.alert_text.hide()
		else:
			self.button_box.setEnabled(False)
			self.alert_text.show()

	def checkLayers(self, group, dict_layer, dizio_layer):
		for child in group.children():
			if isinstance(child, QgsLayerTreeLayer):
				if child.layer().name() in dizio_layer.keys():
					lyr = processing.getObject(child.layer().name())
					fields = lyr.pendingFields()
					field_val = {}
					for field in fields:
						field_val[field.name()] = field.typeName()
					dict_layer[child.layer().name()] = field_val
			else:
				self.checkLayers(child, dict_layer, dizio_layer)

		d1_keys = set(dizio_layer.keys())
		d2_keys = set(dict_layer.keys())
		added = d1_keys - d2_keys
		return added

	def topology_check(self, directory, lyr1, lyr2, campo1, campo2, nome1, nome2, nome3, f, e):
		processing.runandload("saga:polygonselfintersection", lyr1, campo1, directory + os.sep + nome1 + ".shp")
		self.elab_self_intersect(nome1)
		self.remove_record(nome1)
		f.write("	Fatto! Il file contenente le auto-intersezioni del layer '" + lyr1 + "' e' stato salvato nella directory '\\allegati\\log\\analisi\\" + nome1 + ".shp'\n")
		e.write("	Done! File containing auto-intersections of '" + lyr1 + "' layer has been saved in '\\allegati\\log\\analisi\\" + nome1 + ".shp'\n")
		processing.runandload("saga:polygonselfintersection", lyr2, campo2, directory + os.sep + nome2 + ".shp")
		self.elab_self_intersect(nome2)
		self.remove_record(nome2)
		f.write("	Fatto! Il file contenente le auto-intersezioni del layer '" + lyr2 + "' e' stato salvato nella directory '\\allegati\\log\\analisi\\" + nome2 + ".shp'\n")
		e.write("	Done! File containing auto-intersections of '" + lyr2 + "' layer has been saved in '\\allegati\\log\\analisi\\" + nome2 + ".shp'\n")
		processing.runandload("saga:intersect", lyr1, lyr2, True, directory + os.sep + nome3 + ".shp")
		self.elab_intersect(nome3)
		self.remove_record(nome3)
		f.write("	Fatto! Il file contenente le intersezioni tra i layer '" + lyr1 + "' e '" + lyr2 + "' e' stato salvato nella directory '\\allegati\\log\\analisi\\" + nome3 + ".shp'\n\n")
		e.write("	Done! File containing intersections between '" + lyr1 + "' and '" + lyr2 + "' layers was saved in '\\allegati\\log\\analisi\\" + nome3 + ".shp'\n\n")

	def elab_intersect(self, nome_file_inters):
		layer_name = QgsMapLayerRegistry.instance().mapLayersByName("Intersection")[0]
		layer_name.setLayerName(nome_file_inters)
		field_ids = []

		fieldnames = set(['ID_z', 'ID_i'])
		for field in layer_name.fields():
			if field.name() not in fieldnames:
				field_ids.append(layer_name.fieldNameIndex(field.name()))
		layer_name.dataProvider().deleteAttributes(field_ids)
		layer_name.updateFields()

	def elab_self_intersect(self, nome_file_inters):
		layer_name = QgsMapLayerRegistry.instance().mapLayersByName("Intersection")[0]
		layer_name.setLayerName(nome_file_inters)
		layer_name.startEditing()
		for fc in layer_name.getFeatures(QgsFeatureRequest().setFilterExpression('"pkuid" <> 0').setSubsetOfAttributes([]).setFlags(QgsFeatureRequest.NoGeometry)):
			layer_name.deleteFeature(fc.id())
		layer_name.commitChanges()

		field_ids = []
		fieldnames = set(['ID'])
		for field in layer_name.fields():
			if field.name() not in fieldnames:
				field_ids.append(layer_name.fieldNameIndex(field.name()))
		layer_name.dataProvider().deleteAttributes(field_ids)
		layer_name.updateFields()

	def remove_record(self, lyr_name):
		layer_name = QgsMapLayerRegistry.instance().mapLayersByName(lyr_name)[0]
		layer_name.startEditing()
		for elem in layer_name.getFeatures():
			if elem.geometry().area() < 1:
				layer_name.deleteFeature(elem.id())
		layer_name.commitChanges()