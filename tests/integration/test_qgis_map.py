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

import os

import pytest
from qgis.core import QgsCoordinateReferenceSystem, QgsProject, QgsVectorLayer

DEFAULT_TIMEOUT_SECS = 2


def get_timeout():
    is_gui_disabled = os.environ.get("QT_QPA_PLATFORM") == "offscreen"
    timeout_secs = os.environ.get("GUI_TIMEOUT")
    if timeout_secs is not None:
        try:
            timeout_secs = int(timeout_secs)
        except (TypeError, ValueError):
            timeout_secs = None
    return 0 if is_gui_disabled else (timeout_secs if timeout_secs is not None else DEFAULT_TIMEOUT_SECS)


# Timeout value for qgis_show_map tests, parametrized from environment variable or default
TIMEOUT = get_timeout()


class TestQGISMap:
    """Test QGIS map display functionality of pytest-qgis."""

    @pytest.mark.qgis_show_map(timeout=TIMEOUT)
    def test_qgis_map(self, qgis_new_project):
        """Test QGIS map display, add_basemap=True adds a Natural Earth layer
        from world_map.gpkg that ships with QGIS"""

        assert QgsProject.instance() is not None

    @pytest.mark.qgis_show_map(timeout=TIMEOUT)
    def test_qgis_custom_map(self, qgis_new_project):
        """Test QGIS map display with custom basemap."""

        # Test adding a layer - qgis_new_project makes sure that all the
        # map layers and configurations are removed
        layer = QgsVectorLayer("Polygon?crs=EPSG:32633", "memory_layer", "memory")
        assert layer.isValid(), "Memory layer is not valid."

        QgsProject.instance().addMapLayer(layer)

        # the first layer added to an empty project may set the project CRS,
        # so the map CRS is set explicitly afterwards
        QgsProject.instance().setCrs(QgsCoordinateReferenceSystem("EPSG:3857"))

        assert QgsProject.instance().count() == 1
        assert QgsProject.instance().crs().authid() == "EPSG:3857"

    @pytest.mark.qgis_show_map(timeout=TIMEOUT, add_basemap=True)
    def test_show_map_with_basemap(self, qgis_new_project):
        # the Natural Earth layer requested with add_basemap=True is added after the test body
        # and is not counted here
        assert qgis_new_project.count() == 0

        layer = QgsVectorLayer("Polygon", "dummy_polygon_layer", "memory")
        qgis_new_project.addMapLayer(layer)
        assert qgis_new_project.count() == 1
