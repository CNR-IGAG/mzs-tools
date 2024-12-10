CREATE TABLE indice (
    "data_in"    TEXT,
	"regione"    TEXT,
	"cod_reg"    TEXT,
	"provincia"    TEXT,
	"cod_prov"    TEXT NOT NULL,
	"comune"    TEXT,
	"cod_com"    TEXT NOT NULL,
	"soggetto"    TEXT,
	"ufficio"    TEXT,
	"responsabile"    TEXT,
	"ID_MZS"    TEXT
);;

CREATE TRIGGER ins_data_indice 
AFTER INSERT ON indice 
FOR EACH ROW 
BEGIN 
UPDATE indice 
SET ID_MZS = cod_prov || cod_com;
END;;

CREATE TRIGGER upd_data_indice 
AFTER UPDATE ON indice 
FOR EACH ROW 
BEGIN 
UPDATE indice 
SET ID_MZS = cod_prov || cod_com;
END;;

CREATE TABLE hvsr (
    "pkuid"    INTEGER PRIMARY KEY AUTOINCREMENT,
    "id_indpu"      TEXT NOT NULL,
    "qualita"    	TEXT,
	"tipo"			TEXT,
    "f0"    DOUBLE
		CONSTRAINT f0_verify CHECK ("f0" BETWEEN 0.0 AND 10000.0),
    "a0"    DOUBLE
		CONSTRAINT a0_verify CHECK ("a0" BETWEEN 0.0 AND 10000.0),
    "f1"    DOUBLE
		CONSTRAINT f1_verify CHECK ("f1" BETWEEN 0.0 AND 10000.0),
    "a1" 	DOUBLE
		CONSTRAINT a1_verify CHECK ("a1" BETWEEN 0.0 AND 10000.0),
    "f2"    DOUBLE
		CONSTRAINT f2_verify CHECK ("f2" BETWEEN 0.0 AND 10000.0),
    "a2" 	DOUBLE
		CONSTRAINT a2_verify CHECK ("a2" BETWEEN 0.0 AND 10000.0),
    "f3"    DOUBLE
		CONSTRAINT f3_verify CHECK ("f3" BETWEEN 0.0 AND 10000.0),
    "a3" 	DOUBLE
		CONSTRAINT a3_verify CHECK ("a3" BETWEEN 0.0 AND 10000.0),
    CONSTRAINT fk_ind_pu FOREIGN KEY ("id_indpu") REFERENCES indagini_puntuali("id_indpu")
);;

CREATE VIEW "vw_hvsr" AS 
SELECT h.ROWID AS rowid, h.pkuid,
    h.id_indpu, h.qualita,
    h.tipo, h.f0, h.a0,
    h.f1, h.a1, h.f2,
    h.a2, h.f3, h.a3,
    i.id_spu, s.geom AS geom 
FROM indagini_puntuali AS i 
JOIN hvsr AS h ON h.id_indpu = i.id_indpu 
JOIN sito_puntuale AS s ON i.id_spu = s.id_spu 
where i.tipo_ind = 'HVSR';;

INSERT INTO geometry_columns
	(f_table_name,f_geometry_column,geometry_type,coord_dimension,srid,spatial_index_enabled)
	VALUES ('vw_hvsr','geom', 1, 2, 32633, 0);;

INSERT INTO views_geometry_columns
    (view_name, view_geometry, view_rowid, f_table_name, f_geometry_column, read_only)
	VALUES ('vw_hvsr', 'geom', 'rowid', 'sito_puntuale', 'geom', 1);;

CREATE TABLE tbl_qualita (
    cod TEXT,
    descrizione TEXT
);;

INSERT INTO tbl_qualita 
	(cod, descrizione)
	VALUES ('A','H/V affidabile e interpretabile'),('B','H/V sospetta (da interpretare)'),('C','H/V scadente e di difficile interpretazione');;

CREATE TABLE tbl_tipo_hvsr (
    cod TEXT,
    descrizione TEXT
);;

INSERT INTO tbl_tipo_hvsr 
	(cod, descrizione)
	VALUES ('Tipo 1','Almeno un picco chiaro (possibile risonanza)'),('Tipo 2','Non presenta picchi chiari (assenza di risonanza)');;

CREATE VIEW vw_qualita as select cod, cod || ' - ' || descrizione as descrizione from tbl_qualita;;

CREATE VIEW vw_tipo_hvsr as select cod, cod || ' - ' || descrizione as descrizione from tbl_tipo_hvsr;;

INSERT INTO tbl_tipo_gt 
	(pkuid,cod, descrizione)
	VALUES (33,'CVT','Cavita''');;
	
INSERT INTO tbl_classe_ind_p
	(pkuid,cod, descrizione)
	VALUES (7,'EL','Elaborazioni');;
	
INSERT INTO tbl_ind_param_p
	(pkuid,cod_ind, id_ind, cod_param, id_param)
	VALUES (146,'SMS',57,'L',36);;
	
INSERT INTO tbl_tipo_ind_p
	(pkuid,cod_classe,cod,descrizione)
	VALUES (57,'EL','SMS','Stratigrafia zona MS (teorica)');;

DROP TRIGGER ins_data_s_line;;

DROP TRIGGER upd_data_s_line;;

DROP TRIGGER ins_data_s_point;;

DROP TRIGGER upd_data_s_point;;
	
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
SET id_sln = ubicazione_prov || ubicazione_com || 'L' || pkuid;
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
SET id_sln = ubicazione_prov || ubicazione_com || 'L' || pkuid; 
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
SET id_spu = ubicazione_prov || ubicazione_com || 'P' || pkuid; 
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
SET id_spu = ubicazione_prov || ubicazione_com || 'P' || pkuid; 
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

SELECT UpdateLayerStatistics('comune_progetto', 'geom');;
