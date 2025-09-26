-- hvsr view - handle comma as decimal separator in parametri_puntuali.valore
DROP VIEW IF EXISTS "vw_hvsr_punti_misura";

CREATE VIEW "vw_hvsr_punti_misura" AS
SELECT s.pkuid AS rowid,
    hvsr_union.id_parpu,
    i.tipo_ind,
    hvsr_union.valore,
    s.geom
FROM (
    SELECT id_parpu, replace(valore,',','.') as valore, id_indpu
    FROM parametri_puntuali

    UNION ALL

    SELECT NULL AS id_parpu, f0 AS valore, id_indpu
    FROM hvsr
) hvsr_union
    LEFT JOIN indagini_puntuali i ON hvsr_union.id_indpu = i.id_indpu
    LEFT JOIN sito_puntuale s ON i.id_spu = s.id_spu
WHERE i.tipo_ind = 'HVSR';);
