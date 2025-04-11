CREATE VIEW "vw_hvsr_punti_misura" AS
SELECT s.pkuid AS rowid,
    p.id_parpu,
    i.tipo_ind,
    p.valore,
    s.geom
FROM parametri_puntuali p
    LEFT JOIN indagini_puntuali i ON p.id_indpu = i.id_indpu
    LEFT JOIN sito_puntuale s ON i.id_spu = s.id_spu
WHERE i.tipo_ind = 'HVSR';

INSERT INTO views_geometry_columns (
        view_name,
        view_geometry,
        view_rowid,
        f_table_name,
        f_geometry_column,
        read_only
    )
VALUES (
        'vw_hvsr_punti_misura',
        'geom',
        'rowid',
        'sito_puntuale',
        'geom',
        1
    );
