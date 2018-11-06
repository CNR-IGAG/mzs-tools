# -*- coding: utf-8 -*-
#-------------------------------------------------------------------------------
# Name:		tb_nuovo_progetto.py
# Author:	  Tarquini E.
# Created:	 08-02-2018
#-------------------------------------------------------------------------------

from PyQt4 import QtGui, uic
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from qgis.utils import *
from qgis.core import *
from qgis.gui import *
import os, sys, webbrowser, csv, shutil, zipfile


FORM_CLASS, _ = uic.loadUiType(os.path.join(
	os.path.dirname(__file__), 'tb_nuovo_progetto.ui'))


class nuovo_progetto(QtGui.QDialog, FORM_CLASS):
	def __init__(self, parent=None):
		"""Constructor."""
		self.iface = iface
		super(nuovo_progetto, self).__init__(parent)
		self.setupUi(self)
		self.plugin_dir = os.path.dirname(__file__)

	def nuovo(self):
		self.help_button.clicked.connect(lambda: webbrowser.open('https://www.youtube.com/watch?v=TcaljLE5TCk&t=57s&list=PLM5qQOkOkzgWH2VogqeQIDybylmE4P1TQ&index=2'))
		REGIONE = {"01":"Piemonte","02":"Valle d'Aosta","03":"Lombardia","04":"Trentino Alto Adige","05":"Veneto",
		"06":"Friuli Venezia Giulia", "07":"Liguria","08":"Emilia Romagna","09":"Toscana","10":"Umbria","11":"Marche",
		"12":"Lazio","13":"Abruzzo","14":"Molise", "15":"Campania","16":"Puglia","17":"Basilicata","18":"Calabria",
		"19":"Sicilia","20":"Sardegna"}
		dir_svg_input = self.plugin_dir + os.sep + "img" + os.sep + "svg"
		dir_svg_output = self.plugin_dir.split("python")[0] + "svg"
		tabella_controllo = self.plugin_dir + os.sep + "comuni.csv"
		pacchetto = self.plugin_dir + os.sep + "data" + os.sep + "progetto_MS.zip"

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

		self.dir_output.clear()
		self.comune.clear()
		self.cod_istat.clear()
		self.professionista.clear()
		self.tel_prof.clear()
		self.email_prof.clear()
		self.sito_prof.clear()
		self.data_meta.clear()
		self.propretario.clear()
		self.tel_prop.clear()
		self.email_prop.clear()
		self.sito_prop.clear()
		self.keyword.clear()
		self.scala_nom.clear()
		self.accuratezza.clear()
		self.lineage.clear()
		self.button_box.setEnabled(False)
		self.data_meta.setMinimumDate(QDate.currentDate())
		self.comune.addItems(sorted(dizio_comuni.keys()))
		self.comune.model().item(0).setEnabled(False)
		self.comune.currentIndexChanged.connect(lambda: self.update_cod_istat(dizio_comuni, str(self.comune.currentText()), self.cod_istat))
		self.scala_nom.textEdited.connect(lambda: self.update_num(self.scala_nom,0,100000))
		self.comune.currentIndexChanged.connect(self.disableButton)
		self.professionista.textChanged.connect(self.disableButton)
		self.propretario.textChanged.connect(self.disableButton)
		self.scala_nom.textChanged.connect(self.disableButton)
		self.email_prof.textChanged.connect(self.disableButton)
		self.email_prop.textChanged.connect(self.disableButton)
		self.dir_output.textChanged.connect(self.disableButton)

		self.show()
		result = self.exec_()
		if result:

			dir_out = self.dir_output.text()
			if os.path.isdir(dir_out):
				try:
					comune = str(self.comune.currentText())
					cod_istat = self.cod_istat.text()
					professionista = self.professionista.text()
					tel_prof = self.tel_prof.text()
					email_prof = self.email_prof.text()
					sito_prof = self.sito_prof.text()
					data_meta = self.data_meta.text()
					propretario = self.propretario.text()
					tel_prop = self.tel_prop.text()
					email_prop = self.email_prop.text()
					sito_prop = self.sito_prop.text()
					keyword = self.keyword.text()
					scala_nom = self.scala_nom.text()
					accuratezza = self.accuratezza.text()
					lineage = self.lineage.toPlainText()

					if not os.path.exists(dir_svg_output):
						shutil.copytree(dir_svg_input, dir_svg_output)
					else:
						src_files = os.listdir(dir_svg_input)
						for file_name in src_files:
							full_file_name = os.path.join(dir_svg_input, file_name)
							if os.path.isfile(full_file_name):
								shutil.copy(full_file_name, dir_svg_output)

					zip_ref = zipfile.ZipFile(pacchetto, 'r')
					zip_ref.extractall(dir_out)
					zip_ref.close()
					for x, y in dict_comuni.iteritems():
						if x == cod_istat:
							comune_nome = (y[6:]).replace("_"," ")
							path_comune = dir_out + os.sep + y
							os.rename(dir_out + os.sep + "progetto_MS", path_comune)

					metadata = path_comune + os.sep + "allegati" + os.sep + comune_nome + " metadata.txt"
					f = open(metadata,'a')
					f.write("METADATA\nMunicipality of "+ comune_nome +":\n-------------------------------\n\n")
					f.write("Expert: " + unicode(professionista).encode('utf-8') + "\n")
					f.write("Expert's phone: " + unicode(tel_prof).encode('utf-8') + "\n")
					f.write("Expert's email: " + unicode(email_prof).encode('utf-8') + "\n")
					f.write("Expert's website: " + unicode(sito_prof).encode('utf-8') + "\n")
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

					sourceLYR.removeSelection()

					sourceLYR.setSubsetString("cod_regio='" + codice_regio + "'")

					logo_regio_in = os.path.join(self.plugin_dir, "img" + os.sep + "logo_regio" + os.sep + codice_regio + ".png").replace('\\', '/')
					logo_regio_out = os.path.join(path_comune, "progetto" + os.sep + "loghi" + os.sep + "logo_regio.png").replace('\\', '/')
					shutil.copyfile(logo_regio_in, logo_regio_out)

					mainPath = (QgsProject.instance().fileName()).split("progetto")[0]
					self.mappa_insieme(mainPath, sourceLYR)

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
						map_item_2.setText("Regione " + REGIONE[codice_regio])
						map_item_3 = composition.getComposerItemById('com_title')
						map_item_3.setText("Comune di " + nome)
						map_item_4 = composition.getComposerItemById('logo')
						map_item_4.refreshPicture()
						map_item_5 = composition.getComposerItemById('mappa_1')
						map_item_5.refreshPicture()

##					project.write()

				except WindowsError:
					QMessageBox.critical(None, u'ERROR!', u'Error:')
				except Exception as z:
					QMessageBox.critical(None, u'ERROR!', u'Error:\n"' + str(z) + '"')
					if os.path.exists(dir_out + os.sep + "progetto_MS"):
						shutil.rmtree(dir_out + os.sep + "progetto_MS")
			else:
				QMessageBox.warning(iface.mainWindow(), u'WARNING!', u"The selected directory does not exist!")

	def disableButton(self):
		check_campi = [self.professionista.text(), self.propretario.text(), self.scala_nom.text(), self.email_prof.text(), self.email_prop.text(), self.dir_output.text(), str(self.comune.currentText())]
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
			self.button_box.setEnabled(True)
		else:
			self.button_box.setEnabled(False)

	def update_cod_istat(self, dizionario, nome_comune_sel, campo):
		for chiave, valore in dizionario.iteritems():
			if chiave == nome_comune_sel:
				campo.setText(valore)

	def update_num(self, value, n1, n2):
		try:
			valore = int(value.text())
			if valore not in range(n1, n2):
				value.setText('')
		except:
			value.setText('')

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