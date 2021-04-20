# coding=utf-8
""""Utilities for MzS plugin

.. note:: This program is free software; you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation; either version 2 of the License, or
    (at your option) any later version.

"""

__author__ = 'elpaso@itopen.it'
__date__ = '2021-04-09'
__copyright__ = 'Copyright 2021, ItOpen'

import os

from qgis.core import (
    QgsLayout,
    QgsLayoutExporter,
    QgsUnitTypes,
    QgsLayoutSize,
    QgsLayoutItemMap,
    QgsLayoutItemPage,
    QgsProject
)
from qgis.PyQt.QtCore import QSize, QRectF


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
    page.setPageSize(QgsLayoutSize(
        1200, 700, QgsUnitTypes.LayoutMillimeters))
    collection = layout.pageCollection()
    collection.addPage(page)

    item_map = QgsLayoutItemMap(layout)
    item_map.attemptSetSceneRect(QRectF(0, 0, 1200, 700))
    item_map.setCrs(zoom_to_layer.crs())
    item_map.zoomToExtent(extent)
    layout.addItem(item_map)

    dpmm = 200/25.4
    width = int(dpmm * page.pageSize().width())
    height = int(dpmm * page.pageSize().height())

    size = QSize(width, height)
    exporter = QgsLayoutExporter(layout)
    image = exporter.renderPageToImage(0, size)
    image.save(image_path, 'PNG')
