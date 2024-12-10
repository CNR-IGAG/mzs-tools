import configparser
import webbrowser
from pathlib import Path

from qgis.PyQt import uic
from qgis.PyQt.QtCore import QStandardPaths
from qgis.PyQt.QtWidgets import QDialog

from .utils import AUTO_ADVANCED_EDITING_KEY, SETTINGS_SECTION, ensure_config_directory, get_settings

FORM_CLASS, _ = uic.loadUiType(Path(__file__).parent / "tb_settings.ui")


class MzSToolsSettings(QDialog, FORM_CLASS):
    def __init__(self, parent=None):
        """Constructor."""
        super(MzSToolsSettings, self).__init__(parent)
        self.setupUi(self)
        self.plugin_dir = Path(__file__).parent
        self.config_file = Path(QStandardPaths.writableLocation(QStandardPaths.AppConfigLocation)) / "mzs_tools.ini"
        self.config = configparser.ConfigParser()

        # Ensure the configuration directory exists
        ensure_config_directory()

        # Load settings
        self.load_settings()

        # Connect the save button
        self.saveButton.clicked.connect(self.save_settings)

        self.helpButtonAutoEditing.clicked.connect(
            lambda: webbrowser.open(
                "https://mzs-tools.readthedocs.io/it/latest/plugin/editing.html#controllo-delle-sovrapposizioni-tra-layer-diversi"
            )
        )

    def load_settings(self):
        """Load settings from the .ini file."""
        settings = get_settings()
        self.advancedEditingCheckbox.setChecked(settings.get(AUTO_ADVANCED_EDITING_KEY, True))

    def save_settings(self):
        """Save settings to the .ini file."""
        self.config[SETTINGS_SECTION] = {AUTO_ADVANCED_EDITING_KEY: self.advancedEditingCheckbox.isChecked()}
        with self.config_file.open("w") as configfile:
            self.config.write(configfile)

        self.accept()
