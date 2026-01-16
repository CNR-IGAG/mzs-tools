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

"""Unit tests for path utilities and file search functions."""

from mzs_tools.plugin_utils.misc import (
    get_file_path,
    get_path_for_name,
    get_subdir_path,
)


class TestPathUtils:
    """Test path utility functions."""

    def test_get_subdir_path_existing(self, tmp_path):
        """Test finding an existing subdirectory."""
        # Create test directory structure
        test_subdir = tmp_path / "TestSubDir"
        test_subdir.mkdir()

        result = get_subdir_path(tmp_path, "testsubdir")
        assert result == test_subdir

        # Test case sensitivity
        result = get_subdir_path(tmp_path, "TESTSUBDIR")
        assert result == test_subdir

    def test_get_subdir_path_nonexistent(self, tmp_path):
        """Test searching for non-existent subdirectory."""
        result = get_subdir_path(tmp_path, "nonexistent")
        assert result is None

    def test_get_subdir_path_nested(self, tmp_path):
        """Test finding subdirectory in nested structure."""
        # Create nested directory structure
        nested_dir = tmp_path / "level1" / "level2" / "TargetDir"
        nested_dir.mkdir(parents=True)

        result = get_subdir_path(tmp_path, "targetdir")
        assert result == nested_dir

    def test_get_file_path_existing(self, tmp_path):
        """Test finding an existing file."""
        # Create test file
        test_file = tmp_path / "TestFile.txt"
        test_file.write_text("test content")

        result = get_file_path(tmp_path, "testfile.txt")
        assert result == test_file

        # Test case sensitivity
        result = get_file_path(tmp_path, "TESTFILE.TXT")
        assert result == test_file

    def test_get_file_path_nonexistent(self, tmp_path):
        """Test searching for non-existent file."""
        result = get_file_path(tmp_path, "nonexistent.txt")
        assert result is None

    def test_get_file_path_nested(self, tmp_path):
        """Test finding file in nested structure."""
        # Create nested file structure
        nested_file = tmp_path / "level1" / "level2" / "target.txt"
        nested_file.parent.mkdir(parents=True)
        nested_file.write_text("test content")

        result = get_file_path(tmp_path, "target.txt")
        assert result == nested_file

    def test_get_path_for_name_file(self, tmp_path):
        """Test finding file with generic path search."""
        # Create test file
        test_file = tmp_path / "TestItem.txt"
        test_file.write_text("test content")

        result = get_path_for_name(tmp_path, "testitem.txt")
        assert result == test_file

    def test_get_path_for_name_directory(self, tmp_path):
        """Test finding directory with generic path search."""
        # Create test directory
        test_dir = tmp_path / "TestItem"
        test_dir.mkdir()

        result = get_path_for_name(tmp_path, "testitem")
        assert result == test_dir

    def test_get_path_for_name_nonexistent(self, tmp_path):
        """Test searching for non-existent path."""
        result = get_path_for_name(tmp_path, "nonexistent")
        assert result is None

    def test_get_path_for_name_priority(self, tmp_path):
        """Test that files are found before directories when names match."""
        # Create both file and directory with same name
        test_file = tmp_path / "TestItem.txt"
        test_file.write_text("test content")
        test_dir = tmp_path / "nested" / "TestItem"
        test_dir.mkdir(parents=True)

        result = get_path_for_name(tmp_path, "testitem.txt")
        assert result == test_file

        result = get_path_for_name(tmp_path, "testitem")
        # Should find the directory since we're looking for exact name match
        assert result == test_dir
