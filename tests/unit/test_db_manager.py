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

"""Unit tests for DatabaseManager class."""

import sqlite3
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from mzs_tools.core.db_manager import DatabaseError, DatabaseManager


@pytest.fixture
def temp_db_path(tmp_path):
    """Create a temporary database path."""
    return tmp_path / "test.db"


@pytest.fixture
def db_manager(temp_db_path):
    """Create a DatabaseManager instance with a temporary database."""
    db = DatabaseManager(temp_db_path)
    db.connect(create_if_missing=True)
    yield db
    db.disconnect()
    # Clean up the database file
    if temp_db_path.exists():
        temp_db_path.unlink()


@pytest.fixture
def db_with_test_table(db_manager):
    """Create a DatabaseManager with a test table already set up."""
    db_manager.execute_script(
        """
        CREATE TABLE test_table (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            value INTEGER
        )
        """
    )
    return db_manager


class TestDatabaseManagerInit:
    """Tests for DatabaseManager initialization."""

    def test_init_creates_instance(self, temp_db_path):
        """Test that DatabaseManager can be instantiated."""
        db = DatabaseManager(temp_db_path)
        assert db.db_path == temp_db_path
        assert db.connection is None
        assert callable(db.log)

    def test_init_with_logger(self, temp_db_path):
        """Test that DatabaseManager accepts a logger."""
        mock_logger = MagicMock()
        mock_logger.log = MagicMock()
        db = DatabaseManager(temp_db_path, logger=mock_logger)
        assert db.log == mock_logger.log

    def test_init_without_logger(self, temp_db_path):
        """Test that DatabaseManager works without a logger."""
        db = DatabaseManager(temp_db_path, logger=None)
        # Should not raise an error when calling log
        db.log("Test message", log_level=4)


class TestDatabaseManagerConnection:
    """Tests for database connection management."""

    def test_connect_creates_new_database(self, temp_db_path):
        """Test that connect creates a new database file with create_if_missing=True."""
        db = DatabaseManager(temp_db_path)
        assert not temp_db_path.exists()
        db.connect(create_if_missing=True)
        assert temp_db_path.exists()
        assert db.is_connected()
        db.disconnect()

    def test_connect_to_nonexistent_file(self):
        """Test connection to non-existent database in non-existent directory fails."""
        db = DatabaseManager(Path("/nonexistent/directory/db.sqlite"))
        with pytest.raises(DatabaseError, match="Database file does not exist"):
            db.connect()

    def test_connect_to_empty_file(self, temp_db_path):
        """Test connection to empty (corrupted) database fails."""
        # Create an empty file
        temp_db_path.touch()
        db = DatabaseManager(temp_db_path)
        with pytest.raises(DatabaseError, match="Database file is empty"):
            db.connect()

    def test_connect_twice_does_not_create_new_connection(self, db_manager):
        """Test that calling connect twice doesn't create a new connection."""
        first_connection = db_manager.connection
        result = db_manager.connect()
        assert result is True
        assert db_manager.connection is first_connection

    def test_disconnect_closes_connection(self, db_manager):
        """Test that disconnect closes the connection."""
        assert db_manager.is_connected()
        db_manager.disconnect()
        assert not db_manager.is_connected()

    def test_disconnect_without_connection(self, temp_db_path):
        """Test that disconnect without connection doesn't raise error."""
        db = DatabaseManager(temp_db_path)
        db.disconnect()  # Should not raise an error

    def test_is_connected_returns_false_initially(self, temp_db_path):
        """Test that is_connected returns False before connecting."""
        db = DatabaseManager(temp_db_path)
        assert not db.is_connected()


class TestDatabaseManagerContextManager:
    """Tests for context manager functionality."""

    def test_context_manager_connects_and_disconnects(self, temp_db_path):
        """Test that context manager handles connection lifecycle."""
        # Create and initialize database first using sqlite3
        conn = sqlite3.connect(str(temp_db_path))
        conn.execute("CREATE TABLE test (id INTEGER)")
        conn.commit()
        conn.close()

        with DatabaseManager(temp_db_path) as db:
            assert db.is_connected()
        assert not db.is_connected()

    def test_context_manager_disconnects_on_error(self, temp_db_path):
        """Test that context manager disconnects even on error."""
        # Create and initialize database first using sqlite3
        conn = sqlite3.connect(str(temp_db_path))
        conn.execute("CREATE TABLE test (id INTEGER)")
        conn.commit()
        conn.close()

        with pytest.raises(ValueError):
            with DatabaseManager(temp_db_path) as db:
                assert db.is_connected()
                raise ValueError("Test error")
        # Connection should be closed (can't easily verify without accessing internals)


class TestDatabaseManagerQueries:
    """Tests for query execution."""

    def test_execute_query_fetch_all(self, db_with_test_table):
        """Test execute_query with fetch_mode='all'."""
        db_with_test_table.execute_update("INSERT INTO test_table (name, value) VALUES (?, ?)", ("Test1", 10))
        db_with_test_table.execute_update("INSERT INTO test_table (name, value) VALUES (?, ?)", ("Test2", 20))

        rows = db_with_test_table.execute_query("SELECT * FROM test_table ORDER BY id")
        assert len(rows) == 2
        assert rows[0][1] == "Test1"
        assert rows[1][1] == "Test2"

    def test_execute_query_fetch_one(self, db_with_test_table):
        """Test execute_query with fetch_mode='one'."""
        db_with_test_table.execute_update("INSERT INTO test_table (name, value) VALUES (?, ?)", ("Test", 100))

        row = db_with_test_table.execute_query("SELECT * FROM test_table WHERE name = ?", ("Test",), fetch_mode="one")
        assert row is not None
        assert row[1] == "Test"
        assert row[2] == 100

    def test_execute_query_fetch_one_no_result(self, db_with_test_table):
        """Test execute_query with fetch_mode='one' when no rows match."""
        row = db_with_test_table.execute_query(
            "SELECT * FROM test_table WHERE name = ?", ("NonExistent",), fetch_mode="one"
        )
        assert row is None

    def test_execute_query_fetch_value(self, db_with_test_table):
        """Test execute_query with fetch_mode='value'."""
        db_with_test_table.execute_update("INSERT INTO test_table (name, value) VALUES (?, ?)", ("Test1", 10))
        db_with_test_table.execute_update("INSERT INTO test_table (name, value) VALUES (?, ?)", ("Test2", 20))

        count = db_with_test_table.execute_query("SELECT COUNT(*) FROM test_table", fetch_mode="value")
        assert count == 2

    def test_execute_query_fetch_value_no_result(self, db_with_test_table):
        """Test execute_query with fetch_mode='value' when no rows exist."""
        value = db_with_test_table.execute_query(
            "SELECT name FROM test_table WHERE id = ?", (999,), fetch_mode="value"
        )
        assert value is None

    def test_execute_query_invalid_fetch_mode(self, db_with_test_table):
        """Test execute_query with invalid fetch_mode raises error."""
        with pytest.raises(DatabaseError, match="Invalid fetch_mode"):
            db_with_test_table.execute_query("SELECT * FROM test_table", fetch_mode="invalid")

    def test_execute_query_without_connection(self, temp_db_path):
        """Test execute_query without connection raises error."""
        db = DatabaseManager(temp_db_path)
        with pytest.raises(DatabaseError, match="No active database connection"):
            db.execute_query("SELECT 1")

    def test_execute_query_sql_error(self, db_manager):
        """Test execute_query with invalid SQL raises DatabaseError."""
        with pytest.raises(DatabaseError, match="Query execution failed"):
            db_manager.execute_query("SELECT * FROM nonexistent_table")


class TestDatabaseManagerUpdates:
    """Tests for update/insert/delete operations."""

    def test_execute_update_insert(self, db_with_test_table):
        """Test execute_update with INSERT returns last row ID."""
        row_id = db_with_test_table.execute_update("INSERT INTO test_table (name, value) VALUES (?, ?)", ("Test", 42))
        assert row_id > 0
        # Verify the insert
        count = db_with_test_table.get_row_count("test_table")
        assert count == 1

    def test_execute_update_update(self, db_with_test_table):
        """Test execute_update with UPDATE returns affected row count."""
        db_with_test_table.execute_update("INSERT INTO test_table (name, value) VALUES (?, ?)", ("Test1", 10))
        db_with_test_table.execute_update("INSERT INTO test_table (name, value) VALUES (?, ?)", ("Test2", 20))

        affected = db_with_test_table.execute_update("UPDATE test_table SET value = ? WHERE name = ?", (99, "Test1"))
        assert affected == 1

    def test_execute_update_delete(self, db_with_test_table):
        """Test execute_update with DELETE returns affected row count."""
        db_with_test_table.execute_update("INSERT INTO test_table (name, value) VALUES (?, ?)", ("Test1", 10))
        db_with_test_table.execute_update("INSERT INTO test_table (name, value) VALUES (?, ?)", ("Test2", 20))

        affected = db_with_test_table.execute_update("DELETE FROM test_table WHERE name = ?", ("Test1",))
        assert affected == 1
        assert db_with_test_table.get_row_count("test_table") == 1

    def test_execute_update_without_commit(self, db_with_test_table):
        """Test execute_update with commit=False doesn't commit."""
        db_with_test_table.execute_update(
            "INSERT INTO test_table (name, value) VALUES (?, ?)", ("Test", 10), commit=False
        )
        # Manually commit
        db_with_test_table.connection.commit()
        assert db_with_test_table.get_row_count("test_table") == 1

    def test_execute_update_sql_error(self, db_with_test_table):
        """Test execute_update with SQL error raises DatabaseError and rolls back."""
        # Try to insert duplicate primary key
        db_with_test_table.execute_update("INSERT INTO test_table (id, name, value) VALUES (?, ?, ?)", (1, "Test", 10))
        with pytest.raises(DatabaseError, match="Update execution failed"):
            db_with_test_table.execute_update(
                "INSERT INTO test_table (id, name, value) VALUES (?, ?, ?)", (1, "Test2", 20)
            )
        # Should still have only one row
        assert db_with_test_table.get_row_count("test_table") == 1

    def test_execute_update_without_connection(self, temp_db_path):
        """Test execute_update without connection raises error."""
        db = DatabaseManager(temp_db_path)
        with pytest.raises(DatabaseError, match="No active database connection"):
            db.execute_update("UPDATE test SET value = 1")


class TestDatabaseManagerScripts:
    """Tests for script execution."""

    def test_execute_script(self, db_manager):
        """Test execute_script with multiple statements."""
        script = """
            CREATE TABLE test1 (id INTEGER);
            CREATE TABLE test2 (id INTEGER);
            INSERT INTO test1 VALUES (1);
            INSERT INTO test2 VALUES (2);
        """
        db_manager.execute_script(script)
        assert db_manager.table_exists("test1")
        assert db_manager.table_exists("test2")

    def test_execute_script_with_error(self, db_manager):
        """Test execute_script with error rolls back."""
        script = """
            CREATE TABLE test (id INTEGER PRIMARY KEY);
            INSERT INTO test VALUES (1);
            INSERT INTO test VALUES (1);
        """
        with pytest.raises(DatabaseError, match="Script execution failed"):
            db_manager.execute_script(script)

    def test_execute_script_file(self, db_manager, tmp_path):
        """Test execute_script_file reads and executes SQL file."""
        script_file = tmp_path / "test_script.sql"
        script_file.write_text("CREATE TABLE test_from_file (id INTEGER);")

        db_manager.execute_script_file(script_file)
        assert db_manager.table_exists("test_from_file")

    def test_execute_script_file_nonexistent(self, db_manager, tmp_path):
        """Test execute_script_file with nonexistent file raises error."""
        with pytest.raises(DatabaseError, match="Script file execution failed"):
            db_manager.execute_script_file(tmp_path / "nonexistent.sql")


class TestDatabaseManagerTransactions:
    """Tests for transaction handling."""

    def test_transaction_commits_on_success(self, db_with_test_table):
        """Test that transaction commits on success."""
        with db_with_test_table.transaction() as cursor:
            cursor.execute("INSERT INTO test_table (name, value) VALUES (?, ?)", ("Test", 42))

        # Verify data was committed
        assert db_with_test_table.get_row_count("test_table") == 1

    def test_transaction_rollback_on_error(self, db_with_test_table):
        """Test that transaction rolls back on error."""
        with pytest.raises(Exception):
            with db_with_test_table.transaction() as cursor:
                cursor.execute("INSERT INTO test_table (name, value) VALUES (?, ?)", ("Test", 42))
                # Force an error
                raise ValueError("Test error")

        # Verify rollback occurred
        assert db_with_test_table.get_row_count("test_table") == 0

    def test_transaction_rollback_on_constraint_violation(self, db_with_test_table):
        """Test that transaction rolls back on constraint violation."""
        with pytest.raises(Exception):
            with db_with_test_table.transaction() as cursor:
                cursor.execute("INSERT INTO test_table (id, name, value) VALUES (?, ?, ?)", (1, "Test1", 10))
                # Try to insert duplicate primary key
                cursor.execute("INSERT INTO test_table (id, name, value) VALUES (?, ?, ?)", (1, "Test2", 20))

        # Verify rollback occurred - no rows should exist
        assert db_with_test_table.get_row_count("test_table") == 0


class TestDatabaseManagerHelpers:
    """Tests for helper methods."""

    def test_table_exists_true(self, db_with_test_table):
        """Test table_exists returns True for existing table."""
        assert db_with_test_table.table_exists("test_table")

    def test_table_exists_false(self, db_manager):
        """Test table_exists returns False for non-existing table."""
        assert not db_manager.table_exists("nonexistent_table")

    def test_get_row_count_no_where_clause(self, db_with_test_table):
        """Test get_row_count without WHERE clause."""
        db_with_test_table.execute_update("INSERT INTO test_table (name, value) VALUES (?, ?)", ("Test1", 10))
        db_with_test_table.execute_update("INSERT INTO test_table (name, value) VALUES (?, ?)", ("Test2", 20))
        assert db_with_test_table.get_row_count("test_table") == 2

    def test_get_row_count_with_where_clause(self, db_with_test_table):
        """Test get_row_count with WHERE clause."""
        db_with_test_table.execute_update("INSERT INTO test_table (name, value) VALUES (?, ?)", ("Test1", 10))
        db_with_test_table.execute_update("INSERT INTO test_table (name, value) VALUES (?, ?)", ("Test2", 20))
        assert db_with_test_table.get_row_count("test_table", "value > ?", (15,)) == 1

    def test_get_row_count_empty_table(self, db_with_test_table):
        """Test get_row_count on empty table returns 0."""
        assert db_with_test_table.get_row_count("test_table") == 0

    def test_get_sequence_value(self, db_with_test_table):
        """Test get_sequence_value returns correct value."""
        db_with_test_table.execute_update("INSERT INTO test_table (name, value) VALUES (?, ?)", ("Test1", 10))
        db_with_test_table.execute_update("INSERT INTO test_table (name, value) VALUES (?, ?)", ("Test2", 20))
        assert db_with_test_table.get_sequence_value("test_table") == 2

    def test_get_sequence_value_no_sequence(self, db_manager):
        """Test get_sequence_value returns 0 for non-existent sequence."""
        assert db_manager.get_sequence_value("nonexistent_table") == 0

    def test_reset_sequence(self, db_with_test_table):
        """Test reset_sequence sets sequence to specified value."""
        db_with_test_table.execute_update("INSERT INTO test_table (name, value) VALUES (?, ?)", ("Test1", 10))
        db_with_test_table.reset_sequence("test_table", 0)
        assert db_with_test_table.get_sequence_value("test_table") == 0

    def test_reset_sequence_default_value(self, db_with_test_table):
        """Test reset_sequence with default value of 0."""
        db_with_test_table.execute_update("INSERT INTO test_table (name, value) VALUES (?, ?)", ("Test1", 10))
        db_with_test_table.reset_sequence("test_table")
        assert db_with_test_table.get_sequence_value("test_table") == 0


class TestDatabaseManagerCursor:
    """Tests for cursor context manager."""

    def test_cursor_context_manager(self, db_manager):
        """Test cursor context manager closes cursor after use."""
        with db_manager.cursor() as cursor:
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            assert result == (1,)
        # Cursor should be closed now (can't easily verify without accessing internals)

    def test_cursor_context_manager_with_error(self, db_manager):
        """Test cursor context manager closes cursor even on error."""
        with pytest.raises(Exception):
            with db_manager.cursor() as cursor:
                cursor.execute("SELECT 1")
                raise ValueError("Test error")
        # Cursor should still be closed

    def test_cursor_without_connection(self, temp_db_path):
        """Test cursor context manager without connection raises error."""
        db = DatabaseManager(temp_db_path)
        with pytest.raises(DatabaseError, match="No active database connection"):
            with db.cursor():
                pass
