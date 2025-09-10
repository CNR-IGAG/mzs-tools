"""Unit tests for path utilities and file search functions."""

import tempfile
from pathlib import Path

import pytest

from mzs_tools.plugin_utils.misc import (
    get_file_path,
    get_path_for_name,
    get_subdir_path,
)


@pytest.mark.unit
class TestPathUtils:
    """Test path utility functions."""

    def test_get_subdir_path_existing(self):
        """Test finding an existing subdirectory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create test directory structure
            test_subdir = temp_path / "TestSubDir"
            test_subdir.mkdir()

            result = get_subdir_path(temp_path, "testsubdir")
            assert result == test_subdir

            # Test case sensitivity
            result = get_subdir_path(temp_path, "TESTSUBDIR")
            assert result == test_subdir

    def test_get_subdir_path_nonexistent(self):
        """Test searching for non-existent subdirectory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            result = get_subdir_path(temp_path, "nonexistent")
            assert result is None

    def test_get_subdir_path_nested(self):
        """Test finding subdirectory in nested structure."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create nested directory structure
            nested_dir = temp_path / "level1" / "level2" / "TargetDir"
            nested_dir.mkdir(parents=True)

            result = get_subdir_path(temp_path, "targetdir")
            assert result == nested_dir

    def test_get_file_path_existing(self):
        """Test finding an existing file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create test file
            test_file = temp_path / "TestFile.txt"
            test_file.write_text("test content")

            result = get_file_path(temp_path, "testfile.txt")
            assert result == test_file

            # Test case sensitivity
            result = get_file_path(temp_path, "TESTFILE.TXT")
            assert result == test_file

    def test_get_file_path_nonexistent(self):
        """Test searching for non-existent file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            result = get_file_path(temp_path, "nonexistent.txt")
            assert result is None

    def test_get_file_path_nested(self):
        """Test finding file in nested structure."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create nested file structure
            nested_file = temp_path / "level1" / "level2" / "target.txt"
            nested_file.parent.mkdir(parents=True)
            nested_file.write_text("test content")

            result = get_file_path(temp_path, "target.txt")
            assert result == nested_file

    def test_get_path_for_name_file(self):
        """Test finding file with generic path search."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create test file
            test_file = temp_path / "TestItem.txt"
            test_file.write_text("test content")

            result = get_path_for_name(temp_path, "testitem.txt")
            assert result == test_file

    def test_get_path_for_name_directory(self):
        """Test finding directory with generic path search."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create test directory
            test_dir = temp_path / "TestItem"
            test_dir.mkdir()

            result = get_path_for_name(temp_path, "testitem")
            assert result == test_dir

    def test_get_path_for_name_nonexistent(self):
        """Test searching for non-existent path."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            result = get_path_for_name(temp_path, "nonexistent")
            assert result is None

    def test_get_path_for_name_priority(self):
        """Test that files are found before directories when names match."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create both file and directory with same name
            test_file = temp_path / "TestItem.txt"
            test_file.write_text("test content")
            test_dir = temp_path / "nested" / "TestItem"
            test_dir.mkdir(parents=True)

            result = get_path_for_name(temp_path, "testitem.txt")
            assert result == test_file

            result = get_path_for_name(temp_path, "testitem")
            # Should find the directory since we're looking for exact name match
            assert result == test_dir
