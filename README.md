# MzS Tools

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.11125497.svg)](https://doi.org/10.5281/zenodo.6372647) [![Documentation Status](https://readthedocs.org/projects/mzs-tools/badge/?version=latest)](https://mzs-tools.readthedocs.io/it/latest/?badge=latest) ![GitHub License](https://img.shields.io/github/license/CNR-IGAG/mzs-tools) ![GitHub Release](https://img.shields.io/github/v/release/CNR-IGAG/mzs-tools)

## About

**QGIS plugin for italian Seismic Microzonation.**

Download and install MzS Tools using the [QGIS](https://qgis.org/) 3.26+ [plugin manager](https://docs.qgis.org/3.34/en/docs/user_manual/plugins/plugins.html) (search for "mzs tools").

You can also download and install manually a release file from the Releases section or the [QGIS plugin repository](https://plugins.qgis.org/plugins/MzSTools/).

Documentation: [https://mzs-tools.readthedocs.io](https://mzs-tools.readthedocs.io)

Credits: [CREDITS.md](CREDITS.md)

License: [LICENSE](LICENSE)

Changelog: [CHANGELOG.md](CHANGELOG.md)

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
