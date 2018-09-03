# -*- coding: utf-8 -*-
"""
/***************************************************************************
 MzSTools
                                 A QGIS plugin
 Plugin for Italian seismic microzonation.
                             -------------------
        begin                : 2018-07-09
        copyright            : (C) 2018 by IGAG - CNR
        email                : emanuele.tarquini@igag.cnr.it
        git sha              : $Format:%H$
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
 This script initializes the plugin, making it known to QGIS.
"""


# noinspection PyPep8Naming
def classFactory(iface):  # pylint: disable=invalid-name
    """Load MzSTools class from file MzSTools.

    :param iface: A QGIS interface instance.
    :type iface: QgisInterface
    """
    #
    from .MzSTools import MzSTools
    return MzSTools(iface)
