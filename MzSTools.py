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
import os, sys, constants, resources
from tb_wait import wait
from tb_aggiorna_progetto import aggiorna_progetto
from tb_nuovo_progetto import nuovo_progetto
from tb_importa_shp import importa_shp
from tb_esporta_shp import esporta_shp
from tb_edit_win import edit_win
from tb_copia_ms import copia_ms
from tb_valida import valida
from tb_info import info


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

		self.dlg0 = wait()
		self.dlg1 = aggiorna_progetto()
		self.dlg2 = nuovo_progetto()
		self.dlg3 = info()
		self.dlg4 = importa_shp()
		self.dlg5 = esporta_shp()
		self.dlg6 = copia_ms()
		self.dlg7 = valida()
		self.dlg10 = edit_win()

		self.actions = []
		self.menu = self.tr(u'&MzS Tools')
		self.toolbar = self.iface.addToolBar(u'MzSTools')
		self.toolbar.setObjectName(u'MzSTools')

		self.dlg2.dir_output.clear()
		self.dlg2.pushButton_out.clicked.connect(self.select_output_fld_2)

		self.dlg4.dir_input.clear()
		self.dlg4.pushButton_in.clicked.connect(self.select_input_fld_4)

		self.dlg4.tab_input.clear()
		self.dlg4.pushButton_tab.clicked.connect(self.select_tab_fld_4)

		self.dlg5.dir_output.clear()
		self.dlg5.pushButton_out.clicked.connect(self.select_output_fld_5)

		self.iface.projectRead.connect(self.run1)

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
		icon_path2 = self.plugin_dir + os.sep + "img" + os.sep + 'ico_nuovo_progetto.png'
		icon_path3 = self.plugin_dir + os.sep + "img" + os.sep + 'ico_info.png'
		icon_path4 = self.plugin_dir + os.sep + "img" + os.sep + 'ico_importa.png'
		icon_path5 = self.plugin_dir + os.sep + "img" + os.sep + 'ico_esporta.png'
		icon_path6 = self.plugin_dir + os.sep + "img" + os.sep + 'ico_copia_ms.png'
		icon_path7 = self.plugin_dir + os.sep + "img" + os.sep + 'ico_valida.png'
		icon_path8 = self.plugin_dir + os.sep + "img" + os.sep + 'ico_edita.png'
		icon_path9 = self.plugin_dir + os.sep + "img" + os.sep + 'ico_salva_edita.png'
		icon_path10 = self.plugin_dir + os.sep + "img" + os.sep + 'ico_xypoint.png'

		self.add_action(
			icon_path2,
			text=self.tr(u'New project'),
			callback=self.run2,
			parent=self.iface.mainWindow())

		self.toolbar.addSeparator()

		self.add_action(
			icon_path4,
			text=self.tr(u'Import project folder to geodatabase'),
			callback=self.run4,
			parent=self.iface.mainWindow())
		self.add_action(
			icon_path5,
			text=self.tr(u'Export geodatabase to project folder'),
			callback=self.run5,
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

		self.toolbar.addSeparator()

		self.add_action(
			icon_path7,
			text=self.tr(u'Validate project'),
			callback=self.run7,
			parent=self.iface.mainWindow())

		self.toolbar.addSeparator()

		self.add_action(
			icon_path3,
			text=self.tr(u'Help'),
			callback=self.run3,
			parent=self.iface.mainWindow())

	def unload(self):
		for action in self.actions:
			self.iface.removePluginDatabaseMenu(
				self.tr(u'&MzS Tools'),
				action)
			self.iface.removeToolBarIcon(action)
		del self.toolbar

	def select_output_fld_2(self):
		out_dir = QFileDialog.getExistingDirectory(self.dlg2, "","", QFileDialog.ShowDirsOnly)
		self.dlg2.dir_output.setText(out_dir)

	def select_input_fld_4(self):
		in_dir = QFileDialog.getExistingDirectory(self.dlg4, "","", QFileDialog.ShowDirsOnly)
		self.dlg4.dir_input.setText(in_dir)

	def select_tab_fld_4(self):
		tab_dir = QFileDialog.getExistingDirectory(self.dlg4, "","", QFileDialog.ShowDirsOnly)
		self.dlg4.tab_input.setText(tab_dir)

	def select_input_fld_5(self):
		in_dir = QFileDialog.getExistingDirectory(self.dlg5, "","", QFileDialog.ShowDirsOnly)
		self.dlg5.dir_input.setText(in_dir)

	def select_output_fld_5(self):
		out_dir = QFileDialog.getExistingDirectory(self.dlg5, "","", QFileDialog.ShowDirsOnly)
		self.dlg5.dir_output.setText(out_dir)

	def run1(self):
		percorso = QgsProject.instance().homePath()
		dir_output = '/'.join(percorso.split('/')[:-1])
		nome = percorso.split('/')[-1]
		if os.path.exists(percorso + os.sep + "progetto"):
			vers_data = (QgsProject.instance().fileName()).split("progetto")[0] + os.sep + "progetto" + os.sep + "versione.txt"
			try:
				proj_vers = open(vers_data,'r').read()
				if proj_vers < '0.9':
					qApp.processEvents()
					self.dlg1.aggiorna(percorso,dir_output,nome)

			except:
				pass

	def run2(self):
		self.dlg2.igag.setPixmap(QPixmap(self.plugin_dir + os.sep + "img" + os.sep + 'logo-igag.png'))
		self.dlg2.cnr.setPixmap(QPixmap(self.plugin_dir + os.sep + "img" + os.sep + 'logo-cnr.png'))
		self.dlg2.labgis.setPixmap(QPixmap(self.plugin_dir + os.sep + "img" + os.sep + 'logo-labgis.png'))
		self.dlg2.nuovo()

	def run3(self):
		self.dlg3.igag.setPixmap(QPixmap(self.plugin_dir + os.sep + "img" + os.sep + 'logo-igag.png'))
		self.dlg3.cnr.setPixmap(QPixmap(self.plugin_dir + os.sep + "img" + os.sep + 'logo-cnr.png'))
		self.dlg3.labgis.setPixmap(QPixmap(self.plugin_dir + os.sep + "img" + os.sep + 'logo-labgis.png'))
		self.dlg3.help()

	def run4(self):
		self.dlg4.igag.setPixmap(QPixmap(self.plugin_dir + os.sep + "img" + os.sep + 'logo-igag.png'))
		self.dlg4.cnr.setPixmap(QPixmap(self.plugin_dir + os.sep + "img" + os.sep + 'logo-cnr.png'))
		self.dlg4.labgis.setPixmap(QPixmap(self.plugin_dir + os.sep + "img" + os.sep + 'logo-labgis.png'))
		self.dlg4.importa_prog()

	def run5(self):
		self.dlg5.igag.setPixmap(QPixmap(self.plugin_dir + os.sep + "img" + os.sep + 'logo-igag.png'))
		self.dlg5.cnr.setPixmap(QPixmap(self.plugin_dir + os.sep + "img" + os.sep + 'logo-cnr.png'))
		self.dlg5.labgis.setPixmap(QPixmap(self.plugin_dir + os.sep + "img" + os.sep + 'logo-labgis.png'))
		self.dlg5.esporta_prog()

	def run6(self):
		self.dlg6.igag.setPixmap(QPixmap(self.plugin_dir + os.sep + "img" + os.sep + 'logo-igag.png'))
		self.dlg6.cnr.setPixmap(QPixmap(self.plugin_dir + os.sep + "img" + os.sep + 'logo-cnr.png'))
		self.dlg6.labgis.setPixmap(QPixmap(self.plugin_dir + os.sep + "img" + os.sep + 'logo-labgis.png'))
		self.dlg6.copia()

	def run7(self):
		self.dlg7.igag.setPixmap(QPixmap(self.plugin_dir + os.sep + "img" + os.sep + 'logo-igag.png'))
		self.dlg7.cnr.setPixmap(QPixmap(self.plugin_dir + os.sep + "img" + os.sep + 'logo-cnr.png'))
		self.dlg7.labgis.setPixmap(QPixmap(self.plugin_dir + os.sep + "img" + os.sep + 'logo-labgis.png'))
		self.dlg7.controllo()

	def run8(self):
		proj = QgsProject.instance()
		proj.writeEntry('Digitizing', 'SnappingMode', 'all_layers')
		proj.writeEntry('Digitizing','DefaultSnapTolerance', 20.0)
		DIZIO_LAYER = {"Zone stabili liv 1":"Zone instabili liv 1", "Zone instabili liv 1":"Zone stabili liv 1", "Zone stabili liv 2":"Zone instabili liv 2", "Zone instabili liv 2":"Zone stabili liv 2",
		"Zone stabili liv 3":"Zone instabili liv 3", "Zone instabili liv 3":"Zone stabili liv 3"}
		POLY_LYR = ["Unita' geologico-tecniche", "Instabilita' di versante", "Zone stabili liv 1", "Zone instabili liv 1", "Zone stabili liv 2", "Zone instabili liv 2",
		"Zone stabili liv 3", "Zone instabili liv 3"]

		layer = iface.activeLayer()
		if layer != None:
			if layer.name() in POLY_LYR:

				self.dlg0.show()
				for fc in iface.legendInterface().layers():
					if fc.name() in POLY_LYR:
						proj.setSnapSettingsForLayer(fc.id(), True, 0, 0, 20, False)

				for chiave, valore in DIZIO_LAYER.iteritems():
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
				self.dlg0.hide()

			else:
				layer.startEditing()
				iface.actionAddFeature().trigger()

	def run9(self):
		proj = QgsProject.instance()
		proj.writeEntry('Digitizing', 'SnappingMode', 'all_layers')
		proj.writeEntry('Digitizing','DefaultSnapTolerance', 20.0)
		POLIGON_LYR = ["Unita' geologico-tecniche", "Instabilita' di versante", "Zone stabili liv 1", "Zone instabili liv 1", "Zone stabili liv 2", "Zone instabili liv 2",
		"Zone stabili liv 3", "Zone instabili liv 3"]

		layer = iface.activeLayer()
		if layer != None:
			if layer.name() in POLIGON_LYR:

				self.dlg0.show()
				layers = iface.legendInterface().layers()
				for fc in layers:
					if fc.name() in POLIGON_LYR:
						proj.setSnapSettingsForLayer(fc.id(), True, 0, 0, 20, False)

				layer.commitChanges()
				self.dlg0.hide()

			else:
				layer.commitChanges()

	def run10(self):
		self.dlg10.igag.setPixmap(QPixmap(self.plugin_dir + os.sep + "img" + os.sep + 'logo-igag.png'))
		self.dlg10.cnr.setPixmap(QPixmap(self.plugin_dir + os.sep + "img" + os.sep + 'logo-cnr.png'))
		self.dlg10.labgis.setPixmap(QPixmap(self.plugin_dir + os.sep + "img" + os.sep + 'logo-labgis.png'))
		self.dlg10.edita()