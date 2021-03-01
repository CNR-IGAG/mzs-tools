from __future__ import absolute_import
from builtins import str
# -*- coding: utf-8 -*-
#-------------------------------------------------------------------------------
# Name:		tb_esporta_shp.py
# Author:	  Tarquini E.
# Created:	 08-02-2018
#-------------------------------------------------------------------------------

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
import shutil
import zipfile
import sqlite3
from . import constants
from .workers.export_worker import ExportWorker
from .setup_workers import setup_workers


FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'tb_esporta_shp.ui'))


class esporta_shp(QDialog, FORM_CLASS):

    def __init__(self, parent=None):
        """Constructor."""
        self.iface = iface
        super(esporta_shp, self).__init__(parent)
        self.setupUi(self)
        self.plugin_dir = os.path.dirname(__file__)

    def esporta_prog(self):
        self.help_button.clicked.connect(lambda: webbrowser.open(
            'https://www.youtube.com/watch?v=dYcMZSpu6HA&t=2s'))
        self.dir_output.clear()
        self.alert_text.hide()
        self.button_box.setEnabled(False)
        self.dir_output.textChanged.connect(self.disableButton)

        self.show()
        result = self.exec_()
        if result:

            try:
                in_dir = QgsProject.instance().readPath("./")
                out_dir = self.dir_output.text()
                if os.path.exists(out_dir):

                    # create export worker
                    worker = ExportWorker(in_dir, out_dir, self.plugin_dir)

                    # create export log file
                    logfile_path = in_dir + os.sep + "allegati" + os.sep + "log" + os.sep + \
                        str(time.strftime("%Y-%m-%d_%H-%M-%S",
                                          time.gmtime())) + "_export_log.txt"
                    log_file = open(logfile_path, 'a')
                    log_file.write("EXPORT REPORT:" + "\n---------------\n\n")

                    # start export worker
                    setup_workers().start_worker(worker, self.iface,
                                                 'Starting export task...', log_file)

                else:
                    QMessageBox.warning(
                        None, u'WARNING!', u"The selected directory does not exist!")

            except Exception as z:
                QMessageBox.critical(
                    None, u'ERROR!', u'Error:\n"' + str(z) + '"')

    def disableButton(self):
        conteggio = 0
        check_campi = [self.dir_output.text()]
        check_value = []

        layers = self.iface.legendInterface().layers()
        for layer in layers:
            if layer.name() in constants.LISTA_LAYER:
                conteggio += 1

        for x in check_campi:
            if len(x) > 0:
                value_campi = 1
                check_value.append(value_campi)
            else:
                value_campi = 0
                check_value.append(value_campi)
        campi = sum(check_value)

        if conteggio > 23 and campi > 0:
            self.button_box.setEnabled(True)
            self.alert_text.hide()
        elif conteggio > 23 and campi == 0:
            self.button_box.setEnabled(False)
            self.alert_text.hide()
        else:
            self.button_box.setEnabled(False)
            self.alert_text.show()
