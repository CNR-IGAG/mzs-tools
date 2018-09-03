# -*- coding: utf-8 -*-
#-------------------------------------------------------------------------------
# Name:		tb_nuovo_progetto.py
# Author:	  Tarquini E.
# Created:	 08-02-2018
#-------------------------------------------------------------------------------

import os
from PyQt4 import QtGui, uic

FORM_CLASS, _ = uic.loadUiType(os.path.join(
	os.path.dirname(__file__), 'tb_nuovo_progetto.ui'))


class nuovo_progetto(QtGui.QDialog, FORM_CLASS):
	def __init__(self, parent=None):
		"""Constructor."""
		super(nuovo_progetto, self).__init__(parent)
		self.setupUi(self)
