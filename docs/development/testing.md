# Testing the plugin

The plugin uses [pytest](https://docs.pytest.org/en/stable/) with [pytest-qgis](https://github.com/GispoCoding/pytest-qgis) and [pytest-qt](https://github.com/pytest-dev/pytest-qt) for comprehensive testing. Tests are organized in the `tests` directory in separate subfolders with clear separation of concerns:

- `tests/unit`: unit tests
- `tests/integration`: integration tests
- `tests/e2e`: end-to-end tests

Tests can also be run with different QGIS versions in Docker containers (directly or through the GitHub workflow with act): see [Testing with multiple QGIS versions (Docker)](#testing-with-multiple-qgis-versions-docker).

## Test Organization Principles

### Unit Tests (`tests/unit/`)

- **Purpose**: Test individual functions and classes in isolation
- **Dependencies**: Keep dependencies minimal (if any), preferably use mocking to avoid QGIS dependencies
- **Example**: Testing mathematical calculations, utility functions

### Integration Tests (`tests/integration/`)

- **Purpose**: Test functionality that requires interaction between different components and/or QGIS environment
- **Dependencies**: Tests could depend on PyQGIS libraries or entire QGIS environment
- **Example**: Testing map tools, layer operations, GUI components

### End-to-End Tests (`tests/e2e/`)

- **Purpose**: Test complete workflows and user interactions
- **Dependencies**: Full QGIS environment, possibly with test data
- **Example**: Testing plugin initialization, configuration, and execution of main features

#### Test data archives

The Accumoli archives used by the e2e tests (`tests/data/standard_projects/Accumoli.zip`, `tests/data/mzs_projects/057001_Accumoli_v*_imported.zip`) are reduced, anonymized copies of the original (non-public) data, built by `tests/tools/build_test_data.py`: see the module docstring for the commands. After every plugin version bump, regenerate the "imported" project for the new version with `just test-data-imported`. The archives are extracted once per session by the `extracted_archive` fixture in `tests/conftest.py`; a missing archive makes the tests using it fail, not skip.

### Test Markers

Tests in each category are automatically marked as `unit`, `integration`, or `e2e` by the `pytest_collection_modifyitems` hook in the root `conftest.py`, based on their directory. This allows easy filtering of tests during execution.

The test execution order is enforced by the `pytest_collection_modifyitems` hook in the root `conftest.py`:

- Unit tests (`unit`) execute first
- Integration tests (`integration`) execute second
- E2E tests (`e2e`) execute last

This works by examining each test item's file path and grouping them accordingly, then reordering the entire test collection before execution. This approach works regardless of how pytest is invoked.

Tests should be further organized by using appropriate markers to indicate particular characteristics:

- `@pytest.mark.display`: Tests that display GUIs for visual inspection, but can be run in headless CI environments by using `QT_QPA_PLATFORM=offscreen` environment setting or other techniques.
- `@pytest.mark.visual`: Tests that require visual inspection of GUIs or visual output (e.g., map rendering) and are not suitable for headless CI environments.

### GUI Tests

GUI tests should use `pytest-qt` to simulate user interactions and verify GUI behavior. Use `qtbot` fixture for interacting with Qt widgets.

GUI tests can be configured to show the interface for visual inspection for a configurable timeout period. To facilitate this, use the `gui_timeout` fixture defined in `tests/conftest.py`, which reads the timeout value from the `GUI_TIMEOUT` environment variable (defaulting to 2000 ms if not set). This allows easy adjustment of the timeout duration for visual inspection during test runs. The `gui_timeout` fixture should be used to add a delay after showing the GUI in tests:

```python
dialog.show()
qtbot.wait(gui_timeout)
```

The gui tests can also be run in headless mode in CI environments by setting the `QT_QPA_PLATFORM` environment variable to `offscreen` or using the `--qgis_disable_gui` pytest option. The `gui_timeout` will be set to 0 in such cases to avoid unnecessary delays.

## Run tests

### Using justfile (recommended)

```bash
# Run all tests with pytest and coverage info, without GUI display
just test

# Run all tests with pytest and coverage info, with GUI display (GUI_TIMEOUT in seconds, default 2)
just test-gui 2

# Run tests in official QGIS Docker images (see "Testing with multiple QGIS versions" below)
just test-docker                     # default image: stable-resolute
just test-docker 3.44-jammy          # a single entry of the Tester workflow matrix
just test-docker all                 # all the entries of the matrix, one after another
just test-docker stable-resolute -k test_name   # extra arguments are passed to pytest

# Run the GitHub "Tester" workflow locally with act (see "Running the GitHub workflow locally" below)
just test-act stable-resolute
```

The base test command is equivalent to:

```bash
uv sync --group testing
uv run pytest --cov=mzs_tools --cov-report=term-missing --qgis_disable_gui --basetemp=.pytest_tmp -rs -v tests
```

Dependencies are locked in `uv.lock`, which is committed: after changing the dependency groups in `pyproject.toml`, run `uv lock`. `uv sync --group testing` also removes the `ci` group, whose Qt libraries can conflict with QGIS.

Every test has a 300 s timeout (pytest-timeout, `thread` method: on timeout the stacks of all the threads are printed and the process is terminated). A test that is legitimately slower can be marked with `@pytest.mark.timeout(900)`.

### Using pytest directly

```bash
# Install the testing dependencies first (once, and after every change to uv.lock)
uv sync --group testing

# Run all tests
uv run pytest -v

# Run with coverage report
uv run pytest -v --cov=mzs_tools --cov-report=term-missing

# Run specific test file
uv run pytest tests/unit/test_string_utils.py -v
uv run pytest tests/integration/test_plugin_main_module.py -v

# Run specific test class
uv run pytest tests/unit/test_string_utils.py::TestStringUtils -v

# Run specific test method
uv run pytest tests/unit/test_string_utils.py::TestStringUtils::test_sanitize_comune_name_basic -v

# Run one case of a parametrized test
uv run pytest "tests/e2e/test_import_data.py::test_import_siti_task[puntuali-csv]" -v

# Run only unit tests using marker
uv run pytest -m unit

# Run only integration tests
uv run pytest -m integration

# Exclude e2e tests
uv run pytest -m "not e2e"

uv run pytest tests/unit/          # Run only unit tests
uv run pytest tests/integration/   # Run only integration tests
```

When calling pytest directly (not through `just`, which loads `.env.uv`) the `QGIS_PREFIX_PATH` environment variable must point to the QGIS installation (`/usr` on most Linux systems). Without it the prefix may be derived from the virtual environment, so QGIS does not find its data providers: the `spatialite` provider is missing, project layers are invalid, and many tests fail (or a modal "project issues" dialog blocks the run). `just test-check-env` runs a quick check of the environment.

### Testing with multiple QGIS versions (Docker)

[tests/run_docker_tests.sh](../../tests/run_docker_tests.sh) is the single entry point for running the test suite **inside** an official `qgis/qgis` image, so tests use the QGIS, Python and Qt versions installed in the image. It is used by the `Tester` workflow, by `just test-docker` and (through the workflow) by `just test-act`. Docker must be installed and running. Official documentation on the QGIS Docker images: <https://github.com/qgis/QGIS/tree/master/.docker>

The images are the entries of the `qgis-version` matrix in `.github/workflows/tester.yml`:

| Docker image                | QGIS | Qt  | Python |
| --------------------------- | ---- | --- | ------ |
| `qgis/qgis:stable-resolute` | 4.4  | Qt6 | 3.14   |
| `qgis/qgis:stable-trixie`   | 4.4  | Qt6 | 3.13   |
| `qgis/qgis:3.44-noble`      | 3.44 | Qt5 | 3.12   |
| `qgis/qgis:3.44-jammy`      | 3.44 | Qt5 | 3.10   |
| `qgis/qgis:3.34-bookworm`   | 3.34 | Qt5 | 3.11   |

The script, running as root in the container with the repository mounted anywhere:

1. installs the Java runtime (needed for the MDB tests) and uv;
2. creates a virtual environment in `/tmp/mzs-tools-venv` with access to the system site packages (QGIS) and installs the `testing` group from `uv.lock` (`uv sync --locked --only-group testing`);
3. runs `pytest tests/ -v -rs --qgis_disable_gui` with the arguments passed to it;
4. gives the files created as root in the mounted repository back to the owner of the repository.

`just test-docker` runs it with `docker run --rm -t --tmpfs /tmp:exec -v "$PWD":/tests_directory qgis/qgis:<image>`. With `all` the recipe keeps going after a failure and lists the failed images at the end.

Notes:

- `/tmp` must be a tmpfs mounted with `exec`: the virtual environment lives there, and tmpfs is mounted `noexec` by default. The e2e tests also write many temporary projects and databases, and `fsync` on the overlay filesystem of a container is slow: with `/tmp` in RAM a run takes a few minutes instead of about 13. A full run writes about 2.4 GB of test data, but `tmp_path_retention_policy = "failed"` removes the data of passed tests, so the peak usage of `/tmp` is lower.
- Image tags move over time. Always check that a tag is still rebuilt on [Docker Hub](https://hub.docker.com/r/qgis/qgis/tags) before using it: for example `stable-questing` is stuck at QGIS 4.2.3. The `3.34-bookworm` image is frozen and no longer rebuilt.
- Run the images one after another (as `just test-docker all` does): running containers in parallel makes everything much slower.
- pytest-sugar is installed in the testing group and is only active when the output is a terminal (which is the case with `docker run -t`). It calls `os.getcwd()` after every test, so a test must never leave the process in a directory that is later removed. Code calling `QgsLayerDefinition.loadLayerDefinition()` has to restore the working directory afterwards, since QGIS changes it to the folder of the `.qlr` file (see `MzSProjectManager.add_layer_from_qlr`).

#### Layer tree removals and crashes on project reload

`test_update_project_from_2_0_0` used to crash intermittently (exit code 139, truncated output) with a segmentation fault in `QgsProject::addMapLayers()` during the `QgsProject.read()` triggered by `update_project()` through `iface.addProject()`, with any QGIS version. The cause was in the plugin:

1. removing a layer tree group with `removeChildNode()` does not remove its layers from the project: `QgsLayerTreeRegistryBridge` only *queues* their removal, which runs the next time events are processed;
2. the project was written before that, so the layers were saved without a layer tree node (hidden layers);
3. on the following read, pytest-qgis processes events on every `legendLayersAdded` signal, so the queued removal ran while the reloaded layer with the same id was still being added, and `QgsProject::addMapLayers()` used the deleted layer. Whether this happened depended on the order in which layers are loaded, which changes between runs.

Groups containing layers must therefore be removed with `MzSProjectManager._remove_group_with_layers()`, which removes the layers from the project first; `assert_no_layers_outside_layer_tree()` in `tests/e2e/test_update_project.py` checks that no hidden layers are left after an update.

### Running the GitHub workflow locally (act)

The `Tester` workflow (`.github/workflows/tester.yml`) runs the test suite in a job container for each QGIS version of its build matrix. It can be run locally with [act](https://github.com/nektos/act) (Docker must be running):

```bash
just test-act                  # default matrix entry: stable-resolute
just test-act 3.44-noble       # a single entry of the matrix
just test-act all              # all the entries of the matrix, one after another
```

The values to use are the entries of the `qgis-version` matrix in the workflow. With `all` the recipe keeps going after a failure and lists the failed versions at the end; the exit code is non-zero if any entry failed.

Running the workflow with act requires some adjustments, which the recipe does automatically without modifying the workflow file:

- the workflow mounts the workspace in the job container with `${{ github.workspace }}:/home/root/mzs-tools`. With act this expression is not a path on the host, so the recipe runs a temporary copy of the workflow in which this line is replaced with an absolute path (this is what the commented `/path/to/mzs-tools:/home/root/mzs-tools` line in the workflow is for, if you need to run act manually with `-W`);
- the repository is copied to a temporary directory in `/tmp` and mounted from there, so that files created as root by the container don't end up in the working tree. The directory is removed at the end;
- act ignores the `env` block of the job `container`, so `CI`, `DISPLAY`, `NO_MODALS`, `QT_QPA_PLATFORM` and `PYTHONPATH` are passed explicitly with `--env`. If those variables are changed in the workflow, the recipe in the `justfile` must be updated as well.

Notes:

- The job container uses `options: --tmpfs /tmp:exec`. The `exec` flag is required: `tests/run_docker_tests.sh` creates the uv virtual environment in `/tmp`, and tmpfs is mounted `noexec` by default.
- Setting up the job (apt packages, uv, Python dependencies) takes about a minute, and a run takes about 4 minutes per matrix entry.
- act is only an approximation of GitHub Actions: it checks the workflow syntax, the container setup and the commands, but runner specific behaviour (for example how `options` and `volumes` are handled) can differ.
- The `stable-resolute` entry runs with branch coverage (`--cov=mzs_tools --cov-report=xml --cov-report=term`, report only, no threshold) and uploads `coverage.xml` as the `coverage-xml` artifact. The upload step is skipped under act (`ACT=true`), because act runs JavaScript actions inside the job container, which has no `node`.

### Debugging in a container

To debug a failure in a specific QGIS version, start an interactive shell in the container and run the script with the failing test:

```bash
docker run -it --rm --tmpfs /tmp:exec -v $(pwd):/tests_directory qgis/qgis:stable-resolute bash

# inside the container
bash /tests_directory/tests/run_docker_tests.sh -k test_name
# then, to rerun without reinstalling the dependencies
cd /tests_directory
UV_PROJECT_ENVIRONMENT=/tmp/mzs-tools-venv PYTHONPATH=/usr/share/qgis/python/plugins:/usr/share/qgis/python:$PWD \
  QT_QPA_PLATFORM=offscreen uv run --no-sync python -m pytest tests/ -v --qgis_disable_gui -k test_name
```

To run QGIS itself (not the tests) in a container, with the plugin mounted, see the `just run-docker-qgis` and `just run-docker-qgis4` recipes.

#### Environment variables

- `DISPLAY`: X11 display (`:1` in the workflow, not actually used with the `offscreen` platform);
- `QT_QPA_PLATFORM`: Qt platform plugin, `offscreen` for headless runs;
- `PYTHONPATH`: must include the QGIS Python modules (`/usr/share/qgis/python`) and the project directory; `tests/run_docker_tests.sh` sets it;
- `QGIS_PREFIX_PATH`: QGIS installation prefix (`/usr`); it is set by `.env.uv` for `just` recipes and by `tests/run_docker_tests.sh`;
- `CI`: when set, `tests/conftest.py` terminates the process with `os._exit()` in `pytest_unconfigure`, after the test summary and the coverage reports have been written, to avoid QGIS teardown segmentation faults (exit code 139). It is set by the workflow.

### Windows environment with Docker

A Windows virtual machine can be run with a [Dockur](https://github.com/dockur/windows) container, for example to test the plugin on Windows:

```bash
# modify paths in the docker compose file for the VM storage and ISO images as needed
cd docker
docker compose -f dockur-win11.yml up -d
# wait for the VM to boot (check logs with "docker compose -f dockur-win11.yml logs -f")
# use an RDP client to connect to the Windows VM

# after use, stop the VM
docker compose -f dockur-win11.yml down
```

### Temporary files and disk space

The e2e tests copy complete project structures (QGIS project, SQLite databases, attachments) into pytest's `tmp_path` directories, and a single full run writes **about 2.4 GB** (each test using a sample project gets its own copy, about 50-60 MB; the archives themselves are extracted only once per session by the `extracted_archive` fixture). By default pytest creates these under the system temporary directory and keeps the directories of the last 3 runs. On systems where `/tmp` is a RAM-backed `tmpfs` (e.g. Arch Linux, Fedora; often limited to half of the RAM) the space can run out, especially when runs that crashed or were killed leave their directories behind.

Symptoms are misleading and not always an explicit "disk full" message:

- `OSError: [Errno 28] No space left on device`, typically raised while setting up the `tmp_path` fixture (all subsequent tests error at setup);
- **segmentation faults** inside QGIS calls such as `QgsProject.read()` / `iface.addProject()`, with the pytest output truncated and no traceback.

Check with `df -h /tmp` and `du -sh /tmp/pytest-of-$USER` if a run fails in this way.

Workarounds:

- Use `just test` / `just test-gui`: they already pass `--basetemp=.pytest_tmp`, so test data is written inside the repository directory (git-ignored) on the regular disk. pytest empties this directory at the start of each run, so only the last run is kept.
- When calling pytest directly, pass the same option: `uv run pytest --basetemp=.pytest_tmp ...`.
- Alternatively, point the temporary directory to a disk-backed location for the whole shell session: `export TMPDIR=$HOME/.cache/pytest-tmp` (the directory must exist).
- Remove leftovers manually: `rm -rf /tmp/pytest-of-$USER` and `rm -rf .pytest_tmp`.
- `pyproject.toml` sets `tmp_path_retention_policy = "failed"`, so the temporary directories of passed tests are removed at the end of the run and only those of failed tests are kept for inspection. To keep everything (e.g. to inspect the output of passing tests) override it with `-o tmp_path_retention_policy=all`; `-o tmp_path_retention_count=N` controls how many old run directories are kept.
- Run only the subset of tests you need (for example `tests/unit` and `tests/integration` produce very little data compared to `tests/e2e`).

## Coverage

The project uses coverage.py to track test coverage:

```bash
# Generate coverage report
uv run pytest --cov=mzs_tools --cov-report=html

# View HTML coverage report
open htmlcov/index.html
```

Coverage configuration is in `pyproject.toml` (`[tool.coverage.run]`, with branch coverage enabled). Coverage is report-only: there is no minimum threshold. In CI, only the `stable-resolute` entry of the Tester workflow measures coverage, prints the report and uploads `coverage.xml` as the `coverage-xml` artifact.
