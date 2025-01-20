# ruff: noqa: F401

# load form init functions
from .editing.elem_isob_form import (
    elem_isob_form as elineari_form_init,
)
from .editing.elem_isob_form import (
    elem_isob_form as epuntuali_form_init,
)
from .editing.elem_isob_form import (
    elem_isob_form as forme_form_init,
)
from .editing.elem_isob_form import (
    elem_isob_form as isosub_l1_form_init,
)
from .editing.elem_isob_form import (
    elem_isob_form as isosub_l23_form_init,
)
from .editing.geoidr import geoidr_form_init
from .editing.geotec import geotec_form_init
from .editing.instab_geotec import instab_geotec_form_init
from .editing.instab_l1 import instab_l1_form_init
from .editing.instab_l23 import instab_l23_form_init
from .editing.siti_ind_param import (
    curve_form_init,
    hvsr_form_init,
    indagini_lineari_form_init,
    indagini_puntuali_form_init,
    parametri_lineari_form_init,
    parametri_puntuali_form_init,
    sito_lineare_form_init,
    sito_puntuale_form_init,
)
from .editing.stab_l1 import stab_l1_form_init
from .editing.stab_l23 import stab_l23_form_init


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
