## Project Overview

This project ("MzS Tools") is a python QGIS plugin for seismic microzonation ("SM") data management in Italy. SM studies in Italy are carried out in all urban municipalities with a peak ground acceleration (PGA) exceeding 0.125 g. Each study must adhere to the “Standard di rappresentazione e archiviazione informatica” (SM Standards), a technical document that rigorously defines the required data structure and cartographic outputs, ensuring consistency across all projects.

MzS Tools addresses common challenges faced by SM authors:

- Automatically generate a QGIS project structure for a specific municipality, including ready‑to‑use layers, styles, and standard‑compliant print layouts for SM maps.
- Provide a geodatabase structure in SQLite / SpatiaLite format.
- Offer assisted editing of georeferenced geometries with topological checks for selected layers.
- Deliver user‑friendly data‑entry interfaces for attribute tables of vector layers and the survey database, built using QGIS capabilities.
- Import data from existing projects based on shapefiles and survey databases in Microsoft Access, SQLite, or CSV format.
- Export a project structure based on shapefiles (geographic data) and Microsoft Access or SQLite (survey database) formats, as required by the SM Standards for study validation.
- Provide a suite of utilities to streamline project and data management.

## Structure and Development Tools

- `docker/`: Docker configurations for development and testing
- `docs/development/`: Development related documentation
- `help/`: Sphinx based user documentation
- `mzs_tools/`: Main plugin code
- `tests/`: Unit and integration tests
- `justfile`: Task automation file
- `pyproject.toml`: Project configuration file

The primary development tools are **uv** for dependency management and **just** for task automation. The `justfile` defines tasks for running tests, managing dependencies, translations, and more.

`pyproject.toml` organizes dependencies into groups such as `ci`, `testing`, and `development`.

[qgis-plugin-ci](https://github.com/opengisch/qgis-plugin-ci) is used for tasks such as plugin packaging, changelog generation, and continuous integration through GitHub Actions.

When launching terminal commands, use `uv run` to ensure the correct environment is activated.

## Coding Guidelines

Python code should be Python 3.10+ compatible. PyQt is used for GUI development, and the plugin should be compatible with both PyQt5 and PyQt6, until QGIS fully transitions to PyQt6. The PyQt5/PyQt6 compatibility approach is described in the [PyQt Compatibility](../docs/development/pyqt-compatibility.md) document.

When defining text messages directed to the user, use the `QCoreApplication.translate` function to ensure proper translation support.

```python
msg = self.tr("This is a message.")
QMessageBox.information(None, self.tr("Title"), msg)
...

def tr(self, message: str) -> str:
    return QCoreApplication.translate(self.__class__.__name__, message)
```

Avoid translating log messages, especially at debug level, as these are meant for developers and not end-users. Avoid translation of technical identifiers such as field names or variable names, as these should remain consistent across languages for clarity and maintainability.

## Testing

Before adding or modifying tests:

- Always refer to the [Testing the plugin](../docs/development/testing.md) document for detailed information on test organization.
- Inspect [pytest-qgis readme](https://github.com/GispoCoding/pytest-qgis) for proper usage of pytest-qgis features.
