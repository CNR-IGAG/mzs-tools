import os
import re
import webbrowser
from functools import partial

from mzs_tools.core.mzs_project_manager import MzSProjectManager
from qgis.core import QgsFeatureRequest, QgsProject, QgsFieldConstraints, QgsEditorWidgetSetup
from qgis.PyQt.QtCore import QDate
from qgis.PyQt.QtWidgets import (
    QComboBox,
    QDateTimeEdit,
    QDialogButtonBox,
    QFileDialog,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTabWidget,
    QTextEdit,
)
from mzs_tools.plugin_utils.logging import MzSToolsLogger


def change_editor_widget(form, layer, feature):
    prj_manager = MzSProjectManager.instance()
    relation_table_layer_id = prj_manager.find_layer_by_table_name_role("vw_tipo_gt", "editing")
    if feature.attributeMap():
        if feature["tipo_parpu"] == "L":
            setup = QgsEditorWidgetSetup(
                "ValueRelation",
                {
                    "Layer": relation_table_layer_id,
                    "Key": "cod",
                    "Value": "descrizione",
                    "OrderByValue": False,
                    "AllowNull": False,
                },
            )
            # layer.removeFieldConstraint(layer.fields().indexOf("valore"), QgsFieldConstraints.ConstraintExpression)
            layer.setConstraintExpression(
                layer.fields().indexOf("valore"),
                "",
            )
        else:
            setup = QgsEditorWidgetSetup(
                "TextEdit",
                {"DefaultValue": ""},
            )
            # constraint = QgsFieldConstraints()
            # constraint.setConstraintExpression(
            #     "regexp_match(\"valore\",'^([1-9]\\d*|0)(\\.\\d+)?$')",
            #     "Inserire un valore numerico utilizzando il punto per separare i decimali",
            # )
            # layer.fields().field("valore").setConstraints(constraint)
            layer.setFieldConstraint(layer.fields().indexOf("valore"), QgsFieldConstraints.ConstraintExpression)
            val = '"valore"'
            regex = r"'^([1-9]\\d*|0)(\\.\\d+)?$'"
            layer.setConstraintExpression(
                layer.fields().indexOf("valore"),
                f"regexp_match({val},{regex})",
                "Inserire un valore numerico utilizzando il punto per separare i decimali",
            )
        layer.setEditorWidgetSetup(layer.fields().indexOf("valore"), setup)


def sito_puntuale_form_init(dialog, layer, feature):
    quota_slm = dialog.findChild(QLineEdit, "quota_slm")
    # data_sito = dialog.findChild(QDateTimeEdit,"data_sito")
    # today = QtCore.QDate.currentDate()
    tab = dialog.findChild(QTabWidget, "tabWidget")
    # help_button = dialog.findChild(QPushButton, "help_button")

    # nome_layer(tab, layer)
    tab.setTabEnabled(1, feature.id() > 0)
    MzSToolsLogger.log("Sito puntuale form init")

    # data_sito.setDate(today)
    quota_slm.textEdited.connect(partial(update_valore, quota_slm))
    # help_button.clicked.connect(
    #     lambda: webbrowser.open(
    #         "https://www.youtube.com/watch?v=YpzmEt1Xzvs&t=0s&index=5&list=PLM5qQOkOkzgWH2VogqeQIDybylmE4P1TQ"
    #     )
    # )


def sito_lineare_form_init(dialog, layer, feature):
    aquota = dialog.findChild(QLineEdit, "aquota")
    bquota = dialog.findChild(QLineEdit, "bquota")
    # data_sito = dialog.findChild(QDateTimeEdit,"data_sito")
    # today = QtCore.QDate.currentDate()
    tab = dialog.findChild(QTabWidget, "tabWidget")
    help_button = dialog.findChild(QPushButton, "help_button")

    nome_layer(tab, layer)
    # data_sito.setDate(today)
    aquota.textEdited.connect(partial(update_valore, aquota))
    bquota.textEdited.connect(partial(update_valore, bquota))
    help_button.clicked.connect(
        lambda: webbrowser.open(
            "https://www.youtube.com/watch?v=YpzmEt1Xzvs&t=0s&index=5&list=PLM5qQOkOkzgWH2VogqeQIDybylmE4P1TQ"
        )
    )


def indagini_puntuali_form_init(dialog, layer, feature):
    codici_indagini = define_tipo_ind("vw_tipo_ind_p")
    id_indpu = dialog.findChild(QLineEdit, "id_indpu")
    id_spu = dialog.findChild(QComboBox, "id_spu")
    pkey_spu = dialog.findChild(QLineEdit, "pkey_spu")
    tipo_ind_box = dialog.findChild(QComboBox, "tipo_ind_box")
    tipo_ind = dialog.findChild(QLineEdit, "tipo_ind")
    classe_ind = dialog.findChild(QComboBox, "classe_ind")
    doc_ind = dialog.findChild(QLineEdit, "doc_ind")
    button_doc = dialog.findChild(QPushButton, "pushButton")
    data_ind = dialog.findChild(QDateTimeEdit, "data_ind")
    prof_top = dialog.findChild(QLineEdit, "prof_top")
    prof_bot = dialog.findChild(QLineEdit, "prof_bot")
    quota_slm_top = dialog.findChild(QLineEdit, "quota_slm_top")
    quota_slm_bot = dialog.findChild(QLineEdit, "quota_slm_bot")
    # buttonBox = dialog.findChild(QDialogButtonBox, "buttonBox")
    today = QDate.currentDate()
    tab = dialog.findChild(QTabWidget, "tabWidget")
    # help_button = dialog.findChild(QPushButton, "help_button")

    # tipo_ind.setText(None)

    nome_layer(tab, layer)
    data_ind.setDate(today)
    # buttonBox.setEnabled(False)

    pkey_spu.setText(id_spu.currentText().split("P")[-1])
    id_spu.currentIndexChanged.connect(partial(update_pkey, id_spu, pkey_spu, "P"))
    # tab.currentChanged.connect(partial(refresh_variable_ind, classe_ind, doc_ind))
    classe_ind.currentIndexChanged.connect(partial(update_box_ind, classe_ind, tipo_ind_box, codici_indagini))
    tipo_ind_box.currentIndexChanged.connect(partial(update_tipo_ind_p, tipo_ind, tipo_ind_box))
    button_doc.clicked.connect(partial(select_output_file, button_doc, doc_ind))
    # tipo_ind_box.currentIndexChanged.connect(partial(disableButton_p, tipo_ind_box, classe_ind, id_spu, buttonBox))
    # classe_ind.currentIndexChanged.connect(partial(disableButton_p, tipo_ind_box, classe_ind, id_spu, buttonBox))
    # id_spu.currentIndexChanged.connect(partial(disableButton_p, tipo_ind_box, classe_ind, id_spu, buttonBox))
    prof_top.textEdited.connect(partial(update_valore, prof_top))
    prof_bot.textEdited.connect(partial(update_valore, prof_bot))
    quota_slm_top.textEdited.connect(partial(update_valore_slm, quota_slm_top))
    quota_slm_bot.textEdited.connect(partial(update_valore_slm, quota_slm_bot))
    prof_bot.editingFinished.connect(partial(alert_spessore, prof_top, prof_bot, 0))
    prof_top.editingFinished.connect(partial(alert_spessore, prof_top, prof_bot, 0))
    quota_slm_top.editingFinished.connect(partial(alert_spessore, quota_slm_bot, quota_slm_top, 1))
    quota_slm_bot.editingFinished.connect(partial(alert_spessore, quota_slm_bot, quota_slm_top, 1))
    id_indpu.textChanged.connect(partial(update_name_combobox, layer, tipo_ind_box, tipo_ind, codici_indagini))
    # help_button.clicked.connect(lambda: webbrowser.open("https://www.youtube.com/watch?v=aP2buSJk8iE&t=5s"))


def indagini_lineari_form_init(dialog, layer, feature):
    codici_indagini = define_tipo_ind("vw_tipo_ind_l")
    id_indln = dialog.findChild(QLineEdit, "id_indln")
    id_sln = dialog.findChild(QComboBox, "id_sln")
    pkey_sln = dialog.findChild(QLineEdit, "pkey_sln")
    tipo_ind_box = dialog.findChild(QComboBox, "tipo_ind_box")
    tipo_ind = dialog.findChild(QLineEdit, "tipo_ind")
    classe_ind = dialog.findChild(QComboBox, "classe_ind")
    doc_ind = dialog.findChild(QLineEdit, "doc_ind")
    button_doc = dialog.findChild(QPushButton, "pushButton")
    data_ind = dialog.findChild(QDateTimeEdit, "data_ind")
    # alert_text = dialog.findChild(QLabel, "alert_text")
    buttonBox = dialog.findChild(QDialogButtonBox, "buttonBox")
    today = QDate.currentDate()
    tab = dialog.findChild(QTabWidget, "tabWidget")
    # help_button = dialog.findChild(QPushButton, "help_button")

    nome_layer(tab, layer)
    data_ind.setDate(today)
    buttonBox.setEnabled(False)
    # alert_text.hide()

    # button_doc.setEnabled(layer.isEditable())

    pkey_sln.setText(id_sln.currentText().split("L")[-1])
    id_sln.currentIndexChanged.connect(partial(update_pkey, id_sln, pkey_sln, "L"))
    # tab.currentChanged.connect(partial(refresh_variable_ind, classe_ind, doc_ind))
    classe_ind.currentIndexChanged.connect(partial(update_box_ind, classe_ind, tipo_ind_box, codici_indagini))
    tipo_ind_box.currentIndexChanged.connect(
        partial(update_tipo_ind_l, tipo_ind, tipo_ind_box, doc_ind, buttonBox, layer)
    )
    classe_ind.currentIndexChanged.connect(
        partial(update_tipo_ind_l, tipo_ind, tipo_ind_box, doc_ind, buttonBox, layer)
    )
    id_sln.currentIndexChanged.connect(partial(update_tipo_ind_l, tipo_ind, tipo_ind_box, doc_ind, buttonBox, layer))
    button_doc.clicked.connect(partial(select_output_file, button_doc, doc_ind))
    doc_ind.textChanged.connect(partial(document, doc_ind, buttonBox))
    id_indln.textChanged.connect(partial(update_name_combobox, layer, tipo_ind_box, tipo_ind, codici_indagini))
    # help_button.clicked.connect(lambda: webbrowser.open("https://www.youtube.com/watch?v=aP2buSJk8iE&t=5s"))


def parametri_puntuali_form_init(dialog, layer, feature):
    codici_parametri = []
    codici_valori = []
    tipo_parpu_box = dialog.findChild(QComboBox, "tipo_parpu_box")
    tipo_parpu = dialog.findChild(QLineEdit, "tipo_parpu")
    id_indpu = dialog.findChild(QComboBox, "id_indpu")
    pkey_indpu = dialog.findChild(QLineEdit, "pkey_indpu")
    data_par = dialog.findChild(QDateTimeEdit, "data_par")
    prof_top = dialog.findChild(QLineEdit, "prof_top")
    prof_bot = dialog.findChild(QLineEdit, "prof_bot")
    quota_slm_top = dialog.findChild(QLineEdit, "quota_slm_top")
    quota_slm_bot = dialog.findChild(QLineEdit, "quota_slm_bot")
    valore = dialog.findChild(QLineEdit, "valore")
    valore_box = dialog.findChild(QComboBox, "valore_box")
    buttonBox = dialog.findChild(QDialogButtonBox, "buttonBox")
    today = QDate.currentDate()
    simbolo_val = dialog.findChild(QLabel, "simbolo_val")
    tab = dialog.findChild(QTabWidget, "tabWidget")
    # help_button = dialog.findChild(QPushButton, "help_button")

    nome_layer(tab, layer)
    valore.setEnabled(False)
    valore_box.setEnabled(False)
    data_par.setDate(today)
    buttonBox.setEnabled(False)
    define_param(codici_parametri, "vw_param_p")
    define_valore(codici_valori, valore_box)

    if id_indpu.currentText() != "":
        id_indpu.currentIndexChanged.connect(partial(update_param_p, codici_parametri, id_indpu, tipo_parpu_box))
        update_param_p(codici_parametri, id_indpu, tipo_parpu_box)
    else:
        id_indpu.currentIndexChanged.connect(partial(update_param_p, codici_parametri, id_indpu, tipo_parpu_box))

    update_pkey_par(id_indpu, pkey_indpu, "P")
    id_indpu.currentIndexChanged.connect(partial(update_pkey_par, id_indpu, pkey_indpu, "P"))
    # tab.currentChanged.connect(
    #     partial(refresh_variable_par_p, valore_box, valore, tipo_parpu_box, tipo_parpu, codici_parametri, id_indpu)
    # )
    tipo_parpu_box.currentIndexChanged.connect(partial(update_tipo_par, tipo_parpu, tipo_parpu_box))
    tipo_parpu_box.currentIndexChanged.connect(partial(disableButton, tipo_parpu_box, buttonBox))
    valore.textEdited.connect(partial(update_valore, valore))
    prof_top.textEdited.connect(partial(update_valore, prof_top))
    prof_bot.textEdited.connect(partial(update_valore, prof_bot))
    quota_slm_top.textEdited.connect(partial(update_valore_slm, quota_slm_top))
    quota_slm_bot.textEdited.connect(partial(update_valore_slm, quota_slm_bot))
    prof_bot.editingFinished.connect(partial(alert_spessore, prof_top, prof_bot, 0))
    prof_top.editingFinished.connect(partial(alert_spessore, prof_top, prof_bot, 0))
    quota_slm_top.editingFinished.connect(partial(alert_spessore, quota_slm_bot, quota_slm_top, 1))
    quota_slm_bot.editingFinished.connect(partial(alert_spessore, quota_slm_bot, quota_slm_top, 1))

    if layer.isEditable():
        tipo_parpu_box.currentIndexChanged.connect(
            partial(change_valore_p, tipo_parpu_box, valore, valore_box, simbolo_val, codici_parametri)
        )
        valore_box.currentIndexChanged.connect(partial(update_valore_text, valore, valore_box))
    else:
        tipo_parpu_box.currentIndexChanged.connect(
            partial(not_edit_change_p, tipo_parpu_box, tipo_parpu, valore_box, valore, simbolo_val, codici_parametri)
        )

    tipo_parpu_box.currentIndexChanged.connect(
        partial(update_name_combobox, layer, tipo_parpu_box, tipo_parpu, codici_parametri)
    )
    # help_button.clicked.connect(lambda: webbrowser.open("https://www.youtube.com/watch?v=-tjezNh1m1A&t=1s"))


def parametri_lineari_form_init(dialog, layer, feature):
    codici_parametri = []
    tipo_parln_box = dialog.findChild(QComboBox, "tipo_parln_box")
    tipo_parln = dialog.findChild(QLineEdit, "tipo_parln")
    id_indln = dialog.findChild(QComboBox, "id_indln")
    pkey_indln = dialog.findChild(QLineEdit, "pkey_indln")
    attend_mis = dialog.findChild(QComboBox, "attend_mis")
    data_par = dialog.findChild(QDateTimeEdit, "data_par")
    note_par = dialog.findChild(QTextEdit, "note_par")
    prof_bot = dialog.findChild(QLineEdit, "prof_bot")
    prof_top = dialog.findChild(QLineEdit, "prof_top")
    quota_slm_bot = dialog.findChild(QLineEdit, "quota_slm_bot")
    quota_slm_top = dialog.findChild(QLineEdit, "quota_slm_top")
    valore = dialog.findChild(QLineEdit, "valore")
    alert_text = dialog.findChild(QLabel, "alert_text")
    prof_top = dialog.findChild(QLineEdit, "prof_top")
    prof_bot = dialog.findChild(QLineEdit, "prof_bot")
    quota_slm_top = dialog.findChild(QLineEdit, "quota_slm_top")
    quota_slm_bot = dialog.findChild(QLineEdit, "quota_slm_bot")
    buttonBox = dialog.findChild(QDialogButtonBox, "buttonBox")
    today = QDate.currentDate()
    simbolo_val = dialog.findChild(QLabel, "simbolo_val")
    help_button = dialog.findChild(QPushButton, "help_button")

    data_par.setDate(today)
    buttonBox.setEnabled(False)
    alert_text.hide()
    attend_mis.addItem("")
    attend_mis.model().item(3).setEnabled(False)
    define_param(codici_parametri, "vw_param_l")

    if id_indln.currentText() != "":
        id_indln.currentIndexChanged.connect(
            partial(
                update_param_l,
                codici_parametri,
                id_indln,
                tipo_parln_box,
                attend_mis,
                note_par,
                prof_bot,
                prof_top,
                quota_slm_bot,
                quota_slm_top,
                valore,
                data_par,
                alert_text,
                buttonBox,
            )
        )
        update_param_l(
            codici_parametri,
            id_indln,
            tipo_parln_box,
            attend_mis,
            note_par,
            prof_bot,
            prof_top,
            quota_slm_bot,
            quota_slm_top,
            valore,
            data_par,
            alert_text,
            buttonBox,
        )
    else:
        id_indln.currentIndexChanged.connect(
            partial(
                update_param_l,
                codici_parametri,
                id_indln,
                tipo_parln_box,
                attend_mis,
                note_par,
                prof_bot,
                prof_top,
                quota_slm_bot,
                quota_slm_top,
                valore,
                data_par,
                alert_text,
                buttonBox,
            )
        )

    update_pkey_par(id_indln, pkey_indln, "L")
    id_indln.currentIndexChanged.connect(partial(update_pkey_par, id_indln, pkey_indln, "L"))
    # id_indln.currentIndexChanged.connect(
    #     partial(refresh_variable_par_l, valore, tipo_parln_box, tipo_parln, attend_mis, codici_parametri, id_indln)
    # )
    tipo_parln_box.currentIndexChanged.connect(partial(update_tipo_par, tipo_parln, tipo_parln_box))
    tipo_parln_box.currentIndexChanged.connect(partial(disableButton, tipo_parln_box, buttonBox))
    prof_top.textEdited.connect(partial(update_valore, prof_top))
    prof_bot.textEdited.connect(partial(update_valore, prof_bot))
    quota_slm_top.textEdited.connect(partial(update_valore_slm, quota_slm_top))
    quota_slm_bot.textEdited.connect(partial(update_valore_slm, quota_slm_bot))
    prof_bot.editingFinished.connect(partial(alert_spessore, prof_top, prof_bot, 0))
    prof_top.editingFinished.connect(partial(alert_spessore, prof_top, prof_bot, 0))
    quota_slm_top.editingFinished.connect(partial(alert_spessore, quota_slm_bot, quota_slm_top, 1))
    quota_slm_bot.editingFinished.connect(partial(alert_spessore, quota_slm_bot, quota_slm_top, 1))

    if layer.isEditable():
        tipo_parln_box.currentIndexChanged.connect(
            partial(change_valore_l, tipo_parln_box, simbolo_val, codici_parametri)
        )
    else:
        tipo_parln_box.currentIndexChanged.connect(
            partial(not_edit_change_l, tipo_parln, simbolo_val, codici_parametri)
        )

    tipo_parln_box.currentIndexChanged.connect(
        partial(update_name_combobox, layer, tipo_parln_box, tipo_parln, codici_parametri)
    )
    help_button.clicked.connect(lambda: webbrowser.open("https://www.youtube.com/watch?v=-tjezNh1m1A&t=1s"))


def curve_form_init(dialog, layer, feature):
    id_parpu = dialog.findChild(QComboBox, "id_parpu")
    pkey_parpu = dialog.findChild(QLineEdit, "pkey_parpu")
    buttonBox = dialog.findChild(QDialogButtonBox, "buttonBox")
    cond_curve = dialog.findChild(QLineEdit, "cond_curve")
    varx = dialog.findChild(QLineEdit, "varx")
    vary = dialog.findChild(QLineEdit, "vary")
    help_button = dialog.findChild(QPushButton, "help_button")

    buttonBox.setEnabled(False)
    cond_curve.textEdited.connect(partial(update_valore, cond_curve))
    varx.textEdited.connect(partial(update_valore, varx))
    vary.textEdited.connect(partial(update_valore, vary))

    if id_parpu.currentText() != "":
        id_parpu.currentIndexChanged.connect(partial(disableButton_curve, id_parpu, buttonBox))
        disableButton_curve(id_parpu, buttonBox)
    else:
        id_parpu.currentIndexChanged.connect(partial(disableButton_curve, id_parpu, buttonBox))

    update_pkey_par(id_parpu, pkey_parpu, "C")
    id_parpu.currentIndexChanged.connect(partial(update_pkey_par, id_parpu, pkey_parpu, "C"))

    help_button.clicked.connect(lambda: webbrowser.open("https://www.youtube.com/watch?v=EPRPjKvbUwE"))


def hvsr_form_init(dialog, layer, feature):
    id_indpu = dialog.findChild(QComboBox, "id_indpu")
    buttonBox = dialog.findChild(QDialogButtonBox, "buttonBox")
    qualita = dialog.findChild(QComboBox, "qualita")
    tipo = dialog.findChild(QComboBox, "tipo")
    f0 = dialog.findChild(QLineEdit, "f0")
    a0 = dialog.findChild(QLineEdit, "a0")
    f1 = dialog.findChild(QLineEdit, "f1")
    a1 = dialog.findChild(QLineEdit, "a1")
    f2 = dialog.findChild(QLineEdit, "f2")
    a2 = dialog.findChild(QLineEdit, "a2")
    f3 = dialog.findChild(QLineEdit, "f3")
    a3 = dialog.findChild(QLineEdit, "a3")
    fr = dialog.findChild(QLineEdit, "fr")
    ar = dialog.findChild(QLineEdit, "ar")
    help_button = dialog.findChild(QPushButton, "help_button")
    # doc_ind = dialog.findChild(QLineEdit, "doc_ind")

    buttonBox.setEnabled(False)
    # id_indpu.currentIndexChanged.connect(partial(refresh_variable_freq, qualita, tipo))
    f0.textEdited.connect(partial(update_valore, f0))
    a0.textEdited.connect(partial(update_valore, a0))
    f1.textEdited.connect(partial(update_valore, f1))
    a1.textEdited.connect(partial(update_valore, a1))
    f2.textEdited.connect(partial(update_valore, f2))
    a2.textEdited.connect(partial(update_valore, a2))
    f3.textEdited.connect(partial(update_valore, f3))
    a3.textEdited.connect(partial(update_valore, a3))
    fr.textEdited.connect(partial(update_valore, fr))
    ar.textEdited.connect(partial(update_valore, ar))

    if id_indpu.currentText() != "":
        id_indpu.currentIndexChanged.connect(partial(disableButton_freq, id_indpu, qualita, buttonBox))
        qualita.currentIndexChanged.connect(partial(disable_tipo, qualita, tipo))
        disableButton_freq(id_indpu, qualita, buttonBox)
    else:
        id_indpu.currentIndexChanged.connect(partial(disableButton_freq, id_indpu, qualita, buttonBox))
        qualita.currentIndexChanged.connect(partial(disable_tipo, qualita, tipo))

    help_button.clicked.connect(lambda: webbrowser.open("https://www.youtube.com/watch?v=PDjnJThqHE8"))


def update_pkey(value1, value2, param):
    value2.setText(value1.currentText().split(param)[-1])


def update_pkey_par(value1, value2, param):
    if param == "P":
        lista_var = [
            "CD",
            "CU",
            "UU",
            "ELL",
            "CR",
            "BE",
            "TSC",
            "TTC",
            "TC",
            "CPT",
            "CPTE",
            "CPTU",
            "SPT",
            "DMT",
            "VT",
            "DS",
            "DP",
            "DN",
            "DL",
            "PP",
            "PLT",
            "AL",
            "AIV",
            "S",
            "SS",
            "SD",
            "SDS",
            "SC",
            "SP",
            "SI",
            "PI",
            "T",
            "RGM",
            "TP",
            "GEO",
            "PA",
            "SP",
            "LF",
            "ST",
            "PE",
            "ERT",
            "SDMT",
            "SCPT",
            "DH",
            "CH",
            "UH",
            "HVSR",
            "ACC",
            "ESAC_SPAC",
            "GM",
            "AR",
            "SL",
        ]
        for x in lista_var:
            if x in value1.currentText():
                value2.setText(value1.currentText().split(x)[-1])
    elif param == "L":
        lista_var = ["STP", "SGE", "SEV", "SEO", "PR", "ERT", "SL", "SR", "RAD", "MASW", "SASW", "REMI", "FTAN"]
        for x in lista_var:
            if x in value1.currentText():
                value2.setText(value1.currentText().split(x)[-1])
    elif param == "C":
        lista_var = [
            "PV",
            "E1",
            "DR",
            "W",
            "IP",
            "GH",
            "SA",
            "LM",
            "AR",
            "OC",
            "C",
            "F1",
            "CU",
            "G",
            "RT",
            "IS",
            "II",
            "DV",
            "E",
            "CP",
            "QC",
            "FS",
            "U",
            "PT",
            "KR",
            "PTS",
            "SPT",
            "PTM",
            "PTL",
            "SIG",
            "PIA",
            "IL",
            "FDS",
            "KC",
            "KEQ",
            "L",
            "SG",
            "CAM",
            "INC",
            "PS",
            "JV",
            "FAG",
            "FRA",
            "LID",
            "FF",
            "FP",
            "K",
            "T",
            "RHO",
            "VS",
            "VP",
            "FR",
            "ACS",
            "ACB",
            "ACI",
            "ACO",
        ]
        for x in lista_var:
            if x in value1.currentText():
                value2.setText(value1.currentText().split(x)[-1])


def update_valore(value):
    value.setText(re.sub("[^0-9.]", "", value.text()))


def update_valore_slm(value):
    value.setText(re.sub("[^0-9.-]", "", value.text()))


def disableButton(input1, buttonBox):
    if input1.currentText() == "":
        buttonBox.setEnabled(False)
    else:
        buttonBox.setEnabled(True)


def document(doc_ind, buttonBox):
    if len(doc_ind.text()) < 5:
        buttonBox.setEnabled(False)
    else:
        buttonBox.setEnabled(True)


def select_output_file(button_doc, doc_ind):
    doc_ind.clear()
    filedirectory, __ = QFileDialog.getOpenFileName(button_doc, "Select output file ", "", "*.pdf")
    drive, path_and_file = os.path.splitdrive(filedirectory)
    path, filename = os.path.split(path_and_file)
    doc_ind.setText(filename)


def alert_spessore(value1, value2, value3):
    if value2.text() == "":
        pass
    elif value1.text() == "":
        pass
    else:
        if float(value1.text()) > float(value2.text()):
            if value3 == 0:
                QMessageBox.warning(
                    None, "WARNING!", "The value of the 'TOP' field is greater than the value of the 'BOTTOM' field!"
                )
            elif value3 == 1:
                QMessageBox.warning(
                    None, "WARNING!", "The value of the 'BOTTOM' field is greater than the value of the 'TOP' field!"
                )
            value1.setText("")
            value2.setText("")


def define_tipo_ind(nome_tab):
    codici_indagini_layer = QgsProject.instance().mapLayersByName(nome_tab)[0]

    codici_indagini = []
    for classe in codici_indagini_layer.getFeatures(QgsFeatureRequest().setFlags(QgsFeatureRequest.NoGeometry)):
        lista_indagini = [classe.attributes()[1], classe.attributes()[2], classe.attributes()[3]]
        codici_indagini.append(lista_indagini)
    return codici_indagini


def update_tipo_ind_p(tipo_ind, tipo_ind_box):
    TipoIndagine = str(tipo_ind_box.currentText().strip()).split(" - ")[0]
    tipo_ind.setText(TipoIndagine)


def disableButton_p(input1, input2, input3, buttonBox):
    check_campi = [input1.currentText(), input2.currentText(), input3.currentText()]
    check_value = []

    for x in check_campi:
        if len(x) > 0:
            value_campi = 1
            check_value.append(value_campi)
        else:
            value_campi = 0
            check_value.append(value_campi)

    campi = sum(check_value)
    if campi > 2:
        buttonBox.setEnabled(True)
    else:
        buttonBox.setEnabled(False)


def update_box_ind(parent_box, tipo_ind_box, codici_indagini):
    classe_ind_txt = parent_box.currentText()
    curIndex = str(classe_ind_txt.strip()).split(" - ")[0]

    tipo_ind_box.clear()
    tipo_ind_box.addItem("")
    tipo_ind_box.model().item(0).setEnabled(False)
    for row in codici_indagini:
        if row[0] == curIndex:
            tipo_ind_box.addItem(row[2])


def update_tipo_ind_l(tipo_ind, tipo_ind_box, doc_ind, buttonBox, layer):
    saved_tipo_ind = tipo_ind.text()
    selected_tipo_ind = str(tipo_ind_box.currentText().strip()).split(" - ")[0]

    if layer.isEditable():
        tipo_ind_box.setEnabled(True)
        if (saved_tipo_ind and selected_tipo_ind) or (not saved_tipo_ind and selected_tipo_ind):
            tipo_ind.setText(selected_tipo_ind)
    else:
        tipo_ind_box.setEnabled(False)

    doc_ind_required = tipo_ind.text() in ("ERT", "PR", "SEO", "SEV", "RAD", "SL", "SR", "SGE", "STP")

    if not tipo_ind.text() or (doc_ind_required and not doc_ind.text()):
        buttonBox.setEnabled(False)
    else:
        buttonBox.setEnabled(True)


def define_param(codici_parametri, nome_tabella):
    codici_parametri_layer = QgsProject.instance().mapLayersByName(nome_tabella)[0]
    for param in codici_parametri_layer.getFeatures(QgsFeatureRequest().setFlags(QgsFeatureRequest.NoGeometry)):
        lista_parametri = [param.attributes()[1], param.attributes()[2], param.attributes()[3], param.attributes()[4]]
        codici_parametri.append(lista_parametri)
    return codici_parametri


def update_tipo_par(tipo_par, tipo_par_box):
    if tipo_par_box.currentText() != "":
        TipoParametro = tipo_par_box.currentText().strip().split(" - ")[0]
        tipo_par.setText(TipoParametro)


def update_param_p(codici, id_indpu, tipo_parpu_box):
    curIndex = str(id_indpu.currentText().strip())[8:].strip("1234567890")

    tipo_parpu_box.clear()
    tipo_parpu_box.addItem("")
    tipo_parpu_box.model().item(0).setEnabled(False)
    for row in codici:
        if id_indpu.currentText()[6:7] == "P":
            if curIndex == str(row[0]):
                tipo_parpu_box.setEnabled(True)
                tipo_parpu_box.setCurrentIndex(0)
                tipo_parpu_box.addItem(row[2])


def define_valore(codici_valori, valore_box):
    valore_box.clear()
    valore_box.addItem("")
    codici_valori_layer = QgsProject.instance().mapLayersByName("vw_tipo_gt")[0]
    for val in codici_valori_layer.getFeatures(QgsFeatureRequest().setFlags(QgsFeatureRequest.NoGeometry)):
        valore_box.addItem(val.attributes()[2])


def update_valore_text(valore, valore_box):
    TipoValore = str(valore_box.currentText().strip()).split(" - ")[0]
    if not TipoValore == "":
        valore.setText(TipoValore)


def change_valore_p(tipo_parpu_box, valore, valore_box, simbolo_val, codici_parametri):
    if tipo_parpu_box.currentText() == "L - Litologia strato":
        valore.setEnabled(False)
        valore_box.setEnabled(True)
        valore_box.setCurrentIndex(0)
        valore.setText("")
        simbolo_val.setText("")
    else:
        valore.setEnabled(True)
        valore_box.setEnabled(False)
        valore_box.setCurrentIndex(0)
        valore.setText("")
        simbolo_val.setText("")
        for pu in codici_parametri:
            if tipo_parpu_box.currentText() == pu[2]:
                simbolo_val.setText(pu[3])


def not_edit_change_p(tipo_parpu_box, tipo_parpu, valore_box, valore, simbolo_val, codici_parametri):
    if tipo_parpu.text() == "L":
        valore_box.setEnabled(True)
        valore.setEnabled(False)
        valore_box.currentIndexChanged.connect(partial(update_valore_text, valore, valore_box))
        simbolo_val.setText("")
    else:
        valore_box.setEnabled(False)
        valore.setEnabled(True)
        simbolo_val.setText("")
        for pu in codici_parametri:
            if tipo_parpu.text() == pu[1]:
                simbolo_val.setText(pu[3])


def change_valore_l(tipo_parln_box, simbolo_val, codici_parametri):
    simbolo_val.setText("")
    for pu in codici_parametri:
        if tipo_parln_box.currentText() == pu[2]:
            simbolo_val.setText(pu[3])


def not_edit_change_l(tipo_parln, simbolo_val, codici_parametri):
    simbolo_val.setText("")
    for pu in codici_parametri:
        if tipo_parln.text() == pu[1]:
            simbolo_val.setText(pu[3])


def update_param_l(
    codici,
    id_indln,
    tipo_parln_box,
    attend_mis,
    note_par,
    prof_bot,
    prof_top,
    quota_slm_bot,
    quota_slm_top,
    valore,
    data_par,
    alert_text,
    buttonBox,
):
    curIndex = str(id_indln.currentText().strip())[8:].strip("1234567890")
    today = QDate.currentDate()

    tipo_parln_box.clear()
    tipo_parln_box.addItem("")
    tipo_parln_box.model().item(0).setEnabled(False)
    for row in codici:
        if id_indln.currentText()[6:7] == "L":
            if curIndex in ("ERT", "PR", "SEO", "SEV", "RAD", "SL", "SR", "SGE", "STP"):
                alert_text.show()
                buttonBox.setEnabled(False)
                tipo_parln_box.setEnabled(False)
                tipo_parln_box.setCurrentIndex(0)
                attend_mis.setEnabled(False)
                attend_mis.setCurrentIndex(4)
                data_par.setEnabled(False)
                data_par.setDate(today)
                note_par.setEnabled(False)
                note_par.setText("")
                prof_bot.setEnabled(False)
                prof_bot.setText("")
                prof_top.setEnabled(False)
                prof_top.setText("")
                quota_slm_bot.setEnabled(False)
                quota_slm_bot.setText("")
                quota_slm_top.setEnabled(False)
                quota_slm_top.setText("")
                valore.setEnabled(False)
                valore.setText("")
            else:
                if curIndex == str(row[0]):
                    alert_text.hide()
                    tipo_parln_box.setEnabled(True)
                    tipo_parln_box.setCurrentIndex(0)
                    tipo_parln_box.addItem(row[2])
                    attend_mis.setEnabled(True)
                    data_par.setEnabled(True)
                    data_par.setDate(today)
                    note_par.setEnabled(True)
                    prof_bot.setEnabled(True)
                    prof_top.setEnabled(True)
                    quota_slm_bot.setEnabled(True)
                    quota_slm_top.setEnabled(True)
                    valore.setEnabled(True)


def disableButton_curve(id_parpu, buttonBox):
    if len(id_parpu.currentText()) < 1:
        buttonBox.setEnabled(False)
    else:
        buttonBox.setEnabled(True)


def disableButton_freq(id_indpu, qualita, buttonBox):
    if len(id_indpu.currentText()) < 1:
        # if len(doc_ind.text()) < 1:
        buttonBox.setEnabled(False)
    else:
        if str(id_indpu.currentText().strip("1234567890P")) == "HVSR":
            buttonBox.setEnabled(True)
        else:
            buttonBox.setEnabled(False)


# def refresh_variable_ind(classe_ind, doc_ind):
#     QgsMessageLog.logMessage(str(classe_ind.currentText()))
#     QgsMessageLog.logMessage(str(doc_ind.text()))


# def refresh_variable_par_l(valore, tipo_par_box, tipo_par, attend_mis, codici_parametri, id_ind):
#     QgsMessageLog.logMessage(str(valore.text()))
#     QgsMessageLog.logMessage(str(tipo_par_box.currentText()))
#     QgsMessageLog.logMessage(str(tipo_par.text()))
#     QgsMessageLog.logMessage(str(attend_mis.currentText()))
#     QgsMessageLog.logMessage(str(codici_parametri))
#     QgsMessageLog.logMessage(str(id_ind.currentText()))


# def refresh_variable_par_p(valore_box, valore, tipo_par_box, tipo_par, codici_parametri, id_ind):
#     QgsMessageLog.logMessage(str(valore_box.currentText()))
#     QgsMessageLog.logMessage(str(valore.text()))
#     QgsMessageLog.logMessage(str(tipo_par_box.currentText()))
#     QgsMessageLog.logMessage(str(tipo_par.text()))
#     QgsMessageLog.logMessage(str(codici_parametri))
#     QgsMessageLog.logMessage(str(id_ind.currentText()))


# def refresh_variable_freq(qualita, tipo):
#     QgsMessageLog.logMessage(str(qualita.currentText()))
#     QgsMessageLog.logMessage(str(tipo.currentText()))


def nome_layer(tab, inlayer):
    # This is disabled because it was also being called by related layers,
    # effectively stopping editing in the main one.
    # stop_editing(l_name)
    if inlayer.isEditable():
        tab.setTabEnabled(1, False)
        try:
            tab.setTabEnabled(2, False)
        except:
            pass
    else:
        tab.setTabEnabled(1, True)
        try:
            tab.setTabEnabled(2, True)
        except:
            pass


def stop_editing(l_name):
    destLYR_1 = QgsProject.instance().mapLayersByName(l_name[0])[0]
    destLYR_2 = QgsProject.instance().mapLayersByName(l_name[1])[0]

    if destLYR_1.isEditable():
        destLYR_1.commitChanges()
    if destLYR_2.isEditable():
        destLYR_2.commitChanges()


def update_name_combobox(layer, tipo_box, tipo, codici):
    if not layer.isEditable():
        for ogg in codici:
            if tipo.text() == ogg[1]:
                tipo_box.setItemText(0, ogg[2])


def disable_tipo(qualita, tipo):
    if qualita.currentText() == "C - H/V scadente e di difficile interpretazione":
        tipo.setEnabled(False)
        tipo.setCurrentIndex(0)
    else:
        tipo.setEnabled(True)
