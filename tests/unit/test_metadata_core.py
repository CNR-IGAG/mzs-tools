"""Unit tests for plugin metadata that don't require QGIS imports."""

from configparser import ConfigParser
from pathlib import Path

import pytest


@pytest.mark.unit
class TestPluginMetadataCore:
    """Test plugin metadata functionality without QGIS dependencies."""

    def test_metadata_file_exists(self):
        """Test that metadata.txt file exists."""
        # Find the metadata file relative to the test
        plugin_root = Path(__file__).parent.parent.parent / "mzs_tools"
        metadata_file = plugin_root / "metadata.txt"

        assert metadata_file.exists(), f"Metadata file not found at {metadata_file}"
        assert metadata_file.is_file(), f"Metadata path is not a file: {metadata_file}"

    def test_metadata_parsing(self):
        """Test metadata.txt parsing."""
        plugin_root = Path(__file__).parent.parent.parent / "mzs_tools"
        metadata_file = plugin_root / "metadata.txt"

        config = ConfigParser()
        config.read(metadata_file, encoding="UTF-8")

        # Should have a general section
        assert "general" in config.sections()

        general = config["general"]

        # Check required fields
        required_fields = [
            "name",
            "version",
            "author",
            "email",
            "description",
            "qgisminimumversion",
            "repository",
            "homepage",
        ]

        for field in required_fields:
            assert field in general, f"Required field '{field}' missing from metadata"
            assert general[field].strip(), f"Required field '{field}' is empty"

    def test_version_format(self):
        """Test version format in metadata."""
        plugin_root = Path(__file__).parent.parent.parent / "mzs_tools"
        metadata_file = plugin_root / "metadata.txt"

        config = ConfigParser()
        config.read(metadata_file, encoding="UTF-8")

        version = config["general"]["version"]

        # Version should contain dots or dashes
        assert "." in version or "-" in version, f"Version format looks invalid: {version}"

        # Version should start with a digit
        assert version[0].isdigit(), f"Version should start with a digit: {version}"

    def test_email_format(self):
        """Test email format in metadata."""
        plugin_root = Path(__file__).parent.parent.parent / "mzs_tools"
        metadata_file = plugin_root / "metadata.txt"

        config = ConfigParser()
        config.read(metadata_file, encoding="UTF-8")

        email = config["general"]["email"]

        # Basic email validation
        assert "@" in email, f"Email should contain @: {email}"
        assert "." in email.split("@")[1], f"Email domain should contain dot: {email}"

    def test_qgis_version_format(self):
        """Test QGIS version format in metadata."""
        plugin_root = Path(__file__).parent.parent.parent / "mzs_tools"
        metadata_file = plugin_root / "metadata.txt"

        config = ConfigParser()
        config.read(metadata_file, encoding="UTF-8")

        qgis_min = config["general"]["qgisminimumversion"]

        # Should be in format X.Y or X.Y.Z
        version_parts = qgis_min.split(".")
        assert len(version_parts) >= 2, f"QGIS version should have at least major.minor: {qgis_min}"

        # First two parts should be numeric
        assert version_parts[0].isdigit(), f"QGIS major version should be numeric: {qgis_min}"
        assert version_parts[1].isdigit(), f"QGIS minor version should be numeric: {qgis_min}"

    def test_repository_url_format(self):
        """Test repository URL format in metadata."""
        plugin_root = Path(__file__).parent.parent.parent / "mzs_tools"
        metadata_file = plugin_root / "metadata.txt"

        config = ConfigParser()
        config.read(metadata_file, encoding="UTF-8")

        repository = config["general"]["repository"]

        # Should be a valid URL
        assert repository.startswith(("http://", "https://")), f"Repository should be a valid URL: {repository}"

        # Should contain github.com for this project
        assert "github.com" in repository, f"Repository should be on GitHub: {repository}"

    def test_icon_path_in_metadata(self):
        """Test icon path specification in metadata."""
        plugin_root = Path(__file__).parent.parent.parent / "mzs_tools"
        metadata_file = plugin_root / "metadata.txt"

        config = ConfigParser()
        config.read(metadata_file, encoding="UTF-8")

        if "icon" in config["general"]:
            icon_path = config["general"]["icon"]
            icon_file = plugin_root / icon_path

            assert icon_file.exists(), f"Icon file not found: {icon_file}"
            assert icon_path.endswith((".png", ".jpg", ".jpeg", ".svg")), f"Icon should be an image file: {icon_path}"
