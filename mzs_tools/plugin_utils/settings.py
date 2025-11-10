"""
Plugin settings.
Based on https://gitlab.com/Oslandia/qgis/template-qgis-plugin
"""

from dataclasses import asdict, dataclass, fields

from qgis.core import QgsSettings

from ..__about__ import __title__, __version__
from ..plugin_utils import logging


@dataclass
class PlgSettingsStructure:
    """Plugin settings structure and defaults values."""

    # global
    debug_mode: bool = False
    auto_advanced_editing: bool = True
    java_home_path: str = ""
    version: str = __version__


class PlgOptionsManager:
    @staticmethod
    def get_plg_settings() -> PlgSettingsStructure:
        """Load and return plugin settings as a dictionary. \
        Useful to get user preferences across plugin logic.

        :return: plugin settings
        :rtype: PlgSettingsStructure
        """
        # get dataclass fields definition
        settings_fields = fields(PlgSettingsStructure)

        # retrieve settings from QGIS/Qt
        settings = QgsSettings()
        settings.beginGroup(__title__)

        # map settings values to preferences object
        li_settings_values = []
        for i in settings_fields:
            li_settings_values.append(settings.value(key=i.name, defaultValue=i.default, type=i.type))

        # instanciate new settings object
        options = PlgSettingsStructure(*li_settings_values)

        settings.endGroup()

        return options

    @staticmethod
    def get_value_from_key(key: str, default=None, exp_type=None):
        """Load and return plugin settings as a dictionary. \
        Useful to get user preferences across plugin logic.

        :return: plugin settings value matching key
        """
        if not hasattr(PlgSettingsStructure, key):
            field_names = [field.name for field in fields(PlgSettingsStructure)]
            logging.MzSToolsLogger.log(
                message="Bad settings key. Must be one of: {}".format(",".join(field_names)),
                log_level=1,
            )
            return None

        settings = QgsSettings()
        settings.beginGroup(__title__)

        try:
            out_value = settings.value(key=key, defaultValue=default, type=exp_type)
        except Exception as err:
            logging.MzSToolsLogger.log(message="Error occurred trying to get settings: {}.Trace: {}".format(key, err))
            out_value = None

        settings.endGroup()

        return out_value

    @classmethod
    def set_value_from_key(cls, key: str, value) -> bool:
        """Set plugin QSettings value using the key.

        :param key: QSettings key
        :type key: str
        :param value: value to set
        :type value: depending on the settings
        :return: operation status
        :rtype: bool
        """
        if not hasattr(PlgSettingsStructure, key):
            field_names = [field.name for field in fields(PlgSettingsStructure)]
            logging.MzSToolsLogger.log(
                message="Bad settings key. Must be one of: {}".format(",".join(field_names)),
                log_level=2,
            )
            return False

        settings = QgsSettings()
        settings.beginGroup(__title__)

        try:
            settings.setValue(key, value)
            out_value = True
        except Exception as err:
            logging.MzSToolsLogger.log(message="Error occurred trying to set settings: {}.Trace: {}".format(key, err))
            out_value = False

        settings.endGroup()

        return out_value

    @classmethod
    def save_from_object(cls, plugin_settings_obj: PlgSettingsStructure):
        """Load and return plugin settings as a dictionary. \
        Useful to get user preferences across plugin logic.

        :return: plugin settings value matching key
        """
        settings = QgsSettings()
        settings.beginGroup(__title__)

        for k, v in asdict(plugin_settings_obj).items():
            cls.set_value_from_key(k, v)

        settings.endGroup()
