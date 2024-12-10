-- SELECT load_extension('mod_spatialite');

-- upgrade db to spatialite 5
SELECT CreateMissingSystemTables();;
SELECT UpgradeGeometryTriggers(1);;

-- create missing indexes
SELECT CreateSpatialIndex('instab_l23', 'geom');;
SELECT CreateSpatialIndex('stab_l23', 'geom');;
SELECT CreateSpatialIndex('isosub_l23', 'geom');;

-- cleanups
DROP TABLE IF EXISTS idx_comuni_2022_g_33_GEOMETRY;;
SELECT DropTable(NULL, "instab_l2");;
SELECT DropTable(NULL, "instab_l3");;
SELECT DropTable(NULL, "stab_l2");;
SELECT DropTable(NULL, "stab_l3");;
SELECT DropTable(NULL, "isosub_l2");;
SELECT DropTable(NULL, "isosub_l3");;


-- elineari triggers
DROP TRIGGER IF EXISTS ins_data_elineari;;
DROP TRIGGER IF EXISTS upd_data_elineari;;

CREATE TRIGGER ins_data_elineari 
AFTER INSERT ON elineari 
FOR EACH ROW 
BEGIN 
UPDATE elineari 
SET ID_el = pkuid + 40000
WHERE pkuid = NEW.pkuid;
END;;

CREATE TRIGGER upd_data_elineari 
AFTER UPDATE ON elineari 
FOR EACH ROW 
BEGIN 
UPDATE elineari 
SET ID_el = pkuid + 40000
WHERE pkuid = NEW.pkuid; 
END;;

-- epuntuali triggers
DROP TRIGGER IF EXISTS ins_data_epuntuali;;
DROP TRIGGER IF EXISTS upd_data_epuntuali;;

CREATE TRIGGER ins_data_epuntuali 
AFTER INSERT ON epuntuali 
FOR EACH ROW 
BEGIN 
UPDATE epuntuali 
SET ID_ep = pkuid + 40000
WHERE pkuid = NEW.pkuid; 
END;;

CREATE TRIGGER upd_data_epuntuali 
AFTER UPDATE ON epuntuali 
FOR EACH ROW 
BEGIN 
UPDATE epuntuali 
SET ID_ep = pkuid + 40000
WHERE pkuid = NEW.pkuid; 
END;;

-- forme triggers
DROP TRIGGER IF EXISTS ins_data_forme;;
DROP TRIGGER IF EXISTS upd_data_forme;;

CREATE TRIGGER ins_data_forme 
AFTER INSERT ON forme 
FOR EACH ROW 
BEGIN 
UPDATE forme 
SET ID_f = pkuid + 40000
WHERE pkuid = NEW.pkuid; 
END;;

CREATE TRIGGER upd_data_forme 
AFTER UPDATE ON forme 
FOR EACH ROW 
BEGIN 
UPDATE forme 
SET ID_f = pkuid + 40000
WHERE pkuid = NEW.pkuid; 
END;;

-- geoidr triggers
DROP TRIGGER IF EXISTS ins_data_geoidr;;
DROP TRIGGER IF EXISTS upd_data_geoidr;;

CREATE TRIGGER ins_data_geoidr 
AFTER INSERT ON geoidr 
FOR EACH ROW 
BEGIN 
UPDATE geoidr 
SET ID_gi = pkuid + 40000
WHERE pkuid = NEW.pkuid; 
END;;

CREATE TRIGGER upd_data_geoidr 
AFTER UPDATE ON geoidr 
FOR EACH ROW 
BEGIN 
UPDATE geoidr 
SET ID_gi = pkuid + 40000
WHERE pkuid = NEW.pkuid; 
END;;

-- instab_geotec triggers
DROP TRIGGER IF EXISTS ins_data_instab_geotec;;
DROP TRIGGER IF EXISTS upd_data_instab_geotec;;

CREATE TRIGGER ins_data_instab_geotec 
AFTER INSERT ON instab_geotec 
FOR EACH ROW 
BEGIN 
UPDATE instab_geotec 
SET ID_i = pkuid + 40000
WHERE pkuid = NEW.pkuid;
END;;

CREATE TRIGGER upd_data_instab_geotec 
AFTER UPDATE ON instab_geotec 
FOR EACH ROW 
BEGIN 
UPDATE instab_geotec 
SET ID_i = pkuid + 40000
WHERE pkuid = NEW.pkuid; 
END;;


-- sito_lineare triggers
DROP TRIGGER IF EXISTS ins_data_s_line;;
DROP TRIGGER IF EXISTS upd_data_s_line;;

CREATE TRIGGER ins_data_s_line 
AFTER INSERT ON sito_lineare 
FOR EACH ROW 
BEGIN 

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
			WHERE sito_lineare.pkuid = NEW.pkuid AND 
			intersects(sito_lineare.geom, comuni.Geometry)
			)
    END
	) 
WHERE pkuid = NEW.pkuid;

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
			WHERE sito_lineare.pkuid = NEW.pkuid AND 
			intersects(sito_lineare.geom, comuni.Geometry)
			)
    END
	) 
WHERE pkuid = NEW.pkuid;

UPDATE sito_lineare 
SET id_sln = ubicazione_prov || ubicazione_com || 'L' || pkuid
WHERE pkuid = NEW.pkuid; 

UPDATE sito_lineare 
SET acoord_x = ( 
    SELECT round(X(StartPoint(geom))) 
    FROM sito_lineare 
    WHERE pkuid = NEW.pkuid
) 
WHERE pkuid = NEW.pkuid; 

UPDATE sito_lineare 
SET acoord_y = ( 
    SELECT round(Y(StartPoint(geom))) 
    FROM sito_lineare 
    WHERE pkuid = NEW.pkuid
) 
WHERE pkuid = NEW.pkuid;
 
UPDATE sito_lineare 
SET bcoord_x = ( 
    SELECT round(X(EndPoint(geom))) 
    FROM sito_lineare 
    WHERE pkuid = NEW.pkuid
) 
WHERE pkuid = NEW.pkuid; 

UPDATE sito_lineare 
SET bcoord_y = ( 
    SELECT round(Y(EndPoint(geom))) 
    FROM sito_lineare 
    WHERE pkuid = NEW.pkuid
) 
WHERE pkuid = NEW.pkuid; 

END;;

CREATE TRIGGER upd_data_s_line 
AFTER UPDATE ON sito_lineare 
FOR EACH ROW 
BEGIN 

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
			WHERE sito_lineare.pkuid = NEW.pkuid AND 
			intersects(sito_lineare.geom, comuni.Geometry)
			)
    END
	) 
WHERE pkuid = NEW.pkuid;

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
			WHERE sito_lineare.pkuid = NEW.pkuid AND 
			intersects(sito_lineare.geom, comuni.Geometry)
			)
    END
	) 
WHERE pkuid = NEW.pkuid;

UPDATE sito_lineare 
SET id_sln = ubicazione_prov || ubicazione_com || 'L' || pkuid
WHERE pkuid = NEW.pkuid; 

UPDATE sito_lineare 
SET acoord_x = ( 
    SELECT round(X(StartPoint(geom))) 
    FROM sito_lineare 
    WHERE pkuid = NEW.pkuid
) 
WHERE pkuid = NEW.pkuid; 

UPDATE sito_lineare 
SET acoord_y = ( 
    SELECT round(Y(StartPoint(geom))) 
    FROM sito_lineare 
    WHERE pkuid = NEW.pkuid
) 
WHERE pkuid = NEW.pkuid;
 
UPDATE sito_lineare 
SET bcoord_x = ( 
    SELECT round(X(EndPoint(geom))) 
    FROM sito_lineare 
    WHERE pkuid = NEW.pkuid 
) 
WHERE pkuid = NEW.pkuid; 

UPDATE sito_lineare 
SET bcoord_y = ( 
    SELECT round(Y(EndPoint(geom))) 
    FROM sito_lineare 
    WHERE pkuid = NEW.pkuid 
) 
WHERE pkuid = NEW.pkuid; 

END;;

-- sito_puntuale triggers
-- ----------------------------------------
-- DROP TRIGGER IF EXISTS del_data_s_point;;
-- ----------------------------------------
DROP TRIGGER IF EXISTS ins_data_s_point;;
DROP TRIGGER IF EXISTS upd_data_s_point;;

CREATE TRIGGER ins_data_s_point 
AFTER INSERT ON sito_puntuale 
FOR EACH ROW 
BEGIN 

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
			WHERE sito_puntuale.pkuid = NEW.pkuid AND 
			intersects(sito_puntuale.geom, comuni.Geometry)
			)
    END
	) 
WHERE pkuid = NEW.pkuid;

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
			WHERE sito_puntuale.pkuid = NEW.pkuid AND 
			intersects(sito_puntuale.geom, comuni.Geometry)
			)
    END
	) 
WHERE pkuid = NEW.pkuid;
 
UPDATE sito_puntuale 
SET id_spu = ubicazione_prov || ubicazione_com || 'P' || pkuid
WHERE pkuid = NEW.pkuid; 

UPDATE sito_puntuale 
SET coord_x = ( 
	SELECT round(X(geom)) 
	FROM sito_puntuale 
	WHERE pkuid = NEW.pkuid 
	) 
WHERE pkuid = NEW.pkuid;
 
UPDATE sito_puntuale 
SET coord_y = ( 
	SELECT round(Y(geom)) 
	FROM sito_puntuale 
	WHERE pkuid = NEW.pkuid 
	) 
WHERE pkuid = NEW.pkuid; 
END;;

CREATE TRIGGER upd_data_s_point 
AFTER UPDATE ON sito_puntuale 
FOR EACH ROW 
BEGIN 

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
			WHERE sito_puntuale.pkuid = NEW.pkuid AND 
			intersects(sito_puntuale.geom, comuni.Geometry)
			)
    END
	) 
WHERE pkuid = NEW.pkuid;

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
			WHERE sito_puntuale.pkuid = NEW.pkuid AND 
			intersects(sito_puntuale.geom, comuni.Geometry)
			)
    END
	) 
WHERE pkuid = NEW.pkuid;
 
UPDATE sito_puntuale 
SET id_spu = ubicazione_prov || ubicazione_com || 'P' || pkuid
WHERE pkuid = NEW.pkuid; 

UPDATE sito_puntuale 
SET coord_x = ( 
	SELECT round(X(geom)) 
	FROM sito_puntuale 
	WHERE pkuid = NEW.pkuid 
	) 
WHERE pkuid = NEW.pkuid;
 
UPDATE sito_puntuale 
SET coord_y = ( 
	SELECT round(Y(geom)) 
	FROM sito_puntuale 
	WHERE pkuid = NEW.pkuid 
	) 
WHERE pkuid = NEW.pkuid; 
END;;


-- indagini_lineari triggers
-- ----------------------------------------
-- DROP TRIGGER IF EXISTS del_data_i_line;;
-- ----------------------------------------
DROP TRIGGER IF EXISTS ins_data_i_line;;
DROP TRIGGER IF EXISTS upd_data_i_line;;

CREATE TRIGGER ins_data_i_line 
AFTER INSERT ON indagini_lineari 
FOR EACH ROW 
BEGIN 
UPDATE indagini_lineari 
SET "id_indln" = "id_sln" || "tipo_ind" || "pkuid"
WHERE pkuid = NEW.pkuid;
END;;

CREATE TRIGGER upd_data_i_line 
AFTER UPDATE ON indagini_lineari 
FOR EACH ROW 
BEGIN 
UPDATE indagini_lineari 
SET "id_indln" = "id_sln" || "tipo_ind" || "pkuid"
WHERE pkuid = NEW.pkuid;
END;;

-- indagini_puntuali triggers
-- ----------------------------------------
-- DROP TRIGGER IF EXISTS del_data_i_point;;
-- ----------------------------------------
DROP TRIGGER IF EXISTS ins_data_i_point;;
DROP TRIGGER IF EXISTS upd_data_i_point;;

CREATE TRIGGER ins_data_i_point 
AFTER INSERT ON indagini_puntuali 
FOR EACH ROW 
BEGIN 
UPDATE indagini_puntuali 
SET "id_indpu" = "id_spu" || "tipo_ind" || "pkuid",
    "spessore" = "prof_bot" - "prof_top"
WHERE pkuid = NEW.pkuid; 
END;;

CREATE TRIGGER upd_data_i_point 
AFTER UPDATE ON indagini_puntuali 
FOR EACH ROW 
BEGIN 
UPDATE indagini_puntuali 
SET "id_indpu" = "id_spu" || "tipo_ind" || "pkuid", 
    "spessore" = "prof_bot" - "prof_top"
WHERE pkuid = NEW.pkuid; 
END;;


-- parametri_lineari triggers
DROP TRIGGER IF EXISTS ins_data_p_line;;
DROP TRIGGER IF EXISTS upd_data_p_line;;

CREATE TRIGGER ins_data_p_line 
AFTER INSERT ON parametri_lineari 
FOR EACH ROW 
BEGIN 
UPDATE parametri_lineari 
SET "id_parln" = "id_indln" || "tipo_parln" || "pkuid",
    "spessore" = "prof_bot" - "prof_top"
WHERE pkuid = NEW.pkuid; 
END;;

CREATE TRIGGER upd_data_p_line 
AFTER UPDATE ON parametri_lineari 
FOR EACH ROW 
BEGIN 
UPDATE parametri_lineari 
SET "id_parln" = "id_indln" || "tipo_parln" || "pkuid", 
    "spessore" = "prof_bot" - "prof_top"
WHERE pkuid = NEW.pkuid; 
END;;

-- parametri_puntuali triggers
-- ----------------------------------------
-- DROP TRIGGER IF EXISTS del_data_p_point;;
-- ----------------------------------------
DROP TRIGGER IF EXISTS ins_data_p_point;;
DROP TRIGGER IF EXISTS upd_data_p_point;;

CREATE TRIGGER ins_data_p_point 
AFTER INSERT ON parametri_puntuali 
FOR EACH ROW 
BEGIN 
UPDATE parametri_puntuali 
SET "id_parpu" = "id_indpu" || "tipo_parpu" || "pkuid",
    "spessore" = "prof_bot" - "prof_top"
WHERE pkuid = NEW.pkuid; 
END;;

CREATE TRIGGER upd_data_p_point 
AFTER UPDATE ON parametri_puntuali 
FOR EACH ROW 
BEGIN 
UPDATE parametri_puntuali 
SET "id_parpu" = "id_indpu" || "tipo_parpu" || "pkuid",
    "spessore" = "prof_bot" - "prof_top"
WHERE pkuid = NEW.pkuid; 
END;;




-- db maintenance
SELECT RecoverSpatialIndex();;
SELECT UpdateLayerStatistics();;
VACUUM;;