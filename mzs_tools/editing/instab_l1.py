import webbrowser
from functools import partial

from qgis.core import QgsProject, QgsFeatureRequest
from qgis.PyQt.QtWidgets import QComboBox, QLineEdit, QDialog, QDialogButtonBox


def instab_l1_form_init(dialog: QDialog, layer, feature):
    codici_instab = []
    codici_zone = []
    cod_instab = dialog.findChild(QComboBox, "cod_instab")
    cod_stab = dialog.findChild(QComboBox, "cod_stab")
    lineedit_tipo_i = dialog.findChild(QLineEdit, "Tipo_i")
    help_button = dialog.findChild(QDialogButtonBox, "button_box").button(QDialogButtonBox.Help)

    codici_instab_layer = QgsProject.instance().mapLayersByName("vw_cod_instab")[0]
    for i in codici_instab_layer.getFeatures(QgsFeatureRequest().setFlags(QgsFeatureRequest.NoGeometry)):
        attribute_value = int(i.attributes()[1])
        # excluded liv.3 codes
        excluded_values = [3001, 3002, 3052, 3053, 3055, 3056, 3061, 3062, 3081, 3082, 3091, 3092]

        if attribute_value not in excluded_values:
            codici_instab.append(i.attributes()[2])

    cod_instab.addItem("")
    cod_instab.model().item(0).setEnabled(False)
    for c in codici_instab:
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
    help_button.clicked.connect(lambda: webbrowser.open("https://www.youtube.com/watch?v=drs3COLtML8"))


def update_lineedit_tipo_i(cod_instab, cod_stab, lineedit_tipo_i):
    tipo_i = cod_instab.currentText().strip()[:4]
    tipo_z = cod_stab.currentText().strip()[:4]

    no_tipo_z_codes = ["3060", "3069", "3070", "3080", "3090"]

    if tipo_i is None:
        tipo_i = ""
    elif tipo_i in no_tipo_z_codes:
        cod_stab.setEnabled(False)
        cod_stab.setCurrentIndex(0)
        tipo_z = ""
    else:
        cod_stab.setEnabled(True)

    if tipo_z is None:
        tipo_z = ""

    lineedit_tipo_i.setText(tipo_i + tipo_z)
