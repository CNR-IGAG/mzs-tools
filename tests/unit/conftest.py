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

"""Pytest configuration for MzS Tools unit tests."""

import pytest


@pytest.fixture
def sample_comune_names():
    """Fixture providing sample comune names for testing."""
    return {
        "Roma (RM - Lazio)": "Roma",
        "Milano (MI - Lombardia)": "Milano",
        "Sant'Angelo (LE)": "Sant_Angelo",
        "Città Sant'Angelo": "Città_Sant_Angelo",
        "L'Aquila (AQ - Abruzzo)": "L_Aquila",
        "San Giovanni Rotondo": "San_Giovanni_Rotondo",
        "": "",
        "Roma": "Roma",
        "(Test)": "",
        "Test (": "Test",
    }


@pytest.fixture
def temp_file_structure(tmp_path):
    """Fixture creating a temporary file structure for testing."""
    # Create directories
    (tmp_path / "level1" / "level2").mkdir(parents=True)
    (tmp_path / "TestDir").mkdir()

    # Create files
    (tmp_path / "test.txt").write_text("test content")
    (tmp_path / "level1" / "nested.txt").write_text("nested content")
    (tmp_path / "level1" / "level2" / "deep.txt").write_text("deep content")

    return tmp_path
