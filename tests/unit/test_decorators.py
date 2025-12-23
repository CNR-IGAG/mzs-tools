"""Unit tests for decorators and utility functions."""

import sqlite3
from unittest.mock import Mock, patch

import pytest

from mzs_tools.plugin_utils.misc import (
    retry_on_lock,
    skip_file_not_found,
)


class TestDecorators:
    """Test decorator functions."""

    def test_skip_file_not_found_decorator_success(self):
        """Test skip_file_not_found decorator when function succeeds."""

        @skip_file_not_found
        def test_function():
            return "success"

        # The decorator doesn't return the result, it just catches exceptions
        result = test_function()
        assert result is None  # The decorator swallows the return value

    @patch("mzs_tools.plugin_utils.misc.MzSToolsLogger")
    def test_skip_file_not_found_decorator_catches_error(self, mock_logger):
        """Test skip_file_not_found decorator catches FileNotFoundError."""

        @skip_file_not_found
        def test_function():
            raise FileNotFoundError("File not found")

        # Should not raise exception
        result = test_function()
        assert result is None

        # Should log the error
        mock_logger.log.assert_called_once()
        args, kwargs = mock_logger.log.call_args
        assert "File not found" in args[0]
        assert kwargs.get("log_level") == 1

    @patch("mzs_tools.plugin_utils.misc.MzSToolsLogger")
    def test_skip_file_not_found_decorator_other_exceptions(self, mock_logger):
        """Test skip_file_not_found decorator doesn't catch other exceptions."""

        @skip_file_not_found
        def test_function():
            raise ValueError("Different error")

        # Should raise the exception
        with pytest.raises(ValueError, match="Different error"):
            test_function()

        # Should not log anything
        mock_logger.log.assert_not_called()

    @patch("time.sleep")
    def test_retry_on_lock_decorator_success(self, mock_sleep):
        """Test retry_on_lock decorator when function succeeds."""
        mock_obj = Mock()
        mock_obj.log = Mock()

        @retry_on_lock(retries=3, delay=1)
        def test_function(self):
            return "success"

        result = test_function(mock_obj)
        assert result == "success"
        mock_sleep.assert_not_called()

    @patch("time.sleep")
    def test_retry_on_lock_decorator_succeeds_after_retry(self, mock_sleep):
        """Test retry_on_lock decorator succeeds after retry."""
        mock_obj = Mock()
        mock_obj.log = Mock()

        call_count = 0

        @retry_on_lock(retries=3, delay=1)
        def test_function(self):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise sqlite3.OperationalError("database is locked")
            return "success"

        result = test_function(mock_obj)
        assert result == "success"
        assert call_count == 2

        # Should log the retry
        mock_obj.log.assert_called_once()
        args, kwargs = mock_obj.log.call_args
        assert "Database is locked, retrying" in args[0]
        mock_sleep.assert_called_once_with(1)

    @patch("time.sleep")
    def test_retry_on_lock_decorator_max_retries_exceeded(self, mock_sleep):
        """Test retry_on_lock decorator when max retries exceeded."""
        mock_obj = Mock()
        mock_obj.log = Mock()

        @retry_on_lock(retries=2, delay=1)
        def test_function(self):
            raise sqlite3.OperationalError("database is locked")

        with pytest.raises(sqlite3.OperationalError, match="Database is locked after multiple retries"):
            test_function(mock_obj)

        # Should log retries
        assert mock_obj.log.call_count == 2
        assert mock_sleep.call_count == 2

    def test_retry_on_lock_decorator_other_operational_error(self):
        """Test retry_on_lock decorator with other OperationalError."""
        mock_obj = Mock()
        mock_obj.log = Mock()

        @retry_on_lock(retries=3, delay=1)
        def test_function(self):
            raise sqlite3.OperationalError("different error")

        with pytest.raises(sqlite3.OperationalError, match="different error"):
            test_function(mock_obj)

        # Should not log retries for other errors
        mock_obj.log.assert_not_called()

    def test_retry_on_lock_decorator_other_exception_type(self):
        """Test retry_on_lock decorator with non-OperationalError."""
        mock_obj = Mock()
        mock_obj.log = Mock()

        @retry_on_lock(retries=3, delay=1)
        def test_function(self):
            raise ValueError("different error type")

        with pytest.raises(ValueError, match="different error type"):
            test_function(mock_obj)

        # Should not log retries for other error types
        mock_obj.log.assert_not_called()

    def test_retry_on_lock_decorator_default_parameters(self):
        """Test retry_on_lock decorator with default parameters."""
        mock_obj = Mock()
        mock_obj.log = Mock()

        @retry_on_lock()  # Use defaults: retries=5, delay=1
        def test_function(self):
            return "success"

        result = test_function(mock_obj)
        assert result == "success"
