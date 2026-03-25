# -----------------------------------------------------------------------------
# Copyright (C) 2018-2026, CNR-IGAG LabGIS <labgis@igag.cnr.it>
# This file is part of MzS Tools.
#
# MzS Tools is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# MzS Tools is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with MzS Tools.  If not, see <https://www.gnu.org/licenses/>.
# -----------------------------------------------------------------------------

import importlib
import os
import traceback
import warnings
import zipfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest

# Set QGIS prefix path from environment variable if defined
# if os.environ.get("QGIS_PREFIX_PATH"):
#     from qgis.core import QgsApplication

#     QgsApplication.setPrefixPath(os.environ.get("QGIS_PREFIX_PATH"), True)


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


@pytest.fixture(autouse=True)
def patch_qgis_error_dialogs(monkeypatch):
    """
    Patch QGIS error dialogs to prevent modal dialogs from appearing during tests.

    This fixture is automatically applied to all tests and patches qgis.utils functions
    to print exceptions to console instead of showing modal dialogs.
    Based on: https://github.com/qgis/QGIS/blob/master/.docker/qgis_resources/test_runner/qgis_startup.py
    """
    try:
        from qgis import utils
        from qgis.core import Qgis

        def _showException(type, value, tb, msg, messagebar=False, level=Qgis.MessageLevel.Warning):  # type: ignore
            """Print exception instead of showing a dialog."""
            print(msg)
            logmessage = ""
            for s in traceback.format_exception(type, value, tb):
                # Handle both str (Python 3) and bytes (potential legacy)
                logmessage += s.decode("utf-8", "replace") if hasattr(s, "decode") else s  # type: ignore
            print(logmessage)

        def _open_stack_dialog(type, value, tb, msg, pop_error=True):  # type: ignore
            """Print exception instead of opening stack trace dialog."""
            print(msg)

        monkeypatch.setattr(utils, "showException", _showException)
        monkeypatch.setattr(utils, "open_stack_dialog", _open_stack_dialog)
    except ImportError:
        # QGIS not available, skip patching
        pass


@pytest.fixture(autouse=True)
def disable_layers_added_handler(monkeypatch):
    """Disconnect _on_layers_added from layersAdded signal for all tests.

    The duplicate-layer detection handler must not run during tests: project reads and
    internal layer additions would fire the signal and erroneously try to remove layers
    (or call iface.messageBar().pushWarning() which the mock does not support).

    PyQt captures the bound method at connect() time, so patching the class or instance
    after connection does not help. Instead we replace _on_layers_added on the class
    *before* it is connected (covering resets/new instances), and also wrap init_manager
    so the signal is immediately disconnected after each call inside a test.
    """
    try:
        import contextlib

        from qgis.core import QgsProject

        from mzs_tools.core.mzs_project_manager import MzSProjectManager

        noop = lambda *args, **kwargs: None  # noqa: E731

        # Replace on the class so any future lookup or new instance gets the no-op.
        monkeypatch.setattr(MzSProjectManager, "_on_layers_added", noop)

        # Wrap init_manager so that after every call the (possibly already-connected)
        # bound method pointing to the real function is disconnected.
        original_init_manager = MzSProjectManager.init_manager

        def _patched_init_manager(self):
            result = original_init_manager(self)
            with contextlib.suppress(RuntimeError, TypeError):
                QgsProject.instance().layersAdded.disconnect(self._on_layers_added)
            return result

        monkeypatch.setattr(MzSProjectManager, "init_manager", _patched_init_manager)

    except ImportError:
        pass


@pytest.fixture()
def plugin(qgis_iface, monkeypatch):
    """Fixture that imports the plugin main class lazily and returns the class."""
    # mock qgis_iface.projectRead signal
    monkeypatch.setattr(qgis_iface, "projectRead", MagicMock(), raising=False)
    mod = importlib.import_module("mzs_tools.mzs_tools")
    return mod.MzSTools


@pytest.fixture
def prj_manager(qgis_new_project):
    """Fixture that provides a fresh MzSProjectManager instance.

    Resets the singleton instance before each test to ensure clean state.
    Also ensures a clean QGIS project instance.
    """
    from mzs_tools.core.mzs_project_manager import MzSProjectManager

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


@pytest.fixture
def base_project_path_current(tmp_path) -> Path:
    """Fixture that extracts a sample MzS Tools project for testing (current version)."""
    from mzs_tools.__about__ import __base_version__

    project_archive = Path(__file__).parent / "data" / "mzs_projects" / f"057001_Accumoli_v{__base_version__}_new.zip"
    if not project_archive.exists():
        pytest.skip("Sample MzS Tools project archive not available")
    with zipfile.ZipFile(project_archive, "r") as zip_ref:
        zip_ref.extractall(tmp_path)
    project_dir = tmp_path / "057001_Accumoli"
    return project_dir


@pytest.fixture
def base_project_path_current_imported(tmp_path) -> Path:
    """Fixture that extracts a sample MzS Tools project for testing (current version)."""
    from mzs_tools.__about__ import __base_version__

    project_archive = (
        Path(__file__).parent / "data" / "mzs_projects" / f"057001_Accumoli_v{__base_version__}_imported.zip"
    )
    if not project_archive.exists():
        pytest.skip("Sample MzS Tools project archive not available")
    with zipfile.ZipFile(project_archive, "r") as zip_ref:
        zip_ref.extractall(tmp_path)
    project_dir = tmp_path / "057001_Accumoli"
    return project_dir


@pytest.fixture
def base_project_path_2_0_5(tmp_path) -> Path:
    """Fixture that extracts a sample MzS Tools project for testing."""
    project_archive = Path(__file__).parent / "data" / "mzs_projects" / "057001_Accumoli_v2.0.5_new.zip"
    if not project_archive.exists():
        pytest.skip("Sample MzS Tools project archive not available")
    with zipfile.ZipFile(project_archive, "r") as zip_ref:
        zip_ref.extractall(tmp_path)
    project_dir = tmp_path / "057001_Accumoli"
    return project_dir


@pytest.fixture
def base_project_path_2_0_0(tmp_path) -> Path:
    """Fixture that extracts a sample MzS Tools project for testing."""
    project_archive = Path(__file__).parent / "data" / "mzs_projects" / "057001_Accumoli_v2.0.0_new.zip"
    if not project_archive.exists():
        pytest.skip("Sample MzS Tools project archive not available")
    with zipfile.ZipFile(project_archive, "r") as zip_ref:
        zip_ref.extractall(tmp_path)
    project_dir = tmp_path / "057001_Accumoli"
    return project_dir


@pytest.fixture
def base_project_path_1_9_4(tmp_path) -> Path:
    """Fixture that extracts a sample MzS Tools project for testing."""
    project_archive = Path(__file__).parent / "data" / "mzs_projects" / "057001_Accumoli_v1.9.4_new.zip"
    if not project_archive.exists():
        pytest.skip("Sample MzS Tools project archive not available")
    with zipfile.ZipFile(project_archive, "r") as zip_ref:
        zip_ref.extractall(tmp_path)
    project_dir = tmp_path / "057001_Accumoli"
    return project_dir


@pytest.fixture
def base_project_path_1_9_4_imported(tmp_path) -> Path:
    """Fixture that extracts a sample MzS Tools project for testing."""
    project_archive = Path(__file__).parent / "data" / "mzs_projects" / "057001_Accumoli_v1.9.4_imported.zip"
    if not project_archive.exists():
        pytest.skip("Sample MzS Tools project archive not available")
    with zipfile.ZipFile(project_archive, "r") as zip_ref:
        zip_ref.extractall(tmp_path)
    project_dir = tmp_path / "057001_Accumoli"
    return project_dir


@pytest.fixture
def base_project_path_1_0(tmp_path) -> Path:
    """Fixture that extracts a sample MzS Tools project for testing."""
    project_archive = Path(__file__).parent / "data" / "mzs_projects" / "057001_Accumoli_v1.0_new.zip"
    if not project_archive.exists():
        pytest.skip("Sample MzS Tools project archive not available")
    with zipfile.ZipFile(project_archive, "r") as zip_ref:
        zip_ref.extractall(tmp_path)
    project_dir = tmp_path / "057001_Accumoli"
    return project_dir


@pytest.fixture
def base_project_path_1_5(tmp_path) -> Path:
    """Fixture that extracts a sample MzS Tools project for testing."""
    project_archive = Path(__file__).parent / "data" / "mzs_projects" / "057001_Accumoli_v1.5_new.zip"
    if not project_archive.exists():
        pytest.skip("Sample MzS Tools project archive not available")
    with zipfile.ZipFile(project_archive, "r") as zip_ref:
        zip_ref.extractall(tmp_path)
    project_dir = tmp_path / "057001_Accumoli"
    return project_dir


@pytest.fixture
def base_project_path_0_7(tmp_path) -> Path:
    """Fixture that extracts a sample MzS Tools project for testing."""
    project_archive = Path(__file__).parent / "data" / "mzs_projects" / "057001_Accumoli_v0.7_new.zip"
    if not project_archive.exists():
        pytest.skip("Sample MzS Tools project archive not available")
    with zipfile.ZipFile(project_archive, "r") as zip_ref:
        zip_ref.extractall(tmp_path)
    project_dir = tmp_path / "057001_Accumoli"
    return project_dir


@pytest.fixture
def standard_project_path(tmp_path) -> Path:
    """Fixture that extracts a sample "standard" project for testing."""
    project_archive = Path(__file__).parent / "data" / "standard_projects" / "Accumoli.zip"
    if not project_archive.exists():
        pytest.skip("Sample MS standard project archive not available")
    with zipfile.ZipFile(project_archive, "r") as zip_ref:
        zip_ref.extractall(tmp_path)
    project_dir = tmp_path / "Accumoli"
    return project_dir


@pytest.fixture(scope="session")
def mdb_deps_available() -> bool:
    """Fixture that tries to create an mdb connection and returns True if successful.

    Returns False when python dependencies or JRE are not available in the test environment.
    """
    connected = False
    mdb_conn = None

    from mzs_tools.tasks.access_db_connection import AccessDbConnection, JVMError

    mdb_path = Path(__file__).parent.parent / "mzs_tools" / "data" / "CdI_Tabelle_4.2.mdb"
    try:
        mdb_conn = AccessDbConnection(str(mdb_path))
        connected = mdb_conn.open()
    except ImportError as e:
        warnings.warn(
            f"!!! MDB python deps not available (jaydebeapi and/or jpype) !!!\n{e}", UserWarning, stacklevel=2
        )
    except JVMError as e:
        warnings.warn(f"!!! JVM not available for MDB access !!!\n{e}", UserWarning, stacklevel=2)
    except Exception as e:
        warnings.warn(f"!!! MDB connection failed !!!\n{e}", UserWarning, stacklevel=2)
    finally:
        if mdb_conn and connected:
            mdb_conn.close()
    return connected


def pytest_sessionfinish(session, exitstatus):
    """Force immediate process exit in CI to avoid QGIS teardown segfaults (exit code 139).

    QGIS cleanup during Python shutdown can crash with SIGSEGV, causing the Docker
    container to exit with code 139 even when all tests passed. Using os._exit()
    bypasses the teardown entirely and preserves pytest's actual exit code.
    Only active when the CI environment variable is set to avoid suppressing local
    output such as warnings, coverage reports, and the summary.
    """
    if os.environ.get("CI"):
        os._exit(int(exitstatus))


def pytest_collection_modifyitems(session, config, items):
    """Modify the order of collected tests to run unit tests first, then integration, then e2e.

    This hook reorders test items based on their location in the test directory structure:
    - tests/unit/ → executed first
    - tests/integration/ → executed second
    - tests/e2e/ → executed last

    Also applies appropriate markers to each test based on its location.
    """
    unit = []
    integration = []
    e2e = []
    other = []

    for item in items:
        # Use the normalized path string to determine test category
        test_path = str(item.fspath).replace("\\", "/")

        if "/tests/unit/" in test_path:
            item.add_marker(pytest.mark.unit)
            unit.append(item)
        elif "/tests/integration/" in test_path:
            item.add_marker(pytest.mark.integration)
            integration.append(item)
        elif "/tests/e2e/" in test_path:
            item.add_marker(pytest.mark.e2e)
            e2e.append(item)
        else:
            other.append(item)

    # Reorder: unit first, then integration, then e2e, then any other tests
    items[:] = unit + integration + e2e + other
