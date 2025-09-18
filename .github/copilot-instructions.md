The project is a QGIS plugin for italian seismic microzonation data management.

The main development tools are uv for dependency management and just for task automation.
In the `justfile` there are tasks for running tests, managing dependencies and
translations, etc.
In `pyproject.toml` dependencies are grouped into categories such as `ci`, `testing`, and
`development`.

When launching terminal commands, use `uv run` to ensure the correct environment is activated. To avoid possible issues with the fish shell, the use of `bash -c` might be required to run commands that require a shell environment.

Python code should be Python 3.9+ compatible, as the default MacOS QGIS builds still use Python 3.9. PyQt is used for GUI development, and the plugin should be compatible with both PyQt5 and PyQt6, until QGIS fully transitions to PyQt6.

When adding text messages directed to the user, use the `QCoreApplication.translate` function to ensure proper translation support. Use a module level function or method for translations (keeping it at the bottom of the file), like this:

```python
self.tr("Dip Strike Tool activated.")
...

def tr(self, message: str) -> str:
    """Get the translation for a string using Qt translation API.

    :param message: string to be translated.
    :type message: str

    :returns: Translated version of message.
    :rtype: str
    """
    return QCoreApplication.translate(self.__class__.__name__, message)
```

Avoid translation of log messages, especially at debug level, as these are meant for developers and not end-users. Avoid translation of technical identifiers such as field names or variable names, as these should remain consistent across languages for clarity and maintainability.

The plugin uses pytest and [pytest-qgis](https://github.com/GispoCoding/pytest-qgis) for testing, with specific markers for unit tests and QGIS-related tests.

Tests are organized in 2 separate folders:

- `tests/unit`: testing code which is independent of QGIS API (uses mocking)
- `tests/qgis`: testing code which depends on QGIS API (integration tests)

Tests are organized using pytest markers:

- `@pytest.mark.unit`: Unit tests that don't require QGIS
- `@pytest.mark.qgis`: Tests that require QGIS environment
- `@pytest.mark.integration`: Integration tests

When running tests, use the `uv run pytest` command to ensure the correct environment is activated. If there are Qt library issues, use the `--no-group ci` option:

```bash
uv sync --no-group ci
uv sync --group testing
uv run pytest -v
```
