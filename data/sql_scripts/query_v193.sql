-- stab_l1 triggers
DROP TRIGGER IF EXISTS ins_data_stab_l1;;
DROP TRIGGER IF EXISTS upd_data_stab_l1;;

CREATE TRIGGER ins_data_stab_l1 
AFTER INSERT ON stab_l1 
FOR EACH ROW 
BEGIN 
UPDATE stab_l1 
SET livello = 1, 
ID_z = pkuid + 10000
WHERE pkuid = NEW.pkuid;
END;;

CREATE TRIGGER upd_data_stab_l1 
AFTER UPDATE ON stab_l1 
FOR EACH ROW 
BEGIN 
UPDATE stab_l1 
SET livello = 1, 
ID_z = pkuid + 10000
WHERE pkuid = NEW.pkuid;
END;;

--stab_l23 triggers
DROP TRIGGER IF EXISTS ins_data_stab_l23;;
DROP TRIGGER IF EXISTS upd_data_stab_l23;;

CREATE TRIGGER ins_data_stab_l23
AFTER INSERT ON stab_l23 
FOR EACH ROW 
BEGIN
UPDATE stab_l23
SET ID_z = pkuid + 50000
WHERE pkuid = NEW.pkuid;
END;;

CREATE TRIGGER upd_data_stab_l23 
AFTER UPDATE ON stab_l23 
FOR EACH ROW 
BEGIN 
UPDATE stab_l23 
SET ID_z = pkuid + 50000
WHERE pkuid = NEW.pkuid;
END;;

-- instab_l1 triggers
DROP TRIGGER IF EXISTS ins_data_instab_l1;;
DROP TRIGGER IF EXISTS upd_data_instab_l1;;

CREATE TRIGGER ins_data_instab_l1 
AFTER INSERT ON instab_l1 
FOR EACH ROW 
BEGIN 
UPDATE instab_l1 
SET livello = 1, 
ID_i = pkuid + 10000
WHERE pkuid = NEW.pkuid;
END;;

CREATE TRIGGER upd_data_instab_l1 
AFTER UPDATE ON instab_l1 
FOR EACH ROW 
BEGIN 
UPDATE instab_l1 
SET livello = 1, 
ID_i = pkuid + 10000
WHERE pkuid = NEW.pkuid;
END;;

-- instab_l23 triggers
DROP TRIGGER IF EXISTS ins_data_instab_l23;;
DROP TRIGGER IF EXISTS upd_data_instab_l23;;

CREATE TRIGGER ins_data_instab_l23
AFTER INSERT ON instab_l23 
FOR EACH ROW 
BEGIN
UPDATE instab_l23
SET ID_i = pkuid + 50000
WHERE pkuid = NEW.pkuid;
END;;

CREATE TRIGGER upd_data_instab_l23 
AFTER UPDATE ON instab_l23 
FOR EACH ROW 
BEGIN 
UPDATE instab_l23 
SET ID_i = pkuid + 50000
WHERE pkuid = NEW.pkuid;
END;;

-- isosub_l1 triggers
DROP TRIGGER IF EXISTS ins_data_isosub_l1;;
DROP TRIGGER IF EXISTS upd_data_isosub_l1;;

CREATE TRIGGER ins_data_isosub_l1 
AFTER INSERT ON isosub_l1 
FOR EACH ROW 
BEGIN 
UPDATE isosub_l1 
SET ID_isosub = pkuid + 10000
WHERE pkuid = NEW.pkuid;
END;;

CREATE TRIGGER upd_data_isosub_l1 
AFTER UPDATE ON isosub_l1 
FOR EACH ROW 
BEGIN 
UPDATE isosub_l1 
SET ID_isosub = pkuid + 10000
WHERE pkuid = NEW.pkuid;
END;;

-- isosub_l23 triggers
DROP TRIGGER IF EXISTS ins_data_isosub_l23;;
DROP TRIGGER IF EXISTS upd_data_isosub_l23;;

CREATE TRIGGER ins_data_isosub_l23 
AFTER INSERT ON isosub_l23 
FOR EACH ROW 
BEGIN 
UPDATE isosub_l23 
SET ID_isosub = pkuid + 50000
WHERE pkuid = NEW.pkuid;
END;;

CREATE TRIGGER upd_data_isosub_l23 
AFTER UPDATE ON isosub_l23 
FOR EACH ROW 
BEGIN 
UPDATE isosub_l23 
SET ID_isosub = pkuid + 50000
WHERE pkuid = NEW.pkuid;
END;;
