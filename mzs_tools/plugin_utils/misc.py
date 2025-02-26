import sqlite3
import time
from functools import wraps
from pathlib import Path

from qgis.core import (
    QgsLayout,
    QgsLayoutExporter,
    QgsLayoutItemMap,
    QgsLayoutItemPage,
    QgsLayoutSize,
    QgsProject,
    QgsUnitTypes,
)
from qgis.PyQt.QtCore import QRectF, QSize

from ..plugin_utils.logging import MzSToolsLogger


def skip_file_not_found(func):
    """Decorator to catch FileNotFoundError exceptions."""

    @wraps(func)
    def _wrapper(*args, **kwargs):
        try:
            func(*args, **kwargs)
        except FileNotFoundError as e:
            MzSToolsLogger.log(f"File not found: {e}", log_level=1)

    return _wrapper


def retry_on_lock(retries=5, delay=1):
    """Decorator to retry a database operation if the database is locked."""

    def decorator(func):
        def wrapper(*args, **kwargs):
            for attempt in range(retries):
                try:
                    return func(*args, **kwargs)
                except sqlite3.OperationalError as e:
                    if "database is locked" in str(e):
                        args[0].log(f"Database is locked, retrying in {delay} seconds...", log_level=1)
                        time.sleep(delay)
                    else:
                        raise
            raise sqlite3.OperationalError("Database is locked after multiple retries")

        return wrapper

    return decorator


def save_map_image(image_path, zoom_to_layer, canvas):
    """Creates and saves a PNG image of the map canvas
    zoomed to the `zoom_to_layer` layer's extent.

    :param image_path: destination file path for the image
    :type image_path: str
    :param zoom_to_layer: vector layer for the map extent
    :type zoom_to_layer: QgsVectorLayer
    :param canvas: map canvas
    :type canvas: QgsMapCanvas
    """

    extent = zoom_to_layer.extent()
    canvas.setExtent(extent)

    p = QgsProject.instance()
    layout = QgsLayout(p)
    page = QgsLayoutItemPage(layout)
    page.setPageSize(QgsLayoutSize(1200, 700, QgsUnitTypes.LayoutMillimeters))
    collection = layout.pageCollection()
    collection.addPage(page)

    item_map = QgsLayoutItemMap(layout)
    item_map.attemptSetSceneRect(QRectF(0, 0, 1200, 700))
    item_map.setCrs(zoom_to_layer.crs())
    item_map.zoomToExtent(extent)
    layout.addItem(item_map)

    dpmm = 200 / 25.4
    width = int(dpmm * page.pageSize().width())
    height = int(dpmm * page.pageSize().height())

    size = QSize(width, height)
    exporter = QgsLayoutExporter(layout)
    image = exporter.renderPageToImage(0, size)
    image.save(image_path, "PNG")
    MzSToolsLogger.log(f"Map image saved to {image_path}")


def get_subdir_path(root_dir_path, subdir_name):
    """case insensitive recursive search for a subdirectory in the provided path"""
    subdir_name = subdir_name.lower()
    for root, dirs, _ in Path(root_dir_path).walk():
        for d in dirs:
            if d.lower() == subdir_name:
                return root / d
    return None


def get_file_path(root_dir_path, file_name):
    """case insensitive recursive search for a file in the provided path"""
    file_name = file_name.lower()
    for root, _, files in Path(root_dir_path).walk():
        for file in files:
            if file.lower() == file_name:
                return root / file
    return None


def get_path_for_name(root_dir_path, name):
    """case insensitive recursive search for a file or subdirectory in the provided path"""
    name = name.lower()
    for root, dirs, files in Path(root_dir_path).walk():
        for f in files:
            if f.lower() == name:
                return root / f
        for d in dirs:
            if d.lower() == name:
                return root / d
    return None
