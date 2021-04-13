# -*- coding: utf-8 -*-
# -------------------------------------------------------------------------------
# Name:		tb_info.py
# Author:	  Tarquini E.
# Created:	 08-02-2018
# -------------------------------------------------------------------------------

from qgis.PyQt import QtGui, uic
from qgis.PyQt.QtCore import *
from qgis.PyQt.QtGui import *
from qgis.PyQt.QtWidgets import *
from qgis.utils import *
from qgis.core import *
from qgis.gui import *
import os
import sys
import webbrowser

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'tb_info.ui'))


class info(QDialog, FORM_CLASS):

    def __init__(self, parent=None):
        """Constructor."""
        super(info, self).__init__(parent)
        self.setupUi(self)
        self.plugin_dir = os.path.dirname(__file__)

    def help(self):
        self.pushButton_ita.clicked.connect(
            lambda: self.open_pdf(self.plugin_dir, "manuale.pdf"))
        #self.pushButton_eng.clicked.connect(lambda: self.open_pdf(self.plugin_dir, "manual.pdf"))
        self.pushButton_www.clicked.connect(lambda: webbrowser.open(
            'https://github.com/CNR-IGAG/mzs-tools/wiki/MzS-Tools'))

        self.show()
        self.adjustSize()

    def open_pdf(self, pdf_path):
        os.startfile(pdf_path)
