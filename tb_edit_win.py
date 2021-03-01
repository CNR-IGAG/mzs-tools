from builtins import range
# -*- coding: utf-8 -*-
#-------------------------------------------------------------------------------
# Name:		tb_edit_win.py
# Author:	  Tarquini E.
# Created:	 08-02-2018
#-------------------------------------------------------------------------------

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
    os.path.dirname(__file__), 'tb_edit_win.ui'))


class edit_win(QDialog, FORM_CLASS):

    def __init__(self, parent=None):
        """Constructor."""
        super(edit_win, self).__init__(parent)
        self.setupUi(self)
        self.plugin_dir = os.path.dirname(__file__)

    def edita(self):
        self.help_button.clicked.connect(lambda: webbrowser.open(
            'https://www.youtube.com/watch?v=4jQ9OacJ71w&t=4s'))
        codici_mod_identcoord = []
        lista_mod_identcoord = []
        codici_modo_quota = []
        lista_modo_quota = []
        self.coord_x.clear()
        self.coord_y.clear()
        self.indirizzo.clear()
        self.mod_identcoord.clear()
        self.desc_modcoord.clear()
        self.quota_slm.clear()
        self.modo_quota.clear()
        self.data_sito.clear()
        self.note_sito.clear()
        today = QDate.currentDate()
        self.data_sito.setDate(today)
        self.alert_text.hide()
        self.button_box.setEnabled(False)
        self.coord_x.textEdited.connect(
            lambda: self.update_num(self.coord_x, -170000, 801000))
        self.coord_y.textEdited.connect(
            lambda: self.update_num(self.coord_y, 0, 5220000))
        self.quota_slm.textEdited.connect(
            lambda: self.update_num(self.quota_slm, 0, 4900))
        self.coord_x.textChanged.connect(self.disableButton)
        self.coord_y.textChanged.connect(self.disableButton)

        try:
            self.define_mod(codici_mod_identcoord,
                            "vw_mod_identcoord", lista_mod_identcoord)
            self.update_mod_box(self.mod_identcoord, codici_mod_identcoord)
            self.define_mod(codici_modo_quota,
                            "vw_modo_quota", lista_modo_quota)
            self.update_mod_box(self.modo_quota, codici_modo_quota)

        except IndexError:
            pass

        proj = QgsProject.instance()
        proj.writeEntry('Digitizing', 'SnappingMode', 'all_layers')
        proj.writeEntry('Digitizing', 'DefaultSnapTolerance', 20.0)

        self.show()
        result = self.exec_()
        if result:

            vectorLyr = QgsProject.instance(
            ).mapLayersByName("Siti puntuali")[0]
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

            attr[idx1] = self.indirizzo.text()
            attr[idx2] = self.desc_modcoord.text()
            attr[idx3] = self.quota_slm.text()
            attr[idx4] = self.data_sito.text()
            attr[idx5] = self.note_sito.toPlainText()
            attr[idx6] = self.mod_identcoord.currentText().strip().split(" - ")[0]
            attr[idx7] = self.modo_quota.currentText().strip().split(" - ")[0]
            attr[idx8] = self.ubicazione_prov.text()
            attr[idx9] = self.ubicazione_com.text()
            attr[idx10] = self.id_spu.text()

            pnt = QgsGeometry.fromPoint(
                QgsPoint(float(self.coord_x.text()), float(self.coord_y.text())))
            f = QgsFeature()
            f.setGeometry(pnt)
            f.setAttributes(attr)
            vpr.addFeatures([f])
            vectorLyr.updateExtents()

    def update_num(self, value, n1, n2):
        try:
            valore = int(value.text())
            if valore not in list(range(n1, n2)):
                value.setText('')
        except:
            value.setText('')

    def disableButton(self):
        check_campi = [self.coord_x.text(), self.coord_y.text()]
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
            QgsProject.instance().mapLayersByName("Siti puntuali")[0]
            self.alert_text.hide()
            if campi > 1:
                self.button_box.setEnabled(True)
            else:
                self.button_box.setEnabled(False)

        except IndexError:
            self.button_box.setEnabled(False)
            self.alert_text.show()

    def define_mod(self, codici_mod, nome, lista):
        codici_mod_layer = QgsProject.instance().mapLayersByName(nome)[
            0]

        for classe in codici_mod_layer.getFeatures(QgsFeatureRequest().setFlags(QgsFeatureRequest.NoGeometry)):
            lista = [classe.attributes()[1], classe.attributes()[2]]
            codici_mod.append(lista)
        return codici_mod

    def update_mod_box(self, mod_box, codici_mod):
        mod_box.clear()
        mod_box.addItem("")
        mod_box.model().item(0).setEnabled(False)
        for row in codici_mod:
            mod_box.addItem(row[1])
