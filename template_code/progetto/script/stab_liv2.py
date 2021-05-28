# -*- coding: utf-8 -*-
# -------------------------------------------------------------------------------
# Name:		stab_liv2.py
# Author:	  Tarquini E.
# Created:	 24-11-2017
# -------------------------------------------------------------------------------

import re
import webbrowser
from functools import partial

from qgis.core import *
from qgis.PyQt.QtWidgets import *


def stab_liv2(dialog, layer, feature):

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
    help_button = dialog.findChild(QPushButton, "help_button")

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
    help_button.clicked.connect(
        partial(webbrowser.open, 'https://www.youtube.com/watch?v=drs3COLtML8'))


def update_valore(value):

    value.setText(re.sub('[^0-9.]', '', value.text()))
