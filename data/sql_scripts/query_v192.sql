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

-- new field 'FS' in instab_l1, instab_l2, instab_l3
ALTER TABLE instab_l1 ADD COLUMN FS DECIMAL(10,1);;
ALTER TABLE instab_l2 ADD COLUMN FS DECIMAL(10,1);;
ALTER TABLE instab_l3 ADD COLUMN FS DECIMAL(10,1);;

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
