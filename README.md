# MzS Tools

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.11125497.svg)](https://doi.org/10.5281/zenodo.6372647) [![Documentation Status](https://readthedocs.org/projects/mzs-tools/badge/?version=latest)](https://mzs-tools.readthedocs.io/it/latest/?badge=latest) ![GitHub License](https://img.shields.io/github/license/CNR-IGAG/mzs-tools) ![GitHub Release](https://img.shields.io/github/v/release/CNR-IGAG/mzs-tools)

## About

**QGIS plugin for italian Seismic Microzonation.**

Download and install MzS Tools using the [QGIS](https://qgis.org/) 3.26+ [plugin manager](https://docs.qgis.org/3.34/en/docs/user_manual/plugins/plugins.html) (search for "mzs tools").

You can also download and install manually a release file from the Releases section or the [QGIS plugin repository](https://plugins.qgis.org/plugins/MzSTools/).

Documentation: [https://mzs-tools.readthedocs.io](https://mzs-tools.readthedocs.io)

Credits: [CREDITS.md](CREDITS.md)

License: [LICENSE](LICENSE)

## Changelog

### v1.9.2

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

### v1.9.1

- Updated style expressions for MS level 2-3 layers

### v1.9.0

- Updated styles and print layouts
- Improved compatibility with MS standard v4.2

### v1.8.3

- Updated styles and expressions in QGIS project
- Updated and improved print layouts
- Added available regional CTR WMS services
- Fix potential problems in import process

### v1.8.2

- Experimental fixes for slow data import and export processes
- Updated styles and expressions in QGIS project
- Updated and improved print layouts

### v1.8.1

- Fix problem with version strings in project update

### v1.8

- QGIS project template improvements

### v1.7

- Update ISTAT administrative boundaries and codes to the [latest 2022 version](https://www.istat.it/it/archivio/222527)
- Update styles for editing layers
- Add QGIS action for punctual and linear surveys layers to directly search for available survey documents in the project folder

### v1.6

- Fix Python error in geotec editing
- Update project template (snapping options, symbols)

### v1.5

- Ported to QGIS 3
- [Enhancements and fixes](https://github.com/CNR-IGAG/mzs-tools/milestone/1?closed=1)
- [Online documentation](https://mzs-tools.readthedocs.io) with sphinx and Read The Docs

### v1.4

- Updated to new MS 4.2 standards;
- update project (fixed labels, update .py files, added new style);
- updated italian manual.

### v1.3

- updated layout "CDI - Carta delle Indagini" (added legend);
- updated export shapefiles and "Export geodatabase to project folder" tool (to meet the standards);
- removed "Validate project" tool;
- fixed bug in log files;
- update project (fixed labels, update .py files);
- updated italian manual.

### v1.2

- updated layouts ("Carta di Microzonazione Sismica (FA 0.1-0.5 s)", "Carta di Microzonazione Sismica (FA 0.4-0.8 s)", "Carta di Microzonazione Sismica (FA 0.7-1.1 s)");
- added "pkey" field in "Indagini" and "Parametri" tables;
- removed english manual.

### v1.1

- modified the layout layer "CDI - Indagini puntuali";
- modified the layout layer "MOPS - HVSR";
- updated export database ("CdI_Tabelle.sqlite").

### v1.0

- stable version;
- added a new video-guide ("Indagine stazione singola (HVSR)");
- update project (fixed labels and styles errors, update .py files);
- updated italian manuals.

### v0.9

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

### v0.8

- fixed bug in "indagini_puntuali.py";
- update "siti_puntuali" and "siti_lineari" triggers;
- added a new table ("Indagine stazione singola (HVSR)") and a new layout ("Carta delle frequenze naturali dei terreni");
- update project (in particular .ui, .py files);
- changed update project process and removed "Update project" tool;
- updated italian manuals.

### v0.7

- moved import process to a separate thread;
- import progress shown in qgis interface;
- fixed bug with empty numeric values in csv files during import;
- reimplemented import log file;
- added "Update project" tool;
- update project (in particular .ui, .py files);
- updated italian manuals.

### v0.6

- video-guide additions;
- update project (in particular .ui, .py files);
- resolved bugs;
- updated italian manual.

### v0.5

- improved "Add feature or record" tool;
- removed useless tool;
- update project (in particular .ui, .py files);
- resolved bugs;
- updated manuals.

### v0.4

- initial relase.

## Development

Some Python and PyQT libraries may be required depending on the development environment used. On Ubuntu:

```bash
sudo apt install python3-pip virtualenv python3-venv qttools5-dev-tools pyqt5-dev-tools
```

Example of a Linux development environment with Visual Studio Code, poetry and pb_tool:

- Install [poetry](https://python-poetry.org/)
  - Or use a Python virtualenv and install the dependencies listed in `pyproject.toml` with pip
- Install [Visual Studio Code](https://code.visualstudio.com/) with the Python, Pylance and reStructuredText (for documentation) extensions.
- Clone the repository
- Execute `poetry install`
- Open the project in vscode
- Set vscode python interpreter (ctrl-shift-P - "Python: Select interpreter"), selecting the "Poetry" virtualenv in the list
- Set `PYTHONPATH` in `.env` according to the position of the QGIS python libraries in your system
- Change `plugin_path` in `pb_tool.cfg` according to the QGIS plugin path on your system
- Execute `poetry shell` followed by `pb_tool deploy` to install the current plugin version in QGIS (`pb_tool --help` for more commands)
- Install "First Aid" (for debugging) and "Plugin Reloader" (to reload the plugin deployed with `pb_tool deploy`) plugins in QGIS
- Optionally, check and update the linting and formatting options in `.vscode/settings.json`.

Utility scripts:

- Use the `update_project_template.sh` script (execute from the root of the repository), to update `data/progetto_MS.zip` package with modifications made in the `template_code` directory.
- Use `trans_update.sh` to update the translations and then open the `.ts` file(s) in `poedit` to translate new strings or update existing translations.
- Use `trans_compile.sh` to compile the updated translation(s).
