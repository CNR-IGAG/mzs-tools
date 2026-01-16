# Testing with Multiple QGIS Versions using Docker

This document describes how to run tests with different QGIS versions using Docker containers. This approach ensures that the plugin is compatible with multiple QGIS releases and Python/Qt versions.

## Overview

The project uses [tox](https://tox.wiki/) to orchestrate test execution across multiple QGIS Docker images. Tests run **inside** the Docker containers where QGIS is installed, ensuring an authentic testing environment. This provides:

- **Isolated test environments**: Each QGIS version runs in its own container
- **Authentic QGIS environment**: Tests run with the actual QGIS installation
- **Reproducible results**: Tests run in consistent, standardized environments
- **Version compatibility verification**: Ensures the plugin works with latest, stable, LTR, and Qt6 versions
- **CI/CD ready**: Same approach can be used in continuous integration pipelines

## Available QGIS Docker Images

The following official QGIS Docker images are used for testing:

| Environment   | Docker Image                          | QGIS Version | Qt Version | Description                |
| ------------- | ------------------------------------- | ------------ | ---------- | -------------------------- |
| `qgis-latest` | `qgis/qgis:latest`                    | Latest build | Qt5        | Latest development version |
| `qgis-stable` | `qgis/qgis:stable-noble`              | 3.44         | Qt5        | Current stable release     |
| `qgis-ltr`    | `qgis/qgis:ltr-noble`                 | 3.40         | Qt5        | Long-term release          |
| `qgis-qt6`    | `ghcr.io/qgis/qgis-qt6-unstable:main` | Unstable     | Qt6        | Qt6 development version    |

Official documentation on QGIS Docker images: <https://github.com/qgis/QGIS/tree/master/.docker>

## Prerequisites

1. **Docker**: Docker must be installed and running

   ```bash
   # Check Docker installation
   docker --version
   ```

2. **Dependencies**: Install tox

   ```bash
   uv sync --group testing
   ```

## How It Works

The tox configuration defines test environments for each QGIS version. When you run a test environment:

1. Tox pulls the appropriate QGIS Docker image
2. Tox starts a container from that image with the project directory mounted
3. Inside the container, pytest and dependencies are installed
4. Tests execute inside the container using the container's QGIS installation
5. The container is automatically removed after tests complete

This ensures tests run in the exact environment where QGIS is installed, with the correct Python and Qt versions.

## Running Tests

### Using justfile (Recommended)

The easiest way to run Docker-based tests is using the predefined justfile tasks:

```bash
# Test with specific QGIS version
just test-tox-latest   # Latest development version
just test-tox-stable   # Current stable (3.44)
just test-tox-ltr      # Long-term release (3.40)
just test-tox-qt6      # Qt6 version
just test-tox-qt6-gui  # Qt6 version with GUI enabled

# Qt6 tests require building the Docker image first:
just build-image-qgis-qt6-ubuntu-master

# Run tests with all QGIS versions
just test-tox-all
```

### Using tox Directly

You can also run tox commands directly:

```bash
# Run specific environment
uv run tox -e qgis-stable

# Run multiple environments
uv run tox -e qgis-stable,qgis-ltr

# Run all environments
uv run tox -e all

# List available environments
uv run tox list
```

### Using Docker Manually

For more control, you can run tests manually in Docker containers:

```bash
# Pull the QGIS image
docker pull qgis/qgis:stable-noble

# Run container with mounted project directory
docker run -d --name qgis-test \
  -v $(pwd):/tests_directory \
  -e DISPLAY=:99 \
  -e QT_QPA_PLATFORM=offscreen \
  qgis/qgis:stable-noble

# Execute tests inside the container
docker exec -t qgis-test bash -c \
  "cd /tests_directory && python3 -m pytest tests/ -v --qgis_disable_gui"

# Clean up
docker stop qgis-test
docker rm qgis-test
```

## Test Runner Script

A helper script is provided at [tests/run_docker_tests.sh](../../tests/run_docker_tests.sh) that can be executed inside QGIS Docker containers. It handles:

- Environment setup (DISPLAY, QT_QPA_PLATFORM, PYTHONPATH)
- Starting Xvfb if needed
- Installing pytest dependencies if not present
- Running tests with appropriate configuration

Usage inside a container:

```bash
docker exec -t qgis-test /tests_directory/tests/run_docker_tests.sh [pytest-args]
```

## Configuration

### tox.ini

The [tox.ini](../../tox.ini) file defines test environments for each QGIS version. Each environment:

- Pulls the appropriate Docker image
- Runs a container with the project directory mounted at `/tests_directory`
- Sets environment variables for headless testing (`QT_QPA_PLATFORM=offscreen`)
- Installs pytest and dependencies inside the container
- Executes tests using the container's Python and QGIS installation
- Automatically removes the container after completion

Example configuration for the stable environment:

```ini
[testenv:qgis-stable]
description = Run tests with QGIS stable 3.44 (Qt5)
commands =
    bash -c ' \
        docker pull qgis/qgis:stable-noble && \
        docker run --rm \
            --name mzs-tools-test-qgis-stable \
            -v {toxinidir}:/tests_directory \
            -e DISPLAY=:99 \
            -e QT_QPA_PLATFORM=offscreen \
            -e PYTHONPATH=/tests_directory \
            qgis/qgis:stable-noble \
            bash -c "cd /tests_directory && python3 -m pip install --break-system-packages pytest pytest-cov pytest-qt pytest-qgis pytest-sugar factory-boy && python3 -m pytest tests/ -v --cov=mzs_tools --cov-report=term-missing --qgis_disable_gui" \
    '
```

> **Note**: The `--break-system-packages` flag is used when installing pip packages in the Docker containers. This is safe because the containers are ephemeral and destroyed after tests complete. Modern Debian/Ubuntu-based Docker images use PEP 668 to prevent pip from modifying the system Python environment.

### Environment Variables

The following environment variables affect test execution:

- `DISPLAY`: X11 display (default: `:99`)
- `QT_QPA_PLATFORM`: Qt platform abstraction (default: `offscreen` for headless)
- `QGIS_DISABLE_GUI`: Disable GUI in pytest-qgis (set to `1`)
- `QGIS_PREFIX_PATH`: QGIS installation prefix (default: `/usr`)
- `PYTHONPATH`: Python module search path

## Troubleshooting

### Test Failures in Specific QGIS Versions

If tests fail in a specific QGIS version:

1. Run the container interactively to debug:

   ```bash
   docker run -it --rm \
     -v $(pwd):/tests_directory \
     qgis/qgis:stable-noble bash
   ```

2. Inside the container, manually run tests:

   ```bash
   cd /tests_directory
   python3 -m pytest tests/ -v --qgis_disable_gui -k test_name
   ```

3. Check QGIS and Python versions:

   ```bash
   qgis --version
   python3 --version
   ```

## Windows environment with Docker

```bash
# Install, configure and run Windows using a Dockur container and virtual machine
# modify paths in the docker-compose file for the vm storage and ISO images as needed
cd docker
docker compose -f dockur-win11.yml up -d
# wait for the VM to boot (check logs with "docker compose -f dockur-win11.yml logs -f")
# use an RDP client to connect to the Windows VM

# after use, stop the VM
docker compose -f dockur-win11.yml down
```
