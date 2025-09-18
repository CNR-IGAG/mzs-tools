import re
from functools import partial
from pathlib import Path
from typing import Dict

try:
    import pyplugin_installer
except ImportError:
    pyplugin_installer = None

from packaging.version import parse
from qgis.core import QgsApplication
from qgis.PyQt import uic
from qgis.PyQt.QtCore import QCoreApplication, QSettings, Qt, QUrl
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
        self.label_info.setTextFormat(Qt.TextFormat.RichText)
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
            self.label_credits.setTextFormat(Qt.TextFormat.MarkdownText)
            self.label_changelog.setTextFormat(Qt.TextFormat.MarkdownText)

        self.load_and_set_text("LICENSE", self.label_license)
        self.load_and_set_text("CREDITS.md", self.label_credits)
        self.load_and_set_text("CHANGELOG.md", self.label_changelog)

        self.buttonBox.rejected.connect(self.reject)

    def load_and_set_text(self, filename: str, label) -> None:
        """Load text from a file, process it, and set it to a label.

        Args:
            filename: Name of the file to load from plugin root directory
            label: QLabel widget to set the text on
        """
        try:
            file_path = DIR_PLUGIN_ROOT / filename
            if not file_path.exists():
                self.log(f"File not found: {file_path}", log_level=2)
                label.setText(self.tr(f"File not found: {filename}"))
                return

            with open(file_path, "r", encoding="utf-8") as f:
                text = f.read()
                if self.markdown_available and filename.endswith(".md"):
                    text = self.replace_headings(text)
                label.setText(text)

        except UnicodeDecodeError as e:
            self.log(f"Encoding error reading {filename}: {e}", log_level=1)
            label.setText(self.tr(f"Error reading file: {filename}"))
        except Exception as e:
            self.log(f"Error loading {filename}: {e}", log_level=1)
            label.setText(self.tr(f"Error loading file: {filename}"))

    def replace_headings(self, text: str) -> str:
        """Replace heading levels in markdown text to make them smaller for dialog display.

        Args:
            text: Original markdown text

        Returns:
            Modified markdown text with adjusted heading levels
        """
        # Convert headings to smaller levels for dialog display
        # H1 -> H3, H2 -> H4, H3 -> H5
        text = re.sub(r"^### ", "##### ", text, flags=re.MULTILINE)
        text = re.sub(r"^## ", "#### ", text, flags=re.MULTILINE)
        text = re.sub(r"^# ", "### ", text, flags=re.MULTILINE)
        return text

    def showEvent(self, e) -> None:
        """Handle show event to update version information."""
        try:
            plugin_metadata = self.get_plugin_metadata("MzSTools")
            version_installed = __version__
            version_available = plugin_metadata.get("version_available", version_installed) or version_installed
            self.label_version.setText(self.label_version.text().replace("[[]]", version_installed))
            self.update_version_warning(version_installed, version_available)
        except Exception as e:
            self.log(f"Error updating version label: {e}", log_level=1)
            self.label_version_warning.setVisible(False)

    def get_plugin_metadata(self, plugin_name: str) -> Dict[str, str]:
        """Fetch plugin metadata from QGIS plugin manager.

        Args:
            plugin_name: Name of the plugin to fetch metadata for

        Returns:
            Dictionary containing plugin metadata, empty if not found
        """
        plugin_metadata = {}
        try:
            # Skip if interface is not available (during tests)
            if not hasattr(iface, "pluginManagerInterface") or iface is None:
                return plugin_metadata

            # First attempt to get metadata
            plugin_metadata = iface.pluginManagerInterface().pluginMetadata(plugin_name)  # type: ignore

            # If empty, try refreshing the cache and retry once
            if not plugin_metadata:
                self.log(f"Plugin metadata empty for {plugin_name}, refreshing cache", log_level=1)
                if pyplugin_installer is not None:
                    pyplugin_installer.instance().reloadAndExportData()
                plugin_metadata = iface.pluginManagerInterface().pluginMetadata(plugin_name)  # type: ignore

        except AttributeError as e:
            self.log(f"Plugin manager interface not available: {e}", log_level=2)
        except Exception as e:
            self.log(f"Error fetching plugin metadata for {plugin_name}: {e}", log_level=1)

        return plugin_metadata or {}

    def update_version_warning(self, version_installed: str, version_available: str) -> None:
        """Update the version warning label based on version comparison.

        Args:
            version_installed: Currently installed version
            version_available: Available version from repository
        """
        try:
            parsed_version_installed = parse(version_installed)
            parsed_version_available = parse(version_available)

            # Ensure the warning label is visible by default
            self.label_version_warning.setVisible(True)

            if parsed_version_installed.is_prerelease or (parsed_version_installed > parsed_version_available):
                self.label_version_warning.setText(self.tr("(Local or development version)"))
                self.label_version_warning.setStyleSheet("font-style: italic; font-weight: bold; color: red;")
            elif parsed_version_installed < parsed_version_available:
                warning_text = self.tr("New version available: {version}").format(version=version_available)
                self.label_version_warning.setText(warning_text)
                self.label_version_warning.setStyleSheet("font-style: italic; font-weight: bold; color: green;")
            else:
                # Versions are equal - hide the warning
                self.label_version_warning.setVisible(False)
        except Exception as e:
            self.log(f"Error parsing versions: {e}", log_level=1)
            self.label_version_warning.setVisible(False)

    def tr(self, message: str) -> str:
        return QCoreApplication.translate(self.__class__.__name__, message)
