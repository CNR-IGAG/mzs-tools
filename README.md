# MZS TOOLS

This plugin was created to realize a project based on a light and fast SpatiaLite geodatabase for data storage and maps production according to the italian "Criteria for Seismic Microzonation".

Seismic Microzonation studies are carried out in order to define zones, in urban areas, which have a homogeneous seismic behavior.

Seismic Microzonation studies include the following maps:

- Investigation map ("Carta delle Indagini"); 
- Geological-Technical Map for Seismic Microzonation ("Carta Geologico-Tecnica"); 
- Map of Seismically Homogeneous Microzones ("Carta delle Microzone Omogenee in Prospettiva sismica"); 
- Seismic Microzonation Map ("Carta di Microzonazione Sismica"). 

The plugin was created to give the opportunity to quickly perform standard compliant Seismic Microzonation studies.

## Changelog:

### v1.2:
-  updated layouts ("Carta di Microzonazione Sismica (FA 0.1-0.5 s)", "Carta di Microzonazione Sismica (FA 0.4-0.8 s)", "Carta di Microzonazione Sismica (FA 0.7-1.1 s)");
-  added "pkey" field in "Indagini" and "Parametri" tables;
-  removed english manual.	

### v1.1:		
-  modified the layout layer "CDI - Indagini puntuali";
-  modified the layout layer "MOPS - HVSR";
-  updated export database ("CdI_Tabelle.sqlite").

### v1.0:
-  stable version;
-  added a new video-guide ("Indagine stazione singola (HVSR)");
-  update project (fixed labels and styles errors, update .py files);
-  updated italian manuals.

### v0.9:		
-  update table "Indagine stazione singola (HVSR)", "freq.ui" mask and added a new layout ("Carta delle frequenze naturali dei terreni fr");
-  update constraint "quota_slm_top_verify" and "quota_slm_bot_verify" in "indagini_puntuali", "parametri_puntuali" and "parametri_lineari" tables;	
-  moved export process to a separate thread;
-  export progress shown in qgis interface;				
-  fixed bug in "siti_ind_param.py";
-  update "New project" tool;
-  added a new table ("metadati");
-  added a new video-guide ("Indagine stazione singola (HVSR)");
-  update project (in particular .ui, .py files);
-  updated italian manuals.

### v0.8:		
-  fixed bug in "indagini_puntuali.py";
-  update "siti_puntuali" and "siti_lineari" triggers;
-  added a new table ("Indagine stazione singola (HVSR)") and a new layout ("Carta delle frequenze naturali dei terreni");
-  update project (in particular .ui, .py files);
-  changed update project process and removed "Update project" tool;
-  updated italian manuals.
		
### v0.7:
-  moved import process to a separate thread;
-  import progress shown in qgis interface;
-  fixed bug with empty numeric values in csv files during import;
-  reimplemented import log file;
-  added "Update project" tool;
-  update project (in particular .ui, .py files);
-  updated italian manuals.
		
### v0.6:
-  video-guide additions;
-  update project (in particular .ui, .py files);
-  resolved bugs;
-  updated italian manual.
		
### v0.5:
-  improved "Add feature or record" tool;
-  removed useless tool;
-  update project (in particular .ui, .py files);
-  resolved bugs;
-  updated manuals.
		
### v0.4:
-  initial relase.
