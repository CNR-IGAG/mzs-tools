# -*- coding: utf-8 -*-
#-------------------------------------------------------------------------------
# Name:		tb_importa_progetto.py
# Author:	  Tarquini E.
# Created:	 08-02-2018
#-------------------------------------------------------------------------------

import os
from PyQt4 import QtGui, uic

FORM_CLASS, _ = uic.loadUiType(os.path.join(
	os.path.dirname(__file__), 'tb_importa_progetto.ui'))


class importa_progetto(QtGui.QDialog, FORM_CLASS):
	def __init__(self, parent=None):
		"""Constructor."""
		super(importa_progetto, self).__init__(parent)
		self.setupUi(self)
