"""Unit tests for common utility functions."""

from unittest.mock import Mock, patch

import pytest

from mzs_tools.tasks.common_functions import setup_mdb_connection


class TestCommonFunctions:
    """Test common utility functions."""

    @patch("mzs_tools.tasks.common_functions.AccessDbConnection")
    def test_setup_mdb_connection_success(self, mock_access_db):
        """Test successful MDB connection setup."""
        # Setup mock
        mock_conn = Mock()
        mock_conn.open.return_value = True
        mock_access_db.return_value = mock_conn

        # Test
        connected, conn = setup_mdb_connection("/path/to/test.mdb")

        # Assertions
        assert connected is True
        assert conn is mock_conn
        mock_access_db.assert_called_once_with("/path/to/test.mdb", password=None)
        mock_conn.open.assert_called_once()

    @patch("mzs_tools.tasks.common_functions.AccessDbConnection")
    def test_setup_mdb_connection_with_password(self, mock_access_db):
        """Test MDB connection setup with password."""
        # Setup mock
        mock_conn = Mock()
        mock_conn.open.return_value = True
        mock_access_db.return_value = mock_conn

        # Test
        connected, conn = setup_mdb_connection("/path/to/test.mdb", password="secret")

        # Assertions
        assert connected is True
        assert conn is mock_conn
        mock_access_db.assert_called_once_with("/path/to/test.mdb", password="secret")
        mock_conn.open.assert_called_once()

    @patch("mzs_tools.tasks.common_functions.AccessDbConnection")
    def test_setup_mdb_connection_failure(self, mock_access_db):
        """Test MDB connection setup failure."""
        # Setup mock
        mock_conn = Mock()
        mock_conn.open.return_value = False
        mock_access_db.return_value = mock_conn

        # Test
        connected, conn = setup_mdb_connection("/path/to/test.mdb")

        # Assertions
        assert connected is False
        assert conn is mock_conn
        mock_access_db.assert_called_once_with("/path/to/test.mdb", password=None)
        mock_conn.open.assert_called_once()

    @patch("mzs_tools.tasks.common_functions.AccessDbConnection")
    def test_setup_mdb_connection_exception(self, mock_access_db):
        """Test MDB connection setup with exception."""
        # Setup mock to raise exception
        mock_access_db.side_effect = Exception("Connection failed")

        # Test
        with pytest.raises(Exception, match="Connection failed"):
            setup_mdb_connection("/path/to/test.mdb")

    @patch("mzs_tools.tasks.common_functions.AccessDbConnection")
    def test_setup_mdb_connection_open_exception(self, mock_access_db):
        """Test MDB connection setup with exception during open."""
        # Setup mock
        mock_conn = Mock()
        mock_conn.open.side_effect = Exception("Open failed")
        mock_access_db.return_value = mock_conn

        # Test
        with pytest.raises(Exception, match="Open failed"):
            setup_mdb_connection("/path/to/test.mdb")
