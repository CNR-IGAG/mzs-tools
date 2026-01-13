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

from mzs_tools.plugin_utils.qt_compat import (
    IS_PYQT5,
    IS_PYQT6,
    get_alignment_flag,
    get_qt_version_info,
)


class TestQtCompat:
    """Test Qt compatibility layer."""

    def test_version_detection(self):
        """Test that version detection is working."""
        # One of these should be True
        assert IS_PYQT5 or IS_PYQT6
        # But not both
        assert not (IS_PYQT5 and IS_PYQT6)

    def test_get_qt_version_info(self):
        """Test getting Qt version information."""
        info = get_qt_version_info()
        assert isinstance(info, dict)
        assert "qt_version" in info
        assert "pyqt_version" in info
        assert "is_pyqt5" in info
        assert "is_pyqt6" in info
        assert info["is_pyqt5"] == IS_PYQT5
        assert info["is_pyqt6"] == IS_PYQT6

    def test_get_alignment_flag_single(self):
        """Test getting a single alignment flag."""
        result = get_alignment_flag("AlignLeft")
        assert result is not None
        # Result should be an integer or Qt alignment type
        assert isinstance(result, (int, object))

    def test_get_alignment_flag_multiple(self):
        """Test getting multiple alignment flags combined."""
        result = get_alignment_flag("AlignLeft", "AlignVCenter")
        assert result is not None
        assert isinstance(result, (int, object))

        # Test that combining flags gives different result than single flag
        left_only = get_alignment_flag("AlignLeft")
        assert result != left_only

    def test_get_alignment_flag_common_combinations(self):
        """Test common alignment flag combinations."""
        # Test various common combinations
        combinations = [
            ("AlignLeft", "AlignVCenter"),
            ("AlignRight", "AlignTop"),
            ("AlignHCenter", "AlignBottom"),
            ("AlignLeft", "AlignTop"),
            ("AlignRight", "AlignVCenter"),
        ]

        for combo in combinations:
            result = get_alignment_flag(*combo)
            assert result is not None
            assert isinstance(result, (int, object))

    def test_get_alignment_flag_unknown(self):
        """Test handling of unknown alignment flags."""
        # Should not raise an exception, should return fallback value
        result = get_alignment_flag("UnknownAlignment")
        assert result is not None
        # Should be 0 (fallback) for unknown flags
        assert result == 0

    def test_get_alignment_flag_empty(self):
        """Test handling of empty alignment flags."""
        result = get_alignment_flag()
        assert result == 0
