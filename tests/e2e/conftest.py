import pytest

from mzs_tools.core.mzs_project_manager import MzSProjectManager


@pytest.fixture
def prj_manager(qgis_new_project):
    """Fixture that provides a fresh MzSProjectManager instance.

    Resets the singleton instance before each test to ensure clean state.
    Also ensures a clean QGIS project instance.
    """
    # Reset singleton instance
    MzSProjectManager._instance = None
    manager = MzSProjectManager.instance()
    yield manager
    # Cleanup after test - clear the QGIS project and reset manager
    from qgis.core import QgsProject

    QgsProject.instance().clear()
    if manager.db_manager:
        manager.db_manager.disconnect()
    manager.db_manager = None
    manager.is_mzs_project = False
    manager.project_path = None
    manager.db_path = None
    MzSProjectManager._instance = None
