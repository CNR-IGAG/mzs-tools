# -*- coding: utf-8 -*-
#-------------------------------------------------------------------------------
# Name:		tb_copia_ms.py
# Author:	  Tarquini E.
# Created:	 08-02-2018
#-------------------------------------------------------------------------------

import os
from PyQt4 import QtGui, uic

FORM_CLASS, _ = uic.loadUiType(os.path.join(
	os.path.dirname(__file__), 'tb_copia_ms.ui'))


class copia_ms(QtGui.QDialog, FORM_CLASS):
	def __init__(self, parent=None):
		"""Constructor."""
		super(copia_ms, self).__init__(parent)
		self.setupUi(self)
