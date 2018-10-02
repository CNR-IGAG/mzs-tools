# -*- coding: utf-8 -*-
#-------------------------------------------------------------------------------
# Name:		tb_wait.py
# Author:	  Tarquini E.
# Created:	 27-09-2018
#-------------------------------------------------------------------------------

import os
from PyQt4 import QtGui, uic

FORM_CLASS, _ = uic.loadUiType(os.path.join(
	os.path.dirname(__file__), 'tb_wait.ui'))


class wait(QtGui.QDialog, FORM_CLASS):
	def __init__(self, parent=None):
		"""Constructor."""
		super(wait, self).__init__(parent)
		self.setupUi(self)
