import os
import site
import subprocess
import sys
from pathlib import Path

from qgis.core import QgsApplication
from qgis.PyQt.QtCore import QCoreApplication
from qgis.PyQt.QtWidgets import QMessageBox

from ..__about__ import DIR_PLUGIN_ROOT
from .logging import MzSToolsLogger


class DependencyManager:
    """Manages plugin-specific Python dependencies."""

    def __init__(self):
        self.log = MzSToolsLogger.log

        # Use QGIS profile directory for dependencies
        profile_path = Path(QgsApplication.qgisSettingsDirPath())
        self.site_packages = profile_path / "python" / "dependencies"

        # Ensure the directory exists and is in Python path
        self._ensure_path_setup()

    def _get_required_packages(self) -> list[str]:
        """Read required package names from requirements.txt file (for import checking).

        Returns:
            List of package names from requirements.txt (without version specifiers)
        """
        requirements_file = DIR_PLUGIN_ROOT / "requirements.txt"
        packages = []

        try:
            if requirements_file.exists():
                with open(requirements_file, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        # Skip empty lines and comments
                        if line and not line.startswith("#"):
                            # Extract package name (before any version specifiers or inline comments)
                            package_name = (
                                line.split("#")[0]
                                .split("==")[0]
                                .split(">=")[0]
                                .split("<=")[0]
                                .split(">")[0]
                                .split("<")[0]
                                .strip()
                            )
                            if package_name:
                                packages.append(package_name.lower())  # Convert to lowercase for consistency
            else:
                self.log("requirements.txt file not found, using default packages", log_level=1)
                packages = ["jaydebeapi"]  # Fallback to default

        except Exception as e:
            self.log(f"Error reading requirements.txt: {e}", log_level=1)
            packages = ["jaydebeapi"]  # Fallback to default

        return packages

    def _get_requirements_for_install(self) -> list[str]:
        """Read full requirement specifications from requirements.txt file (for pip install).

        Returns:
            List of full requirement specifications with version constraints
        """
        requirements_file = DIR_PLUGIN_ROOT / "requirements.txt"
        requirements = []

        try:
            if requirements_file.exists():
                with open(requirements_file, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        # Skip empty lines and comments
                        if line and not line.startswith("#"):
                            # Remove inline comments but keep the requirement specification
                            requirement = line.split("#")[0].strip()
                            if requirement:
                                requirements.append(requirement)
            else:
                self.log("requirements.txt file not found, using default requirements", log_level=1)
                requirements = ["jaydebeapi"]  # Fallback to default

        except Exception as e:
            self.log(f"Error reading requirements.txt: {e}", log_level=1)
            requirements = ["jaydebeapi"]  # Fallback to default

        return requirements

    def _ensure_path_setup(self):
        """Ensure site-packages directory exists and is in Python path."""
        self.site_packages.mkdir(parents=True, exist_ok=True)
        self._add_to_path()

    def install_dependencies(self, packages: list[str]) -> bool:
        """Install Python packages to plugin directory.

        Args:
            packages: List of package names to install

        Returns:
            True if installation successful, False otherwise
        """
        try:
            # Create site-packages directory if it doesn't exist
            self.site_packages.mkdir(exist_ok=True)

            # Build pip command - allow dependencies but suppress warnings
            cmd = [
                sys.executable,
                "-m",
                "pip",
                "install",
                f"--target={self.site_packages}",
                "--upgrade",
                "--quiet",  # Suppress dependency conflict warnings
            ] + packages

            # Environment to suppress pip warnings
            env = os.environ.copy()
            env["PIP_DISABLE_PIP_VERSION_CHECK"] = "1"
            env["PIP_NO_WARN_SCRIPT_LOCATION"] = "1"

            self.log(f"Installing dependencies: {', '.join(packages)}", log_level=0)

            result = subprocess.run(cmd, capture_output=True, text=True, env=env)

            # Check if installation was successful
            # Even with dependency warnings, installation often succeeds
            if result.returncode == 0 or "Successfully installed" in result.stdout:
                self._add_to_path()
                self.log(
                    self.tr("Successfully installed dependencies: {packages}").format(packages=", ".join(packages)),
                    log_level=3,  # Success
                )
                return True
            else:
                self.log(f"Installation failed: {result.stderr}", log_level=1)  # Warning
                return False

        except Exception as e:
            self.log(f"Installation error: {str(e)}", log_level=2)  # Critical
            return False

    def _add_to_path(self):
        """Add site-packages to Python path."""
        site_packages_str = str(self.site_packages)
        if site_packages_str not in sys.path:
            sys.path.insert(0, site_packages_str)
            site.addsitedir(site_packages_str)

    def check_dependencies(self, packages: list[str]) -> dict[str, bool]:
        """Check if packages are available.

        Returns:
            Dict mapping package names to availability status
        """
        results = {}
        self._add_to_path()  # Ensure our site-packages is in path

        for package in packages:
            try:
                __import__(package)
                results[package] = True
            except ImportError:
                results[package] = False

        return results

    def check_python_dependencies(self) -> bool:
        """Check if Python dependencies for Java connectivity are available.

        Returns:
            True if all dependencies are available, False otherwise
        """
        required_packages = self._get_required_packages()
        status = self.check_dependencies(required_packages)
        return all(status.values())

    def install_python_dependencies_interactive(self) -> bool:
        """Install Python dependencies for Java connectivity with user confirmation.

        Returns:
            True if installation successful, False otherwise
        """
        required_packages = self._get_required_packages()  # For display in dialog
        requirements_for_install = self._get_requirements_for_install()  # For actual pip install

        # Ask user for confirmation
        reply = QMessageBox.question(
            None,
            self.tr("Install Python Dependencies"),
            self.tr(
                "MzS Tools requires additional Python libraries ({packages}) for Access database support.\n\n"
                "Do you want to install them now using pip?\n\n"
                "Alternative: Use the QPIP plugin (recommended).\n\n"
                "Note: You will also need Java JRE installed on your system. Refer to the documentation for details."
            ).format(packages=", ".join(required_packages)),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,  # type: ignore
            QMessageBox.StandardButton.No,
        )

        if reply != QMessageBox.StandardButton.Yes:
            return False

        # Show installation progress
        self.log(
            self.tr("Installing Python dependencies. This may take a few moments..."),
            log_level=0,  # Info
            push=True,
            duration=10,
        )

        success = self.install_dependencies(requirements_for_install)  # Use full requirements with versions

        if success:
            self.log(
                self.tr("Python dependencies installed successfully. Make sure Java JRE is also installed."),
                log_level=3,  # Success
                push=True,
                duration=8,
            )
        else:
            self.log(
                self.tr("Failed to install Python dependencies. Please try using QPIP plugin."),
                log_level=2,  # Critical
                push=True,
                duration=10,
            )

        return success

    def tr(self, message: str) -> str:
        """Get the translation for a string using Qt translation API.

        :param message: string to be translated.
        :type message: str

        :returns: Translated version of message.
        :rtype: str
        """
        return QCoreApplication.translate(self.__class__.__name__, message)
