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

"""Unit tests for AccessDbConnection date validation."""

from unittest.mock import MagicMock

import pytest

from mzs_tools.tasks.access_db_connection import AccessDbConnection


@pytest.fixture
def conn():
    """AccessDbConnection instance created without opening any database connection."""
    conn = AccessDbConnection.__new__(AccessDbConnection)
    conn.log = MagicMock()
    return conn


@pytest.mark.parametrize(
    "value, expected",
    [
        ("2024-11-06", "2024-11-06"),
        ("06/11/2024", "2024-11-06"),
        ("06/13/2024", "2024-06-13"),
        ("2024/11/06", "2024-11-06"),
        ("06-11-2024", "2024-11-06"),
        ("20241106", "2024-11-06"),
        ("  2024-11-06  ", "2024-11-06"),
        ("2024-11-06 14:30:00", "2024-11-06"),
        ("06/11/2024 14:30:00", "2024-11-06"),
        ("06-11-2024 23:59:59", "2024-11-06"),
        ("  06/11/2024 14:30:00  ", "2024-11-06"),
        ("", None),
        (None, None),
        ("   ", None),
    ],
)
def test_validate_date_valid(conn, value, expected):
    """Valid dates and datetimes are returned in ISO format; empty values give None without logging."""
    assert conn._validate_date(value) == expected
    if expected is None:
        conn.log.assert_not_called()


@pytest.mark.parametrize("value", ["06-November-2024", "99/99/9999", "2024-11", "not a date"])
def test_validate_date_invalid_logs(conn, value):
    """Unparsable values give None and log a warning."""
    assert conn._validate_date(value) is None
    conn.log.assert_called_once()
