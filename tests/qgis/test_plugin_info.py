import os
import sys
from pathlib import Path

from packaging.version import parse
from PyQt5.QtCore import QT_VERSION_STR
from qgis.core import QgsProject, QgsVectorLayer
from qgis.PyQt.QtCore import QT_VERSION_STR as QGIS_QT_VERSION_STR

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))


from mzs_tools import __about__


def test_qt_version_compatibility():
    assert (
        QT_VERSION_STR == QGIS_QT_VERSION_STR
    ), f"PyQt5 Qt version ({QT_VERSION_STR}) does not match QGIS Qt version ({QGIS_QT_VERSION_STR})"


def test_add_layer():
    layer = QgsVectorLayer("Polygon", "dummy_polygon_layer", "memory")
    QgsProject.instance().addMapLayer(layer)
    assert set(QgsProject.instance().mapLayers().values()) == {layer}


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
