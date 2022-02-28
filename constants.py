from qgis.PyQt.QtCore import QVariant

POSIZIONE = {
    "Comune del progetto": ["BasiDati", "Comune", "id_com"],
    "Elementi lineari": ["GeoTec", "Elineari", "ID_el"],
    "Elementi puntuali": ["GeoTec", "Epuntuali", "ID_ep"],
    "Forme": ["GeoTec", "Forme", "ID_f"],
    "Elementi geologici e idrogeologici puntuali": ["GeoTec", "Geoidr", "ID_gi"],
    "Unita' geologico-tecniche": ["GeoTec", "Geotec", "ID_gt"],
    "Instabilita' di versante": ["GeoTec", "Instab_geotec", "ID_i"],
    "Siti lineari": ["Indagini", "Ind_ln", "ID_SLN"],
    "Siti puntuali": ["Indagini", "Ind_pu", "ID_SPU"],
    "Zone instabili liv 1": ["MS1", "Instab", "ID_i"],
    "Zone stabili liv 1": ["MS1", "Stab", "ID_z"],
    "Isobate liv 1": ["MS1", "Isosub", "ID_isosub"],
    "Zone instabili liv 2": ["MS23", "Instab", "ID_i"],
    "Zone stabili liv 2": ["MS23", "Stab", "ID_z"],
    "Isobate liv 2": ["MS23", "Isosub", "ID_isosub"],
    "Zone instabili liv 3": ["MS23", "Instab", "ID_i"],
    "Zone stabili liv 3": ["MS23", "Stab", "ID_z"],
    "Isobate liv 3": ["MS23", "Isosub", "ID_isosub"],
}

LISTA_LAYER = [
    "Siti puntuali",
    "Indagini puntuali",
    "Parametri puntuali",
    "Curve di riferimento",
    "Siti lineari",
    "Indagini lineari",
    "Parametri lineari",
    "Elementi geologici e idrogeologici puntuali",
    "Elementi puntuali",
    "Elementi lineari",
    "Forme",
    "Unita' geologico-tecniche",
    "Instabilita' di versante",
    "Isobate liv 1",
    "Zone stabili liv 1",
    "Zone instabili liv 1",
    "Isobate liv 2",
    "Zone stabili liv 2",
    "Zone instabili liv 2",
    "Isobate liv 3",
    "Zone stabili liv 3",
    "Zone instabili liv 3",
    "Comune del progetto",
    "Limiti comunali",
]

DIZIO_CAMPI_L = {
    "pkuid": [QVariant.LongLong, '"csv_sln_pkey_sln"'],
    "ub_prov": [QVariant.String, '"csv_sln_ubicazione_prov"'],
    "ub_com": [QVariant.String, '"csv_sln_ubicazione_com"'],
    "aquota": [QVariant.Double, '"csv_sln_Aquota"'],
    "bquota": [QVariant.Double, '"csv_sln_Bquota"'],
    "data_sito": [QVariant.String, '"csv_sln_data_sito"'],
    "note_sito": [QVariant.String, '"csv_sln_note_sito"'],
    "mod_identc": [QVariant.String, '"csv_sln_mod_identcoord"'],
    "desc_modco": [QVariant.String, '"csv_sln_desc_modcoord"'],
}

DIZIO_CAMPI_P = {
    "pkuid": [QVariant.LongLong, '"csv_spu_pkey_spu"'],
    "ub_prov": [QVariant.String, '"csv_spu_ubicazione_prov"'],
    "ub_com": [QVariant.String, '"csv_spu_ubicazione_com"'],
    "indirizzo": [QVariant.String, '"csv_spu_indirizzo"'],
    "quota_slm": [QVariant.LongLong, '"csv_spu_quota_slm"'],
    "modo_quota": [QVariant.String, '"csv_spu_modo_quota"'],
    "data_sito": [QVariant.String, '"csv_spu_data_sito"'],
    "note_sito": [QVariant.String, '"csv_spu_note_sito"'],
    "mod_identc": [QVariant.String, '"csv_spu_mod_identcoord"'],
    "desc_modco": [QVariant.String, '"csv_spu_desc_modcoord"'],
}

LISTA_TAB = [
    "Sito_Puntuale",
    "Indagini_Puntuali",
    "Parametri_Puntuali",
    "Curve",
    "Sito_Lineare",
    "Indagini_Lineari",
    "Parametri_Lineari",
]

LAYER_DB_TAB = {
    "Siti puntuali": "sito_puntuale",
    "Indagini puntuali": "indagini_puntuali",
    "Parametri puntuali": "parametri_puntuali",
    "Curve di riferimento": "curve",
    "Siti lineari": "sito_lineare",
    "Indagini lineari": "indagini_lineari",
    "Parametri lineari": "parametri_lineari",
}
