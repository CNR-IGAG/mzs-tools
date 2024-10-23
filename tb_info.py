# -*- coding: utf-8 -*-
# -------------------------------------------------------------------------------
# Name:		tb_info.py
# Author:	  Tarquini E.
# Created:	 08-02-2018
# -------------------------------------------------------------------------------

import os
import webbrowser

from qgis.PyQt import uic
from qgis.PyQt.QtWidgets import QDialog
from qgis.utils import iface


FORM_CLASS, _ = uic.loadUiType(os.path.join(os.path.dirname(__file__), "tb_info.ui"))


class info(QDialog, FORM_CLASS):
    def __init__(self, parent=None):
        """Constructor."""
        self.iface = iface
        super().__init__(parent)
        self.setupUi(self)
        self.plugin_dir = os.path.dirname(__file__)

    def help(self):
        # version info from plugin metadata
        version_installed = self.iface.pluginManagerInterface().pluginMetadata("MzSTools")["version_installed"]
        version_available = self.iface.pluginManagerInterface().pluginMetadata("MzSTools")["version_available"]

        label_text = self.label.text().replace("[[]]", version_installed)
        self.label.setText(label_text)

        if version_available:
            if version_installed > version_available:
                self.label_version_warning.setText(f"Local or development version detected: {version_installed}")
                self.label_version_warning.setStyleSheet("font-style: italic; font-weight: bold; color: red;")
            elif version_installed < version_available:
                self.label_version_warning.setText(f"New version available: {version_available}")
                self.label_version_warning.setStyleSheet("font-style: italic; font-weight: bold; color: green;")

        # self.pushButton_ita.clicked.connect(lambda: self.open_pdf(os.path.join(self.plugin_dir, "manuale.pdf")))
        self.pushButton_ita.clicked.connect(lambda: webbrowser.open("https://mzs-tools.readthedocs.io"))
        self.pushButton_www.clicked.connect(lambda: webbrowser.open("https://github.com/CNR-IGAG/mzs-tools/"))

        self.show()
        self.adjustSize()

    # def open_pdf(self, pdf_path):
    #     if sys.platform == "win32":
    #         os.startfile(pdf_path)
    #     else:
    #         opener = "open" if sys.platform == "darwin" else "xdg-open"
    #         subprocess.call([opener, pdf_path])
