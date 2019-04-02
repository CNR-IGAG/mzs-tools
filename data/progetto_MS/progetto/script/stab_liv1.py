# -*- coding: utf-8 -*-
#-------------------------------------------------------------------------------
# Name:		stab_liv1.py
# Author:	  Tarquini E.
# Created:	 22-09-2018
#-------------------------------------------------------------------------------

from qgis.core import *
from qgis.PyQt.QtWidgets import *
import webbrowser


def stab_liv1(dialog, layer, feature):

	help_button = dialog.findChild(QPushButton, "help_button")

	help_button.clicked.connect(lambda: webbrowser.open('https://www.youtube.com/watch?v=drs3COLtML8'))