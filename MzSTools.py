# -*- coding: utf-8 -*-
#-------------------------------------------------------------------------------
# Name:		MzSTools.py
# Author:	  Tarquini E.
# Created:	 20-11-2017
#-------------------------------------------------------------------------------
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from qgis.utils import *
from qgis.core import *
from qgis.gui import *
import os, processing, sys, zipfile, shutil, sqlite3, webbrowser, csv, time, datetime
from tb_apri_progetto import apri_progetto
from tb_copia_ms import copia_ms
from tb_esporta_progetto import esporta_progetto
from tb_esporta_shp import esporta_shp
from tb_importa_progetto import importa_progetto
from tb_nuovo_progetto import nuovo_progetto
from tb_valida import valida
from tb_edit_win import edit_win
from tb_info import info
from tb_importa_shp import importa_shp


class MzSTools:

	def __init__(self, iface):

		self.iface = iface
		self.plugin_dir = os.path.dirname(__file__)
		locale = QSettings().value('locale/userLocale')[0:2]
		locale_path = os.path.join(
			self.plugin_dir,
			'i18n',
			'MzSTools_{}.qm'.format(locale))

		if os.path.exists(locale_path):
			self.translator = QTranslator()
			self.translator.load(locale_path)

			if qVersion() > '4.3.3':
				QCoreApplication.installTranslator(self.translator)

		self.dlg1 = nuovo_progetto()
		self.dlg2 = apri_progetto()
		self.dlg3 = importa_progetto()
		self.dlg4 = esporta_progetto()
		self.dlg5 = esporta_shp()
		self.dlg6 = copia_ms()
		self.dlg7 = valida()
		self.dlg10 = edit_win()
		self.dlg11 = info()
		self.dlg12 = importa_shp()

		self.posizione = {"Comune del progetto":["BasiDati","Comune","id_com"], "Elementi lineari":["GeoTec","Elineari","ID_el"], "Elementi puntuali":["GeoTec","Epuntuali","ID_ep"],
		"Forme":["GeoTec","Forme","ID_f"], "Elementi geologici e idrogeologici puntuali":["GeoTec","Geoidr","ID_gi"], "Unita' geologico-tecniche":["GeoTec","Geotec","ID_gt"],
		"Instabilita' di versante":["GeoTec","Instab_geotec","ID_i"], "Siti lineari":["Indagini","Ind_ln","ID_SLN"], "Siti puntuali":["Indagini","Ind_pu","ID_SPU"],
		"Zone instabili liv 1":["MS1","Instab","ID_i"], "Zone stabili liv 1":["MS1","Stab","ID_z"], "Isobate liv 1":["MS1","Isosub","ID_isosub"], "Zone instabili liv 2":["MS23","Instab","ID_i"],
		"Zone stabili liv 2":["MS23","Stab","ID_z"], "Isobate liv 2":["MS23","Isosub","ID_isosub"], "Zone instabili liv 3":["MS23","Instab","ID_i"], "Zone stabili liv 3":["MS23","Stab","ID_z"],
		"Isobate liv 3":["MS23","Isosub","ID_isosub"]}
		self.lista_layer = ["Siti puntuali", "Indagini puntuali", "Parametri puntuali", "Curve di riferimento", "Siti lineari", "Indagini lineari", "Parametri lineari",
		"Elementi geologici e idrogeologici puntuali", "Elementi puntuali", "Elementi lineari", "Forme", "Unita' geologico-tecniche", "Instabilita' di versante", "Isobate liv 1",
		"Zone stabili liv 1", "Zone instabili liv 1", "Isobate liv 2", "Zone stabili liv 2", "Zone instabili liv 2", "Isobate liv 3", "Zone stabili liv 3", "Zone instabili liv 3",
		"Comune del progetto", "Limiti comunali"]

		self.actions = []
		self.menu = self.tr(u'&MzS Tools')
		self.toolbar = self.iface.addToolBar(u'MzSTools')
		self.toolbar.setObjectName(u'MzSTools')

  		self.dlg1.dir_output.clear()
		self.dlg1.pushButton_out.clicked.connect(self.select_output_fld_1)

		self.dlg3.dir_input.clear()
		self.dlg3.pushButton_in.clicked.connect(self.select_input_fld_3)
  		self.dlg3.dir_output.clear()
		self.dlg3.pushButton_out.clicked.connect(self.select_output_fld_3)

		self.dlg4.dir_input.clear()
		self.dlg4.pushButton_in.clicked.connect(self.select_input_fld_4)
  		self.dlg4.dir_output.clear()
		self.dlg4.pushButton_out.clicked.connect(self.select_output_fld_4)

  		self.dlg5.dir_output.clear()
		self.dlg5.pushButton_out.clicked.connect(self.select_output_fld_5)

		self.dlg12.dir_input.clear()
		self.dlg12.pushButton_in.clicked.connect(self.select_input_fld_12)
  		self.dlg12.tab_input.clear()
		self.dlg12.pushButton_tab.clicked.connect(self.select_tab_fld_12)


	def tr(self, message):

		return QCoreApplication.translate('MzSTools', message)


	def add_action(
		self,
		icon_path,
		text,
		callback,
		enabled_flag=True,
		add_to_menu=True,
		add_to_toolbar=True,
		status_tip=None,
		whats_this=None,
		parent=None):

		icon = QIcon(icon_path)
		action = QAction(icon, text, parent)
		action.triggered.connect(callback)
		action.setEnabled(enabled_flag)

		if status_tip is not None:
			action.setStatusTip(status_tip)

		if whats_this is not None:
			action.setWhatsThis(whats_this)

		if add_to_toolbar:
			self.toolbar.addAction(action)

		if add_to_menu:
			self.iface.addPluginToDatabaseMenu(
				self.menu,
				action)

		self.actions.append(action)

		return action


	def initGui(self):

		icon_path1 = self.plugin_dir + os.sep + "img" + os.sep + 'ico_nuovo_progetto.png'
  		icon_path2 = self.plugin_dir + os.sep + "img" + os.sep + 'ico_apri.png'
		icon_path3 = self.plugin_dir + os.sep + "img" + os.sep + 'ico_importa.png'
		icon_path4 = self.plugin_dir + os.sep + "img" + os.sep + 'ico_esporta.png'
		icon_path5 = self.plugin_dir + os.sep + "img" + os.sep + 'ico_esporta_shp.png'
		icon_path6 = self.plugin_dir + os.sep + "img" + os.sep + 'ico_copia_ms.png'
		icon_path7 = self.plugin_dir + os.sep + "img" + os.sep + 'ico_valida.png'
		icon_path8 = self.plugin_dir + os.sep + "img" + os.sep + 'ico_edita.png'
		icon_path9 = self.plugin_dir + os.sep + "img" + os.sep + 'ico_salva_edita.png'
		icon_path10 = self.plugin_dir + os.sep + "img" + os.sep + 'ico_xypoint.png'
		icon_path11 = self.plugin_dir + os.sep + "img" + os.sep + 'ico_info.png'
		icon_path12 = self.plugin_dir + os.sep + "img" + os.sep + 'ico_importa_shp.png'

		self.add_action(
			icon_path1,
			text=self.tr(u'New project'),
			callback=self.run1,
			parent=self.iface.mainWindow())
		self.add_action(
			icon_path2,
			text=self.tr(u'Open project'),
			callback=self.run2,
			parent=self.iface.mainWindow())

		self.toolbar.addSeparator()

		self.add_action(
			icon_path3,
			text=self.tr(u'Import project'),
			callback=self.run3,
			parent=self.iface.mainWindow())
		self.add_action(
			icon_path12,
			text=self.tr(u'Import shapefile to geodatabase'),
			callback=self.run12,
			parent=self.iface.mainWindow())

		self.toolbar.addSeparator()

		self.add_action(
			icon_path8,
			text=self.tr(u'Add feature or record'),
			callback=self.run8,
			parent=self.iface.mainWindow())
		self.add_action(
			icon_path9,
			text=self.tr(u'Save'),
			callback=self.run9,
			parent=self.iface.mainWindow())
		self.add_action(
			icon_path10,
			text=self.tr(u'Add "Sito puntuale" using XY coordinates'),
			callback=self.run10,
			parent=self.iface.mainWindow())
		self.add_action(
			icon_path6,
			text=self.tr(u'Copy "Stab" or "Instab" layer'),
			callback=self.run6,
			parent=self.iface.mainWindow())
		self.add_action(
			icon_path7,
			text=self.tr(u'Validation'),
			callback=self.run7,
			parent=self.iface.mainWindow())

		self.toolbar.addSeparator()

		self.add_action(
			icon_path4,
			text=self.tr(u'Export project'),
			callback=self.run4,
			parent=self.iface.mainWindow())
		self.add_action(
			icon_path5,
			text=self.tr(u'Export as shapefile'),
			callback=self.run5,
			parent=self.iface.mainWindow())

  		self.toolbar.addSeparator()

		self.add_action(
			icon_path11,
			text=self.tr(u'Help'),
			callback=self.run11,
			parent=self.iface.mainWindow())


	def unload(self):

		for action in self.actions:
			self.iface.removePluginDatabaseMenu(
				self.tr(u'&MzS Tools'),
				action)
			self.iface.removeToolBarIcon(action)
		del self.toolbar


	def select_output_fld_1(self):

  		out_dir = QFileDialog.getExistingDirectory(self.dlg1, "","", QFileDialog.ShowDirsOnly)
		self.dlg1.dir_output.setText(out_dir)


	def select_input_fld_3(self):

		in_dir = QFileDialog.getOpenFileName(self.dlg3, "","", '*.zip')
		self.dlg3.dir_input.setText(in_dir)


	def select_output_fld_3(self):

		out_dir = QFileDialog.getExistingDirectory(self.dlg3, "","", QFileDialog.ShowDirsOnly)
		self.dlg3.dir_output.setText(out_dir)


	def select_input_fld_4(self):

		in_dir = QFileDialog.getExistingDirectory(self.dlg4, "","", QFileDialog.ShowDirsOnly)
		self.dlg4.dir_input.setText(in_dir)


	def select_output_fld_4(self):

		out_dir = QFileDialog.getExistingDirectory(self.dlg4, "","", QFileDialog.ShowDirsOnly)
		self.dlg4.dir_output.setText(out_dir)


	def select_input_fld_5(self):

		in_dir = QFileDialog.getExistingDirectory(self.dlg5, "","", QFileDialog.ShowDirsOnly)
		self.dlg5.dir_input.setText(in_dir)


	def select_output_fld_5(self):

		out_dir = QFileDialog.getExistingDirectory(self.dlg5, "","", QFileDialog.ShowDirsOnly)
		self.dlg5.dir_output.setText(out_dir)


	def select_input_fld_12(self):

		in_dir = QFileDialog.getExistingDirectory(self.dlg12, "","", QFileDialog.ShowDirsOnly)
		self.dlg12.dir_input.setText(in_dir)


	def select_tab_fld_12(self):

		tab_dir = QFileDialog.getExistingDirectory(self.dlg12, "","", QFileDialog.ShowDirsOnly)
		self.dlg12.tab_input.setText(tab_dir)


	def run1(self):

		self.dlg1.centroms.setPixmap(QPixmap(self.plugin_dir + os.sep + "img" + os.sep + 'logo-centroMS.jpg'))
		self.dlg1.igag.setPixmap(QPixmap(self.plugin_dir + os.sep + "img" + os.sep + 'logo-igag.png'))
		self.dlg1.cnr.setPixmap(QPixmap(self.plugin_dir + os.sep + "img" + os.sep + 'logo-cnr.png'))

		regione = {"01":"Piemonte","02":"Valle d'Aosta","03":"Lombardia","04":"Trentino Alto Adige","05":"Veneto",
		"06":"Friuli Venezia Giulia", "07":"Liguria","08":"Emilia Romagna","09":"Toscana","10":"Umbria","11":"Marche",
		"12":"Lazio","13":"Abruzzo","14":"Molise", "15":"Campania","16":"Puglia","17":"Basilicata","18":"Calabria",
		"19":"Sicilia","20":"Sardegna"}
		vers_data = self.plugin_dir + os.sep + "versione.txt"
		versione = open(vers_data,'r').read()
		dir_svg_input = self.plugin_dir + os.sep + "img" + os.sep + "svg"
		dir_svg_output = self.plugin_dir.split("python")[0] + "svg"
		lista_dir_com = self.plugin_dir + os.sep + "dir_comuni_ms.txt"
		tabella_controllo = self.plugin_dir + os.sep + "comuni.csv"
		pacchetto = self.plugin_dir + os.sep + "progetto_MS.zip"

		dizio_comuni = {}
		dict_comuni = {}
		with open(tabella_controllo, 'rb') as csvfile:
			csvreader = csv.reader(csvfile, delimiter=';')
			for row in csvreader:
				cod_istat = str(row[2])
				nome_com = row[3]
				cod_com = row[4]
				nome_comune = cod_istat + "_" + cod_com
				dict_comuni[cod_istat] = nome_comune
				dizio_comuni[nome_com] = cod_istat

		self.dlg1.dir_output.clear()
		self.dlg1.comune.clear()
		self.dlg1.cod_istat.clear()
		self.dlg1.professionista.clear()
		self.dlg1.tel_prof.clear()
		self.dlg1.email_prof.clear()
		self.dlg1.sito_prof.clear()
		self.dlg1.data_meta.clear()
		self.dlg1.propretario.clear()
		self.dlg1.tel_prop.clear()
		self.dlg1.email_prop.clear()
		self.dlg1.sito_prop.clear()
		self.dlg1.keyword.clear()
		self.dlg1.scala_nom.clear()
		self.dlg1.accuratezza.clear()
		self.dlg1.lineage.clear()
  		self.dlg1.button_box.setEnabled(False)
		self.dlg1.data_meta.setMinimumDate(QDate.currentDate())
		self.dlg1.comune.addItems(sorted(dizio_comuni.keys()))
		self.dlg1.comune.model().item(0).setEnabled(False)
		self.dlg1.comune.currentIndexChanged.connect(lambda: self.update_cod_istat(dizio_comuni, str(self.dlg1.comune.currentText()), self.dlg1.cod_istat))
		self.dlg1.scala_nom.textEdited.connect(lambda: self.update_num(self.dlg1.scala_nom,0,100000))
		self.dlg1.comune.currentIndexChanged.connect(self.disableButton_1)
		self.dlg1.professionista.textChanged.connect(self.disableButton_1)
		self.dlg1.propretario.textChanged.connect(self.disableButton_1)
		self.dlg1.scala_nom.textChanged.connect(self.disableButton_1)
		self.dlg1.email_prof.textChanged.connect(self.disableButton_1)
		self.dlg1.email_prop.textChanged.connect(self.disableButton_1)
		self.dlg1.dir_output.textChanged.connect(self.disableButton_1)

		self.dlg1.show()
		result = self.dlg1.exec_()
		if result:

			try:
				dir_out = self.dlg1.dir_output.text()
				comune = str(self.dlg1.comune.currentText())
				cod_istat = self.dlg1.cod_istat.text()
				professionista = self.dlg1.professionista.text()
				tel_prof = self.dlg1.tel_prof.text()
				email_prof = self.dlg1.email_prof.text()
				sito_prof = self.dlg1.sito_prof.text()
				data_meta = self.dlg1.data_meta.text()
				propretario = self.dlg1.propretario.text()
				tel_prop = self.dlg1.tel_prop.text()
				email_prop = self.dlg1.email_prop.text()
				sito_prop = self.dlg1.sito_prop.text()
				keyword = self.dlg1.keyword.text()
				scala_nom = self.dlg1.scala_nom.text()
				accuratezza = self.dlg1.accuratezza.text()
				lineage = self.dlg1.lineage.toPlainText()

				if not os.path.exists(dir_svg_output):
					shutil.copytree(dir_svg_input, dir_svg_output)
				else:
					src_files = os.listdir(dir_svg_input)
					for file_name in src_files:
						full_file_name = os.path.join(dir_svg_input, file_name)
						if os.path.isfile(full_file_name):
							shutil.copy(full_file_name, dir_svg_output)

				e = open(lista_dir_com,'a')
				zip_ref = zipfile.ZipFile(pacchetto, 'r')
				zip_ref.extractall(dir_out)
				zip_ref.close()
				for x, y in dict_comuni.iteritems():
					if x == cod_istat:
						comune_nome = (y[6:]).replace("_"," ")
						path_comune = dir_out + os.sep + y
						os.rename(dir_out + os.sep + "progetto_MS", path_comune)
						e.write("\n" + path_comune + os.sep + "progetto_MS.qgs")

				metadata = path_comune + os.sep + "allegati" + os.sep + comune_nome + " metadata.txt"
				f = open(metadata,'a')
				f.write("Municipality of "+ comune_nome +" Metadata:\n-------------------------------\n\n")
				f.write("Database version: " + versione + "\n")
				f.write("Expert: " + unicode(professionista).encode('utf-8') + "\n")
				f.write("Expert: " + unicode(tel_prof).encode('utf-8') + "\n")
				f.write("Expert email: " + unicode(email_prof).encode('utf-8') + "\n")
				f.write("Expert website: " + unicode(sito_prof).encode('utf-8') + "\n")
				f.write("Date: " + data_meta + "\n")
				f.write("Data owner: " + unicode(propretario).encode('utf-8') + "\n")
				f.write("Owner's phone: " + unicode(tel_prop).encode('utf-8') + "\n")
				f.write("Owner's email: " + unicode(email_prop).encode('utf-8') + "\n")
				f.write("Owner's website: " + unicode(sito_prop).encode('utf-8') + "\n")
				f.write("Keyword: " + unicode(keyword).encode('utf-8') + "\n")
				f.write("Map scale: 1:" + unicode(scala_nom).encode('utf-8') + "\n")
				f.write("Map accuracy: " + unicode(accuratezza).encode('utf-8') + "\n")
				f.write("Lineage: " + unicode(lineage).encode('utf-8') + "\n")

				project = QgsProject.instance()
				project.read(QFileInfo(path_comune + os.sep + "progetto_MS.qgs"))

				sourceLYR = QgsMapLayerRegistry.instance().mapLayersByName("Limiti comunali")[0]
				selection = sourceLYR.getFeatures(QgsFeatureRequest().setFilterExpression (u""""cod_istat" = '""" + cod_istat + """'"""))
				sourceLYR.setSelectedFeatures([k.id() for k in selection])

				destLYR = QgsMapLayerRegistry.instance().mapLayersByName("Comune del progetto")[0]
				selected_features = sourceLYR.selectedFeatures()
				features = []
				for i in selected_features:
					features.append(i)
				destLYR.startEditing()
				data_provider = destLYR.dataProvider()
				data_provider.addFeatures(features)
				destLYR.commitChanges()

				features = destLYR.getFeatures()
				for feat in features:
					attrs = feat.attributes()
					codice_regio = attrs[1]
					nome = attrs[4]

				layer_com = QgsMapLayerRegistry.instance().mapLayersByName("Limiti comunali")[0]
				layer_com.setSubsetString("cod_regio='" + codice_regio + "'")

				logo_regio_in = os.path.join(self.plugin_dir, "img" + os.sep + "logo_regio" + os.sep + codice_regio + ".png").replace('\\', '/')
				logo_regio_out = os.path.join(path_comune, "progetto" + os.sep + "loghi" + os.sep + "logo_regio.png").replace('\\', '/')
				shutil.copyfile(logo_regio_in, logo_regio_out)

				mainPath = (QgsProject.instance().fileName()).split("progetto")[0]
				self.mappa_insieme(mainPath, layer_com)

				canvas = iface.mapCanvas()
				extent = destLYR.extent()
				canvas.setExtent(extent)

				composers = iface.activeComposers()
				for composer_view in composers:
					composition = composer_view.composition()
					map_item = composition.getComposerItemById('mappa_0')
					map_item.setMapCanvas(canvas)
					map_item.zoomToExtent(canvas.extent())
					map_item_2 = composition.getComposerItemById('regio_title')
					map_item_2.setText("Regione " + regione[codice_regio])
					map_item_3 = composition.getComposerItemById('com_title')
					map_item_3.setText("Comune di " + nome)
					map_item_4 = composition.getComposerItemById('logo')
					map_item_4.refreshPicture()
					map_item_5 = composition.getComposerItemById('mappa_1')
					map_item_5.refreshPicture()

				project.write()

			except WindowsError:
				QMessageBox.warning(None, u'WARNING!', u"A folder with the project folder name already exists in the output directory!\nOr the save path is incorrect!")
				if os.path.exists(dir_out + os.sep + "progetto_MS"):
					shutil.rmtree(dir_out + os.sep + "progetto_MS")
			except:
				QMessageBox.critical(None, u'ERROR!', u"Generic error! Contact the plugin developers!")


	def run2(self):

		self.dlg2.centroms.setPixmap(QPixmap(self.plugin_dir + os.sep + "img" + os.sep + 'logo-centroMS.jpg'))
		self.dlg2.igag.setPixmap(QPixmap(self.plugin_dir + os.sep + "img" + os.sep + 'logo-igag.png'))
		self.dlg2.cnr.setPixmap(QPixmap(self.plugin_dir + os.sep + "img" + os.sep + 'logo-cnr.png'))

		lista_dir_com = self.plugin_dir + os.sep + "dir_comuni_ms.txt"
		lista_com = []
		duplicati = []
		g = open(lista_dir_com, 'r')
		h = (g.read()).split("\n")

		for i in h:
			if not os.path.exists(i.split("\\progetto_MS")[0]):
				pass
			else:
				duplicati.append(i)

		for j in duplicati:
			if j not in lista_com:
				lista_com.append(j)

		self.dlg2.listWidget.clear()
		self.dlg2.listWidget.addItems(lista_com)

		self.dlg2.show()
		result = self.dlg2.exec_()
		if result:
			try:
	 			lista = self.dlg2.listWidget.currentItem().text()
				project = QgsProject.instance()
				project.read(QFileInfo(lista))
			except AttributeError:
				QMessageBox.warning(None, u'WARNING!', u"You have not selected any projects!")
			except:
				QMessageBox.critical(None, u'ERROR!', u"Generic error! Contact the plugin developers!")


	def run3(self):

		self.dlg3.centroms.setPixmap(QPixmap(self.plugin_dir + os.sep + "img" + os.sep + 'logo-centroMS.jpg'))
		self.dlg3.igag.setPixmap(QPixmap(self.plugin_dir + os.sep + "img" + os.sep + 'logo-igag.png'))
		self.dlg3.cnr.setPixmap(QPixmap(self.plugin_dir + os.sep + "img" + os.sep + 'logo-cnr.png'))

		self.dlg3.dir_input.clear()
		self.dlg3.dir_output.clear()
		self.dlg3.button_box.setEnabled(False)
		self.dlg3.dir_input.textChanged.connect(self.disableButton_3)
		self.dlg3.dir_output.textChanged.connect(self.disableButton_3)

		self.dlg3.show()
		result = self.dlg3.exec_()
		if result:

			try:
	 			in_dir = self.dlg3.dir_input.text()
	 			out_dir = self.dlg3.dir_output.text()
				if os.path.exists(in_dir) and os.path.exists(out_dir):
					zip_ref = zipfile.ZipFile(in_dir, 'r')
					zip_ref.extractall(out_dir + os.sep + (in_dir.split("/")[-1]).split(".")[0])
					zip_ref.close()

					lista_dir_com = self.plugin_dir + os.sep + "dir_comuni_ms.txt"
					e = open(lista_dir_com,'a')
					e.write("\n" + out_dir + os.sep + (in_dir.split("/")[-1]).split(".")[0] + os.sep + "progetto_MS.qgs")

					project = QgsProject.instance()
					project.read(QFileInfo(out_dir + os.sep + (in_dir.split("/")[-1]).split(".")[0] + os.sep + "progetto_MS.qgs"))

					destLYR = QgsMapLayerRegistry.instance().mapLayersByName("Comune del progetto")[0]
					canvas = iface.mapCanvas()
					extent = destLYR.extent()
					canvas.setExtent(extent)

					features = destLYR.getFeatures()
					for feat in features:
						attrs = feat.attributes()
						codice_regio = attrs[1]

					layer_com = QgsMapLayerRegistry.instance().mapLayersByName("Limiti comunali")[0]
					layer_com.setSubsetString("cod_regio='" + codice_regio + "'")
					project.write()
					QMessageBox.information(None, u'INFORMATION!', u"The project has been imported!")
				else:
					QMessageBox.warning(None, u'WARNING!', u"The selected directory does not exist!")

			except IndexError:
				QMessageBox.warning(None, u'WARNING!', u"An incomplete project has been selected!\nOr it is not a Seismic Microzonation project!")
			except zipfile.BadZipfile:
				QMessageBox.critical(None, u'ERROR!', u"The compressed file is corrupt!\nThe project folder can not be extracted!")
			except:
				QMessageBox.critical(None, u'ERROR!', u"Generic error! Contact the plugin developers!")


	def run4(self):

		self.dlg4.centroms.setPixmap(QPixmap(self.plugin_dir + os.sep + "img" + os.sep + 'logo-centroMS.jpg'))
		self.dlg4.igag.setPixmap(QPixmap(self.plugin_dir + os.sep + "img" + os.sep + 'logo-igag.png'))
		self.dlg4.cnr.setPixmap(QPixmap(self.plugin_dir + os.sep + "img" + os.sep + 'logo-cnr.png'))

		self.dlg4.dir_input.clear()
		self.dlg4.dir_output.clear()
		self.dlg4.button_box.setEnabled(False)
		self.dlg4.dir_input.textChanged.connect(self.disableButton_4)
		self.dlg4.dir_output.textChanged.connect(self.disableButton_4)

		self.dlg4.show()
		result = self.dlg4.exec_()
		if result:

			try:
	 			in_dir = self.dlg4.dir_input.text()
	 			out_dir = self.dlg4.dir_output.text() + os.sep + self.dlg4.dir_input.text().split("\\")[-1]
				if os.path.exists(in_dir) and os.path.exists(self.dlg4.dir_output.text()):
					if os.path.exists(in_dir + os.sep + "progetto_MS.qgs"):
						shutil.make_archive(out_dir, 'zip', in_dir)
						QMessageBox.information(None, u'INFORMATION!', u"The project has been exported!")
					else:
						QMessageBox.warning(None, u'WARNING!', u"An incomplete project has been selected!\nOr it is not a Seismic Microzonation project!")
				else:
					QMessageBox.warning(None, u'WARNING!', u"The selected directory does not exist!")
			except zipfile.LargeZipFile:
				QMessageBox.critical(None, u'ERROR!', u"The project folder is too big!\nReduce the size of the project folder to 2 GB!")
			except IndexError:
				QMessageBox.critical(None, u'ERROR!', u"Generic error! Contact the plugin developers!")

	def run5(self):

		lista_liv_2_3 = [["Zone stabili liv 3","Zone stabili liv 2","Stab.shp","Stab","ID_z"],
		["Zone instabili liv 3","Zone instabili liv 2","Instab.shp","Instab","ID_i"],
		["Isobate liv 3", "Isobate liv 2","Isosub.shp", "Isosub", "ID_isosub"]]
		lista_query = ["""INSERT INTO 'sito_puntuale'(pkey_spu, ubicazione_prov, ubicazione_com, ID_SPU, indirizzo, coord_X, coord_Y,
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

		self.dlg5.centroms.setPixmap(QPixmap(self.plugin_dir + os.sep + "img" + os.sep + 'logo-centroMS.jpg'))
		self.dlg5.igag.setPixmap(QPixmap(self.plugin_dir + os.sep + "img" + os.sep + 'logo-igag.png'))
		self.dlg5.cnr.setPixmap(QPixmap(self.plugin_dir + os.sep + "img" + os.sep + 'logo-cnr.png'))

		self.dlg5.dir_output.clear()
		self.dlg5.alert_text.hide()
		self.dlg5.button_box.setEnabled(False)
		self.dlg5.dir_output.textChanged.connect(self.disableButton_5)

		self.dlg5.show()
		result = self.dlg5.exec_()
		if result:

			try:
				in_dir = QgsProject.instance().readPath("./")
				out_dir = self.dlg5.dir_output.text()
				if os.path.exists(out_dir):
					input_name = out_dir + os.sep + "progetto_shapefile"
					output_name = out_dir + os.sep + in_dir.split("/")[-1]
					zip_ref = zipfile.ZipFile(self.plugin_dir + os.sep + "progetto_shapefile.zip", 'r')
					zip_ref.extractall(out_dir)
					zip_ref.close()
					os.rename(input_name, output_name)

					for chiave, valore in self.posizione.iteritems():
						sourceLYR = QgsMapLayerRegistry.instance().mapLayersByName(chiave)[0]
						QgsVectorFileWriter.writeAsVectorFormat(sourceLYR ,output_name + os.sep + valore[0] + os.sep + valore[1],"utf-8",None,"ESRI Shapefile")
						selected_layer = QgsVectorLayer(output_name + os.sep + valore[0] + os.sep + valore[1] + ".shp", valore[1], 'ogr')
						if chiave == "Zone stabili liv 2" or chiave == "Zone instabili liv 2" or chiave == "Zone stabili liv 3" or chiave == "Zone instabili liv 3":
							pass
						if chiave == "Siti lineari" or chiave == "Siti puntuali":
							self.esporta([0, ['id_spu','id_sln']], selected_layer)
						else:
							self.esporta([1, ['pkuid']], selected_layer)

					for l23_value in lista_liv_2_3:
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
					for query in lista_query:
						conn.execute(query)
						conn.commit()
					conn.close()
					QMessageBox.information(None, u'INFORMATION!', u"The project has been exported!")

				else:
					QMessageBox.warning(None, u'WARNING!', u"The selected directory does not exist!")

			except WindowsError:
				QMessageBox.warning(None, u'WARNING!', u"A folder with the project folder name already exists in the output directory!")
			except Exception as e:
				QMessageBox.critical(None, u'ERROR!', u"Generic error! Contact the plugin developers!")


	def run6(self):

		self.dlg6.centroms.setPixmap(QPixmap(self.plugin_dir + os.sep + "img" + os.sep + 'logo-centroMS.jpg'))
		self.dlg6.igag.setPixmap(QPixmap(self.plugin_dir + os.sep + "img" + os.sep + 'logo-igag.png'))
		self.dlg6.cnr.setPixmap(QPixmap(self.plugin_dir + os.sep + "img" + os.sep + 'logo-cnr.png'))

		self.group = QButtonGroup()
		self.group.addButton(self.dlg6.radio_stab)
		self.group.addButton(self.dlg6.radio_instab)
		self.group.setExclusive(False)
		self.dlg6.radio_stab.setChecked(False)
		self.dlg6.radio_instab.setChecked(False)
		self.group.setExclusive(True)
		self.dlg6.input_ms.clear()
		self.dlg6.output_ms.clear()
		self.dlg6.button_box.setEnabled(False)
		self.dlg6.radio_stab.toggled.connect(self.radio_stab_clicked)
		self.dlg6.radio_instab.toggled.connect(self.radio_instab_clicked)

		self.dlg6.show()
		result = self.dlg6.exec_()
		if result:

			sourceLYR = QgsMapLayerRegistry.instance().mapLayersByName(str(self.dlg6.input_ms.currentText()))[0]
			destLYR = QgsMapLayerRegistry.instance().mapLayersByName(str(self.dlg6.output_ms.currentText()))[0]
			features = []
			for feature in sourceLYR.getFeatures(QgsFeatureRequest().setFlags(QgsFeatureRequest.NoFlags).setSubsetOfAttributes(['tipo_z','tipo_i'], sourceLYR.fields() )):
				features.append(feature)
			destLYR.startEditing()
			data_provider = destLYR.dataProvider()
			data_provider.addFeatures(features)
			destLYR.commitChanges()


	def run7(self):

		self.dlg7.centroms.setPixmap(QPixmap(self.plugin_dir + os.sep + "img" + os.sep + 'logo-centroMS.jpg'))
		self.dlg7.igag.setPixmap(QPixmap(self.plugin_dir + os.sep + "img" + os.sep + 'logo-igag.png'))
		self.dlg7.cnr.setPixmap(QPixmap(self.plugin_dir + os.sep + "img" + os.sep + 'logo-cnr.png'))

		dizio_lyr = {"Siti puntuali":{u'pkuid':'integer', u'ubicazione_prov':'text', u'ubicazione_com':'text', u'id_spu':'text', u'indirizzo':'text', u'coord_x':'real', u'coord_y':'real', u'mod_identcoord':'text', u'desc_modcoord':'text', u'quota_slm':'real', u'modo_quota':'text', u'data_sito':'text', u'note_sito':'text'},
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
		dir_progetto = QgsProject.instance().fileName()
		indagini_punti = True
		indagini_linee = True
		intersezioni_geotec = True
		intersezioni_ms1 = True
		intersezioni_ms2 = True
		intersezioni_ms3 = True

  		self.dlg7.show()
		result = self.dlg7.exec_()
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
				added = self.checkLayers(root, dict_layer, dizio_lyr)
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

				f.write("\n\n2) Sincronizzazione Siti-Indagini-Parametri:\n")
				e.write("\n\n2) Synchronization of Sites-Surveys-Parameters tables:\n")

				f.write("   Sto aggiornando i record delle tabelle dei Siti-Indagini-Parametri puntuali...\n")
				e.write("   I am updating the records of Punctual Sites-Surveys-Parameters tables ...\n")
				if indagini_punti is True:
					self.sincro_indagini("Siti puntuali", 'id_spu', "Indagini puntuali")
					self.sincro_indagini("Indagini puntuali", 'id_indpu', "Parametri puntuali")
					self.sincro_indagini("Parametri puntuali", 'id_parpu', "Curve di riferimento")
					f.write("	Fatto!\n\n")
					e.write("	Done!\n\n")
				else:
					f.write("	Non e' possibile aggiornare le tabelle in quanto manca/mancano uno o piu' layer!\n\n")
					e.write("	I can not update tables because one or more layers is/are missing!\n\n")

				f.write("   Sto aggiornando i record delle tabelle dei Siti-Indagini-Parametri lineari...\n")
				e.write("   I am updating the records of Linear Sites-Surveys-Parameters tables ...\n")
				if indagini_linee is True:
					self.sincro_indagini("Siti lineari", 'id_sln', "Indagini lineari")
					self.sincro_indagini("Indagini lineari", 'id_indln', "Parametri lineari")
					f.write("	Fatto!\n\n")
					e.write("	Done!\n\n")
				else:
					f.write("	Non e' possibile aggiornare le tabelle in quanto manca/mancano uno o piu' layer!\n\n")
					e.write("	I can not update tables because one or more layers is/are missing!\n\n")

				f.write("3) Controllo geometrico:\n")
				e.write("3) Geometric control:\n")

				for nome in self.lista_layer:
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

				f.write("4) Controllo topologico:\n")
				e.write("4) Topological control:\n")

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

			except IOError:
				QMessageBox.warning(None, u'WARNING!', u"Open a Seismic Microzonation project before starting this tool!")
			except WindowsError:
				QMessageBox.warning(None, u'WARNING!', u"Before running this tool, delete shapefiles for topological validation from the project!")
			except:
				QMessageBox.critical(None, u'ERROR!', u"Generic error! Contact the plugin developers!")


	def run8(self):

		proj = QgsProject.instance()
		proj.writeEntry('Digitizing', 'SnappingMode', 'all_layers')
		proj.writeEntry('Digitizing','DefaultSnapTolerance', 20.0)
		layers = iface.legendInterface().layers()
		dizio_layer = {"Zone stabili liv 1":"Zone instabili liv 1", "Zone instabili liv 1":"Zone stabili liv 1", "Zone stabili liv 2":"Zone instabili liv 2", "Zone instabili liv 2":"Zone stabili liv 2",
		"Zone stabili liv 3":"Zone instabili liv 3", "Zone instabili liv 3":"Zone stabili liv 3"}
		poli_lyr = ["Unita' geologico-tecniche", "Instabilita' di versante", "Zone stabili liv 1", "Zone instabili liv 1", "Zone stabili liv 2", "Zone instabili liv 2",
		"Zone stabili liv 3", "Zone instabili liv 3"]

		for fc in layers:
			if fc.name() in poli_lyr:
				proj.setSnapSettingsForLayer(fc.id(), True, 0, 0, 20, False)

		layer = iface.activeLayer()
		if layer <> None:
			for chiave, valore in dizio_layer.iteritems():
				if layer.name() == chiave:
					OtherLayer = QgsMapLayerRegistry.instance().mapLayersByName(valore)[0]
					proj.setSnapSettingsForLayer(layer.id(), True, 0, 0, 20, True)
					proj.setSnapSettingsForLayer(OtherLayer.id(), True, 0, 0, 20, True)
				elif layer.name() == "Unita' geologico-tecniche":
					proj.setSnapSettingsForLayer(layer.id(), True, 0, 0, 20, True)
				elif layer.name() == "Instabilita' di versante":
					proj.setSnapSettingsForLayer(layer.id(), True, 0, 0, 20, True)

			layer.startEditing()
			iface.actionAddFeature().trigger()


	def run9(self):

		proj = QgsProject.instance()
		proj.writeEntry('Digitizing', 'SnappingMode', 'all_layers')
		proj.writeEntry('Digitizing','DefaultSnapTolerance', 20.0)
		poligon_lyr = ["Unita' geologico-tecniche", "Instabilita' di versante", "Zone stabili liv 1", "Zone instabili liv 1", "Zone stabili liv 2", "Zone instabili liv 2",
		"Zone stabili liv 3", "Zone instabili liv 3"]

		layers = iface.legendInterface().layers()
		for fc in layers:
			if fc.name() in poligon_lyr:
				proj.setSnapSettingsForLayer(fc.id(), True, 0, 0, 20, False)

		layer = iface.activeLayer()
		if layer <> None:
			layer.commitChanges()


	def run10(self):

		self.dlg10.centroms.setPixmap(QPixmap(self.plugin_dir + os.sep + "img" + os.sep + 'logo-centroMS.jpg'))
		self.dlg10.igag.setPixmap(QPixmap(self.plugin_dir + os.sep + "img" + os.sep + 'logo-igag.png'))
		self.dlg10.cnr.setPixmap(QPixmap(self.plugin_dir + os.sep + "img" + os.sep + 'logo-cnr.png'))

  		codici_mod_identcoord = []
		lista_mod_identcoord = []
		codici_modo_quota = []
		lista_modo_quota = []
		self.dlg10.coord_x.clear()
		self.dlg10.coord_y.clear()
		self.dlg10.indirizzo.clear()
		self.dlg10.mod_identcoord.clear()
		self.dlg10.desc_modcoord.clear()
		self.dlg10.quota_slm.clear()
	   	self.dlg10.modo_quota.clear()
		self.dlg10.data_sito.clear()
		self.dlg10.note_sito.clear()
		today = QDate.currentDate()
		self.dlg10.data_sito.setDate(today)
  		self.dlg10.alert_text.hide()
		self.dlg10.button_box.setEnabled(False)
		self.dlg10.coord_x.textEdited.connect(lambda: self.update_num(self.dlg10.coord_x,-170000,801000))
		self.dlg10.coord_y.textEdited.connect(lambda: self.update_num(self.dlg10.coord_y,0,5220000))
		self.dlg10.quota_slm.textEdited.connect(lambda: self.update_num(self.dlg10.quota_slm,0,4900))
		self.dlg10.coord_x.textChanged.connect(self.disableButton_10)
		self.dlg10.coord_y.textChanged.connect(self.disableButton_10)

		try:
			self.define_mod(codici_mod_identcoord, "vw_mod_identcoord", lista_mod_identcoord)
			self.update_mod_box(self.dlg10.mod_identcoord, codici_mod_identcoord)
			self.define_mod(codici_modo_quota, "vw_modo_quota", lista_modo_quota)
			self.update_mod_box(self.dlg10.modo_quota, codici_modo_quota)

		except IndexError:
			pass

		proj = QgsProject.instance()
		proj.writeEntry('Digitizing', 'SnappingMode', 'all_layers')
		proj.writeEntry('Digitizing','DefaultSnapTolerance', 20.0)

		self.dlg10.show()
		result = self.dlg10.exec_()
		if result:

			vectorLyr = QgsMapLayerRegistry.instance().mapLayersByName("Siti puntuali")[0]
			it = vectorLyr.getFeatures()
			vpr = vectorLyr.dataProvider()

			idx1 = vpr.fieldNameIndex("indirizzo")
			idx2 = vpr.fieldNameIndex("desc_modcoord")
			idx3 = vpr.fieldNameIndex("quota_slm")
			idx4 = vpr.fieldNameIndex("data_sito")
			idx5 = vpr.fieldNameIndex("note_sito")
			idx6 = vpr.fieldNameIndex("mod_identcoord")
			idx7 = vpr.fieldNameIndex("modo_quota")
			idx8 = vpr.fieldNameIndex("ubicazione_prov")
			idx9 = vpr.fieldNameIndex("ubicazione_com")
			idx10 = vpr.fieldNameIndex("id_spu")

			attr = [None] * len(vpr.fields())

			attr[idx1] = self.dlg10.indirizzo.text()
			attr[idx2] = self.dlg10.desc_modcoord.text()
			attr[idx3] = self.dlg10.quota_slm.text()
			attr[idx4] = self.dlg10.data_sito.text()
			attr[idx5] = self.dlg10.note_sito.toPlainText()
			attr[idx6] = self.dlg10.mod_identcoord.currentText().strip().split(" - ")[0]
			attr[idx7] = self.dlg10.modo_quota.currentText().strip().split(" - ")[0]
			attr[idx8] = self.dlg10.ubicazione_prov.text()
			attr[idx9] = self.dlg10.ubicazione_com.text()
			attr[idx10] = self.dlg10.id_spu.text()

			pnt = QgsGeometry.fromPoint(QgsPoint(float(self.dlg10.coord_x.text()), float(self.dlg10.coord_y.text())))
			f = QgsFeature()
			f.setGeometry(pnt)
			f.setAttributes(attr)
			vpr.addFeatures([f])
			vectorLyr.updateExtents()


	def run11(self):

		self.dlg11.centroms.setPixmap(QPixmap(self.plugin_dir + os.sep + "img" + os.sep + 'logo-centroMS.jpg'))
		self.dlg11.igag.setPixmap(QPixmap(self.plugin_dir + os.sep + "img" + os.sep + 'logo-igag.png'))
		self.dlg11.cnr.setPixmap(QPixmap(self.plugin_dir + os.sep + "img" + os.sep + 'logo-cnr.png'))
		self.dlg11.pushButton_ita.clicked.connect(lambda: self.open_pdf(self.plugin_dir + os.sep + "manuale.pdf"))
		self.dlg11.pushButton_eng.clicked.connect(lambda: self.open_pdf(self.plugin_dir + os.sep + "manual.pdf"))

		self.dlg11.show()
		result = self.dlg11.exec_()
		if result:

			webbrowser.open('https://github.com/CNR-IGAG/mzs-tools/wiki/MzS-Tools')


	def run12(self):

		self.dlg12.centroms.setPixmap(QPixmap(self.plugin_dir + os.sep + "img" + os.sep + 'logo-centroMS.jpg'))
		self.dlg12.igag.setPixmap(QPixmap(self.plugin_dir + os.sep + "img" + os.sep + 'logo-igag.png'))
		self.dlg12.cnr.setPixmap(QPixmap(self.plugin_dir + os.sep + "img" + os.sep + 'logo-cnr.png'))
		self.dlg12.dir_input.clear()
		self.dlg12.tab_input.clear()
		self.dlg12.alert_text.hide()
		self.dlg12.button_box.setEnabled(False)
		self.dlg12.dir_input.textChanged.connect(self.disableButton_12)
		self.dlg12.tab_input.textChanged.connect(self.disableButton_12)

		dizio_campi_l = {"pkuid":[QVariant.LongLong,'"csv_sln_pkey_sln"'], "ub_prov":[QVariant.String, '"csv_sln_ubicazione_prov"'], "ub_com":[QVariant.String, '"csv_sln_ubicazione_com"'],
		"aquota":[QVariant.Double, '"csv_sln_Aquota"'], "bquota":[QVariant.Double, '"csv_sln_Bquota"'], "data_sito":[QVariant.String, '"csv_sln_data_sito"'],
		"note_sito":[QVariant.String, '"csv_sln_note_sito"'], "mod_identc":[QVariant.String, '"csv_sln_mod_identcoord"'], "desc_modco":[QVariant.String, '"csv_sln_desc_modcoord"']}
		dizio_campi_p = {"pkuid":[QVariant.LongLong,'"csv_spu_pkey_spu"'], "ub_prov":[QVariant.String, '"csv_spu_ubicazione_prov"'], "ub_com":[QVariant.String, '"csv_spu_ubicazione_com"'],
		"indirizzo":[QVariant.String, '"csv_spu_indirizzo"'], "quota_slm":[QVariant.LongLong, '"csv_spu_quota_slm"'], "modo_quota":[QVariant.String, '"csv_spu_modo_quota"'],
		"data_sito":[QVariant.String, '"csv_spu_data_sito"'], "note_sito":[QVariant.String, '"csv_spu_note_sito"'], "mod_identc":[QVariant.String, '"csv_spu_mod_identcoord"'],
		"desc_modco":[QVariant.String, '"csv_spu_desc_modcoord"']}
		lista_tab = ["Sito_Puntuale", "Indagini_Puntuali", "Parametri_Puntuali", "Curve", "Sito_Lineare", "Indagini_Lineari", "Parametri_Lineari"]

		self.dlg12.show()
		result = self.dlg12.exec_()
		if result:

			path_absolute = str(QgsProject.instance().readPath("./"))
			path_db = path_absolute + os.sep + "db" + os.sep + "indagini.sqlite"
			path_tabelle = path_absolute + os.sep + "allegati" + os.sep + "altro"
			in_dir = self.dlg12.dir_input.text()
			tab_dir = self.dlg12.tab_input.text()
			dizio_folder = {"Plot" : ["OLD_Plot", path_absolute + os.sep + "allegati" + os.sep + "Plot", in_dir + os.sep + "Plot"], "Documenti" : ["OLD_Documenti", path_absolute + os.sep + "allegati" + os.sep + "Documenti", in_dir + os.sep + "Indagini" + os.sep + "Documenti"], "Spettri" : ["OLD_Spettri", path_absolute + os.sep + "allegati" + os.sep + "Spettri", in_dir + os.sep + "MS23" + os.sep + "Spettri"]}
			check_sito_p = True
			check_sito_l = True
			z_list = []

			if os.path.exists(in_dir) and os.path.exists(tab_dir):
				logfile_ita = path_absolute + os.sep + "allegati" + os.sep + "log" + os.sep + str(time.strftime("%Y-%m-%d_%H-%M-%S", time.gmtime())) + "_log_importazione.txt"
				logfile_eng = path_absolute + os.sep + "allegati" + os.sep + "log" + os.sep + str(time.strftime("%Y-%m-%d_%H-%M-%S", time.gmtime())) + "_import_log.txt"
				f = open(logfile_ita,'a')
				e = open(logfile_eng,'a')
				f.write("REPORT DI IMPORTAZIONE:" +"\n-----------------------\n\n")
				e.write("IMPORT REPORT:" +"\n---------------\n\n")

				try:
					if os.path.exists(path_tabelle + os.sep + "Indagini"):
						shutil.rmtree(path_tabelle + os.sep + "Indagini")
						os.makedirs(path_tabelle + os.sep + "Indagini")
						self.copy_files(in_dir + os.sep + "Indagini", path_tabelle + os.sep + "Indagini")
					else:
						os.makedirs(path_tabelle + os.sep + "Indagini")
						try:
							self.copy_files(in_dir + os.sep + "Indagini", path_tabelle + os.sep + "Indagini")
						except WindowsError:
							pass

					for nome_tab in lista_tab:
						if os.path.exists(path_tabelle + os.sep + nome_tab):
							os.remove(path_tabelle + os.sep + nome_tab)

					self.copy_files(tab_dir, path_tabelle)

					for chiave, valore in self.posizione.iteritems():
						sourceLYR = QgsVectorLayer(in_dir + os.sep + valore[0] + os.sep + valore[1] + ".shp", valore[1], 'ogr')
						destLYR = QgsMapLayerRegistry.instance().mapLayersByName(chiave)[0]
						dest_field = []
						for x in destLYR.fields():
							dest_field.append(x)

						featureList = []
						commonFields = self.attributeAdaptor(destLYR,sourceLYR)

						if chiave == "Zone stabili liv 2" or chiave == "Zone instabili liv 2":
							f.write("Sto copiando lo shapefile '" + chiave + "'\n")
							e.write("I am copying '" + chiave + "' shapefile\n")
							try:
								if os.path.exists(in_dir + os.sep + valore[0] + os.sep + valore[1] + ".shp"):
									sourceFeatures = sourceLYR.getFeatures(QgsFeatureRequest(QgsExpression( " \"LIVELLO\" = 2 " )))
									self.calc_layer(sourceFeatures, destLYR, commonFields, featureList, f, e)
									f.write("  Lo shapefile '" + chiave + "' e' stato copiato!\n\n")
									e.write("  '" + chiave + "' shapefile has been copied!\n\n")
								else:
									f.write("  Lo shapefile '" + chiave + "' non esiste!\n\n")
									e.write("  '" + chiave + "' shapefile does not exist!\n\n")
									pass
							except:
								f.write("  Non sono riuscito a copiare lo shapefile '" + chiave + "'\n\n")
								e.write("  I could not copy '" + chiave + "' shapefile\n\n")
								pass
						elif chiave == "Zone stabili liv 3" or chiave == "Zone instabili liv 3":
							f.write("Sto copiando lo shapefile '" + chiave + "'\n")
							e.write("I am copying the '" + chiave + "' shapefile\n")
							try:
								if os.path.exists(in_dir + os.sep + valore[0] + os.sep + valore[1] + ".shp"):
									sourceFeatures = sourceLYR.getFeatures(QgsFeatureRequest(QgsExpression( " \"LIVELLO\" = 3 " )))
									self.calc_layer(sourceFeatures, destLYR, commonFields, featureList, f, e)
									f.write("  Lo shapefile '" + chiave + "' e' stato copiato!\n\n")
									e.write("  '" + chiave + "' shapefile has been copied!\n\n")
								else:
									f.write("  Lo shapefile '" + chiave + "' non esiste!\n\n")
									e.write("  '" + chiave + "' shapefile does not exist!\n\n")
									pass
							except:
								f.write("  Non sono riuscito a copiare lo shapefile '" + chiave + "'\n\n")
								e.write("  I could not copy '" + chiave + "' shapefile\n\n")
								pass
						elif chiave == "Siti puntuali":
							f.write("Sto copiando lo shapefile '" + chiave + "'\n")
							e.write("I am copying '" + chiave + "' shapefile\n")
							try:
								if os.path.exists(in_dir + os.sep + valore[0] + os.sep + valore[1] + ".shp"):
									if os.path.exists(path_tabelle + os.sep + 'Sito_Puntuale.txt'):
										self.calc_siti(path_tabelle, "Ind_pu", 'Sito_Puntuale.txt', "csv_spu", 'ID_SPU', dizio_campi_p, 'Siti puntuali', 'id_spu', f, e)
										f.write("  Lo shapefile '" + chiave + "' e' stato copiato!\n\n")
										e.write("  '" + chiave + "' shapefile has been copied!\n\n")
										z_list.append("Sito_Puntuale")
										check_sito_p = True
									else:
										f.write("  La tabella 'Sito_Puntuale.txt' non esiste!\n\n")
										e.write("  Table 'Sito_Puntuale.txt' does not exist!\n\n")
										check_sito_p = False
										pass
								else:
									f.write("  Lo shapefile '" + chiave + "' non esiste!\n\n")
									e.write("  '" + chiave + "' shapefile does not exist!\n\n")
									check_sito_p = False
									pass
							except:
								f.write("  Non sono riuscito a copiare lo shapefile '" + chiave + "'\n\n")
								e.write("  I could not copy '" + chiave + "' shapefile\n\n")
								check_sito_p = False
								pass
						elif chiave == "Siti lineari":
							f.write("Sto copiando lo shapefile '" + chiave + "'\n")
							e.write("I am copying '" + chiave + "' shapefile\n")
							try:
								if os.path.exists(in_dir + os.sep + valore[0] + os.sep + valore[1] + ".shp"):
									if os.path.exists(path_tabelle + os.sep + 'Sito_Lineare.txt'):
										self.calc_siti(path_tabelle, "Ind_ln", 'Sito_Lineare.txt', "csv_sln", 'ID_SLN', dizio_campi_l, 'Siti lineari', 'id_sln', f, e)
										f.write("  Lo shapefile '" + chiave + "' e' stato copiato!\n\n")
										e.write("  '" + chiave + "' shapefile has been copied!\n\n")
										z_list.append("Sito_Lineare")
										check_sito_l = True
									else:
										f.write("  La tabella 'Sito_Lineare.txt' non esiste!\n\n")
										e.write("  Table 'Sito_Lineare.txt' does not exist!\n\n")
										check_sito_l = False
										pass
								else:
									f.write("  Lo shapefile '" + chiave + "' non esiste!\n\n")
									e.write("  '" + chiave + "' shapefile does not exist!\n\n")
									check_sito_l = False
									pass
							except:
								f.write("  Non sono riuscito a copiare lo shapefile '" + chiave + "'\n\n")
								e.write("  I could not copy '" + chiave + "' shapefile\n\n")
								check_sito_l = False
								pass
						elif chiave == "Comune del progetto":
							pass
						else:
							f.write("Sto copiando lo shapefile '" + chiave + "'\n")
							e.write("I am copying '" + chiave + "' shapefile\n")
							try:
								if os.path.exists(in_dir + os.sep + valore[0] + os.sep + valore[1] + ".shp"):
									sourceFeatures = sourceLYR.getFeatures()
									self.calc_layer(sourceFeatures, destLYR, commonFields, featureList, f, e)
									f.write("  Lo shapefile '" + chiave + "' e' stato copiato!\n\n")
									e.write("  '" + chiave + "' shapefile has been copied!\n\n")
								else:
									f.write("  Lo shapefile '" + chiave + "' non esiste!\n\n")
									e.write("  '" + chiave + "' shapefile does not exist!\n\n")
									pass
							except:
								f.write("  Non sono riuscito a copiare lo shapefile '" + chiave + "'\n\n")
								e.write("  I could not copy '" + chiave + "' shapefile\n\n")
								pass

					if check_sito_p is True:
						if os.path.exists(path_tabelle + os.sep + "Indagini_Puntuali.txt"):
							z_list.append("Indagini_Puntuali")
							f.write("Sto copiando la tabella 'Indagini_Puntuali.txt'\n")
							e.write("I am copying 'Indagini_Puntuali.txt' table\n")
							try:
								i_p = QgsMapLayerRegistry.instance().mapLayersByName('Indagini puntuali')[0]
								field_i_p = QgsField('temp_pkey_spu', QVariant.LongLong)
								i_p.addExpressionField('"id_spu"', field_i_p)
								conn = sqlite3.connect(path_db)
								conn.text_factory = lambda x: unicode(x, 'utf-8', 'ignore')
								cur = conn.cursor()
								csv_file = path_tabelle + os.sep + "Indagini_Puntuali.txt"
								with open(csv_file,'rb') as fin:
									dr = csv.DictReader(fin, delimiter=';', quotechar='"')
									to_db = [(i['pkey_indpu'], i['pkey_spu'], i['classe_ind'], i['tipo_ind'], i['ID_INDPU'], i['id_indpuex'], i['arch_ex'], i['note_ind'], i['prof_top'], i['prof_bot'], i['spessore'], i['quota_slm_top'], i['quota_slm_bot'], i['data_ind'], i['doc_pag'], i['doc_ind']) for i in dr]
								cur.executemany("INSERT INTO indagini_puntuali (pkuid, id_spu, classe_ind, tipo_ind, id_indpu, id_indpuex, arch_ex, note_ind, prof_top, prof_bot, spessore, quota_slm_top, quota_slm_bot, data_ind, doc_pag, doc_ind) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?);", to_db)
								i_p.addExpressionField('"id_spu"', field_i_p)
								conn.commit()
								conn.close()

								s_p = QgsMapLayerRegistry.instance().mapLayersByName('Siti puntuali')[0]
								self.calc_join(i_p, s_p, 'temp_pkey_spu', '"Siti puntuali_id_spu"', "id_spu")
								f.write("  La tabella 'Indagini_Puntuali.txt' e' stata copiata!\n\n")
								e.write("  'Indagini_Puntuali.txt' table has been copied!\n\n")
							except:
								f.write("  Non sono riuscito a copiare la tabella 'Indagini_Puntuali.txt'\n\n")
								e.write("  I could not copy 'Indagini_Puntuali.txt' table\n\n")
								pass

							if os.path.exists(path_tabelle + os.sep + "Parametri_Puntuali.txt"):
								z_list.append("Parametri_Puntuali")
								f.write("Sto copiando la tabella 'Parametri_Puntuali.txt'\n")
								e.write("I am copying 'Parametri_Puntuali.txt' table\n")
								try:
									p_p = QgsMapLayerRegistry.instance().mapLayersByName('Parametri puntuali')[0]
									field_p_p = QgsField('temp_pkey_indpu', QVariant.LongLong)
									p_p.addExpressionField('"id_indpu"', field_p_p)
									conn = sqlite3.connect(path_db)
									conn.text_factory = lambda x: unicode(x, 'utf-8', 'ignore')
									cur = conn.cursor()
									csv_file = path_tabelle + os.sep + "Parametri_Puntuali.txt"
									with open(csv_file,'rb') as fin:
										dr = csv.DictReader(fin, delimiter=';', quotechar='"')
										to_db = [(i['pkey_parpu'], i['pkey_indpu'], i['tipo_parpu'], i['ID_PARPU'], i['prof_top'], i['prof_bot'], i['spessore'], i['quota_slm_top'], i['quota_slm_bot'], i['valore'], i['attend_mis'], i['tab_curve'], i['note_par'], i['data_par']) for i in dr]
									cur.executemany("INSERT INTO parametri_puntuali (pkuid , id_indpu , tipo_parpu , id_parpu , prof_top , prof_bot , spessore , quota_slm_top , quota_slm_bot , valore , attend_mis , tab_curve , note_par , data_par) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?);", to_db)
									p_p.addExpressionField('"id_indpu"', field_p_p)
									conn.commit()
									conn.close()

									i_p = QgsMapLayerRegistry.instance().mapLayersByName('Indagini puntuali')[0]
									self.calc_join(p_p, i_p, 'temp_pkey_indpu', '"Indagini puntuali_id_indpu"', "id_indpu")
									f.write("  La tabella 'Parametri_Puntuali.txt' e' stata copiata!\n\n")
									e.write("  'Parametri_Puntuali.txt' table has been copied!\n\n")
								except:
									f.write("  Non sono riuscito a copiare la tabella 'Parametri_Puntuali.txt'\n\n")
									e.write("  I could not copy 'Parametri_Puntuali.txt' table\n\n")
									pass

								if os.path.exists(path_tabelle + os.sep + "Curve.txt"):
									z_list.append("Curve")
									f.write("Sto copiando la tabella 'Curve.txt'\n")
									e.write("I am copying 'Curve.txt' table\n")
									try:
										cu = QgsMapLayerRegistry.instance().mapLayersByName('Curve di riferimento')[0]
										field_cu = QgsField('temp_pkey_parpu', QVariant.LongLong)
										cu.addExpressionField('"id_parpu"', field_cu)
										conn = sqlite3.connect(path_db)
										conn.text_factory = lambda x: unicode(x, 'utf-8', 'ignore')
										cur = conn.cursor()
										csv_file = path_tabelle + os.sep + "Curve.txt"
										with open(csv_file,'rb') as fin:
											dr = csv.DictReader(fin, delimiter=';', quotechar='"')
											to_db = [(i['pkey_curve'], i['pkey_parpu'], i['cond_curve'], i['varx'], i['vary']) for i in dr]
										cur.executemany("INSERT INTO curve (pkuid, id_parpu, cond_curve, varx, vary) VALUES (?,?,?,?,?);", to_db)
										cu.addExpressionField('"id_parpu"', field_cu)
										conn.commit()
										conn.close()

										p_p = QgsMapLayerRegistry.instance().mapLayersByName('Parametri puntuali')[0]
										self.calc_join(cu, p_p, 'temp_pkey_parpu', '"Parametri puntuali_id_parpu"', "id_parpu")
										f.write("  La tabella 'Curve.txt' e' stata copiata!\n\n")
										e.write("  'Curve.txt' table has been copied!\n\n")
									except:
										f.write("  Non sono riuscito a copiare la tabella 'Curve.txt'\n\n")
										e.write("  I could not copy 'Curve.txt' table\n\n")
										pass

					if check_sito_l is True:
						if os.path.exists(path_tabelle + os.sep + "Indagini_Lineari.txt"):
							z_list.append("Indagini_Lineari")
							f.write("Sto copiando la tabella 'Indagini_Lineari.txt'\n")
							e.write("I am copying 'Indagini_Lineari.txt' table\n")
							try:
								i_l = QgsMapLayerRegistry.instance().mapLayersByName('Indagini lineari')[0]
								field_i_l = QgsField('temp_pkey_sln', QVariant.LongLong)
								i_l.addExpressionField('"id_sln"', field_i_l)
								conn = sqlite3.connect(path_db)
								conn.text_factory = lambda x: unicode(x, 'utf-8', 'ignore')
								cur = conn.cursor()
								csv_file = path_tabelle + os.sep + "Indagini_Lineari.txt"
								with open(csv_file,'rb') as fin:
									dr = csv.DictReader(fin, delimiter=';', quotechar='"')
									to_db = [(i['pkey_indln'], i['pkey_sln'], i['classe_ind'], i['tipo_ind'], i['ID_INDLN'], i['id_indlnex'], i['arch_ex'], i['note_indln'], i['data_ind'], i['doc_pag'], i['doc_ind']) for i in dr]
								cur.executemany("INSERT INTO indagini_lineari (pkuid, id_sln, classe_ind, tipo_ind, id_indln, id_indlnex, arch_ex, note_indln, data_ind, doc_pag, doc_ind) VALUES (?,?,?,?,?,?,?,?,?,?,?);", to_db)
								i_l.addExpressionField('"id_sln"', field_i_l)
								conn.commit()
								conn.close()

								s_l = QgsMapLayerRegistry.instance().mapLayersByName('Siti lineari')[0]
								self.calc_join(i_l, s_l, 'temp_pkey_sln', '"Siti lineari_id_sln"', "id_sln")
								f.write("  La tabella 'Indagini_Lineari.txt' e' stata copiata!\n\n")
								e.write("  'Indagini_Lineari.txt' table has been copied!\n\n")
							except:
								f.write("  Non sono riuscito a copiare la tabella 'Indagini_Lineari.txt'\n\n")
								e.write("  I could not copy 'Indagini_Lineari.txt' table\n\n")
								pass

							if os.path.exists(path_tabelle + os.sep + "Parametri_Lineari.txt"):
								z_list.append("Parametri_Lineari")
								f.write("Sto copiando la tabella 'Parametri_Lineari.txt'\n")
								e.write("I am copying 'Parametri_Lineari.txt' table\n")
								try:
									p_l = QgsMapLayerRegistry.instance().mapLayersByName('Parametri lineari')[0]
									field_p_l = QgsField('temp_pkey_indln', QVariant.LongLong)
									p_l.addExpressionField('"id_indln"', field_p_l)
									conn = sqlite3.connect(path_db)
									conn.text_factory = lambda x: unicode(x, 'utf-8', 'ignore')
									cur = conn.cursor()
									csv_file = path_tabelle + os.sep + "Parametri_Lineari.txt"
									with open(csv_file,'rb') as fin:
										dr = csv.DictReader(fin, delimiter=';', quotechar='"')
										to_db = [(i['pkey_parln'], i['pkey_indln'], i['tipo_parln'], i['ID_PARLN'], i['prof_top'], i['prof_bot'], i['spessore'], i['quota_slm_top'], i['quota_slm_bot'], i['valore'], i['attend_mis'], i['note_par'], i['data_par']) for i in dr]
									cur.executemany("INSERT INTO parametri_lineari (pkuid, id_indln, tipo_parln, id_parln, prof_top, prof_bot, spessore, quota_slm_top, quota_slm_bot, valore, attend_mis, note_par, data_par) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?);", to_db)
									p_l.addExpressionField('"id_indln"', field_p_l)
									conn.commit()
									conn.close()

									i_l = QgsMapLayerRegistry.instance().mapLayersByName('Indagini lineari')[0]
									self.calc_join(p_l, i_l, 'temp_pkey_indln', '"Indagini lineari_id_indln"', "id_indln")
									f.write("  La tabella 'Parametri_Lineari.txt' e' stata copiata!\n\n")
									e.write("  'Parametri_Lineari.txt' table has been copied!\n\n")
								except:
									f.write("  Non sono riuscito a copiare la tabella 'Parametri_Lineari.txt'\n\n")
									e.write("  I could not copy 'Parametri_Lineari.txt' table\n\n")
									pass

					if check_sito_p is False:
						f.write("Il layer 'Ind_pu' e/o la tabella 'Sito_Puntuale' non sono presenti! Quindi le tabelle correlate delle indagini e dei parametri non verranno copiate!\n\n")
						e.write("'Ind_pu' layer and/or 'Sito_Puntuale' table are not present! So the correlated surveys and parameters tables will not be copied!\n\n")
					if check_sito_l is False:
						f.write("Il layer 'Ind_ln' e/o la tabella 'Sito_Lineare' non sono presenti! Quindi le tabelle correlate delle indagini e dei parametri non verranno copiate!\n\n")
						e.write("'Ind_ln' layer and/or 'Sito_Lineare' table are not present! So the correlated surveys and parameters tables will not be copied!\n\n")
					if check_sito_p is True and check_sito_l is True:
						tab_mancanti = list(set(lista_tab) - set(z_list))
						for t_lost in tab_mancanti:
							f.write("La tabella '" + t_lost + "' non esiste!\n\n")
							e.write("'" + t_lost + "' table does not exist!\n\n")

					for chiave_fold, valore_fold in dizio_folder.iteritems():
						f.write("Sto copiando la cartella '" + chiave_fold + "'\n")
						e.write("I am copying '" + chiave_fold + "' folder\n")
						if os.path.exists(valore_fold[2]):
							if os.path.exists(path_absolute + os.sep + "allegati" + os.sep + chiave_fold):
								shutil.rmtree(path_absolute + os.sep + "allegati" + os.sep + chiave_fold)
								shutil.copytree(valore_fold[2], valore_fold[1])
								f.write("  La cartella '" + chiave_fold + "' e' stata copiata!\n\n")
								e.write("  '" + chiave_fold + "' folder has been copied!\n\n")
							else:
								shutil.copytree(in_dir + os.sep + chiave_fold, path_absolute + os.sep + "allegati" + os.sep + chiave_fold)
								f.write("  La cartella '" + chiave_fold + "' e' stata copiata!\n\n")
								e.write("  '" + chiave_fold + "' folder has been copied!\n\n")
						else:
							f.write("  La cartella non esiste!\n\n")
							e.write("  The folder does not exist!\n\n")

					shutil.rmtree(path_absolute + os.sep + "allegati" + os.sep + "altro")
					os.makedirs(path_absolute + os.sep + "allegati" + os.sep + "altro")

					f.write("\nAnalisi terminata!")
					e.write("\nAnalysis completed!")
					QMessageBox.information(None, u'INFORMATION!', u"Import report was saved in the project folder '...\\allegati\\log'")

				except WindowsError:
					QMessageBox.warning(None, u'WARNING!', u"An incomplete project has been selected!\nOr it is not a Seismic Microzonation project!")
				except:
					QMessageBox.critical(None, u'ERROR!', u"Generic error! Contact the plugin developers!")

			else:
				QMessageBox.warning(None, u'WARNING!', u"The selected directory does not exist!")


	def disableButton_1(self):

		check_campi = [self.dlg1.professionista.text(), self.dlg1.propretario.text(), self.dlg1.scala_nom.text(), self.dlg1.email_prof.text(), self.dlg1.email_prop.text(), self.dlg1.dir_output.text(), str(self.dlg1.comune.currentText())]
		check_value = []

		for x in check_campi:
			if len(x) > 0:
				value_campi = 1
				check_value.append(value_campi)
			else:
				value_campi = 0
				check_value.append(value_campi)

		campi = sum(check_value)
		if campi > 6:
			self.dlg1.button_box.setEnabled(True)
		else:
			self.dlg1.button_box.setEnabled(False)


	def disableButton_3(self):

		check_campi = [self.dlg3.dir_input.text(), self.dlg3.dir_output.text()]
		check_value = []

		for x in check_campi:
			if len(x) > 0:
				value_campi = 1
				check_value.append(value_campi)
			else:
				value_campi = 0
				check_value.append(value_campi)

		campi = sum(check_value)
		if campi > 1:
			self.dlg3.button_box.setEnabled(True)
		else:
			self.dlg3.button_box.setEnabled(False)


	def disableButton_4(self):

		check_campi = [self.dlg4.dir_input.text(), self.dlg4.dir_output.text()]
		check_value = []

		for x in check_campi:
			if len(x) > 0:
				value_campi = 1
				check_value.append(value_campi)
			else:
				value_campi = 0
				check_value.append(value_campi)

		campi = sum(check_value)
		if campi > 1:
			self.dlg4.button_box.setEnabled(True)
		else:
			self.dlg4.button_box.setEnabled(False)


	def disableButton_5(self):

		conteggio = 0
  		check_campi = [self.dlg5.dir_output.text()]
		check_value = []

		layers = self.iface.legendInterface().layers()
		for layer in layers:
		  if layer.name() in self.lista_layer:
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
			self.dlg5.button_box.setEnabled(True)
			self.dlg5.alert_text.hide()
		elif conteggio > 23 and campi == 0:
 			self.dlg5.button_box.setEnabled(False)
			self.dlg5.alert_text.hide()
		else:
			self.dlg5.button_box.setEnabled(False)
			self.dlg5.alert_text.show()


	def disableButton_10(self):

		check_campi = [self.dlg10.coord_x.text(), self.dlg10.coord_y.text()]
		check_value = []

		for x in check_campi:
			if len(x) > 0:
				value_campi = 1
				check_value.append(value_campi)
			else:
				value_campi = 0
				check_value.append(value_campi)
		campi = sum(check_value)

		try:
			QgsMapLayerRegistry.instance().mapLayersByName("Siti puntuali")[0]
			self.dlg10.alert_text.hide()
			if campi > 1:
				self.dlg10.button_box.setEnabled(True)
			else:
				self.dlg10.button_box.setEnabled(False)

		except IndexError:
			self.dlg10.button_box.setEnabled(False)
			self.dlg10.alert_text.show()


	def disableButton_12(self):

		conteggio = 0
		check_campi = [self.dlg12.dir_input.text(), self.dlg12.tab_input.text()]
		check_value = []

		layers = self.iface.legendInterface().layers()
		for layer in layers:
		  if layer.name() in self.lista_layer:
			conteggio += 1

		for x in check_campi:
			if len(x) > 0:
				value_campi = 1
				check_value.append(value_campi)
			else:
				value_campi = 0
				check_value.append(value_campi)
		campi = sum(check_value)

		if conteggio > 23 and campi > 1:
			self.dlg12.button_box.setEnabled(True)
			self.dlg12.alert_text.hide()
		elif conteggio > 23:
 			self.dlg12.button_box.setEnabled(False)
			self.dlg12.alert_text.hide()
		else:
			self.dlg12.button_box.setEnabled(False)
			self.dlg12.alert_text.show()


	def update_cod_istat(self, dizionario, nome_comune_sel, campo):

		for chiave, valore in dizionario.iteritems():
			if chiave == nome_comune_sel:
				campo.setText(valore)


	def radio_stab_clicked(self, enabled):

		if enabled:
			self.dlg6.input_ms.clear()
			self.dlg6.output_ms.clear()

			layers = self.iface.legendInterface().layers()
			layer_stab = []
			layer_instab = []
			for layer in layers:
				if str(layer.name()).startswith("Stab") or str(layer.name()).startswith("Zone stabili"):
					layer_stab.append(layer.name())
					self.dlg6.button_box.setEnabled(True)

			self.dlg6.input_ms.addItems(layer_stab)
			self.dlg6.output_ms.addItems(layer_stab)


	def radio_instab_clicked(self, enabled):

		if enabled:
			self.dlg6.input_ms.clear()
			self.dlg6.output_ms.clear()

			layers = self.iface.legendInterface().layers()
			layer_stab = []
			layer_instab = []
			for layer in layers:
				if str(layer.name()).startswith("Instab") or str(layer.name()).startswith("Zone instabili") or str(layer.name()).startswith("Instabilita' di versante"):
					layer_instab.append(layer.name())
					self.dlg6.button_box.setEnabled(True)

			self.dlg6.input_ms.addItems(layer_instab)
			self.dlg6.output_ms.addItems(layer_instab)


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


	def define_mod(self, codici_mod, nome, lista):

		codici_mod_layer = QgsMapLayerRegistry.instance().mapLayersByName(nome)[0]

		for classe in codici_mod_layer.getFeatures(QgsFeatureRequest().setFlags(QgsFeatureRequest.NoGeometry)):
			lista=[classe.attributes()[1],classe.attributes()[2]]
			codici_mod.append(lista)
		return codici_mod


	def update_mod_box(self, mod_box, codici_mod):

		mod_box.clear()
		mod_box.addItem("")
		mod_box.model().item(0).setEnabled(False)
		for row in codici_mod:
			mod_box.addItem(row[1])


	def update_num(self, value, n1, n2):

		try:
			valore = int(value.text())
			if valore not in range(n1, n2):
				value.setText('')

		except:
			value.setText('')


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


	def sincro_indagini(self, nome_p, fld, nome_f):

		sourceLYR = QgsMapLayerRegistry.instance().mapLayersByName(nome_p)[0]
		destLYR = QgsMapLayerRegistry.instance().mapLayersByName(nome_f)[0]
		features_p = []
		features_f = []
		remove_list = []

		for feature_p in sourceLYR.getFeatures(QgsFeatureRequest().setFlags(QgsFeatureRequest.NoGeometry).setSubsetOfAttributes([fld], sourceLYR.fields())):
			idx = feature_p.fieldNameIndex(fld)
			features_p.append(feature_p.attributes()[idx])
		for feature_f in destLYR.getFeatures(QgsFeatureRequest().setFlags(QgsFeatureRequest.NoGeometry).setSubsetOfAttributes([fld], destLYR.fields())):
			idx = feature_f.fieldNameIndex(fld)
			features_f.append(feature_f.attributes()[idx])
		remove_list = list(set(features_f) - set(features_p))

		destLYR.startEditing()
		for cod in remove_list:
			for fc in destLYR.getFeatures(QgsFeatureRequest().setFilterExpression('"' + fld + '" = \'' + cod + '\'').setSubsetOfAttributes([]).setFlags(QgsFeatureRequest.NoGeometry)):
				destLYR.deleteFeature(fc.id())
		destLYR.commitChanges()


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


	def attributeAdaptor(self,targetLayer, sourceLayer):

		targetLayerFields = []
		sourceLayerFields = []
		primaryKeyList = []

		for index in targetLayer.dataProvider().pkAttributeIndexes():
			primaryKeyList.append(targetLayer.dataProvider().fields().at(index).name())

		for field in sourceLayer.dataProvider().fields().toList():
			sourceLayerFields.append(field.name())

		for field in targetLayer.dataProvider().fields().toList():
			targetLayerFields.append(field.name())

		commonFields = list(set(sourceLayerFields) & set(targetLayerFields))
		commonFields = list(set(commonFields)-set(primaryKeyList))

		return commonFields


	def attributeFill(self, qgsFeature, targetLayer, commonFields):

		featureFields = {}

		try:
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
		except:
			pass

		qgsFeature.setFields(targetLayer.dataProvider().fields())
		if commonFields:
			for fieldName in commonFields:
				try:
					qgsFeature[fieldName]=featureFields[fieldName]
				except:
					pass

		return qgsFeature


	def calc_layer(self, sourceFeatures, destLYR, commonFields, featureList, f, e):

		for feature in sourceFeatures:
			geom = feature.geometry()
			if geom:
				err = geom.validateGeometry()
				if not err:
				   modifiedFeature = self.attributeFill(feature,destLYR,commonFields)
				   featureList.append(modifiedFeature)
				else:
					f.write("  Individuato errore geometrico (la feature %d non verra' copiata)\n" % (feature.id()+1))
					e.write("  Identified geometric error (feature %d will not be copied)\n" % (feature.id()+1))
					pass

		destLYR.startEditing()
		data_provider = destLYR.dataProvider()
		data_provider.addFeatures(featureList)
		destLYR.commitChanges()


	def calc_siti(self, path_tabelle, nome_shape, csv_path, csv_tab_name, id_field, dizionario, nome_layer, id_orig_field, f, e):

		shp_path = path_tabelle + os.sep + "Indagini" + os.sep + nome_shape + ".shp"
		fullname = os.path.join(path_tabelle, csv_path).replace('\\', '/')
		s_geom = iface.addVectorLayer(shp_path, '', 'ogr')
		csv_uri = 'file:///%s?delimiter=;' % (fullname)
		s_attr = QgsVectorLayer(csv_uri, csv_tab_name, "delimitedtext")
		QgsMapLayerRegistry.instance().addMapLayer(s_attr)

		joinObject = QgsVectorJoinInfo()
		joinObject.joinLayerId = s_attr.id()
		joinObject.joinFieldName = id_field
		joinObject.targetFieldName = id_field
		joinObject.memoryCache = True
		s_geom.addJoin(joinObject)

		for chiave, valore in dizionario.iteritems():
			s_geom.dataProvider().addAttributes([QgsField(chiave, valore[0])])
			s_geom.updateFields()
			expression = QgsExpression(valore[1])
			expression.prepare(s_geom.pendingFields())
			s_geom.startEditing()
			for feature in s_geom.getFeatures():
				value = expression.evaluate(feature)
				feature[chiave] = value
				s_geom.updateFeature(feature)
			s_geom.commitChanges()

		s = QgsMapLayerRegistry.instance().mapLayersByName(nome_layer)[0]
		s_geom = QgsMapLayerRegistry.instance().mapLayersByName(nome_shape)[0]
		featureList = []
		commonFields = self.attributeAdaptor(s,s_geom)
		commonFields.append('pkuid')
		commonFields.append('desc_modcoord')
		commonFields.append('mod_identcoord')
		commonFields.append('ubicazione_prov')
		commonFields.append('ubicazione_com')
		commonFields.append(id_orig_field)
		sourceFeatures = s_geom.getFeatures()
		for feature in sourceFeatures:
			geom = feature.geometry()
			if geom:
				err = geom.validateGeometry()
				if not err:
					modifiedFeature = self.attributeFill(feature,s,commonFields)
					featureList.append(modifiedFeature)
				else:
					f.write("  Individuato errore geometrico (la feature %d non verra' copiata)\n" % (feature.id()+1))
					e.write("  Identified geometric error (feature %d will not be copied)\n" % (feature.id()+1))
					pass

		s.startEditing()
		data_provider = s.dataProvider()
		data_provider.addFeatures(featureList)
		s.commitChanges()

		QgsMapLayerRegistry.instance().removeMapLayer(s_attr.id())
		QgsMapLayerRegistry.instance().removeMapLayer(s_geom.id())


	def calc_join(self, orig_tab, link_tab, temp_field, link_field, orig_field):

		joinObject = QgsVectorJoinInfo()
		joinObject.joinLayerId = link_tab.id()
		joinObject.joinFieldName = 'pkuid'
		joinObject.targetFieldName = temp_field
		joinObject.memoryCache = True
		orig_tab.addJoin(joinObject)
		expression = QgsExpression(link_field)
		expression.prepare(orig_tab.pendingFields())
		orig_tab.startEditing()
		for feature in orig_tab.getFeatures():
			value = expression.evaluate(feature)
			feature[orig_field] = value
			orig_tab.updateFeature(feature)
		orig_tab.commitChanges()
		orig_tab.removeJoin(link_tab.id())


	def copy_files(self, src, dest):
		for file_name in os.listdir(src):
			full_file_name = os.path.join(src, file_name)
			if (os.path.isfile(full_file_name)):
				shutil.copy(full_file_name, dest)


	def mappa_insieme(self, mainPath, destLYR):

		destLYR = QgsMapLayerRegistry.instance().mapLayersByName("Limiti comunali")[0]
		canvas = iface.mapCanvas()
		extent = destLYR.extent()
		canvas.setExtent(extent)

		map_settings = iface.mapCanvas().mapSettings()
		c = QgsComposition(map_settings)
		c.setPaperSize(1200, 700)
		c.setPrintResolution(200)

		x, y = 0, 0
		w, h = c.paperWidth(), c.paperHeight()
		composerMap = QgsComposerMap(c, x ,y, w, h)
		composerMap.setBackgroundEnabled(False)
		c.addItem(composerMap)

		dpmm = 200/25.4
		width = int(dpmm * c.paperWidth())
		height = int(dpmm * c.paperHeight())

		image = QImage(QSize(width, height), QImage.Format_ARGB32)
		image.setDotsPerMeterX(dpmm * 1000)
		image.setDotsPerMeterY(dpmm * 1000)
		image.fill(Qt.transparent)

		imagePainter = QPainter(image)

		c.setPlotStyle(QgsComposition.Print)
		c.renderPage(imagePainter, 0)
		imagePainter.end()

		imageFilename =  mainPath + os.sep + "progetto" + os.sep + "loghi" + os.sep + "mappa_reg.png"
		image.save(imageFilename, 'png')


	def open_pdf(self, pdf_path):

		os.startfile(pdf_path)