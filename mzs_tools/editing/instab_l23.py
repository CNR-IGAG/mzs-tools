import os
import re
import webbrowser
from functools import partial

from qgis.core import QgsProject, QgsFeatureRequest
from qgis.PyQt.QtWidgets import QComboBox, QLineEdit, QPushButton, QFileDialog


def instab_l23_form_init(dialog, layer, feature):
    codici_instab = []
    codici_zone = []
    cod_instab = dialog.findChild(QComboBox, "cod_instab")
    cod_stab = dialog.findChild(QComboBox, "cod_stab")
    lineedit_tipo_i = dialog.findChild(QLineEdit, "Tipo_i")
    spettri = dialog.findChild(QLineEdit, "SPETTRI")
    frt = dialog.findChild(QLineEdit, "FRT")
    frr = dialog.findChild(QLineEdit, "FRR")
    il = dialog.findChild(QLineEdit, "IL")
    amb = dialog.findChild(QComboBox, "AMB")
    disl = dialog.findChild(QLineEdit, "DISL")
    fa = dialog.findChild(QLineEdit, "FA")
    fv = dialog.findChild(QLineEdit, "FV")
    ft = dialog.findChild(QLineEdit, "Ft")
    fh0105 = dialog.findChild(QLineEdit, "FH0105")
    fh0510 = dialog.findChild(QLineEdit, "FH0510")
    fh0515 = dialog.findChild(QLineEdit, "FH0515")
    fpga = dialog.findChild(QLineEdit, "FPGA")
    fa0105 = dialog.findChild(QLineEdit, "FA0105")
    fa0408 = dialog.findChild(QLineEdit, "FA0408")
    fa0711 = dialog.findChild(QLineEdit, "FA0711")
    button_doc = dialog.findChild(QPushButton, "pushButton")
    help_button = dialog.findChild(QPushButton, "help_button")
    amb.addItem("")

    codici_instab_layer = QgsProject.instance().mapLayersByName("vw_cod_instab")[0]
    # excluded_codes = [
    #     3011,
    #     3012,
    #     3013,
    #     3014,
    #     3015,
    #     3021,
    #     3022,
    #     3023,
    #     3024,
    #     3025,
    #     3031,
    #     3032,
    #     3033,
    #     3034,
    #     3035,
    #     3041,
    #     3042,
    #     3043,
    #     3044,
    #     3045,
    #     3050,
    #     3060,
    #     3070,
    #     3080,
    # ]

    for feature in codici_instab_layer.getFeatures(QgsFeatureRequest().setFlags(QgsFeatureRequest.NoGeometry)):
        # code = int(feature.attributes()[1])
        codici_instab.append(feature.attributes()[2])
        # if code not in excluded_codes:
        #     codici_instab.append(feature.attributes()[2])

    cod_instab.addItem("")
    cod_instab.model().item(0).setEnabled(False)
    for c in sorted(codici_instab):
        cod_instab.addItem(c)

    codici_zone_layer = QgsProject.instance().mapLayersByName("vw_cod_stab")[0]
    for i in codici_zone_layer.getFeatures(QgsFeatureRequest().setFlags(QgsFeatureRequest.NoGeometry)):
        if int(i.attributes()[1]) > 2000:
            codici_zone.append(i.attributes()[2])
    cod_stab.addItem("")
    cod_stab.model().item(0).setEnabled(False)
    for c in codici_zone:
        cod_stab.addItem(c)

    cod_instab.currentIndexChanged.connect(partial(update_lineedit_tipo_i, cod_instab, cod_stab, lineedit_tipo_i))
    cod_stab.currentIndexChanged.connect(partial(update_lineedit_tipo_i, cod_instab, cod_stab, lineedit_tipo_i))
    # cod_instab.currentIndexChanged.connect(partial(update_lineedit_il, cod_instab, il, amb))
    button_doc.clicked.connect(partial(select_output_file, button_doc, spettri))
    frt.textEdited.connect(partial(update_valore, frt))
    frr.textEdited.connect(partial(update_valore, frr))
    il.textEdited.connect(partial(update_valore, il))
    disl.textEdited.connect(partial(update_valore, disl))
    fa.textEdited.connect(partial(update_valore, fa))
    fv.textEdited.connect(partial(update_valore, fv))
    ft.textEdited.connect(partial(update_valore, ft))
    fh0105.textEdited.connect(partial(update_valore, fh0105))
    fh0510.textEdited.connect(partial(update_valore, fh0510))
    fh0515.textEdited.connect(partial(update_valore, fh0515))
    fpga.textEdited.connect(partial(update_valore, fpga))
    fa0105.textEdited.connect(partial(update_valore, fa0105))
    fa0408.textEdited.connect(partial(update_valore, fa0408))
    fa0711.textEdited.connect(partial(update_valore, fa0711))
    help_button.clicked.connect(lambda: webbrowser.open("https://www.youtube.com/watch?v=drs3COLtML8"))


def update_lineedit_tipo_i(cod_instab, cod_stab, lineedit_tipo_i):
    tipo_i = cod_instab.currentText().strip()[:4]
    tipo_z = cod_stab.currentText().strip()[:4]

    codici_4_cifre = [
        "3060",
        "3061",
        "3062",
        "3070",
        "3080",
        "3081",
        "3082",
        "3090",
        "3091",
        "3092",
        "3069",
    ]

    if tipo_i is None:
        tipo_i = ""
    elif tipo_i in codici_4_cifre:
        cod_stab.setEnabled(False)
        cod_stab.setCurrentIndex(0)
        tipo_z = ""
    else:
        cod_stab.setEnabled(True)
    if tipo_z is None:
        tipo_z = ""
    lineedit_tipo_i.setText(tipo_i + tipo_z)


def select_output_file(button_doc, spettri):
    spettri.clear()
    filedirectory, __ = QFileDialog.getOpenFileName(button_doc, "Select output file ", "", "*.txt")
    drive, path_and_file = os.path.splitdrive(filedirectory)
    path, filename = os.path.split(path_and_file)
    spettri.setText(filename)


# def update_lineedit_il(cod_instab, il, amb):
#     tipo_i = cod_instab.currentText().strip()[:4]
#     if tipo_i == "3001" or tipo_i == "3002" or tipo_i == "3061" or tipo_i == "3062":
#         il.setText("NULL")
#         il.setEnabled(False)
#         amb.setEnabled(False)
#         amb.setCurrentIndex(-1)
#     else:
#         il.setEnabled(True)
#         amb.setEnabled(True)


def update_valore(value):
    value.setText(re.sub("[^0-9.]", "", value.text()))
