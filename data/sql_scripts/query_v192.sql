-- SELECT load_extension('mod_spatialite');

-- DPT ind - param
INSERT INTO tbl_tipo_ind_p VALUES(58,'GS','DPT','Penetrometrica dinamica con maglio cinese');;
INSERT INTO tbl_tipo_par_p VALUES(57, 'DPT','Numero di colpi prova pen. din. cinese','n.');;
INSERT INTO tbl_ind_param_p VALUES(147,'DPT',58,'DPT',57);;

-- new instab codes
INSERT INTO tbl_cod_instab (cod, descrizione) VALUES(3054,'Zona di attenzione per lateral spreading');;
INSERT INTO tbl_cod_instab (cod, descrizione) VALUES(3055,'(Liv.3) Zona di suscettibilita'' per lateral spreading');;
INSERT INTO tbl_cod_instab (cod, descrizione) VALUES(3056,'(Liv.3) Zona di rispetto per lateral spreading');;
INSERT INTO tbl_cod_instab (cod, descrizione) VALUES(3069,'Zona di Fratturazione Attiva (ZFA)');;
INSERT INTO tbl_cod_instab (cod, descrizione) VALUES(3081,'(Liv.3) Zona di suscettibilita'' per cavita'' sotterranee - sinkhole');;
INSERT INTO tbl_cod_instab (cod, descrizione) VALUES(3082,'(Liv.3) Zona di rispetto per cavita'' sotterranee - sinkhole');;
INSERT INTO tbl_cod_instab (cod, descrizione) VALUES(3090,'Zona di attenzione per densificazione indotta dall''azione sismica');;
INSERT INTO tbl_cod_instab (cod, descrizione) VALUES(3091,'(Liv.3) Zona di suscettibilita'' per densificazione indotta dall''azione sismica');;
INSERT INTO tbl_cod_instab (cod, descrizione) VALUES(3092,'(Liv.3) Zona di rispetto per densificazione indotta dall''azione sismica');;

-- unified instab, stab, isosub level 2-3 tables
CREATE TABLE "instab_l23"(
	"pkuid" integer primary key autoincrement,
	"ID_i" integer,
	"Tipo_i" integer,
	"FRT" DOUBLE
		CONSTRAINT FA_verify CHECK ("FRT" BETWEEN 0.0 AND 10000.0),
	"FRR" DOUBLE
		CONSTRAINT FRR_verify CHECK ("FRR" BETWEEN 0.0 AND 10000.0),
	"IL" DOUBLE
		CONSTRAINT IL_verify CHECK ("IL" BETWEEN 0.0 AND 10000.0),
	"DISL" DOUBLE
		CONSTRAINT DISL_verify CHECK ("DISL" BETWEEN 0.0 AND 10000.0),
	"FA" DOUBLE
		CONSTRAINT FA_verify CHECK ("FA" BETWEEN 0.0 AND 10000.0),
	"FV" DOUBLE
		CONSTRAINT FV_verify CHECK ("FV" BETWEEN 0.0 AND 10000.0),
	"Ft" DOUBLE
		CONSTRAINT Ft_verify CHECK ("Ft" BETWEEN 0.0 AND 10000.0),
	"FH0105" DOUBLE
		CONSTRAINT FH0105_verify CHECK ("FH0105" BETWEEN 0.0 AND 10000.0),
	"FH0510" DOUBLE
		CONSTRAINT FH0510_verify CHECK ("FH0510" BETWEEN 0.0 AND 10000.0),
	"FH0515" DOUBLE
		CONSTRAINT FH0515_verify CHECK ("FH0515" BETWEEN 0.0 AND 10000.0),
	"FPGA" DOUBLE
		CONSTRAINT FPGA_verify CHECK ("FPGA" BETWEEN 0.0 AND 10000.0),
	"FA0105" DOUBLE
		CONSTRAINT FA0105_verify CHECK ("FA0105" BETWEEN 0.0 AND 10000.0),
	"FA0408" DOUBLE
		CONSTRAINT FA0408_verify CHECK ("FA0408" BETWEEN 0.0 AND 10000.0),
	"FA0711" DOUBLE
		CONSTRAINT FA0711_verify CHECK ("FA0711" BETWEEN 0.0 AND 10000.0),
    "FS" DOUBLE,
	"S" DOUBLE,
	"SPETTRI" text,
	"LIVELLO" integer,
	"CAT" text,
	"AMB" text);;

SELECT AddGeometryColumn('instab_l23', 'geom', 32633, 'MULTIPOLYGON', 'XY');;

INSERT INTO instab_l23 (ID_i, Tipo_i, FRT, FRR, IL, DISL, FA, FV, Ft, FH0105, FH0510, FH0515, FPGA, FA0105, FA0408, FA0711, SPETTRI, LIVELLO, CAT, AMB, geom) 
SELECT ID_i, Tipo_i, FRT, FRR, IL, DISL, FA, FV, Ft, FH0105, FH0510, FH0515, FPGA, FA0105, FA0408, FA0711, SPETTRI, LIVELLO, CAT, AMB, geom FROM instab_l2;;

INSERT INTO instab_l23 (ID_i, Tipo_i, FRT, FRR, IL, DISL, FA, FV, Ft, FH0105, FH0510, FH0515, FPGA, FA0105, FA0408, FA0711, SPETTRI, LIVELLO, CAT, AMB, geom) 
SELECT ID_i, Tipo_i, FRT, FRR, IL, DISL, FA, FV, Ft, FH0105, FH0510, FH0515, FPGA, FA0105, FA0408, FA0711, SPETTRI, LIVELLO, CAT, AMB, geom FROM instab_l3;;

CREATE TRIGGER ins_data_instab_l23
AFTER INSERT ON instab_l23 
FOR EACH ROW 
BEGIN
UPDATE instab_l23
SET ID_i = pkuid + 50000;
END;;

CREATE TRIGGER upd_data_instab_l23 
AFTER UPDATE ON instab_l23 
FOR EACH ROW 
BEGIN 
UPDATE instab_l23 
SET ID_i = pkuid + 50000; 
END;;

CREATE TABLE "stab_l23" (
	"pkuid" integer primary key autoincrement,
	"ID_z" integer,
	"Tipo_z" integer,
	"FA" DOUBLE
		CONSTRAINT FA_verify CHECK ("FA" BETWEEN 0.0 AND 10000.0),
	"FV" DOUBLE
		CONSTRAINT FV_verify CHECK ("FV" BETWEEN 0.0 AND 10000.0),
	"Ft" DOUBLE
		CONSTRAINT Ft_verify CHECK ("Ft" BETWEEN 0.0 AND 10000.0),
	"FH0105" DOUBLE
		CONSTRAINT FH0105_verify CHECK ("FH0105" BETWEEN 0.0 AND 10000.0),
	"FH0510" DOUBLE
		CONSTRAINT FH0510_verify CHECK ("FH0510" BETWEEN 0.0 AND 10000.0),
	"FH0515" DOUBLE
		CONSTRAINT FH0515_verify CHECK ("FH0515" BETWEEN 0.0 AND 10000.0),
	"FPGA" DOUBLE
		CONSTRAINT FPGA_verify CHECK ("FPGA" BETWEEN 0.0 AND 10000.0),
	"FA0105" DOUBLE
		CONSTRAINT FA0105_verify CHECK ("FA0105" BETWEEN 0.0 AND 10000.0),
	"FA0408" DOUBLE
		CONSTRAINT FA0408_verify CHECK ("FA0408" BETWEEN 0.0 AND 10000.0),
	"FA0711" DOUBLE
		CONSTRAINT FA0711_verify CHECK ("FA0711" BETWEEN 0.0 AND 10000.0),
	"SPETTRI" text,
	"LIVELLO" integer,
	"CAT" text);;

SELECT AddGeometryColumn('stab_l23', 'geom', 32633, 'MULTIPOLYGON', 'XY');;

INSERT INTO stab_l23 (ID_z, Tipo_z, FA, FV, Ft, FH0105, FH0510, FH0515, FPGA, FA0105, FA0408, FA0711, SPETTRI, LIVELLO, CAT, geom) 
SELECT ID_z, Tipo_z, FA, FV, Ft, FH0105, FH0510, FH0515, FPGA, FA0105, FA0408, FA0711, SPETTRI, LIVELLO, CAT, geom FROM stab_l2;;

INSERT INTO stab_l23 (ID_z, Tipo_z, FA, FV, Ft, FH0105, FH0510, FH0515, FPGA, FA0105, FA0408, FA0711, SPETTRI, LIVELLO, CAT, geom) 
SELECT ID_z, Tipo_z, FA, FV, Ft, FH0105, FH0510, FH0515, FPGA, FA0105, FA0408, FA0711, SPETTRI, LIVELLO, CAT, geom FROM stab_l3;;

CREATE TRIGGER ins_data_stab_l23
AFTER INSERT ON stab_l23 
FOR EACH ROW 
BEGIN
UPDATE stab_l23
SET ID_z = pkuid + 50000;
END;;

CREATE TRIGGER upd_data_stab_l23 
AFTER UPDATE ON stab_l23 
FOR EACH ROW 
BEGIN 
UPDATE stab_l23 
SET ID_z = pkuid + 50000; 
END;;

CREATE TABLE "isosub_l23"(
	"pkuid" integer primary key autoincrement,
	"ID_isosub" integer,
	"Quota" DOUBLE
		CONSTRAINT Quota_verify CHECK ("Quota" BETWEEN 0.0 AND 10000.0));;

SELECT AddGeometryColumn('isosub_l23', 'geom', 32633, 'MULTILINESTRING', 'XY');;

INSERT INTO isosub_l23 (ID_isosub, Quota, geom) SELECT ID_isosub, Quota, geom FROM isosub_l2;;
INSERT INTO isosub_l23 (ID_isosub, Quota, geom) SELECT ID_isosub, Quota, geom FROM isosub_l3;;

CREATE TRIGGER ins_data_isosub_l23 
AFTER INSERT ON isosub_l23 
FOR EACH ROW 
BEGIN 
UPDATE isosub_l23 
SET ID_isosub = pkuid + 50000; 
END;;

CREATE TRIGGER upd_data_isosub_l23 
AFTER UPDATE ON isosub_l23 
FOR EACH ROW 
BEGIN 
UPDATE isosub_l23 
SET ID_isosub = pkuid + 50000; 
END;;

-- Add new columns "FS" and "S" to "instab_l1"
ALTER TABLE instab_l1 ADD COLUMN FS DOUBLE;;
ALTER TABLE instab_l1 ADD COLUMN S DOUBLE;;

-- new tipo_el codes
INSERT INTO tbl_tipo_el VALUES(41,'5401','Faglia attiva e capace per creep asismico - Cinematismo non definito - certa');;
INSERT INTO tbl_tipo_el VALUES(42,'5411','Faglia attiva e capace per creep asismico - Diretta - certa');;
INSERT INTO tbl_tipo_el VALUES(43,'5431','Faglia attiva e capace per creep asismico - Trascorrente/obliqua - certa');;

-- fix some tbl_tipo_par_p unita_mis and descrizione
UPDATE tbl_tipo_par_p SET unita_mis = "n." WHERE cod IN ("PT","PTS","SPT","PTM","PTL");;
UPDATE tbl_tipo_par_p SET unita_mis = "m" WHERE cod IN ("FF","FP");;
UPDATE tbl_tipo_par_p SET descrizione = "Falda freatica" WHERE cod = "FF";;

-- fix some tipo_gt descriptions
UPDATE tbl_tipo_gt SET descrizione = "Substrato - Incoerente o poco consolidato" WHERE cod = 'IS';;
UPDATE tbl_tipo_gt SET descrizione = "Substrato - Incoerente o poco consolidato, stratificato"  WHERE cod ='ISS';;
UPDATE tbl_tipo_gt SET descrizione = "Substrato - Incoerente o poco consolidato, fratturato/alterato" WHERE cod = 'SFIS';;
UPDATE tbl_tipo_gt SET descrizione = "Substrato - Incoerente o poco consolidato, stratificato fratturato/alterato"  WHERE cod ='SFISS';;
