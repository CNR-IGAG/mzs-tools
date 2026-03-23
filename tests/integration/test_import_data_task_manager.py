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

"""Integration tests for ImportDataTaskManager lifecycle logic.

These tests verify task-tracking, signal handling, progress reporting,
cancellation, and logger cleanup using mocked QGIS dependencies — no full
project is needed.
"""

import logging
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from qgis.core import Qgis, QgsApplication, QgsTask
from qgis.PyQt.QtWidgets import QProgressBar

from mzs_tools.tasks.import_data_task_manager import ImportDataTaskManager

# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_message_bar():
    """A Mock that acts as the QGIS message bar."""
    return MagicMock()


@pytest.fixture
def manager_with_mock_iface(tmp_path, mock_message_bar):
    """ImportDataTaskManager with mocked iface, prj_manager and log_file_path."""
    with (
        patch("mzs_tools.tasks.import_data_task_manager.MzSProjectManager") as mock_prj_cls,
        patch("mzs_tools.tasks.import_data_task_manager.iface") as mock_iface,
    ):
        mock_iface.messageBar.return_value = mock_message_bar

        mock_prj = MagicMock()
        mock_prj.project_path = tmp_path
        mock_prj_cls.instance.return_value = mock_prj

        mgr = ImportDataTaskManager(
            standard_proj_paths={},
            input_path=tmp_path / "input",
            indagini_data_source="sqlite",
            mdb_password=None,
            csv_files_found=None,
            reset_sequences=False,
            import_spu=False,
            import_sln=False,
            selected_shapefiles=[],
            debug_mode=False,
        )

        # Provide a real progress bar and a stub log file
        mgr.progress_bar = QProgressBar()
        log_file = tmp_path / "test_import.log"
        log_file.write_text("test log content", encoding="utf-8")
        mgr.log_file_path = log_file

        yield mgr


# ---------------------------------------------------------------------------
# Constructor
# ---------------------------------------------------------------------------


def test_task_manager_init(tmp_path):
    """Constructor stores all parameters and initialises tracking state."""
    input_path = tmp_path / "input"
    with (
        patch("mzs_tools.tasks.import_data_task_manager.MzSProjectManager"),
        patch("mzs_tools.tasks.import_data_task_manager.iface"),
    ):
        mgr = ImportDataTaskManager(
            standard_proj_paths={"key": "value"},
            input_path=input_path,
            indagini_data_source="mdb",
            mdb_password="secret",
            csv_files_found={"csv": Path("a.csv")},
            reset_sequences=True,
            import_spu=True,
            import_sln=False,
            selected_shapefiles=["Strati", "MS"],
            debug_mode=True,
        )

    assert mgr.input_path == input_path
    assert mgr.indagini_data_source == "mdb"
    assert mgr.mdb_password == "secret"
    assert mgr.reset_sequences is True
    assert mgr.import_spu is True
    assert mgr.import_sln is False
    assert mgr.selected_shapefiles == ["Strati", "MS"]
    assert mgr.debug_mode is True
    assert mgr._tasks == []
    assert mgr._first_task is None
    assert mgr.task_failed is False
    assert mgr.progress_bar is None
    assert mgr.log_file_path is None
    assert mgr.file_handler is None


# ---------------------------------------------------------------------------
# _on_any_task_terminated
# ---------------------------------------------------------------------------


def test_any_task_terminated_sets_failed_flag(manager_with_mock_iface):
    """_on_any_task_terminated sets task_failed to True."""
    mgr = manager_with_mock_iface
    assert mgr.task_failed is False

    mgr._on_any_task_terminated()

    assert mgr.task_failed is True


def test_any_task_terminated_idempotent(manager_with_mock_iface):
    """Calling _on_any_task_terminated multiple times doesn't raise."""
    mgr = manager_with_mock_iface
    mgr._on_any_task_terminated()
    mgr._on_any_task_terminated()
    assert mgr.task_failed is True


# ---------------------------------------------------------------------------
# _on_tasks_completed
# ---------------------------------------------------------------------------


def test_on_tasks_completed_success(manager_with_mock_iface, mock_message_bar):
    """When task_failed is False, Success level message is pushed."""
    mgr = manager_with_mock_iface
    mgr.task_failed = False

    mgr._on_tasks_completed()

    mock_message_bar.clearWidgets.assert_called_once()
    call_kwargs = mock_message_bar.pushMessage.call_args
    assert call_kwargs.kwargs["level"] == Qgis.MessageLevel.Success


def test_on_tasks_completed_with_failure(manager_with_mock_iface, mock_message_bar):
    """When task_failed is True, Warning level message is pushed."""
    mgr = manager_with_mock_iface
    mgr.task_failed = True

    mgr._on_tasks_completed()

    mock_message_bar.clearWidgets.assert_called_once()
    call_kwargs = mock_message_bar.pushMessage.call_args
    assert call_kwargs.kwargs["level"] == Qgis.MessageLevel.Warning


def test_on_tasks_completed_cleans_up_logger(manager_with_mock_iface, tmp_path):
    """_on_tasks_completed removes the file handler when done."""
    mgr = manager_with_mock_iface
    log_path = tmp_path / "done_test.log"
    handler = logging.FileHandler(log_path, encoding="utf-8")
    mgr.file_handler = handler
    mgr.file_logger.addHandler(handler)

    mgr._on_tasks_completed()

    assert mgr.file_handler is None
    assert handler not in mgr.file_logger.handlers


def test_on_tasks_completed_reads_log_file(manager_with_mock_iface, mock_message_bar, tmp_path):
    """_on_tasks_completed passes log file contents as the detail text."""
    mgr = manager_with_mock_iface
    log_path = tmp_path / "readable.log"
    log_path.write_text("some log output", encoding="utf-8")
    mgr.log_file_path = log_path

    mgr._on_tasks_completed()

    call_args = mock_message_bar.pushMessage.call_args
    # Third positional argument is the detail/text body
    assert call_args.args[2] == "some log output"


# ---------------------------------------------------------------------------
# Progress bar
# ---------------------------------------------------------------------------


def test_on_tasks_progress_updates_bar(manager_with_mock_iface):
    """_on_tasks_progress sets progress_bar value from the signal payload."""
    mgr = manager_with_mock_iface
    assert mgr.progress_bar is not None

    mgr._on_tasks_progress(taskid=0, progress=55)
    assert mgr.progress_bar.value() == 55


def test_on_tasks_progress_no_bar_does_not_raise(manager_with_mock_iface):
    """_on_tasks_progress is safe when progress_bar is None."""
    mgr = manager_with_mock_iface
    mgr.progress_bar = None
    # Should not raise, thanks to contextlib.suppress
    mgr._on_tasks_progress(taskid=0, progress=75)


# ---------------------------------------------------------------------------
# cancel_tasks
# ---------------------------------------------------------------------------


def test_cancel_tasks_calls_cancel_all(manager_with_mock_iface, mock_message_bar):
    """cancel_tasks cancels all QGIS tasks and shows a Warning message."""
    mgr = manager_with_mock_iface

    with patch.object(QgsApplication.taskManager(), "cancelAll") as mock_cancel:
        mgr.cancel_tasks()
        mock_cancel.assert_called_once()

    mock_message_bar.clearWidgets.assert_called_once()
    call_kwargs = mock_message_bar.pushMessage.call_args
    assert call_kwargs.kwargs["level"] == Qgis.MessageLevel.Warning


def test_cancel_tasks_cleans_up_logger(manager_with_mock_iface, tmp_path):
    """cancel_tasks removes and closes the file handler."""
    mgr = manager_with_mock_iface
    log_path = tmp_path / "cancel_test.log"
    handler = logging.FileHandler(log_path, encoding="utf-8")
    mgr.file_handler = handler
    mgr.file_logger.addHandler(handler)

    with patch.object(QgsApplication.taskManager(), "cancelAll"):
        mgr.cancel_tasks()

    assert mgr.file_handler is None
    assert handler not in mgr.file_logger.handlers


# ---------------------------------------------------------------------------
# _disconnect_signals
# ---------------------------------------------------------------------------


def test_disconnect_signals_safe_to_call_multiple_times(manager_with_mock_iface):
    """_disconnect_signals can be called multiple times without error."""
    mgr = manager_with_mock_iface
    # No tasks, no connections — should be a no-op
    mgr._disconnect_signals()
    mgr._disconnect_signals()


def test_disconnect_signals_removes_per_task_connections(manager_with_mock_iface):
    """_disconnect_signals removes taskTerminated signals from all tasks and first_task."""
    mgr = manager_with_mock_iface

    class DummyTask(QgsTask):
        def __init__(self):
            super().__init__("dummy")

        def run(self):
            return True

    task = DummyTask()
    first = DummyTask()
    task.taskTerminated.connect(mgr._on_any_task_terminated)
    first.taskCompleted.connect(mgr._on_tasks_completed)
    first.taskTerminated.connect(mgr._on_tasks_completed)

    mgr._tasks = [task, first]
    mgr._first_task = first

    mgr._disconnect_signals()
    # Second call must also be safe (all signals already gone)
    mgr._disconnect_signals()


# ---------------------------------------------------------------------------
# _cleanup_logger
# ---------------------------------------------------------------------------


def test_cleanup_logger_removes_handler(manager_with_mock_iface, tmp_path):
    """_cleanup_logger removes the file handler and sets it to None."""
    mgr = manager_with_mock_iface
    log_path = tmp_path / "cleanup_test.log"
    handler = logging.FileHandler(log_path, encoding="utf-8")
    mgr.file_handler = handler
    mgr.file_logger.addHandler(handler)

    mgr._cleanup_logger()

    assert mgr.file_handler is None
    assert handler not in mgr.file_logger.handlers


def test_cleanup_logger_noop_when_no_handler(manager_with_mock_iface):
    """_cleanup_logger is safe to call when file_handler is already None."""
    mgr = manager_with_mock_iface
    mgr.file_handler = None
    mgr._cleanup_logger()
