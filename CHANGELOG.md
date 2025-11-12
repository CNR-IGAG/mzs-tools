# Changelog

## [2.0.5-beta4] - 2025-11-12

- Fix for HVSR view to handle comma as decimal separator
- Custom dependency manager and new tool to check and install required python libraries (alternative to QPIP) and detect Java JVM
- New setting to manually store the Java JRE location
- Disabled plugin dependency on QPIP
- Implemented a db_manager module to improve database operations
- Handle malformed date strings for data export to Access
- Data import and export improvements

## [2.0.4] - 2025-09-18

- Update layout layer definitions
- Tooling updates
- WIP PyQt6 compatibility

## [2.0.3] - 2025-07-22

- Reapply the HVSR view migration script, as the change was not included in v2.0.2 db template

## [2.0.2] - 2025-06-18

- Reduced the municipality overview image size in print layouts causing slow project loading and excessive memory usage.
- Update the HVSR db view to include values from the dedicated non-standard hvsr table
- Fixed an SVG symbol in Carta Geologico-Tecnica and Carta delle MOPS

## [2.0.1] - 2025-05-16

- Bug fixes
- Update HVSR map logic by adding a dedicated view in the db

## [2.0.0] - 2025-04-08

- Major plugin rewrite
- Better project and database management
- Direct, cross-platform data import/export from/to Microsoft Access MS standard database "CdI_Tabelle.mdb" (requires Java JVM 64 bit and external libraries managed with "Qpip" QGIS plugin)
- Initial PyQt6 compatibility

## [1.9.4] - 2024-11-21

- Fix print layout layers

## [1.9.3] - 2024-11-15

- Hotfix for editing signals disconnection
- Fix stab, instab, isosub triggers

## [1.9.2] - 2024-11-13

- Initial compatibility with future Standard MS version
- Unified level 2-3 layers "Zone stabili" and "Zone instabili", as described in Standard MS
- Plugin layers are marked as required and/or read-only where applicable
- Simplified and streamlined new project creation tool
- Added a SM study metadata editor tool
- Automatic "don't overlap" and topological editing rules for groups of layers such as "Zone stabili" and "Zone instabili"
- Added a plugin configuration tool with an option to deactivate the automatic editing rules
- Removed editing tools from MzS Tools toolbar
- Removed feature copy tool from MzS Tools toolbar
- Fixed some issues with project import/export tools
- Fixed some minor issues

## [1.9.1] - 2024-05-10

- Updated style expressions for MS level 2-3 layers

## [1.9.0] - 2023-10-27

- Updated styles and print layouts
- Improved compatibility with MS standard v4.2

## [1.8.3] - 2023-05-16

- Updated styles and expressions in QGIS project
- Updated and improved print layouts
- Added available regional CTR WMS services
- Fix potential problems in import process

## [1.8.2] - 2023-02-15

- Experimental fixes for slow data import and export processes
- Updated styles and expressions in QGIS project
- Updated and improved print layouts

## [1.8.1] - 2022-07-29

- Fix problem with version strings in project update

## [1.8] - 2022-07-21

- QGIS project template improvements

## [1.7] - 2022-06-07

- Update ISTAT administrative boundaries and codes to the [latest 2022 version](https://www.istat.it/it/archivio/222527)
- Update styles for editing layers
- Add QGIS action for punctual and linear surveys layers to directly search for available survey documents in the project folder

## [1.6] - 2022-02-28

- Fix Python error in geotec editing
- Update project template (snapping options, symbols)

## [1.5] - 2021-06-17

- Ported to QGIS 3
- [Enhancements and fixes](https://github.com/CNR-IGAG/mzs-tools/milestone/1?closed=1)
- [Online documentation](https://mzs-tools.readthedocs.io) with sphinx and Read The Docs

## [1.3] - 2020-01-16

- updated layout "CDI - Carta delle Indagini" (added legend);
- updated export shapefiles and "Export geodatabase to project folder" tool (to meet the standards);
- removed "Validate project" tool;
- fixed bug in log files;
- update project (fixed labels, update .py files);
- updated italian manual.

## [1.2] - 2019-07-26

- updated layouts ("Carta di Microzonazione Sismica (FA 0.1-0.5 s)", "Carta di Microzonazione Sismica (FA 0.4-0.8 s)", "Carta di Microzonazione Sismica (FA 0.7-1.1 s)");
- added "pkey" field in "Indagini" and "Parametri" tables;
- removed english manual.

## [1.1] - 2019-05-08

- modified the layout layer "CDI - Indagini puntuali";
- modified the layout layer "MOPS - HVSR";
- updated export database ("CdI_Tabelle.sqlite").

## [1.0] - 2019-04-02

- stable version;
- added a new video-guide ("Indagine stazione singola (HVSR)");
- update project (fixed labels and styles errors, update .py files);
- updated italian manuals.

## [0.9] - 2019-03-21

- update table "Indagine stazione singola (HVSR)", "freq.ui" mask and added a new layout ("Carta delle frequenze naturali dei terreni fr");
- update constraint "quota_slm_top_verify" and "quota_slm_bot_verify" in "indagini_puntuali", "parametri_puntuali" and "parametri_lineari" tables;
- moved export process to a separate thread;
- export progress shown in qgis interface;
- fixed bug in "siti_ind_param.py";
- update "New project" tool;
- added a new table ("metadati");
- added a new video-guide ("Indagine stazione singola (HVSR)");
- update project (in particular .ui, .py files);
- updated italian manuals.

## [0.8] - 2019-01-14

- fixed bug in "indagini_puntuali.py";
- update "siti_puntuali" and "siti_lineari" triggers;
- added a new table ("Indagine stazione singola (HVSR)") and a new layout ("Carta delle frequenze naturali dei terreni");
- update project (in particular .ui, .py files);
- changed update project process and removed "Update project" tool;
- updated italian manuals.

## [0.7] - 2018-11-06

- moved import process to a separate thread;
- import progress shown in qgis interface;
- fixed bug with empty numeric values in csv files during import;
- reimplemented import log file;
- added "Update project" tool;
- update project (in particular .ui, .py files);
- updated italian manuals.

## [0.6] - 2018-10-02

- video-guide additions;
- update project (in particular .ui, .py files);
- resolved bugs;
- updated italian manual.

## [0.5] - 2018-09-21

- improved "Add feature or record" tool;
- removed useless tool;
- update project (in particular .ui, .py files);
- resolved bugs;
- updated manuals.

## [0.4] - 2018-08-20

- initial relase.
