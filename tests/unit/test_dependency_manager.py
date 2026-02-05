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

"""Unit tests for dependency_manager module."""

from unittest.mock import MagicMock, patch

import pytest


@pytest.mark.no_qgis
class TestGetRequiredPackages:
    """Test _get_required_packages method."""

    def test_parse_simple_package_names(self, tmp_path):
        """Test parsing simple package names from requirements.txt."""
        requirements_file = tmp_path / "requirements.txt"
        requirements_file.write_text("jaydebeapi\npackage2\npackage3\n")

        with patch("mzs_tools.plugin_utils.dependency_manager.DIR_PLUGIN_ROOT", tmp_path):
            from mzs_tools.plugin_utils.dependency_manager import DependencyManager

            with patch("mzs_tools.plugin_utils.dependency_manager.iface", MagicMock()):
                dm = DependencyManager()
                packages = dm._get_required_packages()

        assert packages == ["jaydebeapi", "package2", "package3"]

    def test_parse_packages_with_version_specifiers(self, tmp_path):
        """Test parsing package names with version specifiers."""
        requirements_file = tmp_path / "requirements.txt"
        requirements_file.write_text(
            "jaydebeapi==1.2.3\npackage2>=2.0.0\npackage3<=3.0.0\npackage4>1.0\npackage5<5.0\n"
        )

        with patch("mzs_tools.plugin_utils.dependency_manager.DIR_PLUGIN_ROOT", tmp_path):
            from mzs_tools.plugin_utils.dependency_manager import DependencyManager

            with patch("mzs_tools.plugin_utils.dependency_manager.iface", MagicMock()):
                dm = DependencyManager()
                packages = dm._get_required_packages()

        assert packages == ["jaydebeapi", "package2", "package3", "package4", "package5"]

    def test_parse_packages_with_comments(self, tmp_path):
        """Test parsing packages with inline and full-line comments."""
        requirements_file = tmp_path / "requirements.txt"
        requirements_file.write_text(
            "# This is a comment\njaydebeapi==1.2.3  # inline comment\npackage2>=2.0.0\n# another comment\npackage3\n"
        )

        with patch("mzs_tools.plugin_utils.dependency_manager.DIR_PLUGIN_ROOT", tmp_path):
            from mzs_tools.plugin_utils.dependency_manager import DependencyManager

            with patch("mzs_tools.plugin_utils.dependency_manager.iface", MagicMock()):
                dm = DependencyManager()
                packages = dm._get_required_packages()

        assert packages == ["jaydebeapi", "package2", "package3"]

    def test_parse_packages_with_empty_lines(self, tmp_path):
        """Test parsing packages with empty lines."""
        requirements_file = tmp_path / "requirements.txt"
        requirements_file.write_text("\n\njaydebeapi\n\n\npackage2\n\n")

        with patch("mzs_tools.plugin_utils.dependency_manager.DIR_PLUGIN_ROOT", tmp_path):
            from mzs_tools.plugin_utils.dependency_manager import DependencyManager

            with patch("mzs_tools.plugin_utils.dependency_manager.iface", MagicMock()):
                dm = DependencyManager()
                packages = dm._get_required_packages()

        assert packages == ["jaydebeapi", "package2"]

    def test_missing_requirements_file(self, tmp_path):
        """Test behavior when requirements.txt doesn't exist."""
        with patch("mzs_tools.plugin_utils.dependency_manager.DIR_PLUGIN_ROOT", tmp_path):
            from mzs_tools.plugin_utils.dependency_manager import DependencyManager

            with patch("mzs_tools.plugin_utils.dependency_manager.iface", MagicMock()):
                dm = DependencyManager()
                packages = dm._get_required_packages()

        # Should fallback to default
        assert packages == ["jaydebeapi"]

    def test_error_reading_requirements_file(self, tmp_path):
        """Test behavior when there's an error reading requirements.txt."""
        requirements_file = tmp_path / "requirements.txt"
        requirements_file.write_text("jaydebeapi\npackage2\n")

        with patch("mzs_tools.plugin_utils.dependency_manager.DIR_PLUGIN_ROOT", tmp_path):
            from mzs_tools.plugin_utils.dependency_manager import DependencyManager

            with patch("mzs_tools.plugin_utils.dependency_manager.iface", MagicMock()):
                dm = DependencyManager()

                # Mock the open to raise an exception
                with patch("builtins.open", side_effect=PermissionError("Cannot read file")):
                    packages = dm._get_required_packages()

        # Should fallback to default
        assert packages == ["jaydebeapi"]

    def test_case_insensitive_package_names(self, tmp_path):
        """Test that package names are converted to lowercase."""
        requirements_file = tmp_path / "requirements.txt"
        requirements_file.write_text("JayDeBeApi\nPACKAGE2\nPackage3\n")

        with patch("mzs_tools.plugin_utils.dependency_manager.DIR_PLUGIN_ROOT", tmp_path):
            from mzs_tools.plugin_utils.dependency_manager import DependencyManager

            with patch("mzs_tools.plugin_utils.dependency_manager.iface", MagicMock()):
                dm = DependencyManager()
                packages = dm._get_required_packages()

        assert packages == ["jaydebeapi", "package2", "package3"]


@pytest.mark.no_qgis
class TestGetRequirementsForInstall:
    """Test _get_requirements_for_install method."""

    def test_full_requirement_specifications(self, tmp_path):
        """Test that full requirement specifications are preserved."""
        requirements_file = tmp_path / "requirements.txt"
        requirements_file.write_text("jaydebeapi==1.2.3\npackage2>=2.0.0\npackage3<=3.0.0\n")

        with patch("mzs_tools.plugin_utils.dependency_manager.DIR_PLUGIN_ROOT", tmp_path):
            from mzs_tools.plugin_utils.dependency_manager import DependencyManager

            with patch("mzs_tools.plugin_utils.dependency_manager.iface", MagicMock()):
                dm = DependencyManager()
                requirements = dm._get_requirements_for_install()

        assert requirements == ["jaydebeapi==1.2.3", "package2>=2.0.0", "package3<=3.0.0"]

    def test_inline_comments_removed(self, tmp_path):
        """Test that inline comments are removed from requirements."""
        requirements_file = tmp_path / "requirements.txt"
        requirements_file.write_text("jaydebeapi==1.2.3  # for database support\npackage2>=2.0.0 # another comment\n")

        with patch("mzs_tools.plugin_utils.dependency_manager.DIR_PLUGIN_ROOT", tmp_path):
            from mzs_tools.plugin_utils.dependency_manager import DependencyManager

            with patch("mzs_tools.plugin_utils.dependency_manager.iface", MagicMock()):
                dm = DependencyManager()
                requirements = dm._get_requirements_for_install()

        assert requirements == ["jaydebeapi==1.2.3", "package2>=2.0.0"]

    def test_missing_file_fallback(self, tmp_path):
        """Test fallback behavior when requirements.txt is missing."""
        with patch("mzs_tools.plugin_utils.dependency_manager.DIR_PLUGIN_ROOT", tmp_path):
            from mzs_tools.plugin_utils.dependency_manager import DependencyManager

            with patch("mzs_tools.plugin_utils.dependency_manager.iface", MagicMock()):
                dm = DependencyManager()
                requirements = dm._get_requirements_for_install()

        assert requirements == ["jaydebeapi"]


@pytest.mark.no_qgis
class TestCheckDependencies:
    """Test check_dependencies method."""

    def test_all_dependencies_available(self):
        """Test when all dependencies are importable."""
        from mzs_tools.plugin_utils.dependency_manager import DependencyManager

        with patch("mzs_tools.plugin_utils.dependency_manager.iface", MagicMock()):
            dm = DependencyManager()

            # Mock successful imports
            with patch("builtins.__import__", return_value=MagicMock()):
                result = dm.check_dependencies(["package1", "package2", "package3"])

        assert result == {"package1": True, "package2": True, "package3": True}

    def test_some_dependencies_missing(self):
        """Test when some dependencies are missing."""
        from mzs_tools.plugin_utils.dependency_manager import DependencyManager

        with patch("mzs_tools.plugin_utils.dependency_manager.iface", MagicMock()):
            dm = DependencyManager()

            def mock_import(name, *args):
                if name == "missing_package":
                    raise ImportError("No module named 'missing_package'")
                return MagicMock()

            with patch("builtins.__import__", side_effect=mock_import):
                result = dm.check_dependencies(["available_package", "missing_package", "another_available"])

        assert result == {"available_package": True, "missing_package": False, "another_available": True}

    def test_empty_package_list(self):
        """Test with empty package list."""
        from mzs_tools.plugin_utils.dependency_manager import DependencyManager

        with patch("mzs_tools.plugin_utils.dependency_manager.iface", MagicMock()):
            dm = DependencyManager()
            result = dm.check_dependencies([])

        assert result == {}


@pytest.mark.no_qgis
class TestPythonCommand:
    """Test python_command method for different platforms."""

    def test_conda_environment(self, tmp_path):
        """Test detection of conda environment."""
        from mzs_tools.plugin_utils.dependency_manager import DependencyManager

        conda_meta = tmp_path / "conda-meta"
        conda_meta.mkdir()

        with patch("mzs_tools.plugin_utils.dependency_manager.iface", MagicMock()):
            dm = DependencyManager()

            with patch("sys.prefix", str(tmp_path)):
                result = dm.python_command()

        assert result == "python"

    def test_windows_python_exe_exists(self, tmp_path):
        """Test Windows with python.exe available."""
        from mzs_tools.plugin_utils.dependency_manager import DependencyManager

        python_exe = tmp_path / "python.exe"
        python_exe.touch()

        with patch("mzs_tools.plugin_utils.dependency_manager.iface", MagicMock()):
            dm = DependencyManager()

            with patch("sys.prefix", str(tmp_path)), patch("platform.system", return_value="Windows"):
                result = dm.python_command()

        assert result == str(python_exe)

    def test_windows_python3_exe_exists(self, tmp_path):
        """Test Windows with python3.exe available."""
        from mzs_tools.plugin_utils.dependency_manager import DependencyManager

        python3_exe = tmp_path / "python3.exe"
        python3_exe.touch()

        with patch("mzs_tools.plugin_utils.dependency_manager.iface", MagicMock()):
            dm = DependencyManager()

            with patch("sys.prefix", str(tmp_path)), patch("platform.system", return_value="Windows"):
                result = dm.python_command()

        assert result == str(python3_exe)

    def test_windows_fallback_to_sys_executable(self, tmp_path):
        """Test Windows fallback when no python exe found."""
        from mzs_tools.plugin_utils.dependency_manager import DependencyManager

        with patch("mzs_tools.plugin_utils.dependency_manager.iface", MagicMock()):
            dm = DependencyManager()

            with (
                patch("sys.prefix", str(tmp_path)),
                patch("platform.system", return_value="Windows"),
                patch("sys.executable", "/path/to/python"),
            ):
                result = dm.python_command()

        assert result == "/path/to/python"

    def test_macos_python_in_prefix(self, tmp_path):
        """Test macOS with python in prefix directory."""
        from mzs_tools.plugin_utils.dependency_manager import DependencyManager

        python_file = tmp_path / "python"
        python_file.touch()

        with patch("mzs_tools.plugin_utils.dependency_manager.iface", MagicMock()):
            dm = DependencyManager()

            with (
                patch("sys.prefix", str(tmp_path)),
                patch("platform.system", return_value="Darwin"),
                patch("sys.executable", "/other/path/python"),
            ):
                result = dm.python_command()

        assert result == str(python_file)

    def test_macos_python3_in_bin(self, tmp_path):
        """Test macOS with python3 in bin subdirectory."""
        from mzs_tools.plugin_utils.dependency_manager import DependencyManager

        bin_dir = tmp_path / "bin"
        bin_dir.mkdir()
        python3_file = bin_dir / "python3"
        python3_file.touch()

        with patch("mzs_tools.plugin_utils.dependency_manager.iface", MagicMock()):
            dm = DependencyManager()

            with (
                patch("sys.prefix", str(tmp_path)),
                patch("platform.system", return_value="Darwin"),
                patch("sys.executable", "/other/path/python"),
            ):
                result = dm.python_command()

        assert result == str(python3_file)

    def test_macos_python_in_executable_parent(self, tmp_path):
        """Test macOS with python in sys.executable parent directory."""
        from mzs_tools.plugin_utils.dependency_manager import DependencyManager

        exec_dir = tmp_path / "exec"
        exec_dir.mkdir()
        python_file = exec_dir / "python"
        python_file.touch()

        with patch("mzs_tools.plugin_utils.dependency_manager.iface", MagicMock()):
            dm = DependencyManager()

            with (
                patch("sys.prefix", str(tmp_path / "other")),
                patch("platform.system", return_value="Darwin"),
                patch("sys.executable", str(exec_dir / "python_link")),
            ):
                result = dm.python_command()

        assert result == str(python_file)

    def test_macos_fallback_to_sys_executable(self, tmp_path):
        """Test macOS fallback to sys.executable."""
        from mzs_tools.plugin_utils.dependency_manager import DependencyManager

        with patch("mzs_tools.plugin_utils.dependency_manager.iface", MagicMock()):
            dm = DependencyManager()

            with (
                patch("sys.prefix", str(tmp_path)),
                patch("platform.system", return_value="Darwin"),
                patch("sys.executable", "/nonexistent/path/to/python3"),
            ):
                result = dm.python_command()

        assert result == "/nonexistent/path/to/python3"

    def test_linux_fallback(self):
        """Test Linux/other platforms fallback."""
        from mzs_tools.plugin_utils.dependency_manager import DependencyManager

        with patch("mzs_tools.plugin_utils.dependency_manager.iface", MagicMock()):
            dm = DependencyManager()

            with (
                patch("platform.system", return_value="Linux"),
                patch("sys.executable", "/nonexistent/path/to/python3"),
            ):
                result = dm.python_command()

        assert result == "/nonexistent/path/to/python3"


@pytest.mark.no_qgis
class TestCheckPythonDependencies:
    """Test check_python_dependencies method."""

    def test_all_dependencies_available(self, tmp_path):
        """Test when all required dependencies are available."""
        from mzs_tools.plugin_utils.dependency_manager import DependencyManager

        requirements_file = tmp_path / "requirements.txt"
        requirements_file.write_text("package1\npackage2\n")

        with (
            patch("mzs_tools.plugin_utils.dependency_manager.DIR_PLUGIN_ROOT", tmp_path),
            patch("mzs_tools.plugin_utils.dependency_manager.iface", MagicMock()),
        ):
            dm = DependencyManager()

            with patch("builtins.__import__", return_value=MagicMock()):
                result = dm.check_python_dependencies()

        assert result is True

    def test_some_dependencies_missing(self, tmp_path):
        """Test when some dependencies are missing."""
        from mzs_tools.plugin_utils.dependency_manager import DependencyManager

        requirements_file = tmp_path / "requirements.txt"
        requirements_file.write_text("available_package\nmissing_package\n")

        with (
            patch("mzs_tools.plugin_utils.dependency_manager.DIR_PLUGIN_ROOT", tmp_path),
            patch("mzs_tools.plugin_utils.dependency_manager.iface", MagicMock()),
        ):
            dm = DependencyManager()

            def mock_import(name, *args):
                if name == "missing_package":
                    raise ImportError("No module named 'missing_package'")
                return MagicMock()

            with patch("builtins.__import__", side_effect=mock_import):
                result = dm.check_python_dependencies()

        assert result is False


@pytest.mark.no_qgis
class TestInstallDependencies:
    """Test install_dependencies method."""

    def test_successful_installation(self, tmp_path):
        """Test successful package installation."""
        from mzs_tools.plugin_utils.dependency_manager import DependencyManager

        with patch("mzs_tools.plugin_utils.dependency_manager.iface", MagicMock()):
            dm = DependencyManager()
            dm.site_packages = tmp_path / "site-packages"

            with patch("mzs_tools.plugin_utils.dependency_manager.run_cmd", return_value=True) as mock_run_cmd:
                result = dm.install_dependencies(["package1", "package2"])

        assert result is True
        assert mock_run_cmd.called
        # Verify pip command structure
        args = mock_run_cmd.call_args[0][0]
        assert "pip" in args
        assert "install" in args
        assert f"--target={dm.site_packages}" in args
        assert "package1" in args
        assert "package2" in args

    def test_failed_installation(self, tmp_path):
        """Test failed package installation."""
        from mzs_tools.plugin_utils.dependency_manager import DependencyManager

        with patch("mzs_tools.plugin_utils.dependency_manager.iface", MagicMock()):
            dm = DependencyManager()
            dm.site_packages = tmp_path / "site-packages"

            with patch("mzs_tools.plugin_utils.dependency_manager.run_cmd", return_value=False):
                result = dm.install_dependencies(["package1"])

        assert result is False

    def test_installation_exception(self, tmp_path):
        """Test installation with exception."""
        from mzs_tools.plugin_utils.dependency_manager import DependencyManager

        with patch("mzs_tools.plugin_utils.dependency_manager.iface", MagicMock()):
            dm = DependencyManager()
            dm.site_packages = tmp_path / "site-packages"

            with patch("mzs_tools.plugin_utils.dependency_manager.run_cmd", side_effect=Exception("Test error")):
                result = dm.install_dependencies(["package1"])

        assert result is False

    def test_site_packages_directory_created(self, tmp_path):
        """Test that site-packages directory is created if it doesn't exist."""
        from mzs_tools.plugin_utils.dependency_manager import DependencyManager

        with patch("mzs_tools.plugin_utils.dependency_manager.iface", MagicMock()):
            dm = DependencyManager()
            dm.site_packages = tmp_path / "new_site_packages"

            with patch("mzs_tools.plugin_utils.dependency_manager.run_cmd", return_value=True):
                dm.install_dependencies(["package1"])

        assert dm.site_packages.exists()
