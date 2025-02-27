import re
from functools import partial
from pathlib import Path
from typing import Dict

import pyplugin_installer
from packaging.version import parse
from qgis.core import QgsApplication
from qgis.PyQt import uic
from qgis.PyQt.Qt import QUrl
from qgis.PyQt.QtCore import QCoreApplication, QSettings, Qt
from qgis.PyQt.QtGui import QDesktopServices, QIcon, QPixmap
from qgis.PyQt.QtWidgets import QDialog
from qgis.utils import iface

from ..__about__ import (
    DIR_PLUGIN_ROOT,
    __email__,
    __summary__,
    __summary_it__,
    __uri_docs__,
    __uri_repository__,
    __version__,
)
from ..plugin_utils.logging import MzSToolsLogger
from ..plugin_utils.misc import skip_file_not_found

FORM_CLASS, _ = uic.loadUiType(Path(__file__).parent / f"{Path(__file__).stem}.ui")


class PluginInfo(QDialog, FORM_CLASS):
    def __init__(self, parent=None):
        """Constructor."""
        super().__init__(parent)
        self.log = MzSToolsLogger().log
        self.setupUi(self)

        self.button_manual.setIcon(QIcon(QgsApplication.getThemeIcon("/mActionHelpContents.svg")))
        self.button_manual.clicked.connect(partial(QDesktopServices.openUrl, QUrl(f"{__uri_docs__}")))

        github_icon = QPixmap(str(DIR_PLUGIN_ROOT / "resources" / "img" / "github-mark.png"))
        self.button_github.setIcon(QIcon(github_icon))
        self.button_github.clicked.connect(partial(QDesktopServices.openUrl, QUrl(f"{__uri_repository__}")))

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

    @skip_file_not_found
    def load_and_set_text(self, filename, label):
        """Load text from a file, process it, and set it to a label."""
        with open(DIR_PLUGIN_ROOT / filename, "r") as f:
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
        plugin_metadata = {}
        try:
            # iface.pluginManagerInterface() and pyplugin_installer.instance() are not available during tests
            plugin_metadata = iface.pluginManagerInterface().pluginMetadata(plugin_name)
            if not plugin_metadata:
                # Try refreshing the plugin manager cache
                pyplugin_installer.instance().reloadAndExportData()
                plugin_metadata = iface.pluginManagerInterface().pluginMetadata(plugin_name)
        except Exception as e:
            self.log(f"Error fetching plugin metadata: {e}", log_level=1)
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


# def _run():
#     from qgis.core import QgsApplication

#     app = QgsApplication([], True)
#     app.initQgis()
#     widget = PluginInfo()
#     widget.show()
#     app.exec_()


# if __name__ == "__main__":
#     _run()
