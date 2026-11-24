# Testing the plugin

The plugin uses [pytest](https://docs.pytest.org/en/stable/) with [pytest-qgis](https://github.com/GispoCoding/pytest-qgis) and [pytest-qt](https://github.com/pytest-dev/pytest-qt) for comprehensive testing. Tests are organized in the `tests` directory in separate subfolders with clear separation of concerns:

- `tests/unit`: unit tests
- `tests/integration`: integration tests
- `tests/e2e`: end-to-end tests

Tests can also be run with different QGIS versions in Docker containers (using tox or the GitHub workflow with act): see [Testing with multiple QGIS versions (tox)](#testing-with-multiple-qgis-versions-tox).

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

### Test Markers

Tests in each category are automatically marked as `unit`, `integration`, or `e2e` in the specific `conftest.py`. This allows easy filtering of tests during execution.

The test execution order is enforced by the `pytest_collection_modifyitems` hook in the root `conftest.py`:

- Unit tests (`unit`) execute first
- Integration tests (`integration`) execute second
- E2E tests (`e2e`) execute last

This works by examining each test item's file path and grouping them accordingly, then reordering the entire test collection before execution. This approach works regardless of how pytest is invoked.

Tests should be further organized by using appropriate markers to indicate particular characteristics:

- `@pytest.mark.no_qgis`: Tests that do not require QGIS environment. This can be useful to quickly filter tests for CI environments where QGIS is not available.
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

# Run tests with different QGIS versions in Docker containers using tox (see "Testing with multiple QGIS versions" below)
just test-tox-stable         # QGIS stable 4.4 (Qt6)
just test-tox-ltr            # QGIS LTR 3.44 (Qt5)
just test-tox-ltr-jammy      # QGIS LTR 3.44 (Qt5) with Python 3.10
just test-tox-old            # QGIS 3.34 (Qt5), the minimum supported version
just test-tox-all            # all of the above, one after another

# Run the GitHub "Tester" workflow locally with act (see "Running the GitHub workflow locally" below)
just test-act stable-resolute
```

The base test command is equivalent to:

```bash
uv sync --no-group ci
# the "--no-group ci" option might be required to avoid Qt library conflicts with qgis-plugin-ci dependencies
uv sync --group testing
uv run pytest --cov=mzs_tools --cov-report=term-missing --qgis_disable_gui --basetemp=.pytest_tmp
```

### Using pytest directly

```bash
# Run all tests
uv run pytest -v

# Run with coverage report
uv run pytest -v --cov=mzs_tools --cov-report=term-missing

# Run specific test file
uv run pytest tests/unit/test_plugin_main.py -v
uv run pytest tests/qgis/test_plugin_main_qgis.py -v

# Run specific test class
uv run pytest tests/unit/test_plugin_main.py::TestDipStrikeToolsPluginBasic -v

# Run specific test method
uv run pytest tests/unit/test_plugin_main.py::TestDipStrikeToolsPluginBasic::test_plugin_import -v

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

### Testing with multiple QGIS versions (tox)

[tox](https://tox.wiki/) is used only as a runner for Docker: each environment in `tox.ini` pulls an official `qgis/qgis` image and runs the whole test suite **inside** the container, so tests use the QGIS, Python and Qt versions installed in the image. This ensures that the plugin works with several QGIS releases and Python/Qt versions, in isolated, reproducible environments. Docker must be installed and running. Official documentation on the QGIS Docker images: <https://github.com/qgis/QGIS/tree/master/.docker>

| tox environment  | Docker image                | QGIS | Qt  | Python |
| ---------------- | --------------------------- | ---- | --- | ------ |
| `qgis-stable`    | `qgis/qgis:stable-resolute` | 4.4  | Qt6 | 3.14   |
| `qgis-ltr`       | `qgis/qgis:ltr-noble`       | 3.44 | Qt5 | 3.12   |
| `qgis-ltr-jammy` | `qgis/qgis:ltr-jammy`       | 3.44 | Qt5 | 3.10   |
| `qgis-old`       | `qgis/qgis:3.34-bookworm`   | 3.34 | Qt5 | 3.11   |

The `all` environment runs the four environments above sequentially. The `qgis4` and `qgis4-gui` environments use a custom QGIS 4 image built locally with `just build-docker-qgis4`.

```bash
uv sync --group testing
uv run tox -e qgis-stable            # a single environment
uv run tox -e qgis-stable,qgis-ltr   # more environments
uv run tox -e all                    # all the official environments
uv run tox list                      # list the available environments
```

Each environment in [tox.ini](../../tox.ini):

1. pulls the Docker image;
2. starts a container with the project directory mounted at `/tests_directory` and the variables needed for headless testing (`DISPLAY`, `QT_QPA_PLATFORM=offscreen`, `PYTHONPATH`);
3. installs the OpenJDK runtime (needed for the MDB tests), pytest and the other test dependencies inside the container;
4. runs pytest with the container's Python and QGIS installation (`--qgis_disable_gui`);
5. removes the container when the tests complete.

Notes:

- A full run of one environment takes about 3-4 minutes. Run the environments one after another (as `tox -e all` does): running containers in parallel makes everything much slower.
- Image tags move over time. Always check that a tag is still rebuilt on [Docker Hub](https://hub.docker.com/r/qgis/qgis/tags) before using it: for example `stable-questing` is stuck at QGIS 4.2.3 and the `ltr` alias now points to the Ubuntu "resolute" image, so `ltr-noble` is used to get Python 3.12. The `3.34-bookworm` image is frozen and no longer rebuilt.
- The project directory is mounted read-write in the container, which runs as root: files created there (e.g. `__pycache__`) are owned by root and must be removed with `sudo`. This includes the QGIS settings that pytest-qgis keeps in `.qgis-settings/` in the project directory: when they are owned by root, local test runs cannot write them and `tests/integration/test_qgis_map.py` crashes or errors in teardown. Fix the ownership with `sudo chown -R $USER: .qgis-settings` (or delete the directory).
- Containers are started with `--tmpfs /tmp`. The e2e tests write many temporary projects and databases, and `fsync` on the overlay filesystem of a container is slow: the export tasks used to take about 46 seconds per test and the whole suite about 13 minutes, against 3-4 minutes with `/tmp` in RAM. Peak usage of `/tmp` is about 1 GiB, because `tmp_path_retention_policy = "failed"` removes the data of passed tests.
- pytest-sugar is installed in the testing group and is only active when the output is a terminal (which is the case in the containers). It calls `os.getcwd()` after every test, so a test must never leave the process in a directory that is later removed. Code calling `QgsLayerDefinition.loadLayerDefinition()` has to restore the working directory afterwards, since QGIS changes it to the folder of the `.qlr` file (see `MzSProjectManager.add_layer_from_qlr`).
- pytest and the other dependencies are installed with `pip install --break-system-packages` in the containers based on recent Debian/Ubuntu releases, which prevent pip from modifying the system Python (PEP 668). This is safe because the containers are destroyed after the tests. The `jammy` image (Python 3.10) does not need the flag.

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

- The job container uses `options: --tmpfs /tmp:exec`. The `exec` flag is required: the workflow creates the uv virtual environment in `/tmp`, and tmpfs is mounted `noexec` by default, which makes `uv run pytest` silently fall back to the system pytest (without pytest-qgis) and fail with `unrecognized arguments: --qgis_disable_gui`.
- Setting up the job (apt packages, uv, Python dependencies) takes about a minute, and a run takes about 4 minutes per matrix entry.
- act is only an approximation of GitHub Actions: it checks the workflow syntax, the container setup and the commands, but runner specific behaviour (for example how `options` and `volumes` are handled) can differ.

### Using Docker without tox

For more control, tests can be run manually in a container:

```bash
docker pull qgis/qgis:stable-resolute

# run a container with the project directory mounted
docker run -d --name qgis-test \
  --tmpfs /tmp \
  -v $(pwd):/tests_directory \
  -e DISPLAY=:99 \
  -e QT_QPA_PLATFORM=offscreen \
  -e PYTHONPATH=/usr/share/qgis/python:/tests_directory \
  qgis/qgis:stable-resolute tail -f /dev/null

# install the dependencies (once) and run the tests inside the container
docker exec -t qgis-test bash -c \
  "apt update && apt remove -y python3-pluggy && apt install -y --no-install-recommends default-jre && \
   python3 -m pip install --break-system-packages pytest pytest-qt pytest-qgis pytest-sugar pytest-env factory-boy jaydebeapi"
docker exec -t qgis-test bash -c \
  "cd /tests_directory && python3 -m pytest tests/ -v -rs --qgis_disable_gui"

# clean up
docker rm -f qgis-test
```

To debug a failure in a specific QGIS version, start an interactive shell in the container, run the failing test and check the versions:

```bash
docker run -it --rm --tmpfs /tmp \
  -v $(pwd):/tests_directory \
  -e PYTHONPATH=/usr/share/qgis/python:/tests_directory \
  qgis/qgis:stable-resolute bash

# inside the container
cd /tests_directory
python3 -m pytest tests/ -v --qgis_disable_gui -k test_name
qgis --version
python3 --version
```

The helper script [tests/run_docker_tests.sh](../../tests/run_docker_tests.sh) can also be executed inside a container: it sets `DISPLAY`, `QT_QPA_PLATFORM`, `PYTHONPATH` and `QGIS_PREFIX_PATH`, installs pytest if missing, starts Xvfb when a non-offscreen platform is requested, and runs `pytest tests/` with the arguments passed to it (`docker exec -t qgis-test /tests_directory/tests/run_docker_tests.sh -v`). It does not install the Java runtime or `jaydebeapi`, so MDB tests are skipped unless those are available.

To run QGIS itself (not the tests) in a container, with the plugin mounted, see the `just run-docker-qgis` and `just run-docker-qgis4` recipes.

#### Environment variables

- `DISPLAY`: X11 display (`:99` in tox, which is not actually used with the `offscreen` platform; `:1` in the workflow);
- `QT_QPA_PLATFORM`: Qt platform plugin, `offscreen` for headless runs;
- `PYTHONPATH`: must include the QGIS Python modules (`/usr/share/qgis/python`) and the project directory;
- `QGIS_PREFIX_PATH`: QGIS installation prefix (`/usr`); it is set by `.env.uv` for `just` recipes, and is not needed in the official containers;
- `CI`: when set, `tests/conftest.py` terminates the process at the end of the session with `os._exit()` to avoid QGIS teardown segmentation faults (exit code 139) when all tests have passed. It is set by the workflow, not by tox. Locally it also hides the pytest summary and coverage report;
- `TESTING_MODE`: set by pytest-env from `pyproject.toml`.

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

The e2e tests copy complete project structures (QGIS project, SQLite databases, attachments) into pytest's `tmp_path` directories, and a single full run writes **about 21 GB**. By default pytest creates these under the system temporary directory and keeps the directories of the last 3 runs. On systems where `/tmp` is a RAM-backed `tmpfs` (e.g. Arch Linux, Fedora; often limited to half of the RAM) the disk fills up after a few runs, and runs that crashed or were killed leave their directories behind.

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

Coverage configuration is in `pyproject.toml`.
