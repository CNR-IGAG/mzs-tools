DROP VIEW vw_id_ind_spu;; 
 
CREATE VIEW "vw_sito_ind" AS 
select p.geom, p.id_spu, a.pkuid as ROWID, a.tipo_ind, COUNT(a.tipo_ind) as conteggio 
from indagini_puntuali a left join sito_puntuale p  
on p.id_spu = a.id_spu 
group by a.tipo_ind, p.id_spu;;
 
INSERT INTO geometry_columns (f_table_name,f_geometry_column,geometry_type,coord_dimension,srid,spatial_index_enabled) 
VALUES ('vw_sito_ind','geom',1,2,32633,0);; 