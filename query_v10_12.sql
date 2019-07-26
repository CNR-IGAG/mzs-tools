DROP VIEW IF EXISTS vw_ind_spu;;
DROP VIEW IF EXISTS vw_ind_sln;;
DROP VIEW IF EXISTS vw_id_ind_spu;; 

CREATE VIEW IF NOT EXISTS "vw_id_ind_sln" AS select p.geom, p.id_sln, a.pkuid as ROWID, a.tipo_ind from indagini_lineari a left join sito_lineare p on p.id_sln = a.id_sln;;
 
CREATE VIEW IF NOT EXISTS "vw_sito_ind" AS select p.geom, p.id_spu, a.pkuid as ROWID, a.tipo_ind, COUNT(a.tipo_ind) as conteggio from indagini_puntuali a left join sito_puntuale p on p.id_spu = a.id_spu group by a.tipo_ind, p.id_spu;;
 
INSERT OR REPLACE INTO geometry_columns (f_table_name,f_geometry_column,geometry_type,coord_dimension,srid,spatial_index_enabled) VALUES ('vw_sito_ind','geom',1,2,32633,0);; 

INSERT OR REPLACE INTO geometry_columns (f_table_name,f_geometry_column,geometry_type,coord_dimension,srid,spatial_index_enabled) VALUES ('vw_id_ind_sln','geom',2,2,32633,0);;

ALTER TABLE indagini_lineari ADD COLUMN "pkey_sln" INTEGER;;

ALTER TABLE indagini_puntuali ADD COLUMN "pkey_spu" INTEGER;;

ALTER TABLE parametri_lineari ADD COLUMN "pkey_indln" INTEGER;;

ALTER TABLE parametri_puntuali ADD COLUMN "pkey_indpu" INTEGER;;

ALTER TABLE curve ADD COLUMN "pkey_parpu" INTEGER;;
