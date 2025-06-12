import sqlite3
import time
from functools import wraps
from pathlib import Path

from qgis.core import (
    QgsMapRendererCustomPainterJob,
    QgsMapSettings,
)
from qgis.PyQt.QtCore import QSize
from qgis.PyQt.QtGui import QImage, QPainter

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


def save_map_image(image_path, zoom_to_layer, canvas, width=1920, height=1080):
    """Creates and saves a PNG image of the map canvas
    zoomed to the `zoom_to_layer` layer's extent.

    :param image_path: destination file path for the image
    :type image_path: str
    :param zoom_to_layer: vector layer for the map extent
    :type zoom_to_layer: QgsVectorLayer
    :param canvas: map canvas
    :type canvas: QgsMapCanvas
    :param width: image width in pixels (default: 1920)
    :type width: int
    :param height: image height in pixels (default: 1080)
    :type height: int
    """
    # Validate inputs
    if not zoom_to_layer or not zoom_to_layer.isValid():
        MzSToolsLogger.log("Error: zoom_to_layer is invalid", log_level=1)
        return

    # Get the extent from the layer
    extent = zoom_to_layer.extent()
    if extent.isEmpty():
        MzSToolsLogger.log("Error: zoom_to_layer extent is empty", log_level=1)
        return

    # Get canvas layers
    canvas_layers = canvas.layers()
    if not canvas_layers:
        MzSToolsLogger.log("Warning: no layers visible in canvas, attempting direct layer rendering", log_level=1)
        # If canvas has no layers, create a minimal layer set with just the zoom layer
        canvas_layers = [zoom_to_layer]

    MzSToolsLogger.log(f"Creating map image: {width}x{height} pixels, extent: {extent}")
    MzSToolsLogger.log(f"Using {len(canvas_layers)} canvas layers: {[layer.name() for layer in canvas_layers]}")

    # Create map settings
    settings = QgsMapSettings()
    settings.setLayers(canvas_layers)  # Use canvas layers to maintain visibility and order
    settings.setExtent(extent)
    settings.setOutputSize(QSize(width, height))
    settings.setDestinationCrs(zoom_to_layer.crs())

    # Create image
    image = QImage(QSize(width, height), QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(0)  # Transparent background

    # Create painter and render
    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    # Create and run the rendering job
    render_job = QgsMapRendererCustomPainterJob(settings, painter)
    render_job.start()
    render_job.waitForFinished()

    painter.end()

    # Save the image
    success = image.save(image_path, "PNG")
    if success:
        MzSToolsLogger.log(f"Map image saved to {image_path} ({width}x{height} pixels)")
    else:
        MzSToolsLogger.log(f"Failed to save map image to {image_path}", log_level=1)


def save_map_image_from_canvas(image_path, zoom_to_layer, canvas, width=1920, height=1080):
    """Creates and saves a PNG image using the map canvas directly.
    This is an alternative approach that preserves the current canvas styling.

    :param image_path: destination file path for the image
    :type image_path: str
    :param zoom_to_layer: vector layer for the map extent
    :type zoom_to_layer: QgsVectorLayer
    :param canvas: map canvas
    :type canvas: QgsMapCanvas
    :param width: image width in pixels (default: 1920)
    :type width: int
    :param height: image height in pixels (default: 1080)
    :type height: int
    """
    # Store current canvas state
    original_extent = canvas.extent()
    original_size = canvas.size()

    try:
        # Set the canvas to the desired extent and size
        extent = zoom_to_layer.extent()
        canvas.setExtent(extent)
        canvas.resize(width, height)
        canvas.refresh()

        # Capture the canvas as an image
        pixmap = canvas.grab()
        pixmap.save(image_path, "PNG")

        MzSToolsLogger.log(f"Map image saved to {image_path} ({width}x{height} pixels)")

    finally:
        # Restore original canvas state
        canvas.setExtent(original_extent)
        canvas.resize(original_size)
        canvas.refresh()


def save_map_image_direct(image_path, layers, extent, crs, width=1920, height=1080):
    """Creates and saves a PNG image directly from specified layers and extent.
    This approach doesn't rely on the canvas and is more reliable for programmatic use.

    :param image_path: destination file path for the image
    :type image_path: str
    :param layers: list of layers to render
    :type layers: list[QgsMapLayer]
    :param extent: map extent to render
    :type extent: QgsRectangle
    :param crs: coordinate reference system
    :type crs: QgsCoordinateReferenceSystem
    :param width: image width in pixels (default: 1920)
    :type width: int
    :param height: image height in pixels (default: 1080)
    :type height: int
    """
    if not layers:
        MzSToolsLogger.log("Error: no layers provided for rendering", log_level=1)
        return

    if extent.isEmpty():
        MzSToolsLogger.log("Error: extent is empty", log_level=1)
        return

    MzSToolsLogger.log(f"Creating map image directly: {width}x{height} pixels")
    MzSToolsLogger.log(f"Using {len(layers)} layers: {[layer.name() for layer in layers]}")
    MzSToolsLogger.log(f"Extent: {extent}")

    # Create map settings
    settings = QgsMapSettings()
    settings.setLayers(layers)
    settings.setExtent(extent)
    settings.setOutputSize(QSize(width, height))
    settings.setDestinationCrs(crs)

    # Create image
    image = QImage(QSize(width, height), QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(0)  # Transparent background

    # Create painter and render
    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    # Create and run the rendering job
    render_job = QgsMapRendererCustomPainterJob(settings, painter)
    render_job.start()
    render_job.waitForFinished()

    painter.end()

    # Save the image
    success = image.save(image_path, "PNG")
    if success:
        MzSToolsLogger.log(f"Map image saved to {image_path} ({width}x{height} pixels)")
    else:
        MzSToolsLogger.log(f"Failed to save map image to {image_path}", log_level=1)


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
