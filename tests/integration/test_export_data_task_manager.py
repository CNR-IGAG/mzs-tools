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

"""Integration tests for ExportDataTaskManager lifecycle logic.

These tests verify task-tracking, signal handling, progress reporting,
cancellation, and logger cleanup using mocked QGIS dependencies — no full
project is needed.
"""

import logging
from unittest.mock import MagicMock, patch

import pytest
from qgis.core import Qgis, QgsApplication, QgsTask
from qgis.PyQt.QtWidgets import QProgressBar

from mzs_tools.tasks.export_data_task_manager import ExportDataTaskManager

# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_message_bar():
    """A Mock that acts as the QGIS message bar."""
    bar = MagicMock()
    return bar


@pytest.fixture
def manager_with_mock_iface(tmp_path, mock_message_bar):
    """ExportDataTaskManager with mocked iface, prj_manager and log_file_path."""
    with (
        patch("mzs_tools.tasks.export_data_task_manager.MzSProjectManager") as mock_prj_cls,
        patch("mzs_tools.tasks.export_data_task_manager.iface") as mock_iface,
    ):
        mock_iface.messageBar.return_value = mock_message_bar

        mock_prj = MagicMock()
        mock_prj.project_path = tmp_path
        mock_prj_cls.instance.return_value = mock_prj

        mgr = ExportDataTaskManager(
            output_path=tmp_path / "out",
            indagini_output_format="sqlite",
            standard_version_string="S42",
            cdi_tabelle_model_file="CdI_Tabelle_4.2.mdb",
            debug_mode=False,
        )

        # Provide a real progress bar and a stub log file
        mgr.progress_bar = QProgressBar()
        log_file = tmp_path / "test_export.log"
        log_file.write_text("test log content", encoding="utf-8")
        mgr.log_file_path = log_file

        yield mgr


# ---------------------------------------------------------------------------
# Constructor
# ---------------------------------------------------------------------------


def test_task_manager_init(tmp_path):
    """Constructor stores all parameters and initialises tracking state."""
    with (
        patch("mzs_tools.tasks.export_data_task_manager.MzSProjectManager"),
        patch("mzs_tools.tasks.export_data_task_manager.iface"),
    ):
        mgr = ExportDataTaskManager(
            output_path=tmp_path / "out",
            indagini_output_format="mdb",
            standard_version_string="S42",
            cdi_tabelle_model_file="CdI_Tabelle_4.2.mdb",
            debug_mode=True,
        )

    assert mgr.output_path == tmp_path / "out"
    assert mgr.indagini_output_format == "mdb"
    assert mgr.standard_version_string == "S42"
    assert mgr.cdi_tabelle_model_file == "CdI_Tabelle_4.2.mdb"
    assert mgr.debug_mode is True
    assert mgr._tasks == []
    assert mgr._task_failed is False
    assert mgr._completed_count == 0
    assert mgr.progress_bar is None
    assert mgr.log_file_path is None
    assert mgr.file_handler is None


# ---------------------------------------------------------------------------
# Task tracking / finalization
# ---------------------------------------------------------------------------


def test_maybe_finalize_not_triggered_until_all_done(manager_with_mock_iface, mock_message_bar):
    """_maybe_finalize should NOT fire completion when only some tasks are done."""
    mgr = manager_with_mock_iface
    # Simulate 2 tracked tasks
    mgr._tasks = [MagicMock(spec=QgsTask), MagicMock(spec=QgsTask)]

    mgr._on_single_task_done()  # only one of two

    assert mgr._completed_count == 1
    # pushMessage must NOT have been called yet
    mock_message_bar.pushMessage.assert_not_called()


def test_all_tasks_done_success(manager_with_mock_iface, mock_message_bar):
    """When all tasks complete without failure, Success level message is shown."""
    mgr = manager_with_mock_iface
    mgr._tasks = [MagicMock(spec=QgsTask), MagicMock(spec=QgsTask)]

    mgr._on_single_task_done()
    mgr._on_single_task_done()

    mock_message_bar.clearWidgets.assert_called_once()
    call_kwargs = mock_message_bar.pushMessage.call_args
    assert call_kwargs.kwargs["level"] == Qgis.MessageLevel.Success
    assert mgr._task_failed is False


def test_all_tasks_done_with_failure(manager_with_mock_iface, mock_message_bar):
    """When one task is terminated, Warning level message is shown."""
    mgr = manager_with_mock_iface
    mgr._tasks = [MagicMock(spec=QgsTask), MagicMock(spec=QgsTask)]

    mgr._on_single_task_terminated()  # one failure
    mgr._on_single_task_done()  # second task completes

    assert mgr._task_failed is True
    call_kwargs = mock_message_bar.pushMessage.call_args
    assert call_kwargs.kwargs["level"] == Qgis.MessageLevel.Warning


def test_single_task_terminated_sets_failed_flag(manager_with_mock_iface):
    """_on_single_task_terminated sets _task_failed and increments counter."""
    mgr = manager_with_mock_iface
    mgr._tasks = [MagicMock(spec=QgsTask)]

    mgr._on_single_task_terminated()

    assert mgr._task_failed is True
    assert mgr._completed_count == 1


# ---------------------------------------------------------------------------
# Progress bar
# ---------------------------------------------------------------------------


def test_on_tasks_progress_updates_bar(manager_with_mock_iface):
    """_on_tasks_progress sets progress_bar value from the signal payload."""
    mgr = manager_with_mock_iface
    assert mgr.progress_bar is not None

    mgr._on_tasks_progress(taskid=0, progress=42)
    assert mgr.progress_bar.value() == 42


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
    """_disconnect_signals can be called multiple times without RuntimeError."""
    mgr = manager_with_mock_iface
    # No tasks, no connections — should be a no-op
    mgr._disconnect_signals()
    mgr._disconnect_signals()  # second call must not raise


def test_disconnect_signals_removes_per_task_connections(manager_with_mock_iface):
    """_disconnect_signals removes taskCompleted/taskTerminated connections."""
    mgr = manager_with_mock_iface

    # Use a real minimal QgsTask subclass to verify signal disconnection
    class DummyTask(QgsTask):
        def __init__(self):
            super().__init__("dummy")

        def run(self):
            return True

    task = DummyTask()
    task.taskCompleted.connect(mgr._on_single_task_done)
    task.taskTerminated.connect(mgr._on_single_task_terminated)
    mgr._tasks = [task]

    mgr._disconnect_signals()

    # Calling again should not raise even though signals are already disconnected
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
    # Should not raise
    mgr._cleanup_logger()
