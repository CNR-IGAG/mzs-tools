import importlib
import os
from unittest.mock import MagicMock

import pytest

GUI_TIMEOUT_DEFAULT = 2000  # milliseconds


@pytest.fixture(scope="session")
def gui_timeout(pytestconfig):
    """
    Determine timeout in milliseconds for GUI tests based on environment settings and pytest options.
    """
    is_gui_disabled = pytestconfig.getoption("qgis_disable_gui") or os.environ.get("QT_QPA_PLATFORM") == "offscreen"
    timeout_secs = os.environ.get("GUI_TIMEOUT")
    if timeout_secs is not None:
        try:
            timeout_secs = int(timeout_secs)
        except (TypeError, ValueError):
            timeout_secs = None

    return 0 if is_gui_disabled else (timeout_secs * 1000 if timeout_secs is not None else GUI_TIMEOUT_DEFAULT)


@pytest.fixture()
def plugin(qgis_iface, monkeypatch):
    """Fixture that imports the plugin main class lazily and returns the class."""

    # mock qgis_iface.projectRead signal
    # Mock or MagicMock would require the use of yield and del to clean up the mock
    # qgis_iface.projectRead = MagicMock()
    # use monkeypatch instead to avoid side effects on other tests
    monkeypatch.setattr(qgis_iface, "projectRead", MagicMock(), raising=False)

    mod = importlib.import_module("mzs_tools.mzs_tools")
    return mod.MzSTools


def pytest_collection_modifyitems(session, config, items):
    """Modify the order of collected tests to run unit tests first, then integration, then e2e.

    This hook reorders test items based on their location in the test directory structure:
    - tests/unit/ → executed first
    - tests/integration/ → executed second
    - tests/e2e/ → executed last
    """
    unit = []
    integration = []
    e2e = []
    other = []

    for item in items:
        # Use the normalized path string to determine test category
        test_path = str(item.fspath).replace("\\", "/")

        if "/tests/unit/" in test_path:
            unit.append(item)
        elif "/tests/integration/" in test_path:
            integration.append(item)
        elif "/tests/e2e/" in test_path:
            e2e.append(item)
        else:
            other.append(item)

    # Reorder: unit first, then integration, then e2e, then any other tests
    items[:] = unit + integration + e2e + other
