DROP VIEW vw_ind_spu;;
DROP VIEW vw_ind_sln;;

CREATE VIEW "vw_id_ind_spu" AS 
	select p.geom, p.id_spu, a.pkuid as ROWID, a.tipo_ind 
	from indagini_puntuali a left join sito_puntuale p 
	on p.id_spu = a.id_spu;;

CREATE VIEW "vw_id_ind_sln" AS 
	select p.geom, p.id_sln, a.pkuid as ROWID, a.tipo_ind 
	from indagini_lineari a left join sito_lineare p 
	on p.id_sln = a.id_sln;;
	
INSERT INTO geometry_columns (f_table_name,f_geometry_column,geometry_type,coord_dimension,srid,spatial_index_enabled)
VALUES ('vw_id_ind_spu','geom',1,2,32633,0);;

INSERT INTO geometry_columns (f_table_name,f_geometry_column,geometry_type,coord_dimension,srid,spatial_index_enabled)
VALUES ('vw_id_ind_sln','geom',2,2,32633,0);;

