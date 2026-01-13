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

"""Database Manager for MzS Tools.

This module provides a centralized database management layer with automatic error handling,
connection management, and common database operations.
"""

import traceback
from contextlib import contextmanager
from pathlib import Path
from typing import Any, List, Literal, Optional, Tuple, Union, overload

from qgis.utils import spatialite_connect


class DatabaseError(Exception):
    """Custom exception for database operations."""

    pass


class DatabaseManager:
    """Manages database connections and operations with automatic error handling.

    This class provides a centralized interface for database operations, including:
    - Connection lifecycle management
    - Automatic error handling and logging
    - Context managers for safe cursor operations
    - Wrapper methods for common database operations
    - Transaction management with automatic rollback on errors

    Attributes:
        db_path: Path to the SQLite/SpatiaLite database file
        connection: Active database connection (None if not connected)
        logger: Logger function for error and debug messages
    """

    def __init__(self, db_path: Path, logger=None):
        """Initialize the DatabaseManager.

        Args:
            db_path: Path to the database file
            logger: Optional logger object with a log() method (dependency injection pattern)
        """
        self.db_path = db_path
        self.connection = None
        # Use logger's log method directly, or a no-op function if no logger provided
        self.log = logger.log if logger and hasattr(logger, "log") else lambda *args, **kwargs: None

    def connect(self, create_if_missing: bool = False) -> bool:
        """Establish a connection to the database.

        Args:
            create_if_missing: If True, create a new database file if it doesn't exist (useful for testing)

        Returns:
            True if connection successful, False otherwise

        Raises:
            DatabaseError: If database file is empty or connection fails
        """
        if self.connection:
            self.log("Database connection already exists", log_level=4)
            return True

        self.log(f"Creating database connection to {self.db_path}...", log_level=4)

        # Check if database file exists
        if not self.db_path.exists():
            if not create_if_missing:
                raise DatabaseError(f"Database file does not exist: {self.db_path}")
            # Ensure parent directory exists for new database
            self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # Check if existing database file is empty (corrupted)
        if self.db_path.exists() and self.db_path.stat().st_size == 0:
            raise DatabaseError(f"Database file is empty (corrupted): {self.db_path}")

        try:
            self.connection = spatialite_connect(str(self.db_path))
            # Validate connection with a quick check (skip for newly created databases)
            if self.db_path.exists() and self.db_path.stat().st_size > 0:
                with self.cursor() as cursor:
                    cursor.execute("PRAGMA quick_check")
            self.log("Database connection established successfully", log_level=4)
            return True
        except Exception as e:
            self.log(f"Error connecting to database: {e}", log_level=2, push=True, duration=0)
            self.log(traceback.format_exc(), log_level=2)
            self.connection = None
            raise DatabaseError(f"Failed to connect to database: {e}") from e

    def disconnect(self):
        """Close the database connection safely."""
        if self.connection:
            try:
                self.connection.close()
                self.log("Database connection closed", log_level=4)
            except Exception as e:
                self.log(f"Error closing database connection: {e}", log_level=2)
            finally:
                self.connection = None

    def is_connected(self) -> bool:
        """Check if database is connected.

        Returns:
            True if connected, False otherwise
        """
        return self.connection is not None

    @contextmanager
    def cursor(self):
        """Context manager for safe cursor operations.

        Automatically closes cursor after use, even if an error occurs.

        Yields:
            Database cursor

        Example:
            with db_manager.cursor() as cursor:
                cursor.execute("SELECT * FROM table")
                results = cursor.fetchall()
        """
        if not self.connection:
            raise DatabaseError("No active database connection. Call connect() first.")

        cursor = self.connection.cursor()
        try:
            yield cursor
        finally:
            cursor.close()

    @contextmanager
    def transaction(self):
        """Context manager for transaction handling with automatic rollback.

        Automatically commits on success or rolls back on error.

        Yields:
            Database cursor

        Example:
            with db_manager.transaction() as cursor:
                cursor.execute("INSERT INTO table VALUES (?)", (value,))
                # Automatically commits if no exception
        """
        if not self.connection:
            raise DatabaseError("No active database connection. Call connect() first.")

        cursor = self.connection.cursor()
        try:
            yield cursor
            self.connection.commit()
        except Exception as e:
            self.connection.rollback()
            self.log(f"Transaction rolled back due to error: {e}", log_level=2)
            raise
        finally:
            cursor.close()

    @overload
    def execute_query(
        self, query: str, params: Optional[Union[Tuple, List]] = None, fetch_mode: Literal["all"] = "all"
    ) -> List[Tuple]: ...

    @overload
    def execute_query(
        self, query: str, params: Optional[Union[Tuple, List]] = None, fetch_mode: Literal["one"] = "one"
    ) -> Optional[Tuple]: ...

    @overload
    def execute_query(
        self, query: str, params: Optional[Union[Tuple, List]] = None, fetch_mode: Literal["value"] = "value"
    ) -> Any: ...

    def execute_query(
        self, query: str, params: Optional[Union[Tuple, List]] = None, fetch_mode: str = "all"
    ) -> Optional[Union[List[Tuple], Tuple, Any]]:
        """Execute a SELECT query and return results.

        Args:
            query: SQL query string
            params: Query parameters (tuple or list)
            fetch_mode: Result fetch mode - "all", "one", or "value"
                - "all": Returns all rows as list of tuples
                - "one": Returns first row as tuple (or None)
                - "value": Returns first column of first row (or None)

        Returns:
            Query results based on fetch_mode

        Raises:
            DatabaseError: If query execution fails

        Example:
            # Fetch all rows
            rows = db.execute_query("SELECT * FROM table WHERE id > ?", (10,))

            # Fetch single row
            row = db.execute_query("SELECT * FROM table WHERE id = ?", (1,), fetch_mode="one")

            # Fetch single value
            count = db.execute_query("SELECT COUNT(*) FROM table", fetch_mode="value")
        """
        with self.cursor() as cursor:
            try:
                cursor.execute(query, params or ())

                if fetch_mode == "all":
                    return cursor.fetchall()
                elif fetch_mode == "one":
                    return cursor.fetchone()
                elif fetch_mode == "value":
                    row = cursor.fetchone()
                    return row[0] if row else None
                else:
                    raise ValueError(f"Invalid fetch_mode: {fetch_mode}")

            except Exception as e:
                self.log(f"Query failed: {query}", log_level=2)
                self.log(f"Error: {e}", log_level=2)
                raise DatabaseError(f"Query execution failed: {e}") from e

    def execute_update(self, query: str, params: Optional[Union[Tuple, List]] = None, commit: bool = True) -> int:
        """Execute an INSERT, UPDATE, or DELETE query.

        Args:
            query: SQL query string
            params: Query parameters (tuple or list)
            commit: Whether to commit immediately (default: True)

        Returns:
            Number of affected rows (for UPDATE/DELETE) or last inserted row ID (for INSERT)

        Raises:
            DatabaseError: If query execution fails

        Example:
            # Insert and get last row ID
            row_id = db.execute_update(
                "INSERT INTO table (name) VALUES (?)",
                ("value",)
            )

            # Update rows
            affected = db.execute_update(
                "UPDATE table SET status = ? WHERE id = ?",
                ("active", 1)
            )
        """
        if not self.connection:
            raise DatabaseError("No active database connection")

        cursor = self.connection.cursor()
        try:
            cursor.execute(query, params or ())

            if commit:
                self.connection.commit()

            # Return lastrowid for INSERT, rowcount for UPDATE/DELETE
            if query.strip().upper().startswith("INSERT"):
                return cursor.lastrowid
            else:
                return cursor.rowcount

        except Exception as e:
            self.connection.rollback()
            self.log(f"Update query failed: {query}", log_level=2)
            self.log(f"Error: {e}", log_level=2)
            raise DatabaseError(f"Update execution failed: {e}") from e
        finally:
            cursor.close()

    def execute_script(self, script: str) -> None:
        """Execute a SQL script containing multiple statements.

        Args:
            script: SQL script string with multiple statements

        Raises:
            DatabaseError: If script execution fails

        Example:
            script = '''
                CREATE TABLE test (id INTEGER);
                INSERT INTO test VALUES (1);
            '''
            db.execute_script(script)
        """
        if not self.connection:
            raise DatabaseError("No active database connection")

        cursor = self.connection.cursor()
        try:
            cursor.executescript(script)
            self.connection.commit()
        except Exception as e:
            self.connection.rollback()
            self.log("Script execution failed", log_level=2)
            self.log(f"Error: {e}", log_level=2)
            raise DatabaseError(f"Script execution failed: {e}") from e
        finally:
            cursor.close()

    def execute_script_file(self, script_path: Path) -> None:
        """Execute a SQL script from a file.

        Args:
            script_path: Path to SQL script file

        Raises:
            DatabaseError: If script file cannot be read or executed

        Example:
            db.execute_script_file(Path("upgrades/query_v200.sql"))
        """
        try:
            with script_path.open("r") as f:
                script = f.read()
            self.execute_script(script)
            self.log(f"Successfully executed script: {script_path.name}", log_level=3)
        except Exception as e:
            self.log(f"Failed to execute script file: {script_path}", log_level=2)
            raise DatabaseError(f"Script file execution failed: {e}") from e

    def table_exists(self, table_name: str) -> bool:
        """Check if a table exists in the database.

        Args:
            table_name: Name of the table to check

        Returns:
            True if table exists, False otherwise

        Example:
            if db.table_exists("mzs_tools_update_history"):
                # Use the table
        """
        result = self.execute_query(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,), fetch_mode="one"
        )
        return result is not None

    def get_row_count(self, table_name: str, where_clause: str = "", params: Optional[Tuple] = None) -> int:
        """Get the number of rows in a table.

        Args:
            table_name: Name of the table
            where_clause: Optional WHERE clause (without the WHERE keyword)
            params: Parameters for the WHERE clause

        Returns:
            Number of rows

        Example:
            # Count all rows
            total = db.get_row_count("sito_puntuale")

            # Count with condition
            active = db.get_row_count("sito_puntuale", "stato = ?", ("active",))
        """
        query = f"SELECT COUNT(*) FROM {table_name}"
        if where_clause:
            query += f" WHERE {where_clause}"

        return self.execute_query(query, params, fetch_mode="value") or 0

    def get_sequence_value(self, table_name: str) -> int:
        """Get the current sequence value for a table (SQLite auto-increment).

        Args:
            table_name: Name of the table

        Returns:
            Current sequence value, or 0 if not found

        Example:
            seq = db.get_sequence_value("sito_puntuale")
        """
        try:
            result = self.execute_query(
                "SELECT seq FROM sqlite_sequence WHERE name=?", (table_name,), fetch_mode="value"
            )
            return result or 0
        except DatabaseError:
            # sqlite_sequence table doesn't exist yet (no AUTO INCREMENT tables have been used)
            return 0

    def reset_sequence(self, table_name: str, value: int = 0) -> None:
        """Reset the auto-increment sequence for a table.

        Args:
            table_name: Name of the table
            value: New sequence value (default: 0)

        Example:
            db.reset_sequence("sito_puntuale", 0)
        """
        self.execute_update("UPDATE sqlite_sequence SET seq = ? WHERE name=?", (value, table_name))

    def __enter__(self):
        """Context manager entry - establishes connection."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - closes connection."""
        self.disconnect()
        return False
