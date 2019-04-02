# -*- coding: utf-8 -*-
#-------------------------------------------------------------------------------
# Name:		geoidr.py
# Author:	  Tarquini E.
# Created:	 24-11-2017
#-------------------------------------------------------------------------------

from qgis.core import *
from qgis.PyQt.QtWidgets import *
from PyQt4 import QtGui
import webbrowser


def geoidr(dialog, layer, feature):

	tipo_gi = dialog.findChild(QComboBox,"Tipo_gi")
	valore = dialog.findChild(QLineEdit,"Valore")
	valore2 = dialog.findChild(QLineEdit,"Valore2")
	alert_text = dialog.findChild(QLabel,"alert_text")
	help_button = dialog.findChild(QPushButton, "help_button")

	alert_text.hide()
	tipo_gi.currentIndexChanged.connect(lambda: update_tipo_gi(tipo_gi,valore,valore2,alert_text))
	valore.textEdited.connect(lambda: update_valore(valore, tipo_gi,alert_text))
	valore2.textEdited.connect(lambda: update_valore2(valore2, tipo_gi))
	help_button.clicked.connect(lambda: webbrowser.open('https://www.youtube.com/watch?v=dnJIjTNzQJQ&t=115s'))


def update_tipo_gi(tipo_gi,valore,valore2,alert_text):

	curIndex = str(tipo_gi.currentText().strip()).split(" - ")[0]

	if curIndex == "11":
		alert_text.show()
		valore.clear()
		valore2.clear()
		valore2.setEnabled(True)
	elif curIndex == "22":
		alert_text.hide()
		valore.clear()
		valore2.setText('')
		valore2.setEnabled(False)
	else:
		alert_text.hide()
		valore.clear()
		valore2.setText('')
		valore2.setEnabled(False)


def update_valore(value, tipo_gi,alert_text):

	try:
		valore = float(value.text())
		curIndex = str(tipo_gi.currentText().strip()).split(" - ")[0]
		alert_text.hide()

		if curIndex == "11":
			alert_text.show()
			if valore not in range(0,360):
				value.setText('')
		if curIndex == "22":
			alert_text.hide()
			if valore == 0:
				value.setText('')
		else:
			alert_text.hide()
	except:
		pass


def update_valore2(value, tipo_gi):

	try:
		valore = float(value.text())
		curIndex = str(tipo_gi.currentText().strip()).split(" - ")[0]
		if curIndex == "11":
			if valore not in range(0,90):
				value.setText('')
	except:
		pass