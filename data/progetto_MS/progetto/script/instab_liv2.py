# -*- coding: utf-8 -*-
#-------------------------------------------------------------------------------
# Name:		instab_liv2.py
# Author:	  Tarquini E.
# Created:	 24-11-2017
#-------------------------------------------------------------------------------

from qgis.core import *
from qgis.PyQt.QtWidgets import *
import re, webbrowser


def instab_liv2(dialog, layer, feature):

	codici_instab = []
	codici_zone = []
	cod_instab = dialog.findChild(QComboBox,"cod_instab")
	cod_stab = dialog.findChild(QComboBox,"cod_stab")
	lineedit_tipo_i = dialog.findChild(QLineEdit,"Tipo_i")
	fa = dialog.findChild(QLineEdit,"FA")
	fv = dialog.findChild(QLineEdit,"FV")
	ft = dialog.findChild(QLineEdit,"Ft")
	fh0105 = dialog.findChild(QLineEdit,"FH0105")
	fh0510 = dialog.findChild(QLineEdit,"FH0510")
	fh0515 = dialog.findChild(QLineEdit,"FH0515")
	fpga = dialog.findChild(QLineEdit,"FPGA")
	fa0105 = dialog.findChild(QLineEdit,"FA0105")
	fa0408 = dialog.findChild(QLineEdit,"FA0408")
	fa0711 = dialog.findChild(QLineEdit,"FA0711")
	help_button = dialog.findChild(QPushButton, "help_button")

	codici_instab_layer = QgsMapLayerRegistry.instance().mapLayersByName("vw_cod_instab")[0]
	for i in codici_instab_layer.getFeatures(QgsFeatureRequest().setFlags(QgsFeatureRequest.NoGeometry)):
		if int(i.attributes()[1]) != 3001 and int(i.attributes()[1]) != 3002 and int(i.attributes()[1]) != 3052 and int(i.attributes()[1]) != 3053 and int(i.attributes()[1]) != 3061 and int(i.attributes()[1]) != 3062:
			codici_instab.append(i.attributes()[2])
	cod_instab.addItem("")
	cod_instab.model().item(0).setEnabled(False)
	for c in codici_instab:
		cod_instab.addItem(c)

	codici_zone_layer = QgsMapLayerRegistry.instance().mapLayersByName("vw_cod_stab")[0]
	for i in codici_zone_layer.getFeatures(QgsFeatureRequest().setFlags(QgsFeatureRequest.NoGeometry)):
		if int(i.attributes()[1]) > 2000:
			codici_zone.append(i.attributes()[2])
	cod_stab.addItem("")
	cod_stab.model().item(0).setEnabled(False)
	for c in codici_zone:
		cod_stab.addItem(c)

	cod_instab.currentIndexChanged.connect(lambda: update_lineedit_tipo_i(cod_instab, cod_stab, lineedit_tipo_i))
	cod_stab.currentIndexChanged.connect(lambda: update_lineedit_tipo_i(cod_instab, cod_stab, lineedit_tipo_i))
	fa.textEdited.connect(lambda: update_valore(fa))
	fv.textEdited.connect(lambda: update_valore(fv))
	ft.textEdited.connect(lambda: update_valore(ft))
	fh0105.textEdited.connect(lambda: update_valore(fh0105))
	fh0510.textEdited.connect(lambda: update_valore(fh0510))
	fh0515.textEdited.connect(lambda: update_valore(fh0515))
	fpga.textEdited.connect(lambda: update_valore(fpga))
	fa0105.textEdited.connect(lambda: update_valore(fa0105))
	fa0408.textEdited.connect(lambda: update_valore(fa0408))
	fa0711.textEdited.connect(lambda: update_valore(fa0711))
	help_button.clicked.connect(lambda: webbrowser.open('https://www.youtube.com/watch?v=drs3COLtML8'))


def update_lineedit_tipo_i(cod_instab, cod_stab, lineedit_tipo_i):
	tipo_i = cod_instab.currentText().strip()[:4]
	tipo_z = cod_stab.currentText().strip()[:4]
	if tipo_i is None:
		tipo_i = ""
	elif tipo_i == "3060" or tipo_i == "3070" or tipo_i == "3080":
		cod_stab.setEnabled(False)
		cod_stab.setCurrentIndex(0)
		tipo_z = ""
	else:
		cod_stab.setEnabled(True)
	if tipo_z is None:
		tipo_z = ""
	lineedit_tipo_i.setText(tipo_i + tipo_z)


def update_valore(value):

	value.setText(re.sub('[^0-9.]','', value.text()))