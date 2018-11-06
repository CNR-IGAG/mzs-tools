# -*- coding: utf-8 -*-
#-------------------------------------------------------------------------------
# Name:		tb_aggiorna_progetto.py
# Author:	  Tarquini E.
# Created:	 24-09-2018
#-------------------------------------------------------------------------------

from PyQt4 import QtGui, uic
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from qgis.utils import *
from qgis.core import *
from qgis.gui import *
import os, sys, webbrowser, shutil, zipfile


FORM_CLASS, _ = uic.loadUiType(os.path.join(
	os.path.dirname(__file__), 'tb_aggiorna_progetto.ui'))


class aggiorna_progetto(QtGui.QDialog, FORM_CLASS):

	def __init__(self, parent=None):
		"""Constructor."""
		super(aggiorna_progetto, self).__init__(parent)
		self.setupUi(self)
		self.plugin_dir = os.path.dirname(__file__)

	def aggiorna(self):
		self.help_button.setEnabled(False)	# da eliminare una volta creata la videoguida!!!
		self.help_button.clicked.connect(lambda: webbrowser.open('https://github.com/CNR-IGAG/mzs-tools/wiki/MzS-Tools'))
		self.dir_input.clear()
		self.button_box.setEnabled(False)
		self.alert_text.hide()
		self.dir_input.textChanged.connect(self.disableButton)

		self.show()
		result = self.exec_()
		if result:

			dir2 = self.dir_input.text()
			if os.path.isdir(dir2):
				try:
					vers_data_1 = self.plugin_dir + os.sep + "versione.txt"
					input1 = open(vers_data_1,'r').read()
					vers_data_2 = dir2 + os.sep + "progetto" + os.sep + "versione.txt"
					input2 = open(vers_data_2,'r').read()
					pacchetto = self.plugin_dir + os.sep + "data" + os.sep + "progetto_MS.zip"

					if input2 < input1:
						zip_ref = zipfile.ZipFile(pacchetto, 'r')
						zip_ref.extractall(dir2)
						zip_ref.close()
						shutil.rmtree(dir2 + os.sep + "progetto" + os.sep + "maschere")
						shutil.copytree(dir2 + os.sep + "progetto_MS" + os.sep + "progetto" + os.sep + "maschere", dir2 + os.sep + "progetto" + os.sep + "maschere")
						shutil.rmtree(dir2 + os.sep + "progetto" + os.sep + "script")
						shutil.copytree(dir2 + os.sep + "progetto_MS" + os.sep + "progetto" + os.sep + "script", dir2 + os.sep + "progetto" + os.sep + "script")
						os.remove(dir2 + os.sep + "progetto" + os.sep + "versione.txt")
						shutil.copyfile(dir2 + os.sep + "progetto_MS" + os.sep + "progetto" + os.sep + "versione.txt", dir2 + os.sep + "progetto" + os.sep + "versione.txt")
						shutil.rmtree(dir2 + os.sep + "progetto_MS")
						project = QgsProject.instance()
						project.read(QFileInfo(dir2 + os.sep + "progetto_MS.qgs"))
						zLayer = QgsMapLayerRegistry.instance().mapLayersByName("Comune del progetto")[0]
						canvas = iface.mapCanvas()
						extent = zLayer.extent()
						canvas.setExtent(extent)
##						project.write()
						QMessageBox.information(None, u'INFORMATION!', u"The project structure has been updated!")
					else:
						QMessageBox.information(None, u'INFORMATION!', u"The project structure is already updated!")

				except Exception as z:
					QMessageBox.critical(None, u'ERROR!', u'Error:\n"' + str(z) + '"')
			else:
				QMessageBox.warning(iface.mainWindow(), u'WARNING!', u"The selected directory does not exist!")

	def disableButton(self):
		check_campi = [self.dir_input.text()]
		check_value = []
		num_l = QgsProject.instance().layerTreeRoot().children()
		if len(num_l) >= 1:
			value_campi = 0
			check_value.append(value_campi)
			self.alert_text.show()
		else:
			value_campi = 1
			check_value.append(value_campi)
			self.alert_text.hide()

		for x in check_campi:
			if len(x) > 0:
				value_campi = 1
				check_value.append(value_campi)
			else:
				value_campi = 0
				check_value.append(value_campi)

		campi = sum(check_value)
		if campi > 1:
			self.button_box.setEnabled(True)
		else:
			self.button_box.setEnabled(False)