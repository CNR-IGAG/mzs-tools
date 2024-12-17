import os
import re
import webbrowser
from functools import wraps
from typing import Dict

import pyplugin_installer
from packaging.version import parse
from qgis.PyQt import uic
from qgis.PyQt.QtCore import QCoreApplication, QSettings, Qt
from qgis.PyQt.QtWidgets import QDialog
from qgis.utils import iface

from mzs_tools.utils import qgs_log

from .__about__ import __email__, __summary__, __summary_it__, __version__

FORM_CLASS, _ = uic.loadUiType(os.path.join(os.path.dirname(__file__), "tb_info.ui"))


class PluginInfo(QDialog, FORM_CLASS):
    def __init__(self, parent=None):
        """Constructor."""
        super().__init__(parent)
        self.setupUi(self)
        self.plugin_dir = os.path.dirname(__file__)
        self.button_manual.clicked.connect(lambda: webbrowser.open("https://mzs-tools.readthedocs.io"))
        self.button_github.clicked.connect(lambda: webbrowser.open("https://github.com/CNR-IGAG/mzs-tools/"))

        try:
            locale = QSettings().value("locale/userLocale", "en", type=str)[0:2]
        except Exception:
            locale = "en"
        self.label_info.setTextFormat(Qt.RichText)
        self.label_info.setText(
            self.label_info.text()
            .replace(
                "[[Abstract]]",
                __summary_it__.replace("\n", "<br>") if locale == "it" else __summary__.replace("\n", "<br>"),
            )
            .replace("[[Contacts]]", f"<b>{__email__}</b>")
        )

        # https://doc.qt.io/qt-6/qt.html#TextFormat-enum
        self.markdown_available = hasattr(Qt, "MarkdownText")  # "MarkdownText" in dir(Qt)
        if self.markdown_available:
            self.label_credits.setTextFormat(Qt.MarkdownText)
            self.label_changelog.setTextFormat(Qt.MarkdownText)

        self.load_and_set_text("LICENSE", self.label_license)
        self.load_and_set_text("CREDITS.md", self.label_credits)
        self.load_and_set_text("CHANGELOG.md", self.label_changelog)

        self.buttonBox.rejected.connect(self.reject)

    def skip_file_not_found(func):
        """Decorator to catch FileNotFoundError exceptions."""

        @wraps(func)
        def _wrapper(*args, **kwargs):
            try:
                func(*args, **kwargs)
            except FileNotFoundError as e:
                qgs_log(f"File not found: {e}", level="warning")

        return _wrapper

    @skip_file_not_found
    def load_and_set_text(self, filename, label):
        """Load text from a file, process it, and set it to a label."""
        with open(os.path.join(self.plugin_dir, filename), "r") as f:
            text = f.read()
            if self.markdown_available:
                text = self.replace_headings(text)
            label.setText(text)

    def replace_headings(self, text):
        """Replace heading levels in markdown text."""
        text = re.sub(r"^### ", "##### ", text, flags=re.MULTILINE)
        text = re.sub(r"^## ", "#### ", text, flags=re.MULTILINE)
        text = re.sub(r"^# ", "### ", text, flags=re.MULTILINE)
        return text

    def showEvent(self, e):
        plugin_metadata = self.get_plugin_metadata("MzSTools")
        version_installed = __version__
        version_available = plugin_metadata.get("version_available", version_installed)

        self.label_version.setText(self.label_version.text().replace("[[]]", version_installed))
        self.update_version_warning(version_installed, version_available)

    def get_plugin_metadata(self, plugin_name: str) -> Dict[str, str]:
        """Fetch plugin metadata."""
        plugin_metadata = iface.pluginManagerInterface().pluginMetadata(plugin_name)
        if not plugin_metadata:
            # Try refreshing the plugin manager cache
            pyplugin_installer.instance().reloadAndExportData()
            plugin_metadata = iface.pluginManagerInterface().pluginMetadata(plugin_name)
        return plugin_metadata or {}

    def update_version_warning(self, version_installed: str, version_available: str):
        """Update the version warning label."""
        if parse(version_installed).is_prerelease or (version_installed > version_available):
            self.label_version_warning.setText(self.tr("(Local or development version)"))
            self.label_version_warning.setStyleSheet("font-style: italic; font-weight: bold; color: red;")
        elif version_installed < version_available:
            self.label_version_warning.setText(self.tr(f"New version available: {version_available}"))
            self.label_version_warning.setStyleSheet("font-style: italic; font-weight: bold; color: green;")
        else:
            self.label_version_warning.setVisible(False)

    def tr(self, message: str) -> str:
        return QCoreApplication.translate(self.__class__.__name__, message)
