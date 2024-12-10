from __future__ import absolute_import
import os
import webbrowser

from builtins import str
from qgis.PyQt import QtGui, uic
from qgis.PyQt.QtCore import *
from qgis.PyQt.QtGui import *
from qgis.PyQt.QtWidgets import *
from qgis.utils import *
from qgis.core import *
from qgis.gui import *
from . import constants
from .workers.import_worker import ImportWorker
from .setup_workers import setup_workers


FORM_CLASS, _ = uic.loadUiType(os.path.join(os.path.dirname(__file__), "tb_importa_shp.ui"))


class importa_shp(QDialog, FORM_CLASS):
    def __init__(self, parent=None):
        """Constructor."""
        self.iface = iface
        super().__init__(parent)
        self.setupUi(self)
        self.plugin_dir = os.path.dirname(__file__)
        self.logfile_path = None  # Will be set later

    def importa_prog(self):
        self.help_button.clicked.connect(lambda: webbrowser.open("https://www.youtube.com/watch?v=8zMFWIEGQJ0&t=4s"))
        self.dir_input.clear()
        self.tab_input.clear()
        self.alert_text.hide()
        self.button_box.setEnabled(False)
        self.dir_input.textChanged.connect(self.disableButton)
        self.tab_input.textChanged.connect(self.disableButton)

        self.show()
        self.adjustSize()
        result = self.exec_()
        if result:
            in_dir = self.dir_input.text()
            tab_dir = self.tab_input.text()
            if os.path.isdir(in_dir) and os.path.isdir(tab_dir):
                proj_abs_path = str(QgsProject.instance().readPath("./"))
                map_registry_instance = QgsProject.instance()

                # create import worker
                worker = ImportWorker(proj_abs_path, in_dir, tab_dir, map_registry_instance)

                # create import log file
                self.logfile_path = os.path.join(
                    proj_abs_path,
                    "Allegati",
                    "log",
                    str(time.strftime("%Y-%m-%d_%H-%M-%S", time.gmtime())) + "_import_log.txt",
                )
                log_file = open(self.logfile_path, "a")
                log_file.write("IMPORT REPORT:" + "\n---------------\n\n")

                # start import worker
                setup_workers().start_worker(
                    worker, self.iface, "Starting import task...", log_file, self.logfile_path
                )
            else:
                QMessageBox.warning(iface.mainWindow(), "WARNING!", "The selected directory does not exist!")

    def disableButton(self):
        if self.dir_input.text() and self.tab_input.text():
            self.button_box.setEnabled(True)
            # self.alert_text.hide()
        else:
            self.button_box.setEnabled(False)
            # self.alert_text.show()

        # conteggio = 0
        # check_campi = [self.dir_input.text(), self.tab_input.text()]
        # check_value = []

        # layers = QgsProject.instance().mapLayers().values()
        # for layer in layers:
        #     if layer.name() in constants.LISTA_LAYER:
        #         conteggio += 1

        # for x in check_campi:
        #     if len(x) > 0:
        #         value_campi = 1
        #         check_value.append(value_campi)
        #     else:
        #         value_campi = 0
        #         check_value.append(value_campi)
        # campi = sum(check_value)

        # if conteggio > 23 and campi > 1:
        #     self.button_box.setEnabled(True)
        #     self.alert_text.hide()
        # elif conteggio > 23:
        #     self.button_box.setEnabled(False)
        #     self.alert_text.hide()
        # else:
        #     self.button_box.setEnabled(False)
        #     self.alert_text.show()
