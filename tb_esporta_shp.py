# -*- coding: utf-8 -*-
#-------------------------------------------------------------------------------
# Name:		tb_esporta_shp.py
# Author:	  Tarquini E.
# Created:	 08-02-2018
#-------------------------------------------------------------------------------

import os
from PyQt4 import QtGui, uic

FORM_CLASS, _ = uic.loadUiType(os.path.join(
	os.path.dirname(__file__), 'tb_esporta_shp.ui'))


class esporta_shp(QtGui.QDialog, FORM_CLASS):
	def __init__(self, parent=None):
		"""Constructor."""
		super(esporta_shp, self).__init__(parent)
		self.setupUi(self)
