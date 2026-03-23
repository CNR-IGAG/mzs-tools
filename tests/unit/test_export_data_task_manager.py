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

"""Unit tests for ExportDataTaskManager shapefile post-processing utilities.

These tests exercise _rename_field, _change_field_type and
_extract_file_name_from_path in isolation using on-disk shapefiles written
to a temporary directory.
"""

import logging
from pathlib import Path
from unittest.mock import MagicMock

from osgeo import ogr, osr
from qgis.core import (
    QgsVectorLayer,
)
from qgis.PyQt.QtCore import QMetaType

from mzs_tools.tasks.export_data_task_manager import ExportDataTaskManager

# ---------------------------------------------------------------------------
# Helpers / Fixtures
# ---------------------------------------------------------------------------


def _make_manager(tmp_path: Path) -> ExportDataTaskManager:
    """Build a minimal ExportDataTaskManager with mocked QGIS dependencies."""
    manager = object.__new__(ExportDataTaskManager)
    manager.file_logger = logging.getLogger("test_export_data_task_manager")
    manager.file_logger.setLevel(logging.DEBUG)
    manager.iface = MagicMock()
    manager.prj_manager = MagicMock()
    manager.output_path = tmp_path
    manager.indagini_output_format = "sqlite"
    manager.standard_version_string = "S42"
    manager.cdi_tabelle_model_file = "CdI_Tabelle_4.2.mdb"
    manager.debug_mode = False
    manager._tasks = []
    manager._task_failed = False
    manager._completed_count = 0
    manager.progress_bar = None
    manager.log_file_path = None
    manager.file_handler = None
    return manager


def _write_shapefile(tmp_path: Path, name: str, fields: list[tuple[str, QMetaType.Type]], rows: list[dict]) -> Path:
    """Write a minimal point shapefile via OGR; returns path to the .shp file."""
    _METATYPE_TO_OGR = {
        QMetaType.Type.Int: ogr.OFTInteger,
        QMetaType.Type.LongLong: ogr.OFTInteger64,
        QMetaType.Type.Double: ogr.OFTReal,
        QMetaType.Type.QString: ogr.OFTString,
    }

    driver = ogr.GetDriverByName("ESRI Shapefile")
    shp_path = tmp_path / f"{name}.shp"
    ds = driver.CreateDataSource(str(shp_path))
    srs = osr.SpatialReference()
    lyr = ds.CreateLayer(name, srs, ogr.wkbPoint)
    for field_name, metatype in fields:
        ogr_type = _METATYPE_TO_OGR.get(metatype, ogr.OFTString)
        lyr.CreateField(ogr.FieldDefn(field_name, ogr_type))
    for row in rows:
        feat = ogr.Feature(lyr.GetLayerDefn())
        feat.SetGeometry(ogr.CreateGeometryFromWkt("POINT(0 0)"))
        for key, value in row.items():
            if value is not None:
                feat.SetField(key, value)
        lyr.CreateFeature(feat)
    ds = None  # flush/close
    return shp_path


# ---------------------------------------------------------------------------
# _rename_field
# ---------------------------------------------------------------------------


def test_rename_field_success(tmp_path, qgis_app):
    """_rename_field renames an existing field to the new name."""
    shp_path = _write_shapefile(
        tmp_path,
        "test_rename",
        [("old_name", QMetaType.Type.Int)],
        [{"old_name": 1}, {"old_name": 2}],
    )
    layer = QgsVectorLayer(str(shp_path), "test", "ogr")
    assert layer.isValid()

    manager = _make_manager(tmp_path)
    manager._rename_field(layer, "old_name", "new_name")

    # Re-open layer to confirm persistence
    layer2 = QgsVectorLayer(str(shp_path), "test", "ogr")
    field_names = [f.name() for f in layer2.fields()]
    assert "new_name" in field_names
    assert "old_name" not in field_names


def test_rename_field_nonexistent_is_noop(tmp_path, qgis_app):
    """_rename_field silently ignores a field that doesn't exist."""
    shp_path = _write_shapefile(
        tmp_path,
        "test_rename_noop",
        [("some_field", QMetaType.Type.Int)],
        [{"some_field": 42}],
    )
    layer = QgsVectorLayer(str(shp_path), "test", "ogr")
    assert layer.isValid()

    manager = _make_manager(tmp_path)
    # Should not raise
    manager._rename_field(layer, "missing_field", "whatever")

    layer2 = QgsVectorLayer(str(shp_path), "test", "ogr")
    field_names = [f.name() for f in layer2.fields()]
    assert "some_field" in field_names


# ---------------------------------------------------------------------------
# _change_field_type
# ---------------------------------------------------------------------------


def test_change_field_type_double_to_int(tmp_path, qgis_app):
    """_change_field_type converts a Double field to Int, preserving values."""
    shp_path = _write_shapefile(
        tmp_path,
        "test_change_type",
        [("score", QMetaType.Type.Double)],
        [{"score": 3.0}, {"score": 7.0}],
    )
    layer = QgsVectorLayer(str(shp_path), "test", "ogr")
    assert layer.isValid()

    manager = _make_manager(tmp_path)
    result = manager._change_field_type(layer, "score", QMetaType.Type.Int)
    assert result is True

    layer2 = QgsVectorLayer(str(shp_path), "test", "ogr")
    field = layer2.fields().field("score")
    assert field.type() in (QMetaType.Type.Int, QMetaType.Type.LongLong)

    values = [feat["score"] for feat in layer2.getFeatures()]  # type: ignore
    assert set(values) == {3, 7}


def test_change_field_type_int_to_double(tmp_path, qgis_app):
    """_change_field_type converts an Int field to Double, preserving values."""
    shp_path = _write_shapefile(
        tmp_path,
        "test_int_to_double",
        [("LIVELLO", QMetaType.Type.Int)],
        [{"LIVELLO": 1}, {"LIVELLO": 2}],
    )
    layer = QgsVectorLayer(str(shp_path), "test", "ogr")
    assert layer.isValid()

    manager = _make_manager(tmp_path)
    result = manager._change_field_type(layer, "LIVELLO", QMetaType.Type.Double)
    assert result is True

    layer2 = QgsVectorLayer(str(shp_path), "test", "ogr")
    field = layer2.fields().field("LIVELLO")
    assert field.type() == QMetaType.Type.Double

    values = [feat["LIVELLO"] for feat in layer2.getFeatures()]  # type: ignore
    assert set(values) == {1.0, 2.0}


def test_change_field_type_nonexistent_returns_false(tmp_path, qgis_app):
    """_change_field_type returns False for a missing field and does not raise."""
    shp_path = _write_shapefile(
        tmp_path,
        "test_change_missing",
        [("some_field", QMetaType.Type.Int)],
        [{"some_field": 1}],
    )
    layer = QgsVectorLayer(str(shp_path), "test", "ogr")
    assert layer.isValid()

    manager = _make_manager(tmp_path)
    result = manager._change_field_type(layer, "nonexistent", QMetaType.Type.Double)
    assert result is False


# ---------------------------------------------------------------------------
# _extract_file_name_from_path
# ---------------------------------------------------------------------------


def test_extract_file_name_from_path(tmp_path, qgis_app):
    """_extract_file_name_from_path replaces full paths with filenames only."""
    shp_path = _write_shapefile(
        tmp_path,
        "test_extract",
        [("SPETTRI", QMetaType.Type.QString)],
        [
            {"SPETTRI": "/some/deep/path/spectrum_001.txt"},
            {"SPETTRI": "/another/path/spectrum_002.txt"},
        ],
    )
    layer = QgsVectorLayer(str(shp_path), "test", "ogr")
    assert layer.isValid()

    manager = _make_manager(tmp_path)
    manager._extract_file_name_from_path(layer, "SPETTRI")

    layer2 = QgsVectorLayer(str(shp_path), "test", "ogr")
    values = [feat["SPETTRI"] for feat in layer2.getFeatures()]  # type: ignore
    assert "spectrum_001.txt" in values
    assert "spectrum_002.txt" in values
    # No full paths should remain
    assert not any("/" in v for v in values if v)


def test_extract_file_name_from_path_empty_values(tmp_path, qgis_app):
    """_extract_file_name_from_path skips NULL/empty values without error."""
    shp_path = _write_shapefile(
        tmp_path,
        "test_extract_empty",
        [("SPETTRI", QMetaType.Type.QString)],
        [{"SPETTRI": None}, {"SPETTRI": ""}, {"SPETTRI": "/path/to/file.txt"}],
    )
    layer = QgsVectorLayer(str(shp_path), "test", "ogr")
    assert layer.isValid()

    manager = _make_manager(tmp_path)
    # Should not raise even with NULL/empty values
    manager._extract_file_name_from_path(layer, "SPETTRI")

    layer2 = QgsVectorLayer(str(shp_path), "test", "ogr")
    non_empty = [feat["SPETTRI"] for feat in layer2.getFeatures() if feat["SPETTRI"]]  # type: ignore
    assert non_empty == ["file.txt"]


def test_extract_file_name_from_path_nonexistent_field(tmp_path, qgis_app):
    """_extract_file_name_from_path returns early when field doesn't exist."""
    shp_path = _write_shapefile(
        tmp_path,
        "test_extract_missing_field",
        [("OTHER", QMetaType.Type.QString)],
        [{"OTHER": "/a/b/c.txt"}],
    )
    layer = QgsVectorLayer(str(shp_path), "test", "ogr")
    assert layer.isValid()

    manager = _make_manager(tmp_path)
    # Should not raise
    manager._extract_file_name_from_path(layer, "SPETTRI")

    # Original data untouched
    layer2 = QgsVectorLayer(str(shp_path), "test", "ogr")
    values = [feat["OTHER"] for feat in layer2.getFeatures()]  # type: ignore
    assert values == ["/a/b/c.txt"]
