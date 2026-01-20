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

"""Unit tests for run_cmd function from misc.py."""

from unittest.mock import Mock, patch

import pytest


@pytest.mark.no_qgis
class TestRunCmdUnit:
    """Unit tests for run_cmd function with subprocess mocking."""

    def test_successful_command(self):
        """Test run_cmd with successful command execution."""
        from mzs_tools.plugin_utils.misc import run_cmd

        mock_process = Mock()
        mock_process.poll.side_effect = [None, None, 0]  # Not finished, not finished, then finished with success
        mock_process.returncode = 0
        mock_process.stdout.read.return_value = "Success output"
        mock_process.stdout.readline.side_effect = ["Line 1\n", "Line 2\n", ""]

        with (
            patch("mzs_tools.plugin_utils.misc.iface") as mock_iface,
            patch("mzs_tools.plugin_utils.misc.Popen", return_value=mock_process) as mock_popen,
            patch("mzs_tools.plugin_utils.misc.QProgressDialog") as mock_progress_dlg,
            patch("mzs_tools.plugin_utils.misc.QgsApplication.processEvents"),
        ):
            mock_iface.mainWindow.return_value = Mock()
            mock_dlg_instance = Mock()
            mock_progress_dlg.return_value = mock_dlg_instance
            mock_dlg_instance.wasCanceled.return_value = False

            result = run_cmd(["echo", "test"], "Testing command")

        assert result is True
        assert mock_popen.called

    def test_failed_command(self):
        """Test run_cmd with failed command execution."""
        from mzs_tools.plugin_utils.misc import run_cmd

        mock_process = Mock()
        mock_process.poll.side_effect = [None, 1]  # Not finished, then finished with error
        mock_process.returncode = 1
        mock_process.stdout.read.return_value = "Error output"
        mock_process.stdout.readline.return_value = ""

        with (
            patch("mzs_tools.plugin_utils.misc.iface") as mock_iface,
            patch("mzs_tools.plugin_utils.misc.Popen", return_value=mock_process),
            patch("mzs_tools.plugin_utils.misc.QProgressDialog") as mock_progress_dlg,
            patch("mzs_tools.plugin_utils.misc.QMessageBox") as mock_msgbox,
            patch("mzs_tools.plugin_utils.misc.QgsApplication.processEvents"),
        ):
            mock_iface.mainWindow.return_value = Mock()
            mock_dlg_instance = Mock()
            mock_progress_dlg.return_value = mock_dlg_instance
            mock_dlg_instance.wasCanceled.return_value = False

            mock_msgbox_instance = Mock()
            mock_msgbox.return_value = mock_msgbox_instance

            result = run_cmd(["false"], "Testing failed command")

        assert result is False
        assert mock_msgbox.called
        assert mock_msgbox_instance.exec.called

    def test_canceled_command(self):
        """Test run_cmd when user cancels the operation."""
        from mzs_tools.plugin_utils.misc import run_cmd

        mock_process = Mock()
        mock_process.poll.side_effect = [None, None, None]  # Never finishes naturally
        mock_process.returncode = -1  # Simulates killed process
        mock_process.stdout.readline.return_value = ""

        with (
            patch("mzs_tools.plugin_utils.misc.iface") as mock_iface,
            patch("mzs_tools.plugin_utils.misc.Popen", return_value=mock_process),
            patch("mzs_tools.plugin_utils.misc.QProgressDialog") as mock_progress_dlg,
            patch("mzs_tools.plugin_utils.misc.QgsApplication.processEvents"),
            patch("mzs_tools.plugin_utils.misc.QMessageBox"),
        ):
            mock_iface.mainWindow.return_value = Mock()
            mock_dlg_instance = Mock()
            mock_progress_dlg.return_value = mock_dlg_instance
            # Simulate user canceling after first check
            mock_dlg_instance.wasCanceled.side_effect = [False, True]

            run_cmd(["sleep", "10"], "Testing cancelable command")

        # Process should be killed
        assert mock_process.kill.called

    def test_output_logging(self):
        """Test that command output is logged."""
        from mzs_tools.plugin_utils.misc import run_cmd

        mock_process = Mock()
        mock_process.poll.side_effect = [None, 0]
        mock_process.returncode = 0
        mock_process.stdout.read.return_value = "Final output line\n"
        mock_process.stdout.readline.side_effect = ["Output line 1\n", "Output line 2\n", ""]

        with (
            patch("mzs_tools.plugin_utils.misc.iface") as mock_iface,
            patch("mzs_tools.plugin_utils.misc.Popen", return_value=mock_process),
            patch("mzs_tools.plugin_utils.misc.QProgressDialog"),
            patch("mzs_tools.plugin_utils.misc.QgsApplication.processEvents"),
        ):
            mock_iface.mainWindow.return_value = Mock()

            result = run_cmd(["test", "command"], "Testing output logging")

        assert result is True

    def test_progress_dialog_updates(self):
        """Test that progress dialog is updated with output."""
        from mzs_tools.plugin_utils.misc import run_cmd

        mock_process = Mock()
        mock_process.poll.side_effect = [None, 0]
        mock_process.returncode = 0
        mock_process.stdout.read.return_value = "Final line\n"
        mock_process.stdout.readline.side_effect = ["Processing...\n", ""]

        with (
            patch("mzs_tools.plugin_utils.misc.iface") as mock_iface,
            patch("mzs_tools.plugin_utils.misc.Popen", return_value=mock_process),
            patch("mzs_tools.plugin_utils.misc.QProgressDialog") as mock_progress_dlg,
            patch("mzs_tools.plugin_utils.misc.QgsApplication.processEvents"),
            patch("mzs_tools.plugin_utils.misc.MzSToolsLogger"),
        ):
            mock_iface.mainWindow.return_value = Mock()
            mock_dlg_instance = Mock()
            mock_progress_dlg.return_value = mock_dlg_instance
            mock_dlg_instance.wasCanceled.return_value = False

            result = run_cmd(["test"], "Testing progress updates")

        assert result is True
        # Verify progress dialog text was updated
        assert mock_dlg_instance.setLabelText.call_count > 0

    def test_command_args_passed_correctly(self):
        """Test that command arguments are passed correctly to Popen."""
        from mzs_tools.plugin_utils.misc import run_cmd

        mock_process = Mock()
        mock_process.poll.return_value = 0
        mock_process.returncode = 0
        mock_process.stdout.read.return_value = ""

        test_args = ["python", "-m", "pip", "install", "package"]

        with (
            patch("mzs_tools.plugin_utils.misc.iface") as mock_iface,
            patch("mzs_tools.plugin_utils.misc.Popen", return_value=mock_process) as mock_popen,
            patch("mzs_tools.plugin_utils.misc.QProgressDialog"),
            patch("mzs_tools.plugin_utils.misc.QgsApplication.processEvents"),
        ):
            mock_iface.mainWindow.return_value = Mock()

            run_cmd(test_args, "Testing argument passing")

        # Verify Popen was called with correct arguments
        call_args = mock_popen.call_args[0][0]
        assert call_args == test_args

    def test_error_message_contains_output(self):
        """Test that error message box contains command output."""
        from mzs_tools.plugin_utils.misc import run_cmd

        error_output = "Error: something went wrong\nLine 2 of error"
        mock_process = Mock()
        mock_process.poll.side_effect = [None, 1]
        mock_process.returncode = 1
        # Return error output when read() is called
        mock_process.stdout.read.return_value = error_output
        mock_process.stdout.readline.side_effect = ["Initial error\n", ""]

        with (
            patch("mzs_tools.plugin_utils.misc.iface") as mock_iface,
            patch("mzs_tools.plugin_utils.misc.Popen", return_value=mock_process),
            patch("mzs_tools.plugin_utils.misc.QProgressDialog"),
            patch("mzs_tools.plugin_utils.misc.QMessageBox") as mock_msgbox,
            patch("mzs_tools.plugin_utils.misc.QgsApplication.processEvents"),
        ):
            mock_iface.mainWindow.return_value = Mock()
            mock_msgbox_instance = Mock()
            mock_msgbox.return_value = mock_msgbox_instance

            result = run_cmd(["false"], "Testing error output")

        assert result is False
        # Verify QMessageBox was created and showed error
        assert mock_msgbox.called
        assert mock_msgbox_instance.setDetailedText.called
        assert mock_msgbox_instance.exec.called

    def test_reading_exception_handling(self):
        """Test handling of exceptions during output reading."""
        from mzs_tools.plugin_utils.misc import run_cmd

        mock_process = Mock()
        mock_process.poll.side_effect = [None, 0]
        mock_process.returncode = 0
        mock_process.stdout.read.return_value = ""
        # Raise exception on first readline, then succeed
        mock_process.stdout.readline.side_effect = [OSError("Read error"), ""]

        with (
            patch("mzs_tools.plugin_utils.misc.iface") as mock_iface,
            patch("mzs_tools.plugin_utils.misc.Popen", return_value=mock_process),
            patch("mzs_tools.plugin_utils.misc.QProgressDialog"),
            patch("mzs_tools.plugin_utils.misc.QgsApplication.processEvents"),
        ):
            mock_iface.mainWindow.return_value = Mock()

            # Should not raise exception, just continue
            result = run_cmd(["test"], "Testing exception handling")

        assert result is True


@pytest.mark.no_qgis
class TestRunCmdEdgeCases:
    """Test edge cases for run_cmd function."""

    def test_empty_command_list(self):
        """Test run_cmd with empty command list."""
        from mzs_tools.plugin_utils.misc import run_cmd

        with (
            patch("mzs_tools.plugin_utils.misc.iface") as mock_iface,
            patch("mzs_tools.plugin_utils.misc.Popen") as mock_popen,
            patch("mzs_tools.plugin_utils.misc.QProgressDialog"),
        ):
            mock_iface.mainWindow.return_value = Mock()

            # This should fail when Popen is called
            mock_popen.side_effect = ValueError("Empty command")
            with pytest.raises(ValueError):
                run_cmd([], "Testing empty command")

    def test_multiline_output(self):
        """Test handling of multiline output."""
        from mzs_tools.plugin_utils.misc import run_cmd

        mock_process = Mock()
        mock_process.poll.side_effect = [None, None, 0]
        mock_process.returncode = 0
        mock_process.stdout.read.return_value = "Line 4\nLine 5\n"
        mock_process.stdout.readline.side_effect = ["Line 1\n", "Line 2\n", "Line 3\n", ""]

        with (
            patch("mzs_tools.plugin_utils.misc.iface") as mock_iface,
            patch("mzs_tools.plugin_utils.misc.Popen", return_value=mock_process),
            patch("mzs_tools.plugin_utils.misc.QProgressDialog") as mock_progress_dlg,
            patch("mzs_tools.plugin_utils.misc.QgsApplication.processEvents"),
        ):
            mock_iface.mainWindow.return_value = Mock()
            mock_dlg_instance = Mock()
            mock_progress_dlg.return_value = mock_dlg_instance
            mock_dlg_instance.wasCanceled.return_value = False

            result = run_cmd(["test"], "Testing multiline output")

        assert result is True
        # Verify multiple updates to progress dialog
        assert mock_dlg_instance.setLabelText.call_count >= 2

    def test_custom_description(self):
        """Test that custom description is used in progress dialog."""
        from mzs_tools.plugin_utils.misc import run_cmd

        mock_process = Mock()
        mock_process.poll.return_value = 0
        mock_process.returncode = 0
        mock_process.stdout.read.return_value = ""

        custom_desc = "Custom operation description"

        with (
            patch("mzs_tools.plugin_utils.misc.iface") as mock_iface,
            patch("mzs_tools.plugin_utils.misc.Popen", return_value=mock_process),
            patch("mzs_tools.plugin_utils.misc.QProgressDialog") as mock_progress_dlg,
            patch("mzs_tools.plugin_utils.misc.QgsApplication.processEvents"),
        ):
            mock_iface.mainWindow.return_value = Mock()
            mock_dlg_instance = Mock()
            mock_progress_dlg.return_value = mock_dlg_instance

            run_cmd(["test"], custom_desc)

        # Verify custom description was used
        progress_args = mock_progress_dlg.call_args[0]
        assert custom_desc in progress_args

    def test_very_long_output_line(self):
        """Test handling of very long output lines."""
        from mzs_tools.plugin_utils.misc import run_cmd

        long_line = "x" * 10000 + "\n"
        mock_process = Mock()
        mock_process.poll.side_effect = [None, 0]
        mock_process.returncode = 0
        # Make sure read() returns the long line when called at the end
        mock_process.stdout.read.return_value = long_line
        # First readline returns the long line, second returns empty
        mock_process.stdout.readline.side_effect = [long_line, ""]

        with (
            patch("mzs_tools.plugin_utils.misc.iface") as mock_iface,
            patch("mzs_tools.plugin_utils.misc.Popen", return_value=mock_process),
            patch("mzs_tools.plugin_utils.misc.QProgressDialog") as mock_progress_dlg,
            patch("mzs_tools.plugin_utils.misc.QgsApplication.processEvents"),
        ):
            mock_iface.mainWindow.return_value = Mock()
            mock_dlg_instance = Mock()
            mock_progress_dlg.return_value = mock_dlg_instance
            mock_dlg_instance.wasCanceled.return_value = False

            result = run_cmd(["test"], "Testing long output")

        assert result is True
        # Verify the long line was handled
        assert mock_dlg_instance.setLabelText.call_count > 0
