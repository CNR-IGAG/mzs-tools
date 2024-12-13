import os
import webbrowser
from typing import Dict

import pyplugin_installer
from qgis.PyQt import uic
from qgis.PyQt.QtWidgets import QDialog
from qgis.utils import iface

from .__about__ import __version__

FORM_CLASS, _ = uic.loadUiType(os.path.join(os.path.dirname(__file__), "tb_info.ui"))


class PluginInfo(QDialog, FORM_CLASS):
    def __init__(self, parent=None):
        """Constructor."""
        self.iface = iface
        super().__init__(parent)
        self.setupUi(self)
        self.plugin_dir = os.path.dirname(__file__)
        self.pushButton_ita.clicked.connect(lambda: webbrowser.open("https://mzs-tools.readthedocs.io"))
        self.pushButton_www.clicked.connect(lambda: webbrowser.open("https://github.com/CNR-IGAG/mzs-tools/"))

    def help(self):
        plugin_metadata = self.get_plugin_metadata("MzSTools")
        version_installed = plugin_metadata.get("version_installed", __version__)
        if not version_installed:
            version_installed = __version__
        version_available = plugin_metadata.get("version_available", version_installed)

        self.update_label(version_installed)
        self.update_version_warning(version_installed, version_available)

        self.show()
        self.adjustSize()

    def get_plugin_metadata(self, plugin_name: str) -> Dict[str, str]:
        """Fetch plugin metadata."""
        plugin_metadata = self.iface.pluginManagerInterface().pluginMetadata(plugin_name)
        if not plugin_metadata:
            # Try refreshing the plugin manager cache
            pyplugin_installer.instance().reloadAndExportData()
            plugin_metadata = self.iface.pluginManagerInterface().pluginMetadata(plugin_name)
        return plugin_metadata or {}

    def update_label(self, version_installed: str):
        """Update the label with the installed version."""
        label_text = self.label.text().replace("[[]]", version_installed)
        self.label.setText(label_text)

    def update_version_warning(self, version_installed: str, version_available: str):
        """Update the version warning label."""
        if version_installed > version_available:
            self.label_version_warning.setText(f"Local or development version detected: {version_installed}")
            self.label_version_warning.setStyleSheet("font-style: italic; font-weight: bold; color: red;")
        elif version_installed < version_available:
            self.label_version_warning.setText(f"New version available: {version_available}")
            self.label_version_warning.setStyleSheet("font-style: italic; font-weight: bold; color: green;")
