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

"""Unit tests for string utilities and sanitization functions."""

import pytest

from mzs_tools.core.mzs_project_manager import MzSProjectManager


class TestStringUtils:
    """Test string utility functions."""

    def test_sanitize_comune_name_basic(self):
        """Test basic comune name sanitization."""
        assert MzSProjectManager.sanitize_comune_name("Roma (RM - Lazio)") == "Roma"
        assert MzSProjectManager.sanitize_comune_name("Milano (MI - Lombardia)") == "Milano"
        assert MzSProjectManager.sanitize_comune_name("Napoli (NA - Campania)") == "Napoli"

    def test_sanitize_comune_name_apostrophe(self):
        """Test comune name sanitization with apostrophes."""
        assert MzSProjectManager.sanitize_comune_name("Sant'Angelo (LE)") == "Sant_Angelo"
        assert MzSProjectManager.sanitize_comune_name("Città Sant'Angelo") == "Città_Sant_Angelo"
        assert MzSProjectManager.sanitize_comune_name("L'Aquila (AQ - Abruzzo)") == "L_Aquila"

    def test_sanitize_comune_name_spaces(self):
        """Test comune name sanitization with spaces."""
        assert MzSProjectManager.sanitize_comune_name("Città Sant Angelo") == "Città_Sant_Angelo"
        assert MzSProjectManager.sanitize_comune_name("San Giovanni Rotondo") == "San_Giovanni_Rotondo"
        assert MzSProjectManager.sanitize_comune_name("Monte San Pietro") == "Monte_San_Pietro"

    def test_sanitize_comune_name_combined(self):
        """Test comune name sanitization with multiple special characters."""
        assert MzSProjectManager.sanitize_comune_name("Sant'Angelo di Piove (PD - Veneto)") == "Sant_Angelo_di_Piove"
        assert MzSProjectManager.sanitize_comune_name("Rocca d'Arce (FR)") == "Rocca_d_Arce"

    def test_sanitize_comune_name_edge_cases(self):
        """Test edge cases for comune name sanitization."""
        assert MzSProjectManager.sanitize_comune_name("") == ""
        assert MzSProjectManager.sanitize_comune_name("Roma") == "Roma"
        assert MzSProjectManager.sanitize_comune_name("(Test)") == "(Test)"  # No opening parenthesis followed by space
        assert (
            MzSProjectManager.sanitize_comune_name("Test (") == "Test"
        )  # Opening parenthesis removes everything after

    def test_sanitize_comune_name_no_parentheses(self):
        """Test comune name sanitization without parentheses."""
        assert MzSProjectManager.sanitize_comune_name("Roma") == "Roma"
        assert MzSProjectManager.sanitize_comune_name("Sant'Angelo") == "Sant_Angelo"
        assert MzSProjectManager.sanitize_comune_name("San Giovanni Rotondo") == "San_Giovanni_Rotondo"
