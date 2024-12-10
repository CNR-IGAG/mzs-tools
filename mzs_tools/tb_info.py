import os
import webbrowser

import pyplugin_installer
from qgis.PyQt import uic
from qgis.PyQt.QtWidgets import QDialog
from qgis.utils import iface

from .utils import plugin_version_from_metadata_file

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
        plugin_metadata = self.iface.pluginManagerInterface().pluginMetadata("MzSTools")
        if not plugin_metadata:
            # try refreshing the plugin manager cache
            pyplugin_installer.instance().reloadAndExportData()

        plugin_metadata = self.iface.pluginManagerInterface().pluginMetadata("MzSTools")
        if plugin_metadata:
            version_installed = plugin_metadata["version_installed"]
            version_available = plugin_metadata["version_available"]
        else:
            version_installed = plugin_version_from_metadata_file() or ""
            version_available = version_installed

        label_text = self.label.text().replace("[[]]", version_installed)
        self.label.setText(label_text)

        if version_available:
            if version_installed > version_available:
                self.label_version_warning.setText(f"Local or development version detected: {version_installed}")
                self.label_version_warning.setStyleSheet("font-style: italic; font-weight: bold; color: red;")
            elif version_installed < version_available:
                self.label_version_warning.setText(f"New version available: {version_available}")
                self.label_version_warning.setStyleSheet("font-style: italic; font-weight: bold; color: green;")

        self.pushButton_ita.clicked.connect(lambda: webbrowser.open("https://mzs-tools.readthedocs.io"))
        self.pushButton_www.clicked.connect(lambda: webbrowser.open("https://github.com/CNR-IGAG/mzs-tools/"))

        self.show()
        self.adjustSize()
