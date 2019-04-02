# -*- coding: utf-8 -*-
#-------------------------------------------------------------------------------
# Name:		instab_geotec.py
# Author:	  Tarquini E.
# Created:	 13-04-2017
#-------------------------------------------------------------------------------

from qgis.core import *
from qgis.PyQt.QtWidgets import *
import webbrowser


def define_tipo_i(dialog, layer, feature):

	codici_instab = []
	cod_instab = dialog.findChild(QComboBox,"cod_instab")
	lineedit_tipo_i = dialog.findChild(QLineEdit,"Tipo_i")
	help_button = dialog.findChild(QPushButton, "help_button")

	codici_instab_layer = QgsMapLayerRegistry.instance().mapLayersByName("vw_cod_instab")[0]
	for i in codici_instab_layer.getFeatures(QgsFeatureRequest().setFlags(QgsFeatureRequest.NoGeometry)):
		if int(i.attributes()[1]) != 3001 and int(i.attributes()[1]) != 3002 and int(i.attributes()[1]) != 3050 and int(i.attributes()[1]) != 3051 and int(i.attributes()[1]) != 3052 and int(i.attributes()[1]) != 3053 and int(i.attributes()[1]) != 3060 and int(i.attributes()[1]) != 3061 and int(i.attributes()[1]) != 3062 and int(i.attributes()[1]) != 3070 and int(i.attributes()[1]) != 3080:
			codici_instab.append(i.attributes()[2])
	cod_instab.addItem("")
	cod_instab.model().item(0).setEnabled(False)
	for c in codici_instab:
		cod_instab.addItem(c)

	cod_instab.currentIndexChanged.connect(lambda: update_lineedit_tipo_i(cod_instab, lineedit_tipo_i))
	help_button.clicked.connect(lambda: webbrowser.open('https://www.youtube.com/watch?v=dnJIjTNzQJQ&t=115s'))


def update_lineedit_tipo_i(cod_instab, lineedit_tipo_i):
	tipo_i = cod_instab.currentText().strip()[:4]

	if tipo_i is None:
		tipo_i = ""
	lineedit_tipo_i.setText(tipo_i)