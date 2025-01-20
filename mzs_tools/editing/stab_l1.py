# -*- coding: utf-8 -*-
# -------------------------------------------------------------------------------
# Name:		stab_liv1.py
# Author:	  Tarquini E.
# Created:	 22-09-2018
# -------------------------------------------------------------------------------

import webbrowser
from functools import partial

from qgis.core import *
from qgis.PyQt.QtWidgets import *


def stab_l1_form_init(dialog, layer, feature):
    help_button = dialog.findChild(QPushButton, "help_button")

    help_button.clicked.connect(partial(webbrowser.open, "https://www.youtube.com/watch?v=drs3COLtML8"))
