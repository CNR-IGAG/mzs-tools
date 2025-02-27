import datetime
import os
import shutil
import traceback
import zipfile
from dataclasses import dataclass
from functools import partial
from pathlib import Path
from sqlite3 import Connection
from typing import Optional

from qgis.core import (
    QgsCoordinateReferenceSystem,
    QgsEditorWidgetSetup,
    QgsLayerDefinition,
    QgsLayerTreeGroup,
    QgsMapLayer,
    QgsPrintLayout,
    QgsProject,
    QgsReadWriteContext,
    QgsRelation,
    QgsSnappingConfig,
    QgsTolerance,
    QgsVectorLayer,
)
from qgis.PyQt.QtCore import QCoreApplication
from qgis.PyQt.QtXml import QDomDocument
from qgis.utils import iface, spatialite_connect

from ..__about__ import DIR_PLUGIN_ROOT, __base_version__, __version__
from ..plugin_utils.logging import MzSToolsLogger
from ..plugin_utils.misc import save_map_image
from ..plugin_utils.settings import PlgOptionsManager


@dataclass
class ComuneData:
    cod_regio: str
    cod_prov: str
    cod_com: str
    comune: str
    provincia: str
    regione: str
    cod_istat: str


class MzSProjectManager:
    """Singleton class to manage MzS Tools project data and structure. It provides various functionalities to handle
    project initialization, database connections, layer management, and project customization."""

    _instance = None

    DEFAULT_BASE_LAYERS = {
        "comune_progetto": {
            "role": "base",
            "type": "vector",
            "layer_name": "Comune del progetto",
            "group": None,
            "qlr_path": "comune_progetto.qlr",
        },
        "comuni": {
            "role": "base",
            "type": "vector",
            "geom_name": "GEOMETRY",
            "subset_string": "cod_regio",
            "layer_name": "Limiti comunali",
            "group": None,
            "qlr_path": "comuni.qlr",
        },
        "basemap": {
            "role": "base",
            "type": "service_group",
            "layer_name": "Basemap",
            "group": None,
            "qlr_path": "basemap.qlr",
        },
    }

    DEFAULT_EDITING_LAYERS = {
        "tavole": {
            "role": "editing",
            "type": "vector",
            "geom_name": "GEOMETRY",
            "layer_name": "tavole",
            "group": None,
            "qlr_path": "tavole.qlr",
        },
        "sito_puntuale": {
            "role": "editing",
            "type": "vector",
            "layer_name": "Siti puntuali",
            "group": "Indagini",
            "qlr_path": "siti_puntuali.qlr",
            "value_relations": {
                "mod_identcoord": {
                    "relation_table": "vw_mod_identcoord",
                    "relation_key": "cod",
                    "relation_value": "descrizione",
                    "order_by_value": True,
                },
                "modo_quota": {
                    "relation_table": "vw_modo_quota",
                    "relation_key": "cod",
                    "relation_value": "descrizione",
                    "order_by_value": True,
                },
            },
        },
        "indagini_puntuali": {
            "role": "editing",
            "type": "table",
            "layer_name": "Indagini puntuali",
            "group": "Indagini",
            "qlr_path": "indagini_puntuali.qlr",
            "value_relations": {
                "id_spu": {
                    "relation_table": "sito_puntuale",
                    "relation_key": "id_spu",
                    "relation_value": "id_spu",
                    "order_by_value": True,
                },
                "classe_ind": {
                    "relation_table": "vw_classe_ind_p",
                    "relation_key": "cod",
                    "relation_value": "descrizione",
                    "order_by_value": True,
                },
                "tipo_ind": {
                    "relation_table": "vw_tipo_ind_p",
                    "relation_key": "cod",
                    "relation_value": "descrizione",
                    "order_by_value": True,
                    "filter_expression": "cod_classe = current_value('classe_ind')",
                },
            },
        },
        "parametri_puntuali": {
            "role": "editing",
            "type": "table",
            "layer_name": "Parametri puntuali",
            "group": "Indagini",
            "qlr_path": "parametri_puntuali.qlr",
            "value_relations": {
                "id_indpu": {
                    "relation_table": "indagini_puntuali",
                    "relation_key": "id_indpu",
                    "relation_value": "id_indpu",
                    "order_by_value": True,
                },
                "attend_mis": {
                    "relation_table": "vw_attend_mis",
                    "relation_key": "cod",
                    "relation_value": "descrizione",
                    "order_by_value": True,
                },
                "tipo_parpu": {
                    "relation_table": "vw_param_p",
                    "relation_key": "cod",
                    "relation_value": "descrizione",
                    "order_by_value": True,
                    "filter_expression": r"cod_ind = regexp_replace(substr(current_value('id_indpu'), 9), '\\d+', '')",
                },
            },
        },
        "curve": {
            "role": "editing",
            "type": "table",
            "layer_name": "Curve di riferimento",
            "group": "Indagini",
            "qlr_path": "curve.qlr",
            "value_relations": {
                "id_parpu": {
                    "relation_table": "parametri_puntuali",
                    "relation_key": "id_parpu",
                    "relation_value": "id_parpu",
                    "order_by_value": True,
                },
            },
        },
        "hvsr": {
            "role": "editing",
            "type": "table",
            "layer_name": "Indagine stazione singola (HVSR)",
            "group": "Indagini",
            "qlr_path": "hvsr.qlr",
            "value_relations": {
                "id_indpu": {
                    "relation_table": "indagini_puntuali",
                    "relation_key": "id_indpu",
                    "relation_value": "id_indpu",
                    "order_by_value": True,
                },
                "qualita": {
                    "relation_table": "vw_qualita",
                    "relation_key": "cod",
                    "relation_value": "descrizione",
                    "order_by_value": True,
                },
                "tipo": {
                    "relation_table": "vw_tipo_hvsr",
                    "relation_key": "cod",
                    "relation_value": "descrizione",
                    "order_by_value": True,
                    "allow_null": True,
                },
            },
        },
        "sito_lineare": {
            "role": "editing",
            "type": "vector",
            "layer_name": "Siti lineari",
            "group": "Indagini",
            "qlr_path": "siti_lineari.qlr",
            "value_relations": {
                "mod_identcoord": {
                    "relation_table": "vw_mod_identcoord",
                    "relation_key": "cod",
                    "relation_value": "descrizione",
                    "order_by_value": True,
                },
            },
        },
        "indagini_lineari": {
            "role": "editing",
            "type": "table",
            "layer_name": "Indagini lineari",
            "group": "Indagini",
            "qlr_path": "indagini_lineari.qlr",
            "value_relations": {
                "id_sln": {
                    "relation_table": "sito_lineare",
                    "relation_key": "id_sln",
                    "relation_value": "id_sln",
                    "order_by_value": True,
                },
                "classe_ind": {
                    "relation_table": "vw_classe_ind_l",
                    "relation_key": "cod",
                    "relation_value": "descrizione",
                    "order_by_value": True,
                },
                "tipo_ind": {
                    "relation_table": "vw_tipo_ind_l",
                    "relation_key": "cod",
                    "relation_value": "descrizione",
                    "order_by_value": True,
                    "filter_expression": "cod_classe = current_value('classe_ind')",
                },
            },
        },
        "parametri_lineari": {
            "role": "editing",
            "type": "table",
            "layer_name": "Parametri lineari",
            "group": "Indagini",
            "qlr_path": "parametri_lineari.qlr",
            "value_relations": {
                "id_indln": {
                    "relation_table": "indagini_lineari",
                    "relation_key": "id_indln",
                    "relation_value": "id_indln",
                    "order_by_value": True,
                },
                "attend_mis": {
                    "relation_table": "vw_attend_mis",
                    "relation_key": "cod",
                    "relation_value": "descrizione",
                    "order_by_value": True,
                },
                "tipo_parpu": {
                    "relation_table": "vw_param_l",
                    "relation_key": "cod",
                    "relation_value": "descrizione",
                    "order_by_value": True,
                    "filter_expression": r"cod_ind = regexp_replace(substr(current_value('id_indln'), 9), '\\d+', '')",
                },
            },
        },
        "isosub_l23": {
            "role": "editing",
            "type": "vector",
            "layer_name": "Isobate liv 2-3",
            "group": "MS livello 2-3",
            "qlr_path": "isosub_l23.qlr",
        },
        "instab_l23": {
            "role": "editing",
            "type": "vector",
            "layer_name": "Zone instabili liv 2-3",
            "group": "MS livello 2-3",
            "qlr_path": "instab_l23.qlr",
            "value_relations": {
                "CAT": {
                    "relation_table": "vw_cat_s",
                    "relation_key": "cod",
                    "relation_value": "descrizione",
                    "order_by_value": False,
                    "allow_null": True,
                },
                "AMB": {
                    "relation_table": "vw_amb",
                    "relation_key": "cod",
                    "relation_value": "descrizione",
                    "order_by_value": False,
                    "allow_null": True,
                },
                "cod_instab": {
                    "relation_table": "vw_cod_instab",
                    "relation_key": "cod",
                    "relation_value": "descrizione",
                    "order_by_value": True,
                },
                "cod_stab": {
                    "relation_table": "vw_cod_stab",
                    "relation_key": "cod",
                    "relation_value": "descrizione",
                    "order_by_value": True,
                    "allow_null": True,
                    "filter_expression": "\"cod\" > (if( array_contains(array(3060, 3061, 3062, 3070, 3080, 3081, 3082, 3090, 3091, 3092, 3069),current_value('cod_instab')), 99999, 2000))",
                },
            },
        },
        "stab_l23": {
            "role": "editing",
            "type": "vector",
            "layer_name": "Zone stabili liv 2-3",
            "group": "MS livello 2-3",
            "qlr_path": "stab_l23.qlr",
            "value_relations": {
                "Tipo_z": {
                    "relation_table": "vw_cod_stab",
                    "relation_key": "cod",
                    "relation_value": "descrizione",
                    "order_by_value": True,
                },
                "CAT": {
                    "relation_table": "vw_cat_s",
                    "relation_key": "cod",
                    "relation_value": "descrizione",
                    "order_by_value": False,
                    "allow_null": True,
                },
            },
        },
        "isosub_l1": {
            "role": "editing",
            "type": "vector",
            "layer_name": "Isobate liv 1",
            "group": "MS livello 1",
            "qlr_path": "isosub_l1.qlr",
        },
        "instab_l1": {
            "role": "editing",
            "type": "vector",
            "layer_name": "Zone instabili liv 1",
            "group": "MS livello 1",
            "qlr_path": "instab_l1.qlr",
            "value_relations": {
                "cod_instab": {
                    "relation_table": "vw_cod_instab",
                    "relation_key": "cod",
                    "relation_value": "descrizione",
                    "order_by_value": True,
                    "filter_expression": '"cod" NOT IN (3001, 3002, 3052, 3053, 3055, 3056, 3061, 3062, 3081, 3082, 3091, 3092)',
                },
                "cod_stab": {
                    "relation_table": "vw_cod_stab",
                    "relation_key": "cod",
                    "relation_value": "descrizione",
                    "order_by_value": True,
                    "allow_null": True,
                    "filter_expression": "\"cod\" > (if( array_contains(array(3060, 3069, 3070, 3080, 3090),current_value('cod_instab')), 99999, 2000))",
                },
            },
        },
        "stab_l1": {
            "role": "editing",
            "type": "vector",
            "layer_name": "Zone stabili liv 1",
            "group": "MS livello 1",
            "qlr_path": "stab_l1.qlr",
            "value_relations": {
                "Tipo_z": {
                    "relation_table": "vw_cod_stab",
                    "relation_key": "cod",
                    "relation_value": "descrizione",
                    "order_by_value": True,
                },
            },
        },
        "nome_sezione": {
            "role": "editing",
            "type": "vector",
            "geom_name": "GEOMETRY",
            "layer_name": "Nome Sezione",
            "group": "Geologico Tecnica",
            "qlr_path": "nome_sezione.qlr",
        },
        "geoidr": {
            "role": "editing",
            "type": "vector",
            "layer_name": "Elementi geologici e idrogeologici puntuali",
            "group": "Geologico Tecnica",
            "qlr_path": "geoidr.qlr",
            "value_relations": {
                "Tipo_gi": {
                    "relation_table": "vw_tipo_gi",
                    "relation_key": "cod",
                    "relation_value": "descrizione",
                    "order_by_value": False,
                },
            },
        },
        "epuntuali": {
            "role": "editing",
            "type": "vector",
            "layer_name": "Elementi puntuali",
            "group": "Geologico Tecnica",
            "qlr_path": "epuntuali.qlr",
            "value_relations": {
                "Tipo_ep": {
                    "relation_table": "vw_tipo_ep",
                    "relation_key": "cod",
                    "relation_value": "descrizione",
                    "order_by_value": False,
                },
            },
        },
        "elineari": {
            "role": "editing",
            "type": "vector",
            "layer_name": "Elementi lineari",
            "group": "Geologico Tecnica",
            "qlr_path": "elineari.qlr",
            "value_relations": {
                "Tipo_el": {
                    "relation_table": "vw_tipo_el",
                    "relation_key": "cod",
                    "relation_value": "descrizione",
                    "order_by_value": False,
                },
            },
        },
        "forme": {
            "role": "editing",
            "type": "vector",
            "layer_name": "Forme",
            "group": "Geologico Tecnica",
            "qlr_path": "forme.qlr",
            "value_relations": {
                "Tipo_f": {
                    "relation_table": "vw_tipo_f",
                    "relation_key": "cod",
                    "relation_value": "descrizione",
                    "order_by_value": False,
                },
            },
        },
        "instab_geotec": {
            "role": "editing",
            "type": "vector",
            "layer_name": "Instabilita' di versante",
            "group": "Geologico Tecnica",
            "qlr_path": "instab_geotec.qlr",
            "value_relations": {
                "Tipo_i": {
                    "relation_table": "vw_cod_instab",
                    "relation_key": "cod",
                    "relation_value": "descrizione",
                    "order_by_value": True,
                    "filter_expression": '"cod" NOT IN (3001,3002,3050,3051,3052,3053,3054,3055,3056,3060,3061,3062,3069,3070,3080,3081,3082,3090,3091,3092)',
                },
            },
        },
        "geotec": {
            "role": "editing",
            "type": "vector",
            "layer_name": "Unita' geologico-tecniche",
            "group": "Geologico Tecnica",
            "qlr_path": "geotec.qlr",
            "value_relations": {
                "Tipo_gt": {
                    "relation_table": "vw_tipo_gt",
                    "relation_key": "cod",
                    "relation_value": "descrizione",
                    "order_by_value": False,
                },
                "Stato": {
                    "relation_table": "vw_stato",
                    "relation_key": "cod",
                    "relation_value": "descrizione",
                    "order_by_value": True,
                    "allow_null": True,
                    "filter_expression": "\"cod\" > (if( array_contains(array('RI','GW','GP','GM','GC','SW','SP','SM','SC','OL','OH','MH','ML','CL','CH','PT','LC'),current_value('Tipo_gt')), 0, 99))",
                },
                "Gen": {
                    "relation_table": "vw_gen",
                    "relation_key": "cod",
                    "relation_value": "descrizione",
                    "order_by_value": True,
                    "allow_null": True,
                    "filter_expression": "\"cod\" > (if( array_contains(array('RI','GW','GP','GM','GC','SW','SP','SM','SC','OL','OH','MH','ML','CL','CH','PT','LC'),current_value('Tipo_gt')), 0, 'zz'))",
                },
            },
        },
        "tabelle_accessorie": {
            "role": "editing",
            "type": "group",
            "layer_name": "Tabelle accessorie",
            "group": None,
            "qlr_path": "tabelle_accessorie.qlr",
        },
    }

    REMOVED_EDITING_LAYERS = [
        "isosub_l2",
        "instab_l2",
        "stab_l2",
        "isosub_l3",
        "instab_l3",
        "stab_l3",
        "indice",
    ]

    DEFAULT_TABLE_LAYERS_NAMES = [
        "metadati",
        "vw_amb",
        "vw_attend_mis",
        "vw_cat_s",
        "vw_classe_ind_l",
        "vw_classe_ind_p",
        "vw_cod_instab",
        "vw_cod_stab",
        "vw_gen",
        "vw_mod_identcoord",
        "vw_modo_quota",
        "vw_param_l",
        "vw_param_p",
        "vw_qualita",
        "vw_stato",
        "vw_tipo_el",
        "vw_tipo_ep",
        "vw_tipo_f",
        "vw_tipo_gi",
        "vw_tipo_gt",
        "vw_tipo_hvsr",
        "vw_tipo_ind_l",
        "vw_tipo_ind_p",
    ]

    DEFAULT_LAYOUT_GROUPS = {
        "Carta delle Indagini": "carta_delle_indagini.qlr",
        "Carta geologico-tecnica": "carta_geologico_tecnica.qlr",
        "Carta delle microzone omogenee in prospettiva sismica (MOPS)": "carta_mops.qlr",
        "Carta di microzonazione sismica (FA 0.1-0.5 s)": "carta_fa_01_05.qlr",
        "Carta di microzonazione sismica (FA 0.4-0.8 s)": "carta_fa_04_08.qlr",
        "Carta di microzonazione sismica (FA 0.7-1.1 s)": "carta_fa_07_11.qlr",
        "Carta delle frequenze naturali dei terreni (f0)": "carta_frequenze_f0.qlr",
        "Carta delle frequenze naturali dei terreni (fr)": "carta_frequenze_fr.qlr",
    }

    DEFAULT_RELATIONS = {
        "siti_indagini_puntuali": {
            "parent": "sito_puntuale",
            "child": "indagini_puntuali",
            "parent_key": "id_spu",
            "child_key": "id_spu",
        },
        "indagini_hvsr_puntuali": {
            "parent": "indagini_puntuali",
            "child": "hvsr",
            "parent_key": "id_indpu",
            "child_key": "id_indpu",
        },
        "indagini_parametri_puntuali": {
            "parent": "indagini_puntuali",
            "child": "parametri_puntuali",
            "parent_key": "id_indpu",
            "child_key": "id_indpu",
        },
        "parametri_curve_puntuali": {
            "parent": "parametri_puntuali",
            "child": "curve",
            "parent_key": "id_parpu",
            "child_key": "id_parpu",
        },
        "siti_indagini_lineari": {
            "parent": "sito_lineare",
            "child": "indagini_lineari",
            "parent_key": "id_sln",
            "child_key": "id_sln",
        },
        "indagini_parametri_lineari": {
            "parent": "indagini_lineari",
            "child": "parametri_lineari",
            "parent_key": "id_indln",
            "child_key": "id_indln",
        },
    }

    PRINT_LAYOUT_MODELS = [
        "carta_delle_indagini.qpt",
        "carta_delle_mops.qpt",
        "carta_frequenze_f0.qpt",
        "carta_frequenze_fr.qpt",
        "carta_geologico_tecnica.qpt",
        "carta_ms_fa_01_05.qpt",
        "carta_ms_fa_04_08.qpt",
        "carta_ms_fa_07_11.qpt",
    ]

    NO_OVERLAPS_LAYER_GROUPS = [
        ["instab_l1", "stab_l1"],
        ["instab_l23", "stab_l23"],
    ]

    @classmethod
    def instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        if MzSProjectManager._instance is not None:
            raise Exception("This class is a singleton!")
        else:
            MzSProjectManager._instance = self

        self.log = MzSToolsLogger().log
        self.current_project: QgsProject = None

        self.project_path = None
        self.project_version = None
        self.project_updateable = False
        self.db_path = None
        self.db_connection: Optional[Connection] = None

        self.comune_data: ComuneData = None
        self.project_metadata = None

        self.required_layer_registry = {}

        self.project_issues = None

        self.is_mzs_project: bool = False

    def init_manager(self):
        """Detect if the current project is a MzS Tools project and setup the manager."""
        self.current_project = QgsProject.instance()

        # be careful using Path with QgsProject functions such as absolutePath(), fileName(), baseName(), etc.
        # when clicking on New Project these functions will return empty strings but Path.resolve() will return
        # the paths relative to the last opened project!
        project_path = self.current_project.absolutePath()
        self.log(f"Current project path: {project_path}", log_level=4)
        db_path = Path(project_path) / "db" / "indagini.sqlite"

        # TODO: better project detection
        # if project_file_name != "progetto_MS" or not db_path.exists() or not version_file_path.exists():
        if not project_path or not db_path.exists():
            self.log("No MzS Tools project detected", log_level=4)
            self.is_mzs_project = False
            self.project_path = None
            self.db_path = None
            self.db_connection = None
            self.project_updateable = False
            self.project_issues = None
            return False

        self.is_mzs_project = True

        self.project_path = Path(project_path)
        self.db_path = db_path

        # setup db connection and save it to the manager
        connected = self._setup_db_connection()
        if not connected:
            return False

        # cleanup db connection on project close
        self.current_project.cleared.connect(self.cleanup_db_connection)

        # TODO: load metadata from db if exists
        # self.sm_project_metadata = self.get_sm_project_metadata()

        # check project structure
        # if not self.project_updateable:
        self.check_project_structure()

        # keep track of connected layers to avoid reconnecting signals
        self.editing_signals_connected_layers = {}

        self.log(f"MzS Tools project version {self.project_version} detected. Manager initialized.")

    def _add_project_issue(self, issue_type: str, issue: str, traceback: str = None, log=True):
        if issue_type not in self.project_issues:
            self.project_issues[issue_type] = []
        if traceback:
            issue = f"{issue}\n{traceback}"
        self.project_issues[issue_type].append(issue)
        if log:
            self.log(f"Project issue found: {issue_type} - {issue}", log_level=2)

    def check_project_structure(self):
        # init project issues dict
        self.project_issues = {}

        # TODO: general project health check

        # check project version
        version_file_path = Path(self.project_path) / "progetto" / "versione.txt"
        try:
            with version_file_path.open("r") as f:
                self.project_version = f.read().strip()
        except Exception as e:
            # self.log(f"Error reading project version: {e}", log_level=2)
            # self.project_issues["general"].append("Error reading project version file")
            self._add_project_issue("project", f"Error reading project version file: {e}")

        if self.project_version and self.project_version < __base_version__:
            self.log(
                f"MzS Project is version {self.project_version} and should be updated to version {__base_version__}",
                log_level=1,
            )
            self.project_updateable = True
        else:
            self.project_updateable = False

        # get comune data from db
        self.comune_data = self.get_project_comune_data()
        if not self.comune_data:
            self._add_project_issue("db", "Error reading comune data from project db")

        # check required layers
        self.required_layer_registry = self._build_required_layers_registry()

        # check relations
        self._check_default_project_relations()

    def _setup_db_connection(self):
        # setup db connection
        if not self.db_connection:
            self.log(f"Creating db connection to {self.db_path}...", log_level=4)
            # database cannot be an empty 0-byte file
            if self.db_path.stat().st_size == 0:
                err_msg = self.tr(f"The database file is empty! {self.db_path}")
                self.log(err_msg, log_level=2, push=True, duration=0)
                # self.project_issues["db"].append("Empty database file")
                self._add_project_issue("db", "Empty database file", log=False)
                self.cleanup_db_connection()
                return False

            try:
                self.db_connection = spatialite_connect(str(self.db_path))
                # validate connection
                cursor = self.db_connection.cursor()
                # TODO: quick check for db version and integrity
                # cursor.execute("PRAGMA integrity_check")
                cursor.execute("PRAGMA quick_check")
                # cursor.execute("SELECT * FROM sito_puntuale LIMIT 1")
                cursor.close()
            except Exception as e:
                err_msg = self.tr(f"Error connecting to db! {self.db_path}")
                self.log(f"{err_msg}: {e}", log_level=2, push=True, duration=0)
                self.log(traceback.format_exc(), log_level=2)
                self.cleanup_db_connection()
                return False

        return True

    def cleanup_db_connection(self):
        if self.db_connection:
            self.log(f"Closing db connection to {self.db_path}...", log_level=4)
            self.db_connection.close()
            self.db_connection = None

    def connect_editing_signals(self):
        """connect editing signals to automatically set advanced overlap config for configured layer groups"""
        # for layer in self.current_project.mapLayers().values():
        for group in self.NO_OVERLAPS_LAYER_GROUPS:
            for table_name in group:
                layer_id = self.find_layer_by_table_name_role(table_name, "editing")
                layer = self.current_project.mapLayer(layer_id)
                if layer and layer not in self.editing_signals_connected_layers:
                    layer.editingStarted.connect(partial(self.set_advanced_editing_config, layer, table_name))
                    layer.editingStopped.connect(self.reset_advanced_editing_config)
                    self.editing_signals_connected_layers[layer] = (
                        self.set_advanced_editing_config,
                        self.reset_advanced_editing_config,
                    )

    def set_advanced_editing_config(self, layer, table_name):
        auto_advanced_editing_setting = PlgOptionsManager.get_value_from_key(
            "auto_advanced_editing", default=True, exp_type=bool
        )
        if not auto_advanced_editing_setting:
            return

        self.log("Setting advanced editing options")

        # TODO: config in plugin options? groups, snapping tolerance, etc.

        # TODO: handle editing started on multiple layers: if any layer in any NO_OVERLAPS_LAYER_GROUPS
        # is already in editing mode, don't save the current config

        # save the current config
        self.proj_snapping_config = self.current_project.snappingConfig()
        self.proj_avoid_intersections_layers = self.current_project.avoidIntersectionsLayers()
        self.topological_editing = self.current_project.topologicalEditing()
        self.avoid_intersections_mode = self.current_project.avoidIntersectionsMode()

        # just fail gracefully if something goes wrong
        try:
            snapping_config = QgsSnappingConfig(self.proj_snapping_config)

            # snapping_config.clearIndividualLayerSettings()
            snapping_config.setEnabled(True)
            snapping_config.setMode(QgsSnappingConfig.AdvancedConfiguration)
            snapping_config.setIntersectionSnapping(True)
            snapping_config.setTolerance(20)

            """
            TODO: deprecation warning when using IndividualLayerSettings constructor
            This works in QGIS but not here:

            proj = QgsProject.instance()
            proj_snapping_config = proj.snappingConfig()

            layer = iface.activeLayer()

            layer_settings = proj_snapping_config.individualLayerSettings(layer)
            layer_settings.setEnabled(True)
            layer_settings.setType(QgsSnappingConfig.Vertex)
            layer_settings.setTolerance(20)
            layer_settings.setUnits(QgsTolerance.ProjectUnits)

            proj_snapping_config.setIndividualLayerSettings(layer, layer_settings)
            #proj_snapping_config.addLayers([layer])

            proj.setSnappingConfig(proj_snapping_config)
            """
            layer_settings = QgsSnappingConfig.IndividualLayerSettings(
                True,
                QgsSnappingConfig.VertexFlag,
                20,
                QgsTolerance.ProjectUnits,
            )

            for layer_group in self.NO_OVERLAPS_LAYER_GROUPS:
                if table_name in layer_group:
                    layer_ids = [self.find_layer_by_table_name_role(t_name, "editing") for t_name in layer_group]
                    layers = []
                    for layer_id in layer_ids:
                        layer = self.current_project.mapLayer(layer_id)
                        if layer:
                            layers.append(layer)
                        snapping_config.setIndividualLayerSettings(layer, layer_settings)
                    self.current_project.setAvoidIntersectionsLayers(layers)

            # actually set "follow advanced config" for overlaps
            self.current_project.setAvoidIntersectionsMode(QgsProject.AvoidIntersectionsMode.AvoidIntersectionsLayers)

            # enable topological editing
            self.current_project.setTopologicalEditing(True)

            # apply the new config
            self.current_project.setSnappingConfig(snapping_config)

        except Exception as e:
            self.log(f"Error setting advanced editing config: {e}", log_level=2)

    def reset_advanced_editing_config(self):
        auto_advanced_editing_setting = PlgOptionsManager.get_value_from_key(
            "auto_advanced_editing", default=True, exp_type=bool
        )
        if not auto_advanced_editing_setting:
            return

        self.log("Resetting advanced editing settings")

        try:
            self.current_project.setSnappingConfig(self.proj_snapping_config)
            self.current_project.setAvoidIntersectionsMode(self.avoid_intersections_mode)
            self.current_project.setAvoidIntersectionsLayers(self.proj_avoid_intersections_layers)
            self.current_project.setTopologicalEditing(self.topological_editing)
        except Exception as e:
            self.log(f"Error resetting advanced editing config: {e}", log_level=2)

    def disconnect_editing_signals(self):
        """Disconnect specific editing signals."""
        for layer, (start_func, stop_func) in self.editing_signals_connected_layers.items():
            layer.editingStarted.disconnect(start_func)
            layer.editingStopped.disconnect(stop_func)
        self.editing_signals_connected_layers.clear()

    def get_project_comune_data(self) -> Optional[ComuneData]:
        data = None
        with self.db_connection as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("SELECT * FROM comune_progetto LIMIT 1")
                row = cursor.fetchone()
                if row:
                    data = ComuneData(
                        cod_regio=row[1],
                        cod_prov=row[2],
                        cod_com=row[3],
                        comune=row[4],
                        provincia=row[7],
                        regione=row[8],
                        cod_istat=row[6],
                    )
            finally:
                cursor.close()
        return data

    def _build_required_layers_registry(self):
        table_layer_map = {}
        # search the editing layers
        for table_name, layer_data in MzSProjectManager.DEFAULT_EDITING_LAYERS.items():
            if layer_data["role"] == "editing" and layer_data["type"] not in ["group", "service_group"]:
                # layer_id = self.find_layer_by_table_name_role(table_name, "editing")
                layers = self.find_layers_by_table_name(table_name)
                valid_layers = [
                    layer for layer in layers if layer and layer.customProperty("mzs_tools/layer_role") == "editing"
                ]

                if not valid_layers:
                    msg = f"No 'editing' layers found for table '{table_name}'"
                    self._add_project_issue("layers", msg)
                elif len(valid_layers) > 1:
                    msg = f"Multiple 'editing' layers found for table '{table_name}'"
                    self._add_project_issue("layers", msg)
                else:
                    table_layer_map[table_name] = valid_layers[0].id()

        # search the lookup tables
        for table_name in MzSProjectManager.DEFAULT_TABLE_LAYERS_NAMES:
            # layer_id = self.find_layer_by_table_name_role(table_name, "editing")
            layers = self.find_layers_by_table_name(table_name)
            valid_layers = [
                layer for layer in layers if layer and layer.customProperty("mzs_tools/layer_role") == "editing"
            ]
            if not valid_layers:
                msg = f"No 'editing' layers found for lookup table '{table_name}'"
                self._add_project_issue("layers", msg)
            elif len(valid_layers) > 1:
                msg = f"Multiple 'editing' layers found for lookup table '{table_name}'"
                self._add_project_issue("layers", msg)
            else:
                table_layer_map[table_name] = valid_layers[0].id()

        # search the base layers (comuni, comune_progetto)
        for table_name, layer_data in MzSProjectManager.DEFAULT_BASE_LAYERS.items():
            if layer_data["role"] == "base" and layer_data["type"] not in ["group", "service_group"]:
                layer_id = self.find_layer_by_table_name_role(table_name, "base")
                if layer_id:
                    table_layer_map[table_name] = layer_id

        return table_layer_map

    def _set_form_ui_file(self, layer: QgsVectorLayer, table_name: str):
        form_config = layer.editFormConfig()
        current_ui_path = form_config.uiForm()
        if not current_ui_path:
            return False
        # check if the file exists
        current_ui_path = Path(current_ui_path)
        if not current_ui_path.exists():
            ui_path = DIR_PLUGIN_ROOT / "editing" / f"{table_name}.ui"
            self.log(
                f"UI form file '{current_ui_path}' for layer {layer.name()} does not exist. Setting new file: '{ui_path}'",
                log_level=1,
            )
            form_config.setUiForm(str(ui_path.absolute()))
            layer.setEditFormConfig(form_config)
        return True

    @staticmethod
    def set_project_layer_capabilities(
        layer: QgsMapLayer, identifiable=True, required=False, searchable=True, private=False
    ):
        """
        Set QgsMapLayer.LayerFlag(s) for a layer, as in Project Properties - Data Sources
        The "Read Only" status must be set with layer.setReadOnly() and is not a QgsMapLayer.LayerFlag

        Flags:
        - Identifiable = 1
        - Removable = 2
        - Searchable = 4
        - Private = 8
        """
        # https://gis.stackexchange.com/questions/318506/setting-layer-identifiable-seachable-and-removable-with-python-in-qgis-3
        flags = 0
        if identifiable:
            flags += QgsMapLayer.Identifiable
        if searchable:
            flags += QgsMapLayer.Searchable
        if not required:
            flags += QgsMapLayer.Removable
        if private:
            flags += QgsMapLayer.Private

        layer.setFlags(QgsMapLayer.LayerFlag(flags))

    def set_layer_custom_property(self, layer: QgsMapLayer, property_name: str, property_value: str):
        if layer:
            self.log(
                f"Setting custom property 'mzs_tools/{property_name}': '{property_value}' for layer {layer.name()}",
                log_level=4,
            )
            layer.setCustomProperty(f"mzs_tools/{property_name}", property_value)

    def _set_custom_layer_properties(self):
        """only for testing"""
        self._set_custom_layer_properties_for_group(MzSProjectManager.DEFAULT_BASE_LAYERS, {"layer_role": "base"})
        self._set_custom_layer_properties_for_group(
            MzSProjectManager.DEFAULT_EDITING_LAYERS, {"layer_role": "editing"}
        )

        # set properties for lookup tables
        for table_name in MzSProjectManager.DEFAULT_TABLE_LAYERS_NAMES:
            layers = self.find_layers_by_table_name(table_name)
            for layer in layers:
                self.set_layer_custom_property(layer, "layer_role", "editing")

        self._set_custom_layer_properties_for_group(MzSProjectManager.DEFAULT_LAYOUT_GROUPS, {"layer_role": "layout"})

    def _set_custom_layer_properties_for_group(self, group_dict: dict, custom_properties: dict):
        """only for testing"""
        for table_name, layer_data in group_dict.items():
            if type(layer_data) is dict and layer_data["role"] not in ["group", "service_group"]:
                layers = self.find_layers_by_table_name(table_name)
                for layer in layers:
                    for prop_name, prop_value in custom_properties.items():
                        self.set_layer_custom_property(layer, prop_name, prop_value)
            elif type(layer_data) is str:
                group = self.current_project.layerTreeRoot().findGroup(table_name)
                if group:
                    for layer in group.findLayers():
                        for prop_name, prop_value in custom_properties.items():
                            self.set_layer_custom_property(layer.layer(), prop_name, prop_value)

    def add_default_layers(self, add_base_layers=True, add_editing_layers=True, add_layout_groups=True):
        """Add the default layers to the project, removing first any existing layers of the
           same category (base, editing or layout) pointing to the same database tables.

        Args:
            add_base_layers (bool, optional): Add the default base layers. Defaults to True.
            add_editing_layers (bool, optional): Add the default editing layers. Defaults to True.
            add_layout_groups (bool, optional): Add the default layout layers. Defaults to True.
        """
        # TODO: group names translation
        if not add_base_layers and not add_editing_layers and not add_layout_groups:
            return
        if add_base_layers:
            self._cleanup_base_layers()
            self.log("Adding default base layers")
            self._add_default_layer_group(MzSProjectManager.DEFAULT_BASE_LAYERS, "Cartografia di base")
        if add_layout_groups:
            self._cleanup_layout_groups()
            self.log("Adding default layout groups")
            self._add_default_layout_groups("LAYOUT DI STAMPA")
        if add_editing_layers:
            self._cleanup_editing_layers()
            self.log("Adding default editing layers")
            self._add_default_layer_group(MzSProjectManager.DEFAULT_EDITING_LAYERS, "BANCA DATI GEOGRAFICA")
            self._add_default_value_relations(MzSProjectManager.DEFAULT_EDITING_LAYERS)
            self._add_default_project_relations()
            # the project must be reloaded after adding the default relations to refresh the relation editor widgets
            # self.current_project.write()
            # iface.addProject(str(self.current_project.absoluteFilePath()))

        # remove empty groups from root
        empty_groups = [group for group in self.current_project.layerTreeRoot().children() if group.children() == []]
        for group in empty_groups:
            self.current_project.layerTreeRoot().removeChildNode(group)

        # check project structure
        # self._check_project_structure()

    def _add_default_layer_group(self, group_dict: dict, group_name: str):
        # create new group layer
        root_layer_group = QgsLayerTreeGroup(group_name)
        root_layer_group.setItemVisibilityChecked(False)
        self.current_project.layerTreeRoot().insertChildNode(0, root_layer_group)

        for table_name, layer_data in group_dict.items():
            layer_group = None
            if layer_data["group"]:
                layer_group = root_layer_group.findGroup(layer_data["group"])
                if not layer_group:
                    layer_group = QgsLayerTreeGroup(layer_data["group"])
                    layer_group.setItemVisibilityChecked(False)
                    root_layer_group.addChildNode(layer_group)
            qlr_full_path = DIR_PLUGIN_ROOT / "data" / "layer_defs" / layer_data["qlr_path"]
            layer_added = self.add_layer_from_qlr(layer_group if layer_group else root_layer_group, qlr_full_path)
            if not layer_added or layer_data["group"] == "service_group":
                continue

            # set the data source and layer options for the newly added layer
            # other layers with the same name might be present in the project in other groups,
            # so `self.current_project.mapLayersByName()` might return more than one layer
            for layer_tree_layer in root_layer_group.findLayers():
                if (
                    layer_tree_layer.name() == layer_data["layer_name"]
                    or layer_tree_layer.parent().name() == layer_data["layer_name"]
                ):
                    # self.log(f"Setting data source for layer: {layer_tree_layer.name()}")
                    # uri = QgsDataSourceUri()
                    # uri.setDatabase(str(self.db_path))
                    # schema = ""
                    # if layer_data["type"] == "vector" and "geom_name" in layer_data:
                    #     geom_column = layer_data["geom_name"]
                    # elif layer_data["type"] == "vector":
                    #     geom_column = "geom"
                    # else:
                    #     geom_column = None
                    # uri.setDataSource(
                    #     schema, table_name if layer_data["type"] != "group" else layer_tree_layer.name(), geom_column
                    # )
                    # layer_tree_layer.layer().setDataSource(
                    #     uri.uri(),
                    #     layer_data["layer_name"] if layer_data["type"] == "vector" else layer_tree_layer.name(),
                    #     "spatialite",
                    # )

                    # set .ui files and editing functions for editing layers
                    # layer = layer_tree_layer.layer()
                    # if layer_data["role"] == "editing":
                    #     form_config = layer.editFormConfig()
                    #     # ui_path = DIR_PLUGIN_ROOT / "editing" / f"{table_name}.ui"
                    #     # self.log(f"Setting UI form for layer {layer.name()}: {ui_path}")
                    #     # form_config.setUiForm(str(ui_path))

                    #     try:
                    #         # QGIS >= 3.32
                    #         form_config.setInitCodeSource(Qgis.AttributeFormPythonInitCodeSource.Dialog)
                    #     except:
                    #         # QGIS < 3.32
                    #         form_config.setInitCodeSource(QgsEditFormConfig.CodeSourceDialog)

                    #     form_config.setInitFunction(f"{table_name}_form_init")
                    #     form_config.setInitCode(f"from mzs_tools import {table_name}_form_init")

                    #     layer.setEditFormConfig(form_config)

                    # set subset string if needed
                    if "subset_string" in layer_data and layer_data["subset_string"] is not None:
                        subset_string = layer_data["subset_string"]
                        if subset_string == "cod_regio":
                            subset_string = f"cod_regio = '{self.comune_data.cod_regio}'"
                            layer_tree_layer.layer().setSubsetString(subset_string)

                    # set custom properties
                    # for prop_name, prop_value in custom_properties.items():
                    #     self.set_layer_custom_property(layer_tree_layer.layer(), prop_name, prop_value)

                    # reset flags for testing
                    # self.set_project_layer_capabilities(layer_tree_layer.layer())

                    if layer_data["type"] != "group":
                        break

    def _add_default_value_relations(self, group_dict: dict):
        for table_name, layer_data in group_dict.items():
            if "value_relations" in layer_data:
                layers = self.find_layers_by_table_name(table_name)
                for layer in layers:
                    # TODO: use only the custom property
                    if layer and (layer.customProperty("mzs_tools/layer_role") == "editing" or not layer.readOnly()):
                        current_layer = layer

                for field_name, relation_data in layer_data["value_relations"].items():
                    table = relation_data["relation_table"]
                    table_layers = self.find_layers_by_table_name(table)
                    if len(table_layers) == 0:
                        self.log(
                            f"Error adding value relations: table not found for relation '{field_name}'",
                            log_level=2,
                        )
                        continue
                    if len(table_layers) > 1:
                        self.log(
                            f"Error adding value relations: multiple layers found for relation '{field_name}'",
                            log_level=2,
                        )
                        continue
                    for layer in table_layers:
                        if layer:
                            self.set_value_relation(current_layer, layer, field_name, relation_data)

    def set_value_relation(
        self, layer: QgsVectorLayer, relation_table_layer: QgsVectorLayer, field_name: str, relation_data: dict
    ):
        self.log(f"Setting value relation for field '{field_name}' in layer '{layer.name()}'", log_level=4)
        setup = QgsEditorWidgetSetup(
            "ValueRelation",
            {
                "Layer": relation_table_layer.id(),
                "Key": relation_data["relation_key"],
                "Value": relation_data["relation_value"],
                "OrderByValue": relation_data.get("order_by_value", False),
                "AllowNull": relation_data.get("allow_null", False),
                "FilterExpression": relation_data.get("filter_expression", ""),
            },
        )
        layer.setEditorWidgetSetup(layer.fields().indexOf(field_name), setup)

    def _check_default_project_relations(self):
        rel_manager = self.current_project.relationManager()
        relations_ok = True
        for relation_name, relation_data in MzSProjectManager.DEFAULT_RELATIONS.items():
            rels = rel_manager.relationsByName(relation_name)
            if not rels:
                # self.log(f"Error: relation '{relation_name}' not found", log_level=2)
                self._add_project_issue("project", f"Relation '{relation_name}' not found")
                relations_ok = False
                continue
            if not rels[0].isValid():
                # self.log(f"Error: relation '{relation_name}' is not valid: {rels[0].validationError()}", log_level=2)
                self._add_project_issue(
                    "project", f"Relation '{relation_name}' is not valid: {rels[0].validationError()}"
                )
                relations_ok = False
                continue

            parent_layers = self.find_layers_by_table_name(relation_data["parent"])
            if not parent_layers:
                self._add_project_issue("project", f"Parent layer not found for relation '{relation_name}'")
                relations_ok = False
                continue
            child_layers = self.find_layers_by_table_name(relation_data["child"])
            if not child_layers:
                self._add_project_issue("project", f"Child layer not found for relation '{relation_name}'")
                relations_ok = False
                continue
            parent_layer_ids = [
                layer.id() for layer in parent_layers if layer.customProperty("mzs_tools/layer_role") == "editing"
            ]
            if rels[0].referencedLayerId() not in parent_layer_ids:
                self._add_project_issue("project", f"Relation '{relation_name}' parent layer is not set correctly")
                relations_ok = False
                continue
            child_layer_ids = [
                layer.id() for layer in child_layers if layer.customProperty("mzs_tools/layer_role") == "editing"
            ]
            if rels[0].referencingLayerId() not in child_layer_ids:
                self._add_project_issue("project", f"Relation '{relation_name}' child layer is not set correctly")
                relations_ok = False
                continue

        return relations_ok

    def _add_default_project_relations(self):
        rel_manager = self.current_project.relationManager()

        for relation_name, relation_data in MzSProjectManager.DEFAULT_RELATIONS.items():
            parent_layer_id = self.find_layer_by_table_name_role(relation_data["parent"], "editing")
            child_layer_id = self.find_layer_by_table_name_role(relation_data["child"], "editing")
            if not parent_layer_id or not child_layer_id:
                msg = f"Error adding relations: parent or child layer not found for relation '{relation_name}'"
                # self.log(msg, log_level=2)
                # self.project_issues["layers"].append(msg)
                self._add_project_issue("project", msg)
                continue

            rel = QgsRelation()
            rel.setId(relation_name)
            rel.setName(relation_name)
            rel.setReferencedLayer(parent_layer_id)
            rel.setReferencingLayer(child_layer_id)
            rel.addFieldPair(relation_data["parent_key"], relation_data["child_key"])

            if not rel.isValid():
                msg = f"Error creating relation '{relation_name}': {rel.validationError()}"
                # self.log(msg, log_level=2)
                # self.project_issues["layers"].append(msg)
                self._add_project_issue("project", msg)
                continue

            rel_manager.addRelation(rel)

    def _add_default_layout_groups(self, group_name):
        root_layer_group = QgsLayerTreeGroup(group_name)
        root_layer_group.setIsMutuallyExclusive(True)
        root_layer_group.setItemVisibilityChecked(False)
        self.current_project.layerTreeRoot().insertChildNode(0, root_layer_group)
        for group_name, qlr_path in MzSProjectManager.DEFAULT_LAYOUT_GROUPS.items():
            qlr_full_path = DIR_PLUGIN_ROOT / "data" / "layer_defs" / "print_layout" / qlr_path
            self.add_layer_from_qlr(root_layer_group, qlr_full_path)
        # set custom property for all layout layers
        # for layer_tree_layer in root_layer_group.findLayers():
        #     for prop_name, prop_value in custom_properties.items():
        #         self.set_layer_custom_property(layer_tree_layer.layer(), prop_name, prop_value)

    def load_ogc_services(self, regional_wms=True, webms_wms=True, webms_wfs=True, geo_ispra=True):
        root_layer_group = self.current_project.layerTreeRoot().findGroup("Cartografia di base")
        if not root_layer_group:
            # add new OGC services groups
            root_layer_group = QgsLayerTreeGroup("SERVIZI OGC")
            root_layer_group.setItemVisibilityChecked(False)
            self.current_project.layerTreeRoot().addChildNode(root_layer_group)

        if regional_wms:
            self.add_layer_from_qlr(
                root_layer_group, DIR_PLUGIN_ROOT / "data" / "layer_defs" / "ogc_services" / "ctr_regioni.qlr"
            )
        if webms_wms:
            self.add_layer_from_qlr(
                root_layer_group, DIR_PLUGIN_ROOT / "data" / "layer_defs" / "ogc_services" / "ms_cle_wms.qlr"
            )
        if webms_wfs:
            self.add_layer_from_qlr(
                root_layer_group, DIR_PLUGIN_ROOT / "data" / "layer_defs" / "ogc_services" / "ms_cle_wfs.qlr"
            )
        if geo_ispra:
            self.add_layer_from_qlr(
                root_layer_group,
                DIR_PLUGIN_ROOT / "data" / "layer_defs" / "ogc_services" / "servizio_geologico_25k.qlr",
            )

        return root_layer_group.name()

    def add_layer_from_qlr(self, layer_group: QgsLayerTreeGroup, qlr_full_path: Path):
        # copy .qlr file in project folder
        shutil.copy(qlr_full_path, self.project_path)
        success, error_msg = QgsLayerDefinition.loadLayerDefinition(
            str(self.project_path / qlr_full_path.name),
            self.current_project,
            layer_group,
        )
        # remove the copied qlr file
        os.remove(self.project_path / qlr_full_path.name)
        if not success:
            self.log(f"Error loading layer from .qlr ({qlr_full_path}): {error_msg}", log_level=2)
        return success

    def _cleanup_base_layers(self):
        self.log("Cleaning up base layers...", log_level=4)
        for table_name, layer_data in MzSProjectManager.DEFAULT_BASE_LAYERS.items():
            if layer_data["type"] == "service_group":
                group = self.current_project.layerTreeRoot().findGroup(layer_data["layer_name"])
                if group:
                    self.log(f"Removing group '{table_name}'", log_level=4)
                    parent_node = group.parent()
                    parent_node.removeChildNode(group)
                continue
            layers = self.find_layers_by_table_name(table_name)
            for layer in layers:
                # To remove old layers without the custom property, the "required" flag could be used.
                # However, this is not necessary if the projects are cleared on update to 2.0.0
                if layer and layer.customProperty("mzs_tools/layer_role") == "base":
                    self.log(f"Removing layer '{layer.name()}' (table: '{table_name}')", log_level=4)
                    layer_node = self.current_project.layerTreeRoot().findLayer(layer.id())
                    parent_node = None
                    if layer_node:
                        parent_node = layer_node.parent()
                    self.current_project.removeMapLayer(layer)
                    # remove parent group if empty
                    if parent_node and len(parent_node.children()) == 0 and parent_node.parent():
                        parent_node.parent().removeChildNode(parent_node)

    def _cleanup_editing_layers(self):
        self.log("Cleaning up removed layers...", log_level=4)
        for table_name in MzSProjectManager.REMOVED_EDITING_LAYERS:
            layers = self.find_layers_by_table_name(table_name)
            for layer in layers:
                if layer:
                    self.log(f"Removing old layer '{layer.name()}' (table: '{table_name}')", log_level=4)
                    layer_node = self.current_project.layerTreeRoot().findLayer(layer.id())
                    parent_node = None
                    if layer_node:
                        parent_node = layer_node.parent()
                    self.current_project.removeMapLayer(layer)
                    # remove parent group if empty
                    if parent_node and len(parent_node.children()) == 0 and parent_node.parent():
                        parent_node.parent().removeChildNode(parent_node)

        self.log("Cleaning up editing layers...", log_level=4)
        for table_name in MzSProjectManager.DEFAULT_EDITING_LAYERS.keys():
            layers = self.find_layers_by_table_name(table_name)
            for layer in layers:
                if layer and layer.customProperty("mzs_tools/layer_role") == "editing":
                    self.log(f"Removing layer '{layer.name()}' (table: '{table_name}')", log_level=4)
                    layer_node = self.current_project.layerTreeRoot().findLayer(layer.id())
                    parent_node = None
                    if layer_node:
                        parent_node = layer_node.parent()
                    self.current_project.removeMapLayer(layer)
                    # remove parent group if empty
                    if parent_node and len(parent_node.children()) == 0 and parent_node.parent():
                        parent_node.parent().removeChildNode(parent_node)

        self.log("Cleaning up table layers...", log_level=4)
        for table_name in MzSProjectManager.DEFAULT_TABLE_LAYERS_NAMES:
            layers = self.find_layers_by_table_name(table_name)
            for layer in layers:
                if layer and layer.customProperty("mzs_tools/layer_role") == "editing":
                    self.log(f"Removing layer '{layer.name()}' (table: '{table_name}')", log_level=4)
                    layer_node = self.current_project.layerTreeRoot().findLayer(layer.id())
                    parent_node = None
                    if layer_node:
                        parent_node = layer_node.parent()
                    self.current_project.removeMapLayer(layer)
                    # remove parent group if empty
                    if parent_node and len(parent_node.children()) == 0 and parent_node.parent():
                        parent_node.parent().removeChildNode(parent_node)

    def _cleanup_layout_groups(self):
        self.log("Cleaning up layout groups...", log_level=4)
        for group_name in MzSProjectManager.DEFAULT_LAYOUT_GROUPS.keys():
            group = self.current_project.layerTreeRoot().findGroup(group_name)
            if group:
                parent_node = None
                if group.parent():
                    parent_node = group.parent()
                else:
                    continue
                self.log(f"Removing layout group '{group_name}'", log_level=4)
                parent_node.removeChildNode(group)
                # remove parent group if empty
                if parent_node and len(parent_node.children()) == 0 and parent_node.parent():
                    parent_node.parent().removeChildNode(parent_node)

    def find_layers_by_table_name(self, table_name: str) -> list:
        """Find all vector layers in the currrent project with the given table name in datasource uri."""
        layers = []
        for layer in self.current_project.mapLayers().values():
            if type(layer) is QgsVectorLayer:
                uri_table = layer.dataProvider().uri().table()
                if not uri_table:
                    # try to get the table name from 'layername' in dataSourceUri()...
                    strings = layer.dataProvider().dataSourceUri().split("layername=")
                    if len(strings) > 1:
                        uri_table = strings[1]
                if uri_table == table_name:
                    layers.append(layer)
        return layers

    def find_layer_by_table_name_role(self, table_name: str, role: str) -> Optional[str]:
        """Find a single vector layer by table name and custom property mzs_tools/layer_role

        Args:
            table_name (str): Name of the database table
            role (str): Value of the custom property 'mzs_tools/layer_role' assigned to the layer

        Returns:
            Optional[str]: Layer ID or None if not found or multiple layers found
        """
        layers = self.find_layers_by_table_name(table_name)
        valid_layers = [layer for layer in layers if layer and layer.customProperty("mzs_tools/layer_role") == role]
        if not valid_layers or len(valid_layers) > 1:
            return None
        return valid_layers[0].id()

    # def add_editing_layer(self, table_name, layer_name, type):
    #     if not self.db_connection:
    #         self.log("No db connection available!", log_level=2)
    #         return

    #     with self.db_connection as conn:
    #         cursor = conn.cursor()
    #         cursor.execute(f"SELECT * FROM {table_name} LIMIT 1")
    #         fields = cursor.description
    #         cursor.close()

    #     # create the layer
    #     uri = QgsDataSourceUri()
    #     uri.setDatabase(str(self.db_path))
    #     schema = ""
    #     geom_column = "geom" if type == "vector" else None
    #     uri.setDataSource(schema, table_name, geom_column)

    #     layer = QgsVectorLayer(uri.uri(), layer_name, "spatialite")
    #     # if not layer.isValid():
    #     #     self.log(f"Error creating layer {layer_name}", log_level=2)
    #     #     return

    #     # set the fields
    #     layer_fields = layer.fields()
    #     for field in fields:
    #         field_name = field[0]
    #         field_type = field[1]
    #         if field_name == "pkuid":
    #             continue
    #         layer_fields.append(QgsField(field_name, self.get_qvariant_type(field_type)))

    #     layer.updateFields()

    #     # add the layer to the project
    #     self.current_project.addMapLayer(layer)

    #     # load the QLR style
    #     # layer.loadNamedStyle(str(DIR_PLUGIN_ROOT / "data" / "styles" / qlr_path))
    #     # layer.triggerRepaint()

    # def get_qvariant_type(self, field_type):
    #     if field_type == "INTEGER":
    #         return QVariant.Int
    #     elif field_type == "REAL":
    #         return QVariant.Double
    #     elif field_type == "TEXT":
    #         return QVariant.String
    #     elif field_type == "BLOB":
    #         return QVariant.ByteArray
    #     else:
    #         return QVariant.String

    def create_project_from_template(self, comune_name, cod_istat, study_author, author_email, dir_out):
        """pre-2.0.0 method to create a new project"""
        # extract project template in the output directory
        self.extract_project_template(dir_out)

        comune_name = self.sanitize_comune_name(comune_name)
        new_project_path = os.path.join(dir_out, f"{cod_istat}_{comune_name}")
        os.rename(os.path.join(dir_out, "progetto_MS"), new_project_path)

        self.current_project.read(os.path.join(new_project_path, "progetto_MS.qgs"))

        # init new project info
        self.current_project = QgsProject.instance()
        self.project_path = Path(self.current_project.absolutePath())
        self.db_path = self.project_path / "db" / "indagini.sqlite"

        self._setup_db_connection()

        self.customize_project_template(cod_istat)

        self.create_basic_project_metadata(cod_istat, study_author, author_email)

        # Refresh layouts
        self.refresh_project_layouts()

        # write the version file
        with open(os.path.join(self.project_path, "progetto", "versione.txt"), "w") as f:
            f.write(__base_version__)

        # Save the project
        self.current_project.write(os.path.join(new_project_path, "progetto_MS.qgs"))

        # completely reload the project
        iface.addProject(os.path.join(new_project_path, "progetto_MS.qgs"))

        return new_project_path

    def create_project(
        self, comune_name: str, cod_istat: str, study_author: str, author_email: str, dir_out: str
    ) -> Path:
        """Create a new MzS Tools project for a municipality in the specified directory.

        Args:
            comune_name (str): Name of the municipality
            cod_istat (str): ISTAT code of the municipality
            study_author (str): Name of the study author
            author_email (str): Email of the study author
            dir_out (str): Output directory

        Returns:
            Path: Path to the created project directory
        """
        comune_name = self.sanitize_comune_name(comune_name)
        new_project_path = Path(dir_out) / f"{cod_istat}_{comune_name}"
        # create the project directory
        new_project_path.mkdir(parents=True, exist_ok=False)

        # Allegati paths
        allegati_paths = ["Altro", "Documenti", "log", "Plot", "Spettri"]
        for sub_dir in allegati_paths:
            sub_dir_path = new_project_path / "Allegati" / sub_dir
            sub_dir_path.mkdir(parents=True, exist_ok=False)

        loghi_path = new_project_path / "progetto" / "loghi"
        loghi_path.mkdir(parents=True, exist_ok=False)

        # copy the db file
        db_path = new_project_path / "db"
        db_path.mkdir(parents=True, exist_ok=False)
        self.extract_database_template(db_path)

        self.current_project = QgsProject.instance()

        self.project_path = new_project_path
        self.db_path = new_project_path / "db" / "indagini.sqlite"
        self._setup_db_connection()

        self.update_db_version_info()

        self._insert_comune_progetto(cod_istat)
        self.comune_data = self.get_project_comune_data()

        self.add_default_layers()

        self.customize_project(cod_istat)

        self.create_basic_project_metadata(cod_istat, study_author, author_email)

        self.refresh_project_layouts()

        # write the version file
        with open(os.path.join(self.project_path, "progetto", "versione.txt"), "w") as f:
            f.write(__base_version__)

        # Save the project
        self.current_project.write(os.path.join(new_project_path, "progetto_MS.qgz"))

        # completely reload the project
        iface.addProject(os.path.join(new_project_path, "progetto_MS.qgz"))

        return new_project_path

    def update_project_from_template(self):
        """pre-2.0.0 method to update a project"""
        if not self.project_updateable:
            self.log("Requested project update for non-updateable project!", log_level=1)
            return

        # extract project template in the current project directory (will be in "progetto_MS" subdir)
        self.extract_project_template(self.project_path)

        # remove old project files (maschere, script, loghi, progetto_MS.qgs)
        shutil.rmtree(os.path.join(self.project_path, "progetto", "maschere"))
        shutil.copytree(
            os.path.join(self.project_path, "progetto_MS", "progetto", "maschere"),
            os.path.join(self.project_path, "progetto", "maschere"),
        )

        shutil.rmtree(os.path.join(self.project_path, "progetto", "script"))
        shutil.copytree(
            os.path.join(self.project_path, "progetto_MS", "progetto", "script"),
            os.path.join(self.project_path, "progetto", "script"),
        )

        shutil.rmtree(os.path.join(self.project_path, "progetto", "loghi"))
        shutil.copytree(
            os.path.join(self.project_path, "progetto_MS", "progetto", "loghi"),
            os.path.join(self.project_path, "progetto", "loghi"),
        )

        # write the new version to the version file
        with open(os.path.join(self.project_path, "progetto", "versione.txt"), "w") as f:
            f.write(__base_version__)

        os.remove(os.path.join(self.project_path, "progetto_MS.qgs"))
        shutil.copyfile(
            os.path.join(self.project_path, "progetto_MS", "progetto_MS.qgs"),
            os.path.join(self.project_path, "progetto_MS.qgs"),
        )

        # read the new project file inside the loaded (old) project
        self.current_project.read(os.path.join(self.project_path, "progetto_MS.qgs"))

        self._setup_db_connection()

        # apply project customizations without creating comune feature
        self.customize_project_template(self.comune_data.cod_istat, insert_comune_progetto=False)

        # cleanup the extracted project template
        shutil.rmtree(os.path.join(self.project_path, "progetto_MS"))

        # Refresh layouts
        self.refresh_project_layouts()

        # Save the project
        self.current_project.write(os.path.join(self.project_path, "progetto_MS.qgs"))

        # completely reload the project
        iface.addProject(os.path.join(self.project_path, "progetto_MS.qgs"))

        return self.project_path

    def update_project(self):
        """Update the project without loading the project template.
        The database structure should be already updated.
        """
        if not self.project_updateable:
            self.log("Requested project update for non-updateable project!", log_level=1)
            return

        old_version = self.project_version

        if old_version < "2.0.0":
            # version is too old, clear the project and start from scratch
            if self.db_connection:
                self.update_history_table("project", old_version, __version__, "clearing and rebuilding project")
            self.current_project.clear()  # db connection is automatically closed!

            self.add_default_layers()
            self.customize_project(self.comune_data.cod_istat)
            self.refresh_project_layouts()

            # write the version file
            with open(self.project_path / "progetto" / "versione.txt", "w") as f:
                f.write(__base_version__)

            # Save the project
            self.current_project.write(str(self.project_path / "progetto_MS.qgz"))

            # cleanup project files
            old_files = [
                self.project_path / "progetto_MS.qgs",
                self.project_path / "progetto_MS.qgs~",
                self.project_path / "progetto_MS_attachments.zip",
                self.project_path / "progetto" / "script",
                self.project_path / "progetto" / "maschere",
            ]
            for path in old_files:
                if path.exists():
                    if path.is_file():
                        path.unlink()
                    elif path.is_dir():
                        shutil.rmtree(path)

            # completely reload the project
            iface.addProject(os.path.join(self.project_path, "progetto_MS.qgz"))

        # for future versions it should be possible to update what's needed without clearing the project
        # elif self.project_version < "2.0.1":
        #   self.add_default_layers(add_base_layers=False, add_editing_layers=False, add_layout_groups=True)

        if self.db_connection:
            self.update_history_table("project", old_version, __version__, "project updated successfully")

        self.log(
            self.tr(f"Project upgrades completed! Project upgraded to version {__base_version__}"),
            push=True,
            duration=0,
        )

    def customize_project_template(self, cod_istat, insert_comune_progetto=True):
        """pre-2.0.0 method to customize the project with the selected comune data."""

        # comune_record = self.get_comune_record(cod_istat)
        # feature = self.create_comune_feature(comune_record)

        # TODO: get layer from self.table_layer_map
        layer_comune_progetto = self.current_project.mapLayersByName("Comune del progetto")[0]

        # if insert_comune_progetto:
        #     layer_comune_progetto.startEditing()
        #     data_provider = layer_comune_progetto.dataProvider()
        #     data_provider.addFeatures([feature])
        #     layer_comune_progetto.commitChanges()
        #     layer_comune_progetto.updateExtents()

        comune_data = None
        if insert_comune_progetto:
            with self.db_connection as conn:
                cursor = conn.cursor()
                try:
                    cursor.execute(
                        """INSERT INTO comune_progetto (cod_regio, cod_prov, "cod_com ", comune, geom, cod_istat, provincia, regione)
                        SELECT cod_regio, cod_prov, cod_com, comune, GEOMETRY, cod_istat, provincia, regione FROM comuni WHERE cod_istat = ?""",
                        (cod_istat,),
                    )
                    conn.commit()

                    last_inserted_id = cursor.lastrowid

                    cursor.execute(
                        """SELECT cod_regio, comune, provincia, regione
                        FROM comune_progetto WHERE rowid = ?""",
                        (last_inserted_id,),
                    )
                    comune_data = cursor.fetchone()
                except Exception as e:
                    conn.rollback()
                    self.log(f"Failed to insert comune data: {e}", log_level=2, push=True, duration=0)
                finally:
                    cursor.close()
        else:
            with self.db_connection as conn:
                try:
                    cursor = conn.cursor()
                    # assuming there is only one record in comune_progetto
                    cursor.execute("""SELECT cod_regio, comune, provincia, regione FROM comune_progetto LIMIT 1""")
                    comune_data = cursor.fetchone()
                except Exception as e:
                    self.log(f"Failed to read comune data: {e}", log_level=2, push=True, duration=0)
                finally:
                    cursor.close()

        # attribute_map = feature.attributeMap()
        # codice_regio = attribute_map["cod_regio"]
        # comune = attribute_map["comune"]
        # provincia = attribute_map["provincia"]
        # regione = attribute_map["regione"]

        codice_regio = comune_data[0]
        comune = comune_data[1]
        provincia = comune_data[2]
        regione = comune_data[3]

        layer_limiti_comunali = self.current_project.mapLayersByName("Limiti comunali")[0]
        layer_limiti_comunali.removeSelection()
        layer_limiti_comunali.setSubsetString(f"cod_regio='{codice_regio}'")

        logo_regio_in = os.path.join(DIR_PLUGIN_ROOT, "img", "logo_regio", codice_regio + ".png")
        logo_regio_out = os.path.join(self.project_path, "progetto", "loghi", "logo_regio.png")
        shutil.copyfile(logo_regio_in, logo_regio_out)

        mainPath = QgsProject.instance().homePath()
        canvas = iface.mapCanvas()

        imageFilename = os.path.join(mainPath, "progetto", "loghi", "mappa_reg.png")
        # TODO: this assumes comune_progetto and comuni layers are the only layers currently active
        save_map_image(imageFilename, layer_limiti_comunali, canvas)

        layer_comune_progetto.dataProvider().updateExtents()
        layer_comune_progetto.updateExtents()
        # extent = layer_comune_progetto.dataProvider().extent()
        canvas.setExtent(layer_comune_progetto.extent())

        layout_manager = QgsProject.instance().layoutManager()
        layouts = layout_manager.printLayouts()

        for layout in layouts:
            map_item = layout.itemById("mappa_0")
            map_item.zoomToExtent(canvas.extent())
            map_item_2 = layout.itemById("regio_title")
            map_item_2.setText("Regione " + regione)
            map_item_3 = layout.itemById("com_title")
            map_item_3.setText("Comune di " + comune)
            map_item_4 = layout.itemById("logo")
            map_item_4.refreshPicture()
            map_item_5 = layout.itemById("mappa_1")
            map_item_5.refreshPicture()

        # set project title
        project_title = f"MzS Tools - Comune di {comune} ({provincia}, {regione}) - Studio di Microzonazione Sismica"
        self.current_project.setTitle(project_title)

    def customize_project(self, cod_istat):
        """Customize the project with the selected comune data."""

        crs = QgsCoordinateReferenceSystem("EPSG:32633")
        self.current_project.setCrs(crs)

        logo_regio_in = DIR_PLUGIN_ROOT / "resources" / "logo_regioni" / f"{self.comune_data.cod_regio}.png"
        logo_regio_out = self.project_path / "progetto" / "loghi" / "logo_regio.png"
        shutil.copyfile(logo_regio_in, logo_regio_out)

        # TODO: define a resource list for a project
        logo_regioni_path = DIR_PLUGIN_ROOT / "resources" / "img" / "logo_conferenza_regioni_province_autonome.jpg"
        shutil.copy(logo_regioni_path, self.project_path / "progetto" / "loghi")
        logo_dpc_path = DIR_PLUGIN_ROOT / "resources" / "img" / "logo_dpc.jpg"
        shutil.copy(logo_dpc_path, self.project_path / "progetto" / "loghi")

        mainPath = QgsProject.instance().homePath()
        canvas = iface.mapCanvas()

        image_file_path = os.path.join(mainPath, "progetto", "loghi", "mappa_reg.png")
        layer_limiti_comunali_id = self.find_layer_by_table_name_role("comuni", "base")
        layer_limiti_comunali_node = self.current_project.layerTreeRoot().findLayer(layer_limiti_comunali_id)
        layer_limiti_comunali = layer_limiti_comunali_node.layer()

        layer_comune_progetto_id = self.find_layer_by_table_name_role("comune_progetto", "base")
        layer_comune_progetto_node = self.current_project.layerTreeRoot().findLayer(layer_comune_progetto_id)
        layer_comune_progetto = layer_comune_progetto_node.layer()
        layer_comune_progetto.dataProvider().updateExtents()
        layer_comune_progetto.updateExtents()
        # extent = layer_comune_progetto.dataProvider().extent()
        canvas.setExtent(layer_comune_progetto.extent())

        # TODO: this assumes comune_progetto and comuni layers are the only layers currently active
        layer_limiti_comunali_node.setItemVisibilityCheckedParentRecursive(True)
        layer_comune_progetto_node.setItemVisibilityCheckedParentRecursive(True)
        save_map_image(image_file_path, layer_limiti_comunali, canvas)

        canvas.setExtent(layer_comune_progetto.extent())

        self.load_print_layouts()

        layout_manager = QgsProject.instance().layoutManager()
        layouts = layout_manager.printLayouts()

        for layout in layouts:
            map_item = layout.itemById("mappa_0")
            map_item.zoomToExtent(canvas.extent())
            map_item_2 = layout.itemById("regio_title")
            map_item_2.setText("Regione " + self.comune_data.regione)
            map_item_3 = layout.itemById("com_title")
            map_item_3.setText("Comune di " + self.comune_data.comune)
            map_item_4 = layout.itemById("logo")
            map_item_4.refreshPicture()
            map_item_5 = layout.itemById("mappa_1")
            map_item_5.refreshPicture()

        # set project title
        project_title = f"MzS Tools - Comune di {self.comune_data.comune} ({self.comune_data.provincia}, {self.comune_data.regione}) - Studio di Microzonazione Sismica"
        self.current_project.setTitle(project_title)

    def _insert_comune_progetto(self, cod_istat):
        with self.db_connection as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(
                    """INSERT INTO comune_progetto (cod_regio, cod_prov, "cod_com ", comune, geom, cod_istat, provincia, regione)
                        SELECT cod_regio, cod_prov, cod_com, comune, GEOMETRY, cod_istat, provincia, regione FROM comuni WHERE cod_istat = ?""",
                    (cod_istat,),
                )
                conn.commit()
            except Exception as e:
                conn.rollback()
                self.log(f"Failed to insert comune data: {e}", log_level=2, push=True, duration=0)
            finally:
                cursor.close()

    def load_print_layouts(self):
        for model_file_name in MzSProjectManager.PRINT_LAYOUT_MODELS:
            self.load_print_layout_model(model_file_name)

    def load_print_layout_model(self, model_file_name: str):
        layout_manager = self.current_project.layoutManager()

        layout = QgsPrintLayout(self.current_project)

        # load the layout model
        layout_model_path = DIR_PLUGIN_ROOT / "data" / "print_layouts" / model_file_name

        with layout_model_path.open("r") as f:
            layout_model = f.read()

        doc = QDomDocument()
        doc.setContent(layout_model)

        layout.loadFromTemplate(doc, QgsReadWriteContext())

        layout_manager.addLayout(layout)

    def refresh_project_layouts(self):
        layout_manager = self.current_project.layoutManager()
        layouts = layout_manager.printLayouts()
        for layout in layouts:
            layout.refresh()

    def update_db(self):
        sql_scripts = []
        if self.project_version < "0.8":
            sql_scripts.append("query_v08.sql")
        if self.project_version < "0.9":
            sql_scripts.append("query_v09.sql")
        if self.project_version < "1.2":
            sql_scripts.append("query_v10_12.sql")
        if self.project_version < "1.9":
            sql_scripts.append("query_v19.sql")
        if self.project_version < "1.9.2":
            sql_scripts.append("query_v192.sql")
        if self.project_version < "1.9.3":
            sql_scripts.append("query_v193.sql")
        if self.project_version < "2.0.0":
            sql_scripts.append("query_v200.sql")

        for upgrade_script in sql_scripts:
            self.log(f"Executing: {upgrade_script}", log_level=1)
            self._exec_db_upgrade_script(upgrade_script)

        for upgrade_script in sql_scripts:
            # doing this in a separate loop because the mzs_tools_update_history table was created only in v2.0.0
            self.update_history_table("db", self.project_version, __version__, f"executed script {upgrade_script}")

        # update mzs_tools_version table
        self.update_db_version_info()

        self.log(
            self.tr(f"Database upgrades completed! Database upgraded to version {__base_version__}"),
            push=True,
            duration=0,
        )

    def _exec_db_upgrade_script(self, script_name):
        with self.db_connection as conn:
            cursor = conn.cursor()
            script_path = DIR_PLUGIN_ROOT / "data" / "sql_scripts" / script_name
            with script_path.open("r") as f:
                cursor.executescript(f.read())
            cursor.close()

    def update_history_table(self, component: str, from_version: str, to_version: str, notes: str = None):
        try:
            with self.db_connection as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='mzs_tools_update_history'")
                if cursor.fetchone():
                    cursor.execute(
                        "INSERT INTO mzs_tools_update_history (updated_component, from_version, to_version, notes) VALUES (?, ? ,?, ?)",
                        (component, from_version, to_version, notes),
                    )
                    conn.commit()
        except Exception as e:
            self.log(f"Failed to update history table: {e}", log_level=2)
        finally:
            cursor.close()

    def update_db_version_info(self):
        try:
            with self.db_connection as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT OR REPLACE INTO mzs_tools_version (id, db_version) VALUES (?, ?)",
                    (
                        1,
                        __base_version__,
                    ),
                )
                conn.commit()
        except Exception as e:
            self.log(f"Failed to update version info: {e}", log_level=2)
        finally:
            cursor.close()

    def create_basic_project_metadata(self, cod_istat, study_author=None, author_email=None):
        """Create a basic metadata record for an MzS Tools project."""
        date_now = datetime.datetime.now().strftime(r"%d/%m/%Y")
        layer_comune_id = self.find_layer_by_table_name_role("comune_progetto", "base")
        extent = self.current_project.layerTreeRoot().findLayer(layer_comune_id).layer().extent()
        values = {
            "id_metadato": f"{cod_istat}M1",
            "liv_gerarchico": "series",
            "resp_metadato_nome": study_author,
            "resp_metadato_email": author_email,
            "data_metadato": date_now,
            "srs_dati": 32633,
            "ruolo": "owner",
            "formato": "mapDigital",
            "tipo_dato": "vector",
            "keywords": "Microzonazione Sismica, Pericolosita Sismica",
            "keywords_inspire": "Zone a rischio naturale, Geologia",
            "limitazione": "nessuna limitazione",
            "vincoli_accesso": "nessuno",
            "vincoli_fruibilita": "nessuno",
            "vincoli_sicurezza": "nessuno",
            "categoria_iso": "geoscientificInformation",
            "estensione_ovest": str(extent.xMinimum()),
            "estensione_est": str(extent.xMaximum()),
            "estensione_sud": str(extent.yMinimum()),
            "estensione_nord": str(extent.yMaximum()),
        }
        with self.db_connection as conn:
            conn.execute(
                """
                INSERT INTO metadati (
                    id_metadato, liv_gerarchico, resp_metadato_nome, resp_metadato_email, data_metadato, srs_dati, 
                    ruolo, formato, tipo_dato, keywords, keywords_inspire, limitazione, vincoli_accesso, vincoli_fruibilita, 
                    vincoli_sicurezza, categoria_iso, estensione_ovest, estensione_est, estensione_sud, estensione_nord
                ) VALUES (
                    :id_metadato, :liv_gerarchico, :resp_metadato_nome, :resp_metadato_email, :data_metadato, :srs_dati, 
                    :ruolo, :formato, :tipo_dato, :keywords, :keywords_inspire, :limitazione, :vincoli_accesso, :vincoli_fruibilita,
                    :vincoli_sicurezza, :categoria_iso, :estensione_ovest, :estensione_est, :estensione_sud, :estensione_nord
                );
                """,
                values,
            )

    def count_indagini_data(self):
        result = {
            "sito_puntuale": [],
            "indagini_puntuali": [],
            "parametri_puntuali": [],
            "curve": [],
            "sito_lineare": [],
            "indagini_lineari": [],
            "parametri_lineari": [],
        }
        with self.db_connection as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM sito_puntuale")
            result["sito_puntuale"].append(cursor.fetchone()[0])
            res = cursor.execute('SELECT seq FROM sqlite_sequence WHERE name="sito_puntuale"').fetchone()
            result["sito_puntuale"].append(res[0] if res else 0)

            cursor.execute("SELECT COUNT(*) FROM indagini_puntuali")
            result["indagini_puntuali"].append(cursor.fetchone()[0])
            res = cursor.execute('SELECT seq FROM sqlite_sequence WHERE name="indagini_puntuali"').fetchone()
            result["indagini_puntuali"].append(res[0] if res else 0)

            cursor.execute("SELECT COUNT(*) FROM parametri_puntuali")
            result["parametri_puntuali"].append(cursor.fetchone()[0])
            res = cursor.execute('SELECT seq FROM sqlite_sequence WHERE name="parametri_puntuali"').fetchone()
            result["parametri_puntuali"].append(res[0] if res else 0)

            cursor.execute("SELECT COUNT(*) FROM curve")
            result["curve"].append(cursor.fetchone()[0])
            res = cursor.execute('SELECT seq FROM sqlite_sequence WHERE name="curve"').fetchone()
            result["curve"].append(res[0] if res else 0)

            cursor.execute("SELECT COUNT(*) FROM sito_lineare")
            result["sito_lineare"].append(cursor.fetchone()[0])
            res = cursor.execute('SELECT seq FROM sqlite_sequence WHERE name="sito_lineare"').fetchone()
            result["sito_lineare"].append(res[0] if res else 0)

            cursor.execute("SELECT COUNT(*) FROM indagini_lineari")
            result["indagini_lineari"].append(cursor.fetchone()[0])
            res = cursor.execute('SELECT seq FROM sqlite_sequence WHERE name="indagini_lineari"').fetchone()
            result["indagini_lineari"].append(res[0] if res else 0)

            cursor.execute("SELECT COUNT(*) FROM parametri_lineari")
            result["parametri_lineari"].append(cursor.fetchone()[0])
            res = cursor.execute('SELECT seq FROM sqlite_sequence WHERE name="parametri_lineari"').fetchone()
            result["parametri_lineari"].append(res[0] if res else 0)

            cursor.close()
        return result

    def reset_indagini_sequences(self):
        with self.db_connection as conn:
            cursor = conn.cursor()
            cursor.execute('UPDATE sqlite_sequence SET seq = 0 WHERE name="sito_puntuale"')
            cursor.execute('UPDATE sqlite_sequence SET seq = 0 WHERE name="indagini_puntuali"')
            cursor.execute('UPDATE sqlite_sequence SET seq = 0 WHERE name="parametri_puntuali"')
            cursor.execute('UPDATE sqlite_sequence SET seq = 0 WHERE name="curve"')
            cursor.execute('UPDATE sqlite_sequence SET seq = 0 WHERE name="sito_lineare"')
            cursor.execute('UPDATE sqlite_sequence SET seq = 0 WHERE name="indagini_lineari"')
            cursor.execute('UPDATE sqlite_sequence SET seq = 0 WHERE name="parametri_lineari"')
            conn.commit()
            cursor.close()

    def backup_project(self, out_dir=None):
        if not out_dir:
            out_dir = self.project_path.parent

        project_folder_name = Path(self.project_path).name
        backup_dir_name = f"{project_folder_name}_backup_v{self.project_version}_{datetime.datetime.now().strftime('%Y_%m_%d_%H_%M')}"
        backup_path = out_dir / backup_dir_name

        self.log(f"Backing up project in {backup_path}...")
        shutil.copytree(self.project_path, backup_path)

        return backup_path

    def backup_database(self, out_dir=None):
        if not out_dir:
            out_dir = self.project_path / "db"

        db_backup_path = (
            out_dir
            / f"indagini_backup_v{self.project_version}_{datetime.datetime.now().strftime('%Y_%m_%d_%H_%M')}.sqlite"
        )

        self.log(f"Backing up database in {db_backup_path}...")
        shutil.copy(self.db_path, db_backup_path)

        return db_backup_path

    def backup_qgis_project(self) -> Path:
        project_file_name = f"{self.current_project.baseName()}_backup_v{self.project_version}_{datetime.datetime.now().strftime('%Y_%m_%d-%H_%M')}.qgz"
        project_backup_path = self.project_path / project_file_name

        self.log(f"Backing up QGIS project to {project_backup_path}...")
        shutil.copy(self.current_project.absoluteFilePath(), project_backup_path)

        return project_backup_path

    # TODO: function to check, copy and fix all file attachments
    # indagini puntuali (doc_ind, tab_curve), indagini lineari (doc_ind), stab + instab lv.3 (spettri)
    # when inserting data, the attachments have a path relative to the project folder:
    # the function should (for every indagine):
    # - check if the file exists and copy it in the project folder
    # - update the attachment path in the database

    @staticmethod
    def extract_project_template(dir_out):
        project_template_path = DIR_PLUGIN_ROOT / "data" / "progetto_MS.zip"
        with zipfile.ZipFile(str(project_template_path), "r") as zip_ref:
            zip_ref.extractall(dir_out)

    @staticmethod
    def extract_database_template(dir_out):
        database_template_path = DIR_PLUGIN_ROOT / "data" / "indagini.sqlite.zip"
        with zipfile.ZipFile(str(database_template_path), "r") as zip_ref:
            zip_ref.extractall(dir_out)

    @staticmethod
    def sanitize_comune_name(comune_name):
        return comune_name.split(" (")[0].replace(" ", "_").replace("'", "_")

    def tr(self, message: str) -> str:
        return QCoreApplication.translate(self.__class__.__name__, message)
