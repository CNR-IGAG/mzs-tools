# PLUGIN_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__)))
# if PLUGIN_DIR not in sys.path:
#     sys.path.append(PLUGIN_DIR)


def classFactory(iface):
    """Load MzSTools class from file MzSTools.

    :param iface: A QGIS interface instance.
    :type iface: QgisInterface
    """

    from .mzs_tools import MzSTools

    return MzSTools(iface)
