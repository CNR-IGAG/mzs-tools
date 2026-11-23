-- Trigger set for multi-municipality (merged) projects.
-- Applied only to merged databases: survey IDs are preserved from the source projects,
-- so UPDATE triggers must never rebuild them, and new sites get the municipality
-- of the nearest comune_progetto geometry.

DROP TRIGGER IF EXISTS ins_data_s_point;
CREATE TRIGGER ins_data_s_point 
AFTER INSERT ON sito_puntuale 
FOR EACH ROW 
BEGIN 

UPDATE sito_puntuale 
SET ubicazione_com = (
	SELECT cp."cod_com " 
	FROM comune_progetto cp 
	ORDER BY Distance(cp.geom, NEW.geom), cp.pkuid 
	LIMIT 1
	),
	ubicazione_prov = (
	SELECT cp.cod_prov 
	FROM comune_progetto cp 
	ORDER BY Distance(cp.geom, NEW.geom), cp.pkuid 
	LIMIT 1
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
END;

DROP TRIGGER IF EXISTS ins_data_s_line;
CREATE TRIGGER ins_data_s_line 
AFTER INSERT ON sito_lineare 
FOR EACH ROW 
BEGIN 

UPDATE sito_lineare 
SET ubicazione_com = (
	SELECT cp."cod_com " 
	FROM comune_progetto cp 
	ORDER BY Distance(cp.geom, NEW.geom), cp.pkuid 
	LIMIT 1
	),
	ubicazione_prov = (
	SELECT cp.cod_prov 
	FROM comune_progetto cp 
	ORDER BY Distance(cp.geom, NEW.geom), cp.pkuid 
	LIMIT 1
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

END;

DROP TRIGGER IF EXISTS upd_data_s_point;
CREATE TRIGGER upd_data_s_point 
AFTER UPDATE ON sito_puntuale 
FOR EACH ROW 
BEGIN 

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
END;

DROP TRIGGER IF EXISTS upd_data_s_line;
CREATE TRIGGER upd_data_s_line 
AFTER UPDATE ON sito_lineare 
FOR EACH ROW 
BEGIN 

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

END;

DROP TRIGGER IF EXISTS upd_data_i_point;
CREATE TRIGGER upd_data_i_point 
AFTER UPDATE ON indagini_puntuali 
FOR EACH ROW 
BEGIN 
UPDATE indagini_puntuali 
SET "spessore" = "prof_bot" - "prof_top"
WHERE pkuid = NEW.pkuid; 
END;

DROP TRIGGER IF EXISTS upd_data_i_line;

DROP TRIGGER IF EXISTS upd_data_p_point;
CREATE TRIGGER upd_data_p_point 
AFTER UPDATE ON parametri_puntuali 
FOR EACH ROW 
BEGIN 
UPDATE parametri_puntuali 
SET "spessore" = "prof_bot" - "prof_top",
	"valore" = CASE 
				WHEN "valore_appoggio" IS NOT NULL
					THEN "valore_appoggio"
					ELSE "valore"
			    END,
    "valore_appoggio" = CASE
	                     WHEN "valore"/1 > 0
	                      THEN NULL
	                     ELSE "valore_appoggio"
	                    END
WHERE pkuid = NEW.pkuid; 
END;

DROP TRIGGER IF EXISTS upd_data_p_line;
CREATE TRIGGER upd_data_p_line 
AFTER UPDATE ON parametri_lineari 
FOR EACH ROW 
BEGIN 
UPDATE parametri_lineari 
SET "spessore" = "prof_bot" - "prof_top"
WHERE pkuid = NEW.pkuid; 
END;
