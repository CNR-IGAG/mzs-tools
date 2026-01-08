"""Unit tests for AccessDbConnection date validation."""

from unittest.mock import MagicMock, patch

import pytest


class TestAccessDbDateValidation:
    """Test date validation in AccessDbConnection."""

    @pytest.fixture
    def mock_connection(self):
        """Create a mock AccessDbConnection without actually connecting to a database."""
        # Mock the imports at import time, not in sys.modules
        with patch.dict(
            "sys.modules",
            {
                "jaydebeapi": MagicMock(),
                "jpype": MagicMock(),
                "jpype.imports": MagicMock(),
                "jpype.types": MagicMock(),
            },
        ):
            # Import happens inside the context manager
            from mzs_tools.tasks import access_db_connection

            # Mock the connection initialization to avoid actual DB connection
            with patch.object(access_db_connection.AccessDbConnection, "__init__", lambda self, db_path: None):
                conn = access_db_connection.AccessDbConnection("/fake/path.mdb")
                conn.log = MagicMock()
                conn.connection = MagicMock()
                conn.cursor = MagicMock()

                # Get the actual _validate_date method from the class
                # and bind it to our instance
                conn._validate_date = access_db_connection.AccessDbConnection._validate_date.__get__(conn)

                yield conn

    def test_validate_date_iso_format(self, mock_connection):
        """Test validation of ISO format date (yyyy-MM-dd)."""
        result = mock_connection._validate_date("2024-11-06")
        assert result == "2024-11-06"

    def test_validate_date_dd_mm_yyyy(self, mock_connection):
        """Test validation of dd/MM/yyyy format - returns ISO format."""
        result = mock_connection._validate_date("06/11/2024")
        assert result == "2024-11-06"

    def test_validate_date_mm_dd_yyyy(self, mock_connection):
        """Test validation of MM/dd/yyyy format - returns ISO format.
        Using 13/06/2024 to disambiguate from dd/MM/yyyy (13 can only be a day)."""
        result = mock_connection._validate_date("06/13/2024")
        assert result == "2024-06-13"

    def test_validate_date_yyyy_mm_dd_slash(self, mock_connection):
        """Test validation of yyyy/MM/dd format - returns ISO format."""
        result = mock_connection._validate_date("2024/11/06")
        assert result == "2024-11-06"

    def test_validate_date_dd_mm_yyyy_dash(self, mock_connection):
        """Test validation of dd-MM-yyyy format - returns ISO format."""
        result = mock_connection._validate_date("06-11-2024")
        assert result == "2024-11-06"

    def test_validate_date_yyyymmdd(self, mock_connection):
        """Test validation of yyyyMMdd format - returns ISO format."""
        result = mock_connection._validate_date("20241106")
        assert result == "2024-11-06"

    def test_validate_date_empty_string(self, mock_connection):
        """Test validation of empty string."""
        result = mock_connection._validate_date("")
        assert result is None

    def test_validate_date_none(self, mock_connection):
        """Test validation of None."""
        result = mock_connection._validate_date(None)
        assert result is None

    def test_validate_date_whitespace_only(self, mock_connection):
        """Test validation of whitespace-only string."""
        result = mock_connection._validate_date("   ")
        assert result is None

    def test_validate_date_invalid_format(self, mock_connection):
        """Test validation of invalid date format."""
        result = mock_connection._validate_date("06-November-2024")
        assert result is None
        mock_connection.log.assert_called()

    def test_validate_date_invalid_values(self, mock_connection):
        """Test validation of invalid date values."""
        result = mock_connection._validate_date("99/99/9999")
        assert result is None
        mock_connection.log.assert_called()

    def test_validate_date_with_spaces(self, mock_connection):
        """Test validation of date with leading/trailing spaces."""
        result = mock_connection._validate_date("  2024-11-06  ")
        assert result == "2024-11-06"

    def test_validate_date_partial_date(self, mock_connection):
        """Test validation of partial date."""
        result = mock_connection._validate_date("2024-11")
        assert result is None
        mock_connection.log.assert_called()

    def test_validate_date_text(self, mock_connection):
        """Test validation of plain text."""
        result = mock_connection._validate_date("not a date")
        assert result is None
        mock_connection.log.assert_called()

    def test_validate_datetime_iso_format(self, mock_connection):
        """Test validation of ISO datetime format (yyyy-MM-dd HH:mm:ss) - returns ISO date."""
        result = mock_connection._validate_date("2024-11-06 14:30:00")
        assert result == "2024-11-06"

    def test_validate_datetime_dd_mm_yyyy(self, mock_connection):
        """Test validation of dd/MM/yyyy HH:mm:ss format - returns ISO date."""
        result = mock_connection._validate_date("06/11/2024 14:30:00")
        assert result == "2024-11-06"

    def test_validate_datetime_with_midnight(self, mock_connection):
        """Test validation of datetime with midnight time - returns ISO date."""
        result = mock_connection._validate_date("06/11/2024 00:00:00")
        assert result == "2024-11-06"

    def test_validate_datetime_short_time(self, mock_connection):
        """Test validation of datetime with HH:mm format - returns ISO date."""
        result = mock_connection._validate_date("2024-11-06 14:30")
        assert result == "2024-11-06"

    def test_validate_datetime_with_extra_spaces(self, mock_connection):
        """Test validation of datetime with extra spaces - returns ISO date."""
        result = mock_connection._validate_date("  06/11/2024 14:30:00  ")
        assert result == "2024-11-06"

    def test_validate_datetime_dd_mm_yyyy_dash(self, mock_connection):
        """Test validation of dd-MM-yyyy HH:mm:ss format - returns ISO date."""
        result = mock_connection._validate_date("06-11-2024 23:59:59")
        assert result == "2024-11-06"
