DROP TRIGGER IF EXISTS del_data_i_point;

CREATE TRIGGER del_data_i_point AFTER DELETE ON indagini_puntuali
WHEN ((select count() from indagini_puntuali where "id_indpu" = OLD."id_indpu") = 0)
BEGIN
DELETE FROM hvsr WHERE "id_indpu" = OLD."id_indpu" ;
DELETE FROM parametri_puntuali WHERE "id_indpu" = OLD."id_indpu" ;
END;
