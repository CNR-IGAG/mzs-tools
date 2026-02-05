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

"""Unit tests for plugin metadata and version information."""

from mzs_tools.__about__ import (
    PLG_METADATA_FILE,
    __author__,
    __email__,
    __license__,
    __title__,
    __title_clean__,
    __version__,
    __version_info__,
    plugin_metadata_as_dict,
)


class TestPluginMetadata:
    """Test plugin metadata and version information."""

    def test_metadata_file_exists(self):
        """Test that metadata.txt file exists."""
        assert PLG_METADATA_FILE.exists()
        assert PLG_METADATA_FILE.is_file()

    def test_plugin_metadata_structure(self):
        """Test plugin metadata structure."""
        metadata = plugin_metadata_as_dict()
        assert isinstance(metadata, dict)
        assert "general" in metadata

        general = metadata["general"]
        assert "name" in general
        assert "version" in general
        assert "author" in general
        assert "email" in general

    def test_version_format(self):
        """Test version format and parsing."""
        assert isinstance(__version__, str)
        assert len(__version__) > 0

        # Version should contain dots or dashes
        assert "." in __version__ or "-" in __version__

        # Version info should be a tuple
        assert isinstance(__version_info__, tuple)
        assert len(__version_info__) >= 2

    def test_version_info_components(self):
        """Test version info tuple components."""
        # First component should be a number (major version)
        assert isinstance(__version_info__[0], int)
        # Second component should be a number (minor version)
        assert isinstance(__version_info__[1], int)

    def test_title_and_clean_title(self):
        """Test plugin title and clean title."""
        assert isinstance(__title__, str)
        assert len(__title__) > 0

        assert isinstance(__title_clean__, str)
        # Clean title should only contain alphanumeric characters
        assert __title_clean__.isalnum()

    def test_author_and_email(self):
        """Test author and email information."""
        assert isinstance(__author__, str)
        assert len(__author__) > 0

        assert isinstance(__email__, str)
        assert "@" in __email__  # Basic email validation

    def test_license(self):
        """Test license information."""
        assert isinstance(__license__, str)
        assert __license__ == "GPLv3"

    def test_metadata_consistency(self):
        """Test consistency between metadata file and variables."""
        metadata = plugin_metadata_as_dict()
        general = metadata["general"]

        assert general["name"] == __title__
        assert general["version"] == __version__
        assert general["author"] == __author__
        assert general["email"] == __email__

    def test_required_metadata_fields(self):
        """Test that all required metadata fields are present."""
        metadata = plugin_metadata_as_dict()
        general = metadata["general"]

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
            assert general[field], f"Required field '{field}' is empty"

    def test_qgis_version_format(self):
        """Test QGIS version format in metadata."""
        metadata = plugin_metadata_as_dict()
        general = metadata["general"]

        qgis_min = general.get("qgisminimumversion", "")
        assert qgis_min, "QGIS minimum version should be specified"

        # Should be in format X.Y or X.Y.Z
        version_parts = qgis_min.split(".")
        assert len(version_parts) >= 2, "QGIS version should have at least major.minor"

        # First two parts should be numeric
        assert version_parts[0].isdigit(), "Major version should be numeric"
        assert version_parts[1].isdigit(), "Minor version should be numeric"
