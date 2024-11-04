from qgis.PyQt.QtCore import QVariant

SUGGESTED_QGIS_VERSION = "3.26"

NO_OVERLAPS_LAYER_GROUPS = [
    ["Zone instabili liv 1", "Zone stabili liv 1"],
    ["Zone instabili liv 2", "Zone stabili liv 2"],
    ["Zone instabili liv 3", "Zone stabili liv 3"],
    ["Zone instabili liv 2-3", "Zone stabili liv 2-3"],
]

""" 
MzS Tools QGIS layer / standard MS shapefile mapping, used in import/export functions.

key: layer name
value: list of 3 elements
    1. standard project folder containing the corresponding shapefile
    2. shapefile name
    3. shapefile id field
"""
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
    # "Zone instabili liv 2": ["MS23", "Instab", "ID_i"],
    # "Zone stabili liv 2": ["MS23", "Stab", "ID_z"],
    # "Isobate liv 2": ["MS23", "Isosub", "ID_isosub"],
    # "Zone instabili liv 3": ["MS23", "Instab", "ID_i"],
    # "Zone stabili liv 3": ["MS23", "Stab", "ID_z"],
    # "Isobate liv 3": ["MS23", "Isosub", "ID_isosub"],
    "Zone instabili liv 2-3": ["MS23", "Instab", "ID_i"],
    "Zone stabili liv 2-3": ["MS23", "Stab", "ID_z"],
    "Isobate liv 2-3": ["MS23", "Isosub", "ID_isosub"],
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
    "Isobate liv 2-3",
    "Zone stabili liv 2-3",
    "Zone instabili liv 2-3",
    # "Isobate liv 2",
    # "Zone stabili liv 2",
    # "Zone instabili liv 2",
    # "Isobate liv 3",
    # "Zone stabili liv 3",
    # "Zone instabili liv 3",
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
    "Elementi lineari": "elineari",
    "Elementi puntuali": "epuntuali",
    "Forme": "forme",
    "Elementi geologici e idrogeologici puntuali": "geoidr",
    "Unita' geologico-tecniche": "geotec",
    "Instabilita' di versante": "instab_geotec",
    "Zone instabili liv 1": "instab_l1",
    "Zone stabili liv 1": "stab_l1",
    "Isobate liv 1": "isosub_l1",
    "Zone instabili liv 2-3": "instab_l23",
    "Zone stabili liv 2-3": "stab_l23",
    "Isobate liv 2-3": "isosub_l23",
    # "Zone instabili liv 2": "instab_l2",
    # "Zone stabili liv 2": "stab_l2",
    # "Isobate liv 2": "isosub_l2",
    # "Zone instabili liv 3": "instab_l3",
    # "Zone stabili liv 3": "stab_l3",
    # "Isobate liv 3": "isosub_l3",
}

SITO_PUNTUALE_INS_TRIG_QUERIES = """
    UPDATE sito_puntuale 
    SET ubicazione_com = (
        SELECT CASE WHEN EXISTS (SELECT 1 FROM comune_progetto) 
            THEN ( 
                SELECT "cod_com " 
                FROM comune_progetto
                )
            ELSE (
                SELECT comuni.cod_com 
                FROM sito_puntuale, comuni 
                WHERE pkuid = sito_puntuale.pkuid AND
                intersects(sito_puntuale.geom, comuni.Geometry)
                )
        END
    );

    UPDATE sito_puntuale 
    SET ubicazione_prov = (
        SELECT CASE WHEN EXISTS (SELECT 1 FROM comune_progetto) 
            THEN ( 
                SELECT cod_prov 
                FROM comune_progetto	
                )
            ELSE ( 
                SELECT comuni.cod_prov 
                FROM sito_puntuale, comuni 
                WHERE pkuid = sito_puntuale.pkuid AND 
                intersects(sito_puntuale.geom, comuni.Geometry)
                )
        END
    );
    
    UPDATE sito_puntuale 
    SET id_spu = ubicazione_prov || ubicazione_com || 'P' || pkuid; 

    UPDATE sito_puntuale 
    SET coord_x = ( 
        SELECT round(X(geom)) 
        FROM sito_puntuale 
        WHERE pkuid = sito_puntuale.pkuid 
    );
    
    UPDATE sito_puntuale 
    SET coord_y = ( 
        SELECT round(Y(geom)) 
        FROM sito_puntuale 
        WHERE pkuid = sito_puntuale.pkuid
    ); 
"""

SITO_LINEARE_INS_TRIG_QUERIES = """
    UPDATE sito_lineare 
    SET ubicazione_com = (
        SELECT CASE WHEN EXISTS (SELECT 1 FROM comune_progetto) 
            THEN ( 
                SELECT "cod_com " 
                FROM comune_progetto
                )
            ELSE (
                SELECT comuni.cod_com 
                FROM sito_lineare, comuni 
                WHERE pkuid = sito_lineare.pkuid AND
                intersects(sito_lineare.geom, comuni.Geometry)
                )
        END
        );

    UPDATE sito_lineare 
    SET ubicazione_prov = (
        SELECT CASE WHEN EXISTS (SELECT 1 FROM comune_progetto) 
            THEN ( 
                SELECT cod_prov 
                FROM comune_progetto	
                )
            ELSE ( 
                SELECT comuni.cod_prov 
                FROM sito_lineare, comuni 
                WHERE pkuid = sito_lineare.pkuid AND
                intersects(sito_lineare.geom, comuni.Geometry)
                )
        END
        );

    UPDATE sito_lineare 
    SET id_sln = ubicazione_prov || ubicazione_com || 'L' || pkuid; 

    UPDATE sito_lineare 
    SET acoord_x = ( 
    SELECT round(X(StartPoint(geom))) 
    FROM sito_lineare 
    WHERE pkuid = sito_lineare.pkuid
    );

    UPDATE sito_lineare 
    SET acoord_y = ( 
    SELECT round(Y(StartPoint(geom))) 
    FROM sito_lineare 
    WHERE pkuid = sito_lineare.pkuid 
    );
    
    UPDATE sito_lineare 
    SET bcoord_x = ( 
    SELECT round(X(EndPoint(geom))) 
    FROM sito_lineare 
    WHERE pkuid = sito_lineare.pkuid
    ); 

    UPDATE sito_lineare 
    SET bcoord_y = ( 
    SELECT round(Y(EndPoint(geom))) 
    FROM sito_lineare 
    WHERE pkuid = sito_lineare.pkuid
    ); 
"""
