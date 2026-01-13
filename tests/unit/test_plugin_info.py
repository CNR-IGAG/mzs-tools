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

from pathlib import Path

from packaging.version import parse

from mzs_tools import __about__


def test_metadata_types():
    """Test types."""
    # plugin metadata.txt file
    assert isinstance(__about__.PLG_METADATA_FILE, Path)
    assert __about__.PLG_METADATA_FILE.is_file()

    # plugin dir
    assert isinstance(__about__.DIR_PLUGIN_ROOT, Path)
    assert __about__.DIR_PLUGIN_ROOT.is_dir()

    # metadata as dict
    assert isinstance(__about__.__plugin_md__, dict)

    # general
    assert isinstance(__about__.__author__, str)
    assert isinstance(__about__.__copyright__, str)
    assert isinstance(__about__.__email__, str)
    assert isinstance(__about__.__keywords__, list)
    assert isinstance(__about__.__license__, str)
    assert isinstance(__about__.__summary__, str)
    assert isinstance(__about__.__title__, str)
    assert isinstance(__about__.__title_clean__, str)
    assert isinstance(__about__.__version__, str)
    assert isinstance(__about__.__version_info__, tuple)

    # misc
    assert len(__about__.__title_clean__) <= len(__about__.__title__)

    # QGIS versions
    assert isinstance(__about__.__plugin_md__.get("general").get("qgisminimumversion"), str)
    assert isinstance(__about__.__plugin_md__.get("general").get("qgismaximumversion"), str)

    min_version_parsed = parse(__about__.__plugin_md__.get("general").get("qgisminimumversion"))
    max_version_parsed = parse(__about__.__plugin_md__.get("general").get("qgismaximumversion"))
    assert min_version_parsed <= max_version_parsed


def test_version_semver():
    """Test if version comply with semantic versioning."""
    assert parse(__about__.__version__) is not None


def test_version_comparisons():
    assert parse(__about__.__version__) >= parse("1.9.4")


# pluginManagerInterface appears to be unknown to the qgis_iface fixture
# def test_plugin_metadata_from_plugin_manager_interface(qgis_iface):
#     plugin_metadata = qgis_iface.pluginManagerInterface().pluginMetadata("MzSTools")
#     if not plugin_metadata:
#         # Try refreshing the plugin manager cache
#         pyplugin_installer.instance().reloadAndExportData()
#         plugin_metadata = qgis_iface.pluginManagerInterface().pluginMetadata("MzSTools")
#     assert plugin_metadata
