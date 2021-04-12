from builtins import str
# -*- coding: utf-8 -*-
# -------------------------------------------------------------------------------
# Name:		tb_copia_ms.py
# Author:	  Tarquini E.
# Created:	 08-02-2018
# -------------------------------------------------------------------------------

from qgis.PyQt import QtGui, uic
from qgis.PyQt.QtCore import *
from qgis.PyQt.QtGui import *
from qgis.PyQt.QtWidgets import *
from qgis.utils import *
from qgis.core import *
from qgis.gui import *
import os
import sys
import webbrowser


FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'tb_copia_ms.ui'))


class copia_ms(QDialog, FORM_CLASS):

    def __init__(self, parent=None):
        """Constructor."""
        self.iface = iface
        super(copia_ms, self).__init__(parent)
        self.setupUi(self)
        self.plugin_dir = os.path.dirname(__file__)

    def copia(self):
        self.help_button.clicked.connect(lambda: webbrowser.open(
            'https://www.youtube.com/watch?v=gghT6tragWM&t=1s'))
        self.group = QButtonGroup()
        self.group.addButton(self.radio_stab)
        self.group.addButton(self.radio_instab)
        self.group.setExclusive(False)
        self.radio_stab.setChecked(False)
        self.radio_instab.setChecked(False)
        self.group.setExclusive(True)
        self.input_ms.clear()
        self.output_ms.clear()
        self.button_box.setEnabled(False)
        self.radio_stab.toggled.connect(self.radio_stab_clicked)
        self.radio_instab.toggled.connect(self.radio_instab_clicked)

        self.show()
        result = self.exec_()
        if result:

            sourceLYR = QgsProject.instance().mapLayersByName(
                str(self.input_ms.currentText()))[0]
            destLYR = QgsProject.instance().mapLayersByName(
                str(self.output_ms.currentText()))[0]
            features = []
            for feature in sourceLYR.getFeatures(QgsFeatureRequest().setFlags(QgsFeatureRequest.NoFlags).setSubsetOfAttributes(['tipo_z', 'tipo_i'], sourceLYR.fields())):
                features.append(feature)
            destLYR.startEditing()
            data_provider = destLYR.dataProvider()
            data_provider.addFeatures(features)
            destLYR.commitChanges()

    def radio_stab_clicked(self, enabled):
        if enabled:
            self.input_ms.clear()
            self.output_ms.clear()

            layers = self.QsProject.instance().mapLayers().values()
            layer_stab = []
            for layer in layers:
                if str(layer.name()).startswith("Stab") or str(layer.name()).startswith("Zone stabili"):
                    layer_stab.append(layer.name())
                    self.button_box.setEnabled(True)

            self.input_ms.addItems(layer_stab)
            self.output_ms.addItems(layer_stab)

    def radio_instab_clicked(self, enabled):
        if enabled:
            self.input_ms.clear()
            self.output_ms.clear()

            layers = self.QsProject.instance().mapLayers().values()
            layer_instab = []
            for layer in layers:
                if str(layer.name()).startswith("Instab") or str(layer.name()).startswith("Zone instabili") or str(layer.name()).startswith("Instabilita' di versante"):
                    layer_instab.append(layer.name())
                    self.button_box.setEnabled(True)

            self.input_ms.addItems(layer_instab)
            self.output_ms.addItems(layer_instab)
