# -*- coding: utf-8 -*-
#-------------------------------------------------------------------------------
# Name:		stab_liv2.py
# Author:	  Tarquini E.
# Created:	 24-11-2017
#-------------------------------------------------------------------------------

from qgis.core import *
from qgis.PyQt.QtWidgets import *
import re, webbrowser


def stab_liv2(dialog, layer, feature):

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


def update_valore(value):

	value.setText(re.sub('[^0-9.]','', value.text()))