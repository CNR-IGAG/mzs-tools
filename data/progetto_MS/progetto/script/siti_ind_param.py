# -*- coding: utf-8 -*-
#-------------------------------------------------------------------------------
# Name:		siti_ind_param.py
# Author:	  Tarquini E.
# Created:	 19-09-2018
#-------------------------------------------------------------------------------
#		QgsMessageLog.logMessage("test")

from PyQt4.QtCore import *
from PyQt4.QtGui import *
from qgis.utils import *
from qgis.gui import *
from qgis.core import *
from qgis.PyQt.QtWidgets import *
import processing, re, webbrowser


def siti_puntuali(dialog, layer, feature):

	sp_name = ["Indagini puntuali", "Parametri puntuali"]
	quota_slm = dialog.findChild(QLineEdit,"quota_slm")
	data_sito = dialog.findChild(QDateTimeEdit,"data_sito")
	today = QtCore.QDate.currentDate()
	tab = dialog.findChild(QTabWidget, "tabWidget")
	help_button = dialog.findChild(QPushButton, "help_button")

	nome_layer(tab,layer,sp_name)
	data_sito.setDate(today)
	quota_slm.textEdited.connect(lambda: update_valore(quota_slm))
	help_button.clicked.connect(lambda: webbrowser.open('https://www.youtube.com/watch?v=YpzmEt1Xzvs&t=0s&index=5&list=PLM5qQOkOkzgWH2VogqeQIDybylmE4P1TQ'))


def siti_lineari(dialog, layer, feature):

	sl_name = ["Indagini lineari", "Parametri lineari"]
	aquota = dialog.findChild(QLineEdit,"aquota")
	bquota = dialog.findChild(QLineEdit,"bquota")
	data_sito = dialog.findChild(QDateTimeEdit,"data_sito")
	today = QtCore.QDate.currentDate()
	tab = dialog.findChild(QTabWidget, "tabWidget")
	help_button = dialog.findChild(QPushButton, "help_button")

	nome_layer(tab,layer,sl_name)
	data_sito.setDate(today)
	aquota.textEdited.connect(lambda: update_valore(aquota))
	bquota.textEdited.connect(lambda: update_valore(bquota))
	help_button.clicked.connect(lambda: webbrowser.open('https://www.youtube.com/watch?v=YpzmEt1Xzvs&t=0s&index=5&list=PLM5qQOkOkzgWH2VogqeQIDybylmE4P1TQ'))


def indagini_puntuali(dialog, layer, feature):

	ip_name = ["Siti puntuali", "Parametri puntuali"]
	codici_indagini = []
	lista_indagini = []
	id_indpu = dialog.findChild(QLineEdit,"id_indpu")
	id_spu = dialog.findChild(QComboBox,"id_spu")
	tipo_ind_box = dialog.findChild(QComboBox,"tipo_ind_box")
	tipo_ind = dialog.findChild(QLineEdit,"tipo_ind")
	classe_ind = dialog.findChild(QComboBox,"classe_ind")
	doc_ind = dialog.findChild(QLineEdit,"doc_ind")
	button_doc = dialog.findChild(QPushButton,"pushButton")
	data_ind = dialog.findChild(QDateTimeEdit,"data_ind")
	prof_top = dialog.findChild(QLineEdit,"prof_top")
	prof_bot = dialog.findChild(QLineEdit,"prof_bot")
	quota_slm_top = dialog.findChild(QLineEdit,"quota_slm_top")
	quota_slm_bot = dialog.findChild(QLineEdit,"quota_slm_bot")
	buttonBox = dialog.findChild(QDialogButtonBox, "buttonBox")
	today = QtCore.QDate.currentDate()
	tab = dialog.findChild(QTabWidget, "tabWidget")
	help_button = dialog.findChild(QPushButton, "help_button")

	nome_layer(tab,layer,ip_name)
	data_ind.setDate(today)
	buttonBox.setEnabled(False)
	define_tipo_ind(codici_indagini,"vw_tipo_ind_p")
	tab.currentChanged.connect(lambda: refresh_variable_ind(classe_ind,doc_ind))
	classe_ind.currentIndexChanged.connect(lambda: update_box_ind(classe_ind.currentText(),tipo_ind_box,codici_indagini))
	tipo_ind_box.currentIndexChanged.connect(lambda: update_tipo_ind_p(tipo_ind, tipo_ind_box))
	button_doc.clicked.connect(lambda: select_output_file(button_doc,doc_ind))
	tipo_ind_box.currentIndexChanged.connect(lambda: disableButton_p(tipo_ind_box, classe_ind, id_spu, buttonBox))
	classe_ind.currentIndexChanged.connect(lambda: disableButton_p(tipo_ind_box, classe_ind, id_spu, buttonBox))
	id_spu.currentIndexChanged.connect(lambda: disableButton_p(tipo_ind_box, classe_ind, id_spu, buttonBox))
	prof_top.textEdited.connect(lambda: update_valore(prof_top))
	prof_bot.textEdited.connect(lambda: update_valore(prof_bot))
	quota_slm_top.textEdited.connect(lambda: update_valore_slm(quota_slm_top))
	quota_slm_bot.textEdited.connect(lambda: update_valore_slm(quota_slm_bot))
	prof_bot.editingFinished.connect(lambda: alert_spessore(prof_top, prof_bot, 0))
	prof_top.editingFinished.connect(lambda: alert_spessore(prof_top, prof_bot, 0))
	quota_slm_top.editingFinished.connect(lambda: alert_spessore(quota_slm_bot, quota_slm_top, 1))
	quota_slm_bot.editingFinished.connect(lambda: alert_spessore(quota_slm_bot, quota_slm_top, 1))
	id_indpu.textChanged.connect(lambda: update_name_combobox(layer, tipo_ind_box, tipo_ind, codici_indagini))
	help_button.clicked.connect(lambda: webbrowser.open('https://www.youtube.com/watch?v=aP2buSJk8iE&t=5s'))


def indagini_lineari(dialog, layer, feature):

	il_name = ["Siti lineari", "Parametri lineari"]
	codici_indagini = []
	lista_indagini = []
	id_indln = dialog.findChild(QLineEdit,"id_indln")
	id_sln = dialog.findChild(QComboBox,"id_sln")
	tipo_ind_box = dialog.findChild(QComboBox,"tipo_ind_box")
	tipo_ind = dialog.findChild(QLineEdit,"tipo_ind")
	classe_ind = dialog.findChild(QComboBox,"classe_ind")
	doc_ind = dialog.findChild(QLineEdit,"doc_ind")
	button_doc = dialog.findChild(QPushButton,"pushButton")
	data_ind = dialog.findChild(QDateTimeEdit,"data_ind")
	alert_text = dialog.findChild(QLabel,"alert_text")
	buttonBox = dialog.findChild(QDialogButtonBox, "buttonBox")
	today = QtCore.QDate.currentDate()
	tab = dialog.findChild(QTabWidget, "tabWidget")
	help_button = dialog.findChild(QPushButton, "help_button")

	nome_layer(tab,layer,il_name)
	data_ind.setDate(today)
	buttonBox.setEnabled(False)
	alert_text.hide()
	define_tipo_ind(codici_indagini,"vw_tipo_ind_l")
	tab.currentChanged.connect(lambda: refresh_variable_ind(classe_ind,doc_ind))
	classe_ind.currentIndexChanged.connect(lambda: update_box_ind(classe_ind.currentText(),tipo_ind_box,codici_indagini))
	tipo_ind_box.currentIndexChanged.connect(lambda: update_tipo_ind_l(tipo_ind, tipo_ind_box,alert_text,doc_ind,buttonBox, classe_ind, id_sln))
	classe_ind.currentIndexChanged.connect(lambda: update_tipo_ind_l(tipo_ind, tipo_ind_box,alert_text,doc_ind,buttonBox, classe_ind, id_sln))
	id_sln.currentIndexChanged.connect(lambda: update_tipo_ind_l(tipo_ind, tipo_ind_box,alert_text,doc_ind,buttonBox, classe_ind, id_sln))
	button_doc.clicked.connect(lambda: select_output_file(button_doc,doc_ind))
	doc_ind.textChanged.connect(lambda: document(doc_ind,buttonBox))
	id_indln.textChanged.connect(lambda: update_name_combobox(layer, tipo_ind_box, tipo_ind, codici_indagini))
	help_button.clicked.connect(lambda: webbrowser.open('https://www.youtube.com/watch?v=aP2buSJk8iE&t=5s'))


def parametri_puntuali(dialog, layer, feature):

	pp_name = ["Siti puntuali", "Indagini puntuali"]
	codici_parametri = []
	lista_parametri = []
	codici_valori = []
	tipo_parpu_box = dialog.findChild(QComboBox,"tipo_parpu_box")
	tipo_parpu = dialog.findChild(QLineEdit,"tipo_parpu")
	id_indpu = dialog.findChild(QComboBox,"id_indpu")
	data_par = dialog.findChild(QDateTimeEdit,"data_par")
	prof_top = dialog.findChild(QLineEdit,"prof_top")
	prof_bot = dialog.findChild(QLineEdit,"prof_bot")
	quota_slm_top = dialog.findChild(QLineEdit,"quota_slm_top")
	quota_slm_bot = dialog.findChild(QLineEdit,"quota_slm_bot")
	valore = dialog.findChild(QLineEdit,"valore")
	valore_box = dialog.findChild(QComboBox,"valore_box")
	buttonBox = dialog.findChild(QDialogButtonBox, "buttonBox")
	today = QtCore.QDate.currentDate()
	simbolo_val = dialog.findChild(QLabel,"simbolo_val")
	tab = dialog.findChild(QTabWidget, "tabWidget")
	help_button = dialog.findChild(QPushButton, "help_button")

	nome_layer(tab,layer,pp_name)
	valore.setEnabled(False)
	valore_box.setEnabled(False)
	data_par.setDate(today)
	buttonBox.setEnabled(False)
	define_param(codici_parametri,"vw_param_p")
	define_valore(codici_valori, valore_box)

	if id_indpu.currentText() != '':
		id_indpu.currentIndexChanged.connect(lambda: update_param_p(codici_parametri, id_indpu, tipo_parpu_box))
		update_param_p(codici_parametri, id_indpu, tipo_parpu_box)
	else:
		id_indpu.currentIndexChanged.connect(lambda: update_param_p(codici_parametri, id_indpu, tipo_parpu_box))

	tab.currentChanged.connect(lambda: refresh_variable_par_p(valore_box, valore, tipo_parpu_box, tipo_parpu, codici_parametri, id_indpu))
	tipo_parpu_box.currentIndexChanged.connect(lambda: update_tipo_par(tipo_parpu, tipo_parpu_box))
	tipo_parpu_box.currentIndexChanged.connect(lambda: disableButton(tipo_parpu_box, buttonBox))
	valore.textEdited.connect(lambda: update_valore(valore))
	prof_top.textEdited.connect(lambda: update_valore(prof_top))
	prof_bot.textEdited.connect(lambda: update_valore(prof_bot))
	quota_slm_top.textEdited.connect(lambda: update_valore_slm(quota_slm_top))
	quota_slm_bot.textEdited.connect(lambda: update_valore_slm(quota_slm_bot))
	prof_bot.editingFinished.connect(lambda: alert_spessore(prof_top, prof_bot, 0))
	prof_top.editingFinished.connect(lambda: alert_spessore(prof_top, prof_bot, 0))
	quota_slm_top.editingFinished.connect(lambda: alert_spessore(quota_slm_bot, quota_slm_top, 1))
	quota_slm_bot.editingFinished.connect(lambda: alert_spessore(quota_slm_bot, quota_slm_top, 1))

	if layer.isEditable():
		tipo_parpu_box.currentIndexChanged.connect(lambda: change_valore_p(tipo_parpu_box, valore, valore_box, simbolo_val, codici_parametri))
		valore_box.currentIndexChanged.connect(lambda: update_valore_text(valore, valore_box))
	else:
		tipo_parpu_box.currentIndexChanged.connect(lambda: not_edit_change_p(tipo_parpu_box, tipo_parpu, valore_box, valore, simbolo_val, codici_parametri))

	tipo_parpu_box.currentIndexChanged.connect(lambda: update_name_combobox(layer, tipo_parpu_box, tipo_parpu, codici_parametri))
	help_button.clicked.connect(lambda: webbrowser.open('https://www.youtube.com/watch?v=-tjezNh1m1A&t=1s'))


def parametri_lineari(dialog, layer, feature):

	codici_parametri = []
	lista_parametri = []
	tipo_parln_box = dialog.findChild(QComboBox,"tipo_parln_box")
	tipo_parln = dialog.findChild(QLineEdit,"tipo_parln")
	id_indln = dialog.findChild(QComboBox,"id_indln")
	attend_mis = dialog.findChild(QComboBox,"attend_mis")
	data_par = dialog.findChild(QDateTimeEdit,"data_par")
	note_par = dialog.findChild(QTextEdit,"note_par")
	prof_bot = dialog.findChild(QLineEdit,"prof_bot")
	prof_top = dialog.findChild(QLineEdit,"prof_top")
	quota_slm_bot = dialog.findChild(QLineEdit,"quota_slm_bot")
	quota_slm_top = dialog.findChild(QLineEdit,"quota_slm_top")
	valore = dialog.findChild(QLineEdit,"valore")
	alert_text = dialog.findChild(QLabel,"alert_text")
	prof_top = dialog.findChild(QLineEdit,"prof_top")
	prof_bot = dialog.findChild(QLineEdit,"prof_bot")
	quota_slm_top = dialog.findChild(QLineEdit,"quota_slm_top")
	quota_slm_bot = dialog.findChild(QLineEdit,"quota_slm_bot")
	buttonBox = dialog.findChild(QDialogButtonBox, "buttonBox")
	today = QtCore.QDate.currentDate()
	simbolo_val = dialog.findChild(QLabel,"simbolo_val")
	help_button = dialog.findChild(QPushButton, "help_button")

	data_par.setDate(today)
	buttonBox.setEnabled(False)
	alert_text.hide()
	attend_mis.addItem("")
	attend_mis.model().item(3).setEnabled(False)
	define_param(codici_parametri,"vw_param_l")

	if id_indln.currentText() != '':
		id_indln.currentIndexChanged.connect(lambda: update_param_l(codici_parametri, id_indln, tipo_parln_box, attend_mis, note_par, prof_bot, prof_top, quota_slm_bot, quota_slm_top, valore, data_par, alert_text, buttonBox))
		update_param_l(codici_parametri, id_indln, tipo_parln_box, attend_mis, note_par, prof_bot, prof_top, quota_slm_bot, quota_slm_top, valore, data_par, alert_text, buttonBox)
	else:
		id_indln.currentIndexChanged.connect(lambda: update_param_l(codici_parametri, id_indln, tipo_parln_box, attend_mis, note_par, prof_bot, prof_top, quota_slm_bot, quota_slm_top, valore, data_par, alert_text, buttonBox))

	id_indln.currentIndexChanged.connect(lambda: refresh_variable_par_l(valore, tipo_parln_box, tipo_parln, attend_mis, codici_parametri, id_indln))
	tipo_parln_box.currentIndexChanged.connect(lambda: update_tipo_par(tipo_parln, tipo_parln_box))
	tipo_parln_box.currentIndexChanged.connect(lambda: disableButton(tipo_parln_box, buttonBox))
	prof_top.textEdited.connect(lambda: update_valore(prof_top))
	prof_bot.textEdited.connect(lambda: update_valore(prof_bot))
	quota_slm_top.textEdited.connect(lambda: update_valore_slm(quota_slm_top))
	quota_slm_bot.textEdited.connect(lambda: update_valore_slm(quota_slm_bot))
	prof_bot.editingFinished.connect(lambda: alert_spessore(prof_top, prof_bot, 0))
	prof_top.editingFinished.connect(lambda: alert_spessore(prof_top, prof_bot, 0))
	quota_slm_top.editingFinished.connect(lambda: alert_spessore(quota_slm_bot, quota_slm_top, 1))
	quota_slm_bot.editingFinished.connect(lambda: alert_spessore(quota_slm_bot, quota_slm_top, 1))

	if layer.isEditable():
		tipo_parln_box.currentIndexChanged.connect(lambda: change_valore_l(tipo_parln_box, simbolo_val, codici_parametri))
	else:
		tipo_parln_box.currentIndexChanged.connect(lambda: not_edit_change_l(tipo_parln, simbolo_val, codici_parametri))

	tipo_parln_box.currentIndexChanged.connect(lambda: update_name_combobox(layer, tipo_parln_box, tipo_parln, codici_parametri))
	help_button.clicked.connect(lambda: webbrowser.open('https://www.youtube.com/watch?v=-tjezNh1m1A&t=1s'))


def curve(dialog, layer, feature):

	id_parpu = dialog.findChild(QComboBox,"id_parpu")
	buttonBox = dialog.findChild(QDialogButtonBox, "buttonBox")
	cond_curve = dialog.findChild(QLineEdit,"cond_curve")
	varx = dialog.findChild(QLineEdit,"varx")
	vary = dialog.findChild(QLineEdit,"vary")
	help_button = dialog.findChild(QPushButton, "help_button")

	buttonBox.setEnabled(False)
	cond_curve.textEdited.connect(lambda: update_valore(cond_curve))
	varx.textEdited.connect(lambda: update_valore(varx))
	vary.textEdited.connect(lambda: update_valore(vary))

	if id_parpu.currentText() != '':
		id_parpu.currentIndexChanged.connect(lambda: disableButton_curve(id_parpu, buttonBox))
		disableButton_curve(id_parpu, buttonBox)
	else:
		id_parpu.currentIndexChanged.connect(lambda: disableButton_curve(id_parpu, buttonBox))

	help_button.clicked.connect(lambda: webbrowser.open('https://www.youtube.com/watch?v=EPRPjKvbUwE'))


def freq(dialog, layer, feature):

	id_indpu = dialog.findChild(QComboBox,"id_indpu")
	buttonBox = dialog.findChild(QDialogButtonBox, "buttonBox")
	qualita = dialog.findChild(QComboBox,"qualita")
	tipo = dialog.findChild(QComboBox,"tipo")
	f0 = dialog.findChild(QLineEdit,"f0")
	a0 = dialog.findChild(QLineEdit,"a0")
	f1 = dialog.findChild(QLineEdit,"f1")
	a1 = dialog.findChild(QLineEdit,"a1")
	f2 = dialog.findChild(QLineEdit,"f2")
	a2 = dialog.findChild(QLineEdit,"a2")
	f3 = dialog.findChild(QLineEdit,"f3")
	a3 = dialog.findChild(QLineEdit,"a3")
	fr = dialog.findChild(QLineEdit,"fr")
	ar = dialog.findChild(QLineEdit,"ar")
	help_button = dialog.findChild(QPushButton, "help_button")

	buttonBox.setEnabled(False)
	id_indpu.currentIndexChanged.connect(lambda: refresh_variable_freq(qualita,tipo))
	f0.textEdited.connect(lambda: update_valore(f0))
	a0.textEdited.connect(lambda: update_valore(a0))
	f1.textEdited.connect(lambda: update_valore(f1))
	a1.textEdited.connect(lambda: update_valore(a1))
	f2.textEdited.connect(lambda: update_valore(f2))
	a2.textEdited.connect(lambda: update_valore(a2))
	f3.textEdited.connect(lambda: update_valore(f3))
	a3.textEdited.connect(lambda: update_valore(a3))
	fr.textEdited.connect(lambda: update_valore(fr))
	ar.textEdited.connect(lambda: update_valore(ar))

	if id_indpu.currentText() != '':
		id_indpu.currentIndexChanged.connect(lambda: disableButton_freq(id_indpu, qualita, buttonBox))
		qualita.currentIndexChanged.connect(lambda: disable_tipo(qualita,tipo))
		disableButton_freq(id_indpu, qualita, buttonBox)
	else:
		id_indpu.currentIndexChanged.connect(lambda: disableButton_freq(id_indpu, qualita, buttonBox))
		qualita.currentIndexChanged.connect(lambda: disable_tipo(qualita,tipo))

	help_button.clicked.connect(lambda: webbrowser.open('https://www.youtube.com/watch?v=PDjnJThqHE8'))


def update_valore(value):

	value.setText(re.sub('[^0-9.]','', value.text()))


def update_valore_slm(value):

	value.setText(re.sub('[^0-9.-]','', value.text()))


def disableButton(input1, buttonBox):

	if input1.currentText() == '':
		buttonBox.setEnabled(False)
	else:
		buttonBox.setEnabled(True)


def document(doc_ind,buttonBox):
	if len(doc_ind.text()) < 5:
		buttonBox.setEnabled(False)
	else:
		buttonBox.setEnabled(True)


def select_output_file(button_doc,doc_ind):

	doc_ind.clear()
	filedirectory = QFileDialog.getOpenFileName(button_doc, "Select output file ","", '*.pdf')
	drive, path_and_file = os.path.splitdrive(filedirectory)
	path, filename = os.path.split(path_and_file)
	doc_ind.setText(filename)


def alert_spessore(value1, value2, value3):

	if value2.text() == '':
		pass
	elif value1.text() == '':
		pass
	else:
		if float(value1.text()) > float(value2.text()):
			if value3 == 0:
				QMessageBox.warning(None, u'WARNING!', u"The value of the 'TOP' field is greater than the value of the 'BOTTOM' field!")
			elif value3 == 1:
				QMessageBox.warning(None, u'WARNING!', u"The value of the 'BOTTOM' field is greater than the value of the 'TOP' field!")
			value1.setText('')
			value2.setText('')


def define_tipo_ind(codici_indagini,nome_tab):

	codici_indagini_layer = QgsMapLayerRegistry.instance().mapLayersByName(nome_tab)[0]

	for classe in codici_indagini_layer.getFeatures(QgsFeatureRequest().setFlags(QgsFeatureRequest.NoGeometry)):
		lista_indagini=[classe.attributes()[1],classe.attributes()[2],classe.attributes()[3]]
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


def update_box_ind(classe_ind_txt,tipo_ind_box,codici_indagini):

	curIndex = str(classe_ind_txt.strip()).split(" - ")[0]

	tipo_ind_box.clear()
	tipo_ind_box.addItem("")
	tipo_ind_box.model().item(0).setEnabled(False)
	for row in codici_indagini:
		if row[0]==curIndex:
			tipo_ind_box.addItem(row[2])


def update_tipo_ind_l(tipo_ind, tipo_ind_box,alert_text,doc_ind,buttonBox, classe_ind, id_sln):

	TipoIndagine = str(tipo_ind_box.currentText().strip()).split(" - ")[0]

	check_campi = [tipo_ind_box.currentText(), classe_ind.currentText(), id_sln.currentText()]
	check_value = []

	for x in check_campi:
		if len(x) > 0:
			value_campi = 1
			check_value.append(value_campi)
		else:
			value_campi = 0
			check_value.append(value_campi)

	campi = sum(check_value)
	tipo_ind.setText(TipoIndagine)

	if campi > 2:
		if tipo_ind.text() in ("ERT","PR","SEO","SEV","RAD","SL","SR","SGE","STP"):
			alert_text.show()
			if len(doc_ind.text()) < 5:
				buttonBox.setEnabled(False)
			else:
				buttonBox.setEnabled(True)
		else:
			alert_text.hide()
			buttonBox.setEnabled(True)
	else:
		buttonBox.setEnabled(False)


def define_param(codici_parametri,nome_tabella):

	codici_parametri_layer = QgsMapLayerRegistry.instance().mapLayersByName(nome_tabella)[0]
	for param in codici_parametri_layer.getFeatures(QgsFeatureRequest().setFlags(QgsFeatureRequest.NoGeometry)):
		lista_parametri=[param.attributes()[1],param.attributes()[2],param.attributes()[3],param.attributes()[4]]
		codici_parametri.append(lista_parametri)
	return codici_parametri


def update_tipo_par(tipo_par, tipo_par_box):

	if tipo_par_box.currentText() != '':
		TipoParametro = tipo_par_box.currentText().strip().split(" - ")[0]
		tipo_par.setText(TipoParametro)


def update_param_p(codici, id_indpu, tipo_parpu_box):

	curIndex = str(id_indpu.currentText().strip())[8:].strip("1234567890")

	tipo_parpu_box.clear()
	tipo_parpu_box.addItem("")
	tipo_parpu_box.model().item(0).setEnabled(False)
	for row in codici:
		if id_indpu.currentText()[6:7] == 'P':
			if curIndex == str(row[0]):
				tipo_parpu_box.setEnabled(True)
				tipo_parpu_box.setCurrentIndex(0)
				tipo_parpu_box.addItem(row[2])


def define_valore(codici_valori, valore_box):

	valore_box.clear()
	valore_box.addItem("")
	codici_valori_layer = QgsMapLayerRegistry.instance().mapLayersByName("vw_tipo_gt")[0]
	for val in codici_valori_layer.getFeatures(QgsFeatureRequest().setFlags(QgsFeatureRequest.NoGeometry)):
		valore_box.addItem(val.attributes()[2])


def update_valore_text(valore, valore_box):

	TipoValore = str(valore_box.currentText().strip()).split(" - ")[0]
	if not TipoValore == '':
	   valore.setText(TipoValore)


def change_valore_p(tipo_parpu_box, valore, valore_box, simbolo_val, codici_parametri):

	if tipo_parpu_box.currentText() == 'L - Litologia strato':
		valore.setEnabled(False)
		valore_box.setEnabled(True)
		valore_box.setCurrentIndex(0)
		valore.setText('')
		simbolo_val.setText('')
	else:
		valore.setEnabled(True)
		valore_box.setEnabled(False)
		valore_box.setCurrentIndex(0)
		valore.setText('')
		simbolo_val.setText('')
		for pu in codici_parametri:
			if tipo_parpu_box.currentText() == pu[2]:
				simbolo_val.setText(pu[3])


def not_edit_change_p(tipo_parpu_box, tipo_parpu, valore_box, valore, simbolo_val, codici_parametri):

	if tipo_parpu.text() == 'L':
		valore_box.setEnabled(True)
		valore.setEnabled(False)
		valore_box.currentIndexChanged.connect(lambda: update_valore_text(valore, valore_box))
		simbolo_val.setText('')
	else:
		valore_box.setEnabled(False)
		valore.setEnabled(True)
		simbolo_val.setText('')
		for pu in codici_parametri:
			if tipo_parpu.text() == pu[1]:
				simbolo_val.setText(pu[3])


def change_valore_l(tipo_parln_box, simbolo_val, codici_parametri):

	simbolo_val.setText('')
	for pu in codici_parametri:
		if tipo_parln_box.currentText() == pu[2]:
			simbolo_val.setText(pu[3])


def not_edit_change_l(tipo_parln, simbolo_val, codici_parametri):

	simbolo_val.setText('')
	for pu in codici_parametri:
		if tipo_parln.text() == pu[1]:
			simbolo_val.setText(pu[3])


def update_param_l(codici, id_indln, tipo_parln_box, attend_mis, note_par, prof_bot, prof_top, quota_slm_bot, quota_slm_top, valore, data_par, alert_text, buttonBox):

	curIndex = str(id_indln.currentText().strip())[8:].strip("1234567890")
	today = QtCore.QDate.currentDate()

	tipo_parln_box.clear()
	tipo_parln_box.addItem("")
	tipo_parln_box.model().item(0).setEnabled(False)
	for row in codici:
		if id_indln.currentText()[6:7] == 'L':
			if curIndex in ("ERT","PR","SEO","SEV","RAD","SL","SR","SGE","STP"):
				alert_text.show()
				buttonBox.setEnabled(False)
				tipo_parln_box.setEnabled(False)
				tipo_parln_box.setCurrentIndex(0)
				attend_mis.setEnabled(False)
				attend_mis.setCurrentIndex(4)
				data_par.setEnabled(False)
				data_par.setDate(today)
				note_par.setEnabled(False)
				note_par.setText('')
				prof_bot.setEnabled(False)
				prof_bot.setText('')
				prof_top.setEnabled(False)
				prof_top.setText('')
				quota_slm_bot.setEnabled(False)
				quota_slm_bot.setText('')
				quota_slm_top.setEnabled(False)
				quota_slm_top.setText('')
				valore.setEnabled(False)
				valore.setText('')
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


def disableButton_curve(id_parpu,buttonBox):

	if len(id_parpu.currentText()) < 1:
		buttonBox.setEnabled(False)
	else:
		buttonBox.setEnabled(True)


def disableButton_freq(id_indpu,qualita,buttonBox):

	if len(id_indpu.currentText()) < 1:
		if len(doc_ind.text()) < 1:
			buttonBox.setEnabled(False)
	else:
		if str(id_indpu.currentText().strip("1234567890P")) == 'HVSR':
			buttonBox.setEnabled(True)
		else:
			buttonBox.setEnabled(False)


def refresh_variable_ind(classe_ind,doc_ind):

	QgsMessageLog.logMessage(str(classe_ind.currentText()))
	QgsMessageLog.logMessage(str(doc_ind.text()))


def refresh_variable_par_l(valore, tipo_par_box, tipo_par, attend_mis, codici_parametri, id_ind):

	QgsMessageLog.logMessage(str(valore.text()))
	QgsMessageLog.logMessage(str(tipo_par_box.currentText()))
	QgsMessageLog.logMessage(str(tipo_par.text()))
	QgsMessageLog.logMessage(str(attend_mis.currentText()))
	QgsMessageLog.logMessage(str(codici_parametri))
	QgsMessageLog.logMessage(str(id_ind.currentText()))


def refresh_variable_par_p(valore_box, valore, tipo_par_box, tipo_par, codici_parametri, id_ind):

	QgsMessageLog.logMessage(str(valore_box.currentText()))
	QgsMessageLog.logMessage(str(valore.text()))
	QgsMessageLog.logMessage(str(tipo_par_box.currentText()))
	QgsMessageLog.logMessage(str(tipo_par.text()))
	QgsMessageLog.logMessage(str(codici_parametri))
	QgsMessageLog.logMessage(str(id_ind.currentText()))

def refresh_variable_freq(qualita,tipo):

	QgsMessageLog.logMessage(str(qualita.currentText()))
	QgsMessageLog.logMessage(str(tipo.currentText()))


def nome_layer(tab,inlayer,l_name):

	stop_editing(l_name)
	if inlayer.isEditable():
		tab.setTabEnabled (1, False)
		try:
			tab.setTabEnabled (2, False)
		except:
			pass
	else:
		tab.setTabEnabled (1, True)
		try:
			tab.setTabEnabled (2, True)
		except:
			pass


def stop_editing(l_name):

	destLYR_1 = QgsMapLayerRegistry.instance().mapLayersByName(l_name[0])[0]
	destLYR_2 = QgsMapLayerRegistry.instance().mapLayersByName(l_name[1])[0]

	if destLYR_1.isEditable():
		destLYR_1.commitChanges()
	if destLYR_2.isEditable():
		destLYR_2.commitChanges()


def update_name_combobox(layer, tipo_box, tipo, codici):

	if not layer.isEditable():
		for ogg in codici:
			if tipo.text() == ogg[1]:
				tipo_box.setItemText(0,ogg[2])


def disable_tipo(qualita,tipo):

	if qualita.currentText() == "C - H/V scadente e di difficile interpretazione":
		tipo.setEnabled(False)
		tipo.setCurrentIndex(0)
	else:
		tipo.setEnabled(True)