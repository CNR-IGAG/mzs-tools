def classFactory(iface):
    """Load MzSTools class from file MzSTools.

    :param iface: A QGIS interface instance.
    :type iface: QgisInterface
    """

    from .mzs_tools import MzSTools

    return MzSTools(iface)
