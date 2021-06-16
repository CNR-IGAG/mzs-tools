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

FORM_CLASS, _ = uic.loadUiType(os.path.join(os.path.dirname(__file__), "tb_info.ui"))


class info(QDialog, FORM_CLASS):
    def __init__(self, parent=None):
        """Constructor."""
        super(info, self).__init__(parent)
        self.setupUi(self)
        self.plugin_dir = os.path.dirname(__file__)

    def help(self):
        # self.pushButton_ita.clicked.connect(lambda: self.open_pdf(os.path.join(self.plugin_dir, "manuale.pdf")))

        self.pushButton_ita.clicked.connect(
            lambda: webbrowser.open("https://mzs-tools.readthedocs.io")
        )

        self.pushButton_www.clicked.connect(
            lambda: webbrowser.open("https://github.com/CNR-IGAG/mzs-tools/")
        )

        self.show()
        self.adjustSize()

    # def open_pdf(self, pdf_path):
    #     if sys.platform == "win32":
    #         os.startfile(pdf_path)
    #     else:
    #         opener = "open" if sys.platform == "darwin" else "xdg-open"
    #         subprocess.call([opener, pdf_path])
