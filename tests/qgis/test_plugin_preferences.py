import pytest
from qgis.core import QgsSettings

from mzs_tools.__about__ import __title__, __version__
from mzs_tools.plugin_utils.settings import PlgOptionsManager, PlgSettingsStructure


@pytest.fixture
def settings_manager():
    """Fixture to provide clean PlgOptionsManager for each test"""
    settings = QgsSettings()
    settings.beginGroup(__title__)
    settings.remove("")  # Clear all settings in group
    settings.endGroup()
    return PlgOptionsManager()


def test_get_plg_settings(settings_manager):
    """Test retrieving plugin settings"""
    settings = settings_manager.get_plg_settings()

    # Test return type
    assert isinstance(settings, PlgSettingsStructure)

    # Test default values
    assert settings.debug_mode is False
    assert settings.version == __version__
    assert settings.auto_advanced_editing is True


def test_get_value_from_key(settings_manager):
    """Test getting individual setting values"""
    # Test valid key
    assert settings_manager.get_value_from_key("debug_mode", default=False, exp_type=bool) is False

    # Test invalid key
    # assert settings_manager.get_value_from_key("invalid_key") is None

    # Test with explicit type
    debug_val = settings_manager.get_value_from_key("debug_mode", default=False, exp_type=bool)
    assert isinstance(debug_val, bool)


def test_set_value_from_key(settings_manager):
    """Test setting individual setting values"""
    # Test valid key
    assert settings_manager.set_value_from_key("debug_mode", True) is True
    assert settings_manager.get_value_from_key("debug_mode", exp_type=bool) is True

    # Test invalid key
    # assert settings_manager.set_value_from_key("invalid_key", True) is False


def test_save_from_object(settings_manager):
    """Test saving entire settings object"""
    test_settings = PlgSettingsStructure(debug_mode=True, auto_advanced_editing=False, version="test_version")

    # Save settings
    settings_manager.save_from_object(test_settings)

    # Verify saved settings
    loaded_settings = settings_manager.get_plg_settings()
    assert loaded_settings.debug_mode is True
    assert loaded_settings.auto_advanced_editing is False
    assert loaded_settings.version == "test_version"


def test_settings_persistence(settings_manager):
    """Test if settings persist between instances"""
    # Set a value
    settings_manager.set_value_from_key("debug_mode", True)

    # Create new instance
    new_manager = PlgOptionsManager()

    # Verify value persists
    assert new_manager.get_value_from_key("debug_mode", exp_type=bool) is True


@pytest.fixture(autouse=True)
def cleanup_settings():
    """Cleanup settings after each test"""
    yield
    settings = QgsSettings()
    settings.beginGroup(__title__)
    settings.remove("")
    settings.endGroup()
