from functools import wraps

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

from mzs_tools.plugin_utils.logging import MzSToolsLogger


def skip_file_not_found(func):
    """Decorator to catch FileNotFoundError exceptions."""

    @wraps(func)
    def _wrapper(*args, **kwargs):
        try:
            func(*args, **kwargs)
        except FileNotFoundError as e:
            MzSToolsLogger.log(f"File not found: {e}", log_level=1)

    return _wrapper


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
