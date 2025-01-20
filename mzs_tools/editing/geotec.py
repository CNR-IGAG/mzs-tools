# -*- coding: utf-8 -*-
# -------------------------------------------------------------------------------
# Name:		geotec.py
# Author:	  Tarquini E.
# Created:	 04-04-2018
# -------------------------------------------------------------------------------

import webbrowser
from builtins import str
from functools import partial

from qgis.core import *
from qgis.PyQt import QtGui
from qgis.PyQt.QtWidgets import *


def geotec_form_init(dialog, layer, feature):
    codici_stato = []
    lista_stato = []
    codici_gen = []
    lista_gen = []
    tipo_gt = dialog.findChild(QComboBox, "Tipo_gt")
    stato_box = dialog.findChild(QComboBox, "stato_box")
    stato = dialog.findChild(QLineEdit, "Stato")
    gen_box = dialog.findChild(QComboBox, "gen_box")
    gen = dialog.findChild(QLineEdit, "Gen")
    alert_text = dialog.findChild(QLabel, "alert_text")
    help_button = dialog.findChild(QPushButton, "help_button")

    alert_text.hide()
    define_stato(codici_stato)
    tipo_gt.currentIndexChanged.connect(partial(update_box_stato, tipo_gt, stato_box, codici_stato))
    stato_box.currentIndexChanged.connect(partial(update_stato, stato, stato_box))
    define_gen(codici_gen)
    tipo_gt.currentIndexChanged.connect(partial(update_box_gen, tipo_gt, gen_box, codici_gen))
    gen_box.currentIndexChanged.connect(partial(update_gen, gen, gen_box))
    tipo_gt.currentIndexChanged.connect(partial(update_alert, tipo_gt, gen_box, stato_box, alert_text))
    help_button.clicked.connect(lambda: webbrowser.open("https://www.youtube.com/watch?v=dnJIjTNzQJQ&t=115s"))


def define_stato(codici_stato):
    codici_stato_layer = QgsProject.instance().mapLayersByName("vw_stato")[0]

    for classe in codici_stato_layer.getFeatures(QgsFeatureRequest().setFlags(QgsFeatureRequest.NoGeometry)):
        lista_stato = [classe.attributes()[1], classe.attributes()[2], classe.attributes()[3]]
        codici_stato.append(lista_stato)
    return codici_stato


def update_box_stato(tipo_gt, stato_box, codici_stato):
    if not tipo_gt.currentText():
        return

    curIndex = str(tipo_gt.currentText().strip()).split(" - ")[1]

    stato_box.clear()
    stato_box.addItem("")
    stato_box.model().item(0).setEnabled(False)
    for row in codici_stato:
        if row[2] == curIndex:
            stato_box.addItem(row[1])


def update_stato(stato, stato_box):
    TipoStato = str(stato_box.currentText().strip()).split(" - ")[0]

    stato.setText(TipoStato)


def define_gen(codici_gen):
    codici_gen_layer = QgsProject.instance().mapLayersByName("vw_gen")[0]

    for classe in codici_gen_layer.getFeatures(QgsFeatureRequest().setFlags(QgsFeatureRequest.NoGeometry)):
        lista_gen = [classe.attributes()[1], classe.attributes()[2], classe.attributes()[3]]
        codici_gen.append(lista_gen)
    return codici_gen


def update_box_gen(tipo_gt, gen_box, codici_gen):
    if not tipo_gt.currentText():
        return

    curIndex = str(tipo_gt.currentText().strip()).split(" - ")[1]

    gen_box.clear()
    gen_box.addItem("")
    gen_box.model().item(0).setEnabled(False)
    for row in codici_gen:
        if row[2] == curIndex:
            gen_box.addItem(row[1])


def update_gen(gen, gen_box):
    Tipogen = str(gen_box.currentText().strip()).split(" - ")[0]

    gen.setText(Tipogen)


def update_alert(tipo_gt, gen_box, stato_box, alert_text):
    curIndex = str(tipo_gt.currentText().strip()).split(" - ")[0]

    if curIndex in (
        "RI",
        "GW",
        "GP",
        "GM",
        "GC",
        "SW",
        "SP",
        "SM",
        "SC",
        "OL",
        "OH",
        "MH",
        "ML",
        "CL",
        "CH",
        "PT",
        "LC",
    ):
        alert_text.hide()
        gen_box.setEnabled(True)
        stato_box.setEnabled(True)
    elif curIndex in (
        "LP",
        "GR",
        "CO",
        "AL",
        "LPS",
        "GRS",
        "COS",
        "ALS",
        "SFLP",
        "SFGR",
        "SFCO",
        "SFAL",
        "SFLPS",
        "SFGRS",
        "SFCOS",
        "SFALS",
        "IS",
        "ISS",
        "SFIS",
        "SFISS",
    ):
        alert_text.show()
        gen_box.setEnabled(False)
        stato_box.setEnabled(False)
