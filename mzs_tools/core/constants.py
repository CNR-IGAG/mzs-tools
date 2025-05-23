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

PRINT_LAYOUT_MODELS = {
    "01 - CdI carta delle indagini": "carta_delle_indagini.qpt",
    "02 - CGT carta geologico tecnica": "carta_geologico_tecnica.qpt",
    "03 - MOPS carta di microzonazione sismica liv1": "carta_delle_mops.qpt",
    "04 - MS23 carta di microzonazione sismica liv2-3 FA 01-05s": "carta_ms_fa_01_05.qpt",
    "05 - MS23 carta di microzonazione sismica liv2-3 FA 04-08s": "carta_ms_fa_04_08.qpt",
    "06 - MS23 carta di microzonazione sismica liv2-3 FA 07-11s": "carta_ms_fa_07_11.qpt",
    "07 - Carta delle frequenze naturali dei terreni f0": "carta_frequenze_f0.qpt",
    "08 - Carta delle frequenze naturali dei terreni fr": "carta_frequenze_fr.qpt",
}

NO_OVERLAPS_LAYER_GROUPS = [
    ["instab_l1", "stab_l1"],
    ["instab_l23", "stab_l23"],
]
