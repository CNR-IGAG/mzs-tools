CREATE TABLE metadati (    
	"id_metadato"    TEXT PRIMARY KEY,
    "liv_gerarchico"    TEXT,
    "resp_metadato_nome"    TEXT,
    "resp_metadato_email"    TEXT,
    "resp_metadato_sito"    TEXT,
    "data_metadato"    TEXT,
    "srs_dati"    TEXT,
    "proprieta_dato_nome"    TEXT,
    "proprieta_dato_email"    TEXT,
    "proprieta_dato_sito"    TEXT,
    "data_dato"    TEXT,
    "ruolo"    TEXT,
    "desc_dato"    TEXT,
    "formato"    TEXT,
    "tipo_dato"    TEXT,
    "contatto_dato_nome"    TEXT,
    "contatto_dato_email"    TEXT,
    "contatto_dato_sito"    TEXT,
    "keywords"    TEXT,
    "keywords_inspire"    TEXT,
    "limitazione"    TEXT,
    "vincoli_accesso"    TEXT,
    "vincoli_fruibilita"    TEXT,
    "vincoli_sicurezza"    TEXT,
    "scala"    TEXT,
    "categoria_iso"    TEXT,
    "estensione_ovest"    TEXT,
    "estensione_est"    TEXT,
    "estensione_sud"    TEXT,
    "estensione_nord"    TEXT,
    "formato_dati"    TEXT,
    "distributore_dato_nome"    TEXT,
    "distributore_dato_telefono"    TEXT,
    "distributore_dato_email"    TEXT,
    "distributore_dato_sito"    TEXT,
    "url_accesso_dato"    TEXT,
    "funzione_accesso_dato"    TEXT,
    "precisione"    TEXT,
    "genealogia"    TEXT
);;

ALTER TABLE hvsr 
ADD fr DOUBLE;;

ALTER TABLE hvsr 
ADD ar DOUBLE;;

CREATE VIEW "vw_hvsr_fr" AS SELECT h.ROWID AS rowid, h.pkuid,
h.id_indpu, h.qualita,
h.tipo, h.f0, h.a0,
h.f1, h.a1, h.f2,
h.a2, h.f3, h.a3,
h.ar, h.fr,
i.id_spu, s.geom AS geom  
FROM indagini_puntuali AS i 
JOIN hvsr AS h ON h.id_indpu = i.id_indpu 
JOIN sito_puntuale AS s ON i.id_spu = s.id_spu 
where i.tipo_ind = 'HVSR';;

INSERT INTO geometry_columns
	(f_table_name,f_geometry_column,geometry_type,coord_dimension,srid,spatial_index_enabled)
	VALUES ('vw_hvsr_fr','geom', 1, 2, 32633, 0);;

INSERT INTO views_geometry_columns
    (view_name, view_geometry, view_rowid, f_table_name, f_geometry_column, read_only)
	VALUES ('vw_hvsr_fr', 'geom', 'rowid', 'sito_puntuale', 'geom', 1);;

CREATE TABLE parametri_puntuali_temp AS SELECT * FROM parametri_puntuali;;
CREATE TABLE indagini_puntuali_temp AS SELECT * FROM indagini_puntuali;;
CREATE TABLE parametri_lineari_temp AS SELECT * FROM parametri_lineari;;

DROP TABLE parametri_puntuali;;
DROP TABLE indagini_puntuali;;
DROP TABLE parametri_lineari;;

CREATE TABLE parametri_puntuali (
    "pkuid"    INTEGER PRIMARY KEY AUTOINCREMENT,
    "id_indpu"      TEXT NOT NULL,
    "tipo_parpu"    TEXT NOT NULL,
    "id_parpu"      TEXT UNIQUE NOT NULL,
    "prof_top"      DOUBLE
		CONSTRAINT prof_top_verify CHECK ("prof_top" BETWEEN 0.0 AND 10000.0),
    "prof_bot"      DOUBLE
		CONSTRAINT prof_bot_verify CHECK ("prof_bot" BETWEEN 0.0 AND 10000.0),
    "spessore"      DOUBLE
		CONSTRAINT spessore_verify CHECK ("spessore" BETWEEN 0.0 AND 10000.0),
    "quota_slm_top" DOUBLE
		CONSTRAINT quota_slm_top_verify CHECK ("quota_slm_top" BETWEEN -1000.0 AND 10000.0),
    "quota_slm_bot" DOUBLE
		CONSTRAINT quota_slm_bot_verify CHECK ("quota_slm_bot" BETWEEN -1000.0 AND 10000.0),
    "valore"        TEXT,
    "attend_mis"    TEXT,
    "tab_curve"     TEXT,
    "note_par"      TEXT,
    "data_par"      TEXT,
    CONSTRAINT fk_par_pu FOREIGN KEY ("id_indpu") REFERENCES indagini_puntuali("id_indpu")
);;

CREATE TRIGGER del_data_p_point after delete ON parametri_puntuali  
WHEN ((select count() from parametri_puntuali where "id_parpu" = OLD."id_parpu") = 0)
BEGIN 
DELETE FROM curve WHERE "id_parpu" = OLD."id_parpu" ;
END;;

CREATE TRIGGER ins_data_p_point 
AFTER INSERT ON parametri_puntuali 
FOR EACH ROW 
BEGIN 
UPDATE parametri_puntuali 
SET "id_parpu" = "id_indpu" || "tipo_parpu" || "pkuid"; 
UPDATE parametri_puntuali 
SET "spessore" = "prof_bot" - "prof_top"; 
END;;

CREATE TRIGGER upd_data_p_point 
AFTER UPDATE ON parametri_puntuali 
FOR EACH ROW 
BEGIN 
UPDATE parametri_puntuali 
SET "id_parpu" = "id_indpu" || "tipo_parpu" || "pkuid"; 
UPDATE parametri_puntuali 
SET "spessore" = "prof_bot" - "prof_top"; 
END;;

CREATE TABLE indagini_puntuali (
    "pkuid"    INTEGER PRIMARY KEY AUTOINCREMENT,
    "id_spu"        TEXT NOT NULL,
    "classe_ind"    TEXT NOT NULL,
    "tipo_ind"      TEXT NOT NULL,
    "id_indpu"      TEXT UNIQUE NOT NULL,
    "id_indpuex"    TEXT,
    "arch_ex"       TEXT,
    "note_ind"      TEXT,
    "prof_top"      DOUBLE
		CONSTRAINT prof_top_verify CHECK ("prof_top" BETWEEN 0.0 AND 10000.0),
    "prof_bot"      DOUBLE
		CONSTRAINT prof_bot_verify CHECK ("prof_bot" BETWEEN 0.0 AND 10000.0),
    "spessore"      DOUBLE
		CONSTRAINT spessore_verify CHECK ("spessore" BETWEEN 0.0 AND 10000.0),
    "quota_slm_top" DOUBLE
		CONSTRAINT quota_slm_top_verify CHECK ("quota_slm_top" BETWEEN -1000.0 AND 10000.0),
    "quota_slm_bot" DOUBLE
		CONSTRAINT quota_slm_bot_verify CHECK ("quota_slm_bot" BETWEEN -1000.0 AND 10000.0),
    "data_ind"      TEXT,
    "doc_pag"       INTEGER,
    "doc_ind"       TEXT,
    CONSTRAINT fk_ind_pu FOREIGN KEY ("id_spu") REFERENCES sito_puntuale("id_spu")
);;

CREATE TRIGGER del_data_i_point after delete ON indagini_puntuali  
WHEN ((select count() from indagini_puntuali where "id_indpu" = OLD."id_indpu") = 0)
BEGIN 
DELETE FROM parametri_puntuali WHERE "id_indpu" = OLD."id_indpu" ;
END;;

CREATE TRIGGER ins_data_i_point 
AFTER INSERT ON indagini_puntuali 
FOR EACH ROW 
BEGIN 
UPDATE indagini_puntuali 
SET "id_indpu" = "id_spu" || "tipo_ind" || "pkuid";
UPDATE indagini_puntuali 
SET "spessore" = "prof_bot" - "prof_top"; 
END;;

CREATE TRIGGER upd_data_i_point 
AFTER UPDATE ON indagini_puntuali 
FOR EACH ROW 
BEGIN 
UPDATE indagini_puntuali 
SET "id_indpu" = "id_spu" || "tipo_ind" || "pkuid";
UPDATE indagini_puntuali 
SET "spessore" = "prof_bot" - "prof_top"; 
END;;

CREATE TABLE parametri_lineari (
    "pkuid"    INTEGER PRIMARY KEY AUTOINCREMENT,
    "id_indln"      TEXT  NOT NULL,
    "tipo_parln"    TEXT  NOT NULL,
    "id_parln"      TEXT UNIQUE NOT NULL,
    "prof_top"      DOUBLE
		CONSTRAINT prof_top_verify CHECK ("prof_top" BETWEEN 0.0 AND 10000.0),
    "prof_bot"      DOUBLE
		CONSTRAINT prof_bot_verify CHECK ("prof_bot" BETWEEN 0.0 AND 10000.0),
    "spessore"      DOUBLE
		CONSTRAINT spessore_verify CHECK ("spessore" BETWEEN 0.0 AND 10000.0),
    "quota_slm_top" DOUBLE
		CONSTRAINT quota_slm_top_verify CHECK ("quota_slm_top" BETWEEN -1000.0 AND 10000.0),
    "quota_slm_bot" DOUBLE
		CONSTRAINT quota_slm_bot_verify CHECK ("quota_slm_bot" BETWEEN -1000.0 AND 10000.0),
    "valore"        DOUBLE
		CONSTRAINT valore_verify CHECK ("valore" BETWEEN 0.0 AND 10000.0),
    "attend_mis"    TEXT,
    "note_par"      TEXT,
    "data_par"      TEXT,
    CONSTRAINT fk_par_ln FOREIGN KEY ("id_indln") REFERENCES indagini_lineari("id_indln")
);;

CREATE TRIGGER ins_data_p_line 
AFTER INSERT ON parametri_lineari 
FOR EACH ROW 
BEGIN 
UPDATE parametri_lineari 
SET "id_parln" = "id_indln" || "tipo_parln" || "pkuid";
UPDATE parametri_lineari 
SET "spessore" = "prof_bot" - "prof_top";
END;;

CREATE TRIGGER upd_data_p_line 
AFTER UPDATE ON parametri_lineari 
FOR EACH ROW 
BEGIN 
UPDATE parametri_lineari 
SET "id_parln" = "id_indln" || "tipo_parln" || "pkuid"; 
UPDATE parametri_lineari 
SET "spessore" = "prof_bot" - "prof_top"; 
END;;

INSERT INTO indagini_puntuali SELECT * FROM indagini_puntuali_temp;;
INSERT INTO parametri_puntuali SELECT * FROM parametri_puntuali_temp;;
INSERT INTO parametri_lineari SELECT * FROM parametri_lineari_temp;;

DROP TABLE parametri_puntuali_temp;;
DROP TABLE indagini_puntuali_temp;;
DROP TABLE parametri_lineari_temp;;