-- SELECT load_extension('mod_spatialite');

SELECT DiscardGeometryColumn('vw_hvsr', 'geom');
SELECT DiscardGeometryColumn('vw_hvsr_fr', 'geom');
SELECT DiscardGeometryColumn('vw_sito_ind', 'geom');
SELECT DiscardGeometryColumn('vw_id_ind_sln', 'geom');

DELETE
FROM views_geometry_columns
WHERE view_name = 'vw_hvsr';

DELETE
FROM views_geometry_columns
WHERE view_name = 'vw_hvsr_fr';

DROP VIEW IF EXISTS "vw_hvsr";
DROP VIEW IF EXISTS "vw_hvsr_fr";
DROP VIEW IF EXISTS "vw_sito_ind";
DROP VIEW IF EXISTS "vw_id_ind_sln";

CREATE VIEW "vw_sito_ind" AS
SELECT p.geom,
       p.id_spu,
       p.pkuid AS rowid,
       a.tipo_ind,
       COUNT(a.tipo_ind) AS conteggio
FROM indagini_puntuali a
LEFT JOIN sito_puntuale p ON p.id_spu = a.id_spu
GROUP BY a.tipo_ind,
         p.id_spu;

CREATE VIEW "vw_id_ind_sln" AS
SELECT p.geom,
       p.id_sln,
       p.pkuid AS rowid,
       a.tipo_ind
FROM indagini_lineari a
LEFT JOIN sito_lineare p ON p.id_sln = a.id_sln;

CREATE VIEW "vw_hvsr" AS
SELECT s.pkuid AS rowid,
       h.id_indpu,
       h.qualita,
       h.tipo,
       h.f0,
       h.a0,
       h.f1,
       h.a1,
       h.f2,
       h.a2,
       h.f3,
       h.a3,
       h.ar,
       h.fr,
       i.id_spu,
       s.geom AS geom
FROM indagini_puntuali AS i
JOIN hvsr AS h ON h.id_indpu = i.id_indpu
JOIN sito_puntuale AS s ON i.id_spu = s.id_spu
WHERE i.tipo_ind = 'HVSR';

INSERT INTO views_geometry_columns (view_name, view_geometry, view_rowid, f_table_name, f_geometry_column, read_only)
VALUES ('vw_sito_ind', 'geom', 'rowid', 'sito_puntuale', 'geom', 1);

INSERT INTO views_geometry_columns (view_name, view_geometry, view_rowid, f_table_name, f_geometry_column, read_only)
VALUES ('vw_id_ind_sln', 'geom', 'rowid', 'sito_lineare', 'geom', 1);

INSERT INTO views_geometry_columns (view_name, view_geometry, view_rowid, f_table_name, f_geometry_column, read_only)
VALUES ('vw_hvsr', 'geom', 'rowid', 'sito_puntuale', 'geom', 1);
