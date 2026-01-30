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

"""Integration tests for dependency_manager module requiring QGIS environment."""

import sys
from unittest.mock import Mock, patch

import pytest


class TestDependencyManagerIntegration:
    """Integration tests for DependencyManager requiring QGIS."""

    def test_initialization_with_qgis(self, tmp_path):
        """Test DependencyManager initialization with QGIS environment."""
        from mzs_tools.plugin_utils.dependency_manager import DependencyManager

        # Mock QgsApplication.qgisSettingsDirPath to use tmp_path
        with patch(
            "mzs_tools.plugin_utils.dependency_manager.QgsApplication.qgisSettingsDirPath",
            return_value=str(tmp_path),
        ):
            dm = DependencyManager()

        # Verify initialization
        assert dm.iface is not None
        assert dm.site_packages == tmp_path / "python" / "dependencies"
        assert dm.site_packages.exists()

    def test_site_packages_in_python_path(self, tmp_path):
        """Test that site-packages directory is added to Python path."""
        from mzs_tools.plugin_utils.dependency_manager import DependencyManager

        with patch(
            "mzs_tools.plugin_utils.dependency_manager.QgsApplication.qgisSettingsDirPath",
            return_value=str(tmp_path),
        ):
            dm = DependencyManager()

        # Check if site_packages is in sys.path
        assert str(dm.site_packages) in sys.path

    def test_check_dependencies_with_real_modules(self, tmp_path):
        """Test check_dependencies with real importable modules."""
        from mzs_tools.plugin_utils.dependency_manager import DependencyManager

        with patch(
            "mzs_tools.plugin_utils.dependency_manager.QgsApplication.qgisSettingsDirPath",
            return_value=str(tmp_path),
        ):
            dm = DependencyManager()

        # Test with standard library modules that should always be available
        result = dm.check_dependencies(["os", "sys", "pathlib"])

        assert result == {"os": True, "sys": True, "pathlib": True}

    def test_check_dependencies_with_missing_modules(self, tmp_path):
        """Test check_dependencies with non-existent modules."""
        from mzs_tools.plugin_utils.dependency_manager import DependencyManager

        with patch(
            "mzs_tools.plugin_utils.dependency_manager.QgsApplication.qgisSettingsDirPath",
            return_value=str(tmp_path),
        ):
            dm = DependencyManager()

        # Test with modules that definitely don't exist
        result = dm.check_dependencies(
            ["nonexistent_module_12345", "another_fake_module_67890", "definitely_not_a_real_module_00000"]
        )

        assert result == {
            "nonexistent_module_12345": False,
            "another_fake_module_67890": False,
            "definitely_not_a_real_module_00000": False,
        }

    def test_check_dependencies_mixed(self, tmp_path):
        """Test check_dependencies with mix of available and missing modules."""
        from mzs_tools.plugin_utils.dependency_manager import DependencyManager

        with patch(
            "mzs_tools.plugin_utils.dependency_manager.QgsApplication.qgisSettingsDirPath",
            return_value=str(tmp_path),
        ):
            dm = DependencyManager()

        result = dm.check_dependencies(["os", "nonexistent_module_xyz", "sys"])

        assert result == {"os": True, "nonexistent_module_xyz": False, "sys": True}

    def test_translation_function(self, tmp_path):
        """Test translation function works with QGIS environment."""
        from mzs_tools.plugin_utils.dependency_manager import DependencyManager

        with patch(
            "mzs_tools.plugin_utils.dependency_manager.QgsApplication.qgisSettingsDirPath",
            return_value=str(tmp_path),
        ):
            dm = DependencyManager()

        # Test translation function
        msg = dm.tr("Test message")
        assert isinstance(msg, str)
        assert len(msg) > 0


class TestInstallPythonDependenciesIntegration:
    """Integration tests for install_python_dependencies method."""

    def test_install_python_dependencies_interactive_declined(self, tmp_path, monkeypatch):
        """Test install_python_dependencies when user declines."""
        from qgis.PyQt.QtWidgets import QMessageBox

        from mzs_tools.plugin_utils.dependency_manager import DependencyManager

        with patch(
            "mzs_tools.plugin_utils.dependency_manager.QgsApplication.qgisSettingsDirPath",
            return_value=str(tmp_path),
        ):
            dm = DependencyManager()

        # Mock QMessageBox to return No
        with patch.object(QMessageBox, "question", return_value=QMessageBox.StandardButton.No) as mock_question:
            result = dm.install_python_dependencies(interactive=True)

        assert result is False
        assert mock_question.called

    def test_install_python_dependencies_non_interactive(self, tmp_path):
        """Test install_python_dependencies in non-interactive mode."""
        from mzs_tools.plugin_utils.dependency_manager import DependencyManager

        requirements_file = tmp_path / "requirements.txt"
        requirements_file.write_text("fake_package\n")

        with (
            patch("mzs_tools.plugin_utils.dependency_manager.DIR_PLUGIN_ROOT", tmp_path),
            patch(
                "mzs_tools.plugin_utils.dependency_manager.QgsApplication.qgisSettingsDirPath",
                return_value=str(tmp_path / "qgis"),
            ),
        ):
            dm = DependencyManager()
            dm.iface.messageBar().clearWidgets = Mock()  # type: ignore # Add clearWidgets mock

            # Mock install_dependencies to avoid actual installation
            with patch.object(dm, "install_dependencies", return_value=True) as mock_install:
                result = dm.install_python_dependencies(interactive=False)

        assert result is True
        assert mock_install.called

    def test_install_python_dependencies_failure_handling(self, tmp_path):
        """Test install_python_dependencies handles installation failure."""
        from mzs_tools.plugin_utils.dependency_manager import DependencyManager

        requirements_file = tmp_path / "requirements.txt"
        requirements_file.write_text("fake_package\n")

        with (
            patch("mzs_tools.plugin_utils.dependency_manager.DIR_PLUGIN_ROOT", tmp_path),
            patch(
                "mzs_tools.plugin_utils.dependency_manager.QgsApplication.qgisSettingsDirPath",
                return_value=str(tmp_path / "qgis"),
            ),
        ):
            dm = DependencyManager()
            dm.iface.messageBar().clearWidgets = Mock()  # type: ignore # Add clearWidgets mock
            # Mock pushMessage to accept showMore argument
            dm.iface.messageBar().pushMessage = Mock()  # type: ignore

            # Mock install_dependencies to return failure
            with patch.object(dm, "install_dependencies", return_value=False):
                result = dm.install_python_dependencies(interactive=False)

        assert result is False


class TestRunCmdIntegration:
    """Integration tests for run_cmd function."""

    @pytest.mark.filterwarnings("ignore::ResourceWarning")
    def test_run_cmd_with_qgis_simple_command(self):
        """Test run_cmd with a simple command in QGIS environment."""
        from mzs_tools.plugin_utils.misc import run_cmd

        # Use a simple command that should succeed
        result = run_cmd([sys.executable, "-c", "print('test')"], "Testing simple command")

        assert result is True

    @pytest.mark.filterwarnings("ignore::ResourceWarning")
    def test_run_cmd_with_qgis_version_check(self):
        """Test run_cmd with python version check command."""
        from mzs_tools.plugin_utils.misc import run_cmd

        # Use python --version which should always succeed
        result = run_cmd([sys.executable, "--version"], "Checking Python version")

        assert result is True

    @pytest.mark.filterwarnings("ignore::ResourceWarning")
    def test_run_cmd_with_failing_command(self):
        """Test run_cmd with a command that fails."""
        from mzs_tools.plugin_utils.misc import run_cmd

        # Mock QMessageBox to avoid actual dialog
        mock_msgbox_instance = Mock()
        with patch("mzs_tools.plugin_utils.misc.QMessageBox", return_value=mock_msgbox_instance):
            # Use a command that should fail
            result = run_cmd([sys.executable, "-c", "import nonexistent_module"], "Testing failing command")

        assert result is False
        assert mock_msgbox_instance.exec.called


class TestPythonCommandWithRealEnvironment:
    """Test python_command with real QGIS Python environment."""

    def test_python_command_returns_valid_executable(self, tmp_path):
        """Test that python_command returns a valid Python executable."""
        from mzs_tools.plugin_utils.dependency_manager import DependencyManager

        with patch(
            "mzs_tools.plugin_utils.dependency_manager.QgsApplication.qgisSettingsDirPath",
            return_value=str(tmp_path),
        ):
            dm = DependencyManager()

        python_cmd = dm.python_command()

        # Verify it's a string and not empty
        assert isinstance(python_cmd, str)
        assert len(python_cmd) > 0

        # Should be either 'python', a path to python.exe, or sys.executable
        assert "python" in python_cmd.lower() or python_cmd == sys.executable

    def test_python_command_consistency(self, tmp_path):
        """Test that python_command returns consistent results."""
        from mzs_tools.plugin_utils.dependency_manager import DependencyManager

        with patch(
            "mzs_tools.plugin_utils.dependency_manager.QgsApplication.qgisSettingsDirPath",
            return_value=str(tmp_path),
        ):
            dm = DependencyManager()

        # Call multiple times and verify consistency
        cmd1 = dm.python_command()
        cmd2 = dm.python_command()
        cmd3 = dm.python_command()

        assert cmd1 == cmd2 == cmd3


class TestEnsurePathSetup:
    """Test _ensure_path_setup method."""

    def test_ensure_path_setup_creates_directory(self, tmp_path):
        """Test that _ensure_path_setup creates the site-packages directory."""
        from mzs_tools.plugin_utils.dependency_manager import DependencyManager

        with patch(
            "mzs_tools.plugin_utils.dependency_manager.QgsApplication.qgisSettingsDirPath",
            return_value=str(tmp_path),
        ):
            dm = DependencyManager()

        # Verify directory was created
        assert dm.site_packages.exists()
        assert dm.site_packages.is_dir()

    def test_ensure_path_setup_adds_to_sys_path(self, tmp_path):
        """Test that _ensure_path_setup adds directory to sys.path."""
        from mzs_tools.plugin_utils.dependency_manager import DependencyManager

        with patch(
            "mzs_tools.plugin_utils.dependency_manager.QgsApplication.qgisSettingsDirPath",
            return_value=str(tmp_path),
        ):
            dm = DependencyManager()

        # Verify it's in sys.path
        assert str(dm.site_packages) in sys.path

    def test_ensure_path_setup_idempotent(self, tmp_path):
        """Test that _ensure_path_setup can be called multiple times safely."""
        from mzs_tools.plugin_utils.dependency_manager import DependencyManager

        with patch(
            "mzs_tools.plugin_utils.dependency_manager.QgsApplication.qgisSettingsDirPath",
            return_value=str(tmp_path),
        ):
            dm = DependencyManager()

        # Call multiple times
        initial_path_count = sys.path.count(str(dm.site_packages))
        dm._ensure_path_setup()
        dm._ensure_path_setup()

        # Should not add duplicate entries
        final_path_count = sys.path.count(str(dm.site_packages))
        assert final_path_count == initial_path_count
