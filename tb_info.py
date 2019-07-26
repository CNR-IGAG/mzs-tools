# -*- coding: utf-8 -*-
#-------------------------------------------------------------------------------
# Name:		tb_info.py
# Author:	  Tarquini E.
# Created:	 08-02-2018
#-------------------------------------------------------------------------------

from PyQt4 import QtGui, uic
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from qgis.utils import *
from qgis.core import *
from qgis.gui import *
import os, sys, webbrowser

FORM_CLASS, _ = uic.loadUiType(os.path.join(
	os.path.dirname(__file__), 'tb_info.ui'))


class info(QtGui.QDialog, FORM_CLASS):

	def __init__(self, parent=None):
		"""Constructor."""
		super(info, self).__init__(parent)
		self.setupUi(self)
		self.plugin_dir = os.path.dirname(__file__)

	def help(self):
		self.pushButton_ita.clicked.connect(lambda: self.open_pdf(self.plugin_dir + os.sep + "manuale.pdf"))
		#self.pushButton_eng.clicked.connect(lambda: self.open_pdf(self.plugin_dir + os.sep + "manual.pdf"))
		self.pushButton_www.clicked.connect(lambda: webbrowser.open('https://github.com/CNR-IGAG/mzs-tools/wiki/MzS-Tools'))

		self.show()

	def open_pdf(self, pdf_path):
		os.startfile(pdf_path)