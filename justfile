PLUGIN_SLUG:="mzs_tools"

# load environment variables from .env.uv file for uv commands
export UV_ENV_FILE:=".env.uv"

# default recipe to display help information
default:
  @just --list

# create venv with uv on linux, automatically detecting system python version and qgis path
create-venv:
    #!/bin/bash
    set -euo pipefail

    # Detect system Python version
    PYTHON_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
    echo "Detected system Python version: $PYTHON_VERSION"

    # Try to find QGIS Python libraries in common locations
    QGIS_PYTHON_LIB_PATH=""
    for path in "/usr/lib/python${PYTHON_VERSION}/site-packages" "/usr/share/qgis/python" "/usr/local/lib/python${PYTHON_VERSION}/site-packages"; do
        if [ -d "$path/qgis" ]; then
            QGIS_PYTHON_LIB_PATH="$path"
            echo "Found QGIS libraries at: $QGIS_PYTHON_LIB_PATH"
            break
        fi
    done

    if [ -z "$QGIS_PYTHON_LIB_PATH" ]; then
        echo "Warning: Could not find QGIS Python libraries. Using default path."
        QGIS_PYTHON_LIB_PATH="/usr/lib/python${PYTHON_VERSION}/site-packages"
    fi

    # Create virtual environment
    rm -rf .venv
    uv venv --system-site-packages --python "$PYTHON_VERSION"
    echo "$QGIS_PYTHON_LIB_PATH" > .venv/lib/python${PYTHON_VERSION}/site-packages/qgis.pth
    uv sync --all-groups
    uv run qgis-plugin-ci changelog latest

# create venv with manual python version and qgis path (for special cases)
create-venv-manual PYTHON_VERSION QGIS_PYTHON_LIB_PATH:
    rm -rf .venv
    uv venv --system-site-packages --python "{{ PYTHON_VERSION }}"
    echo "{{ QGIS_PYTHON_LIB_PATH }}" > .venv/lib/python{{ PYTHON_VERSION }}/site-packages/qgis.pth
    uv sync --all-groups
    uv run qgis-plugin-ci changelog latest

# create symbolic links for development
dev-link QGIS_PLUGIN_PATH="~/.local/share/QGIS/QGIS3/profiles/default/python/plugins" QGIS4_PLUGIN_PATH="~/.local/share/QGIS/QGIS4/profiles/default/python/plugins":
    #!/bin/bash
    # Ensure the target directory exists
    mkdir -p {{ QGIS_PLUGIN_PATH }}
    mkdir -p {{ QGIS4_PLUGIN_PATH }}
    rm -rf {{ QGIS_PLUGIN_PATH }}/{{ PLUGIN_SLUG }}
    rm -rf {{ QGIS4_PLUGIN_PATH }}/{{ PLUGIN_SLUG }}

    # Create a relative path symlink
    PLUGIN_SOURCE=$(pwd)/{{ PLUGIN_SLUG }}
    cd {{ QGIS_PLUGIN_PATH }}
    ln -sf $(python3 -c "import os; print(os.path.relpath('$PLUGIN_SOURCE', os.getcwd()))")

    cd {{ QGIS4_PLUGIN_PATH }}
    ln -sf $(python3 -c "import os; print(os.path.relpath('$PLUGIN_SOURCE', os.getcwd()))")

    cd -

    # Create symlinks for supporting files
    ln -sf $(pwd)/LICENSE $(pwd)/{{ PLUGIN_SLUG }}/LICENSE
    ln -sf $(pwd)/CREDITS.md $(pwd)/{{ PLUGIN_SLUG }}/CREDITS.md
    ln -sf $(pwd)/CHANGELOG.md $(pwd)/{{ PLUGIN_SLUG }}/CHANGELOG.md

    # Create symlink for Continue plugin rules
    mkdir -p $(pwd)/.continue/rules
    ln -sf $(pwd)/.github/copilot-instructions.md $(pwd)/.continue/rules/01-general.md

    # Show success message
    echo "Plugin symlink created at {{ QGIS_PLUGIN_PATH }}/{{ PLUGIN_SLUG }}"
    echo "Plugin symlink created at {{ QGIS4_PLUGIN_PATH }}/{{ PLUGIN_SLUG }}"

@bootstrap-dev: create-venv dev-link
    pre-commit install

@deps-update-check:
    uv sync --all-groups
    uv pip list --outdated

@deps-update:
    uv lock --upgrade

trans-update:
    uv run pylupdate5 ./{{ PLUGIN_SLUG }}/{{ PLUGIN_SLUG }}.pro

trans-compile:
    uv run lrelease ./{{ PLUGIN_SLUG }}/i18n/MzSTools_it.ts

docs-autobuild:
    uv sync --group docs
    uv run sphinx-autobuild -b html -c help/source help/source help/_build --port 8000

docs-build-html:
    uv sync --group docs
    uv run sphinx-build -b html -j auto -d help/_build/cache -q help/source help/_build/html

docs-build-pdf:
    #!/bin/bash
    set -e
    uv run sphinx-build -b latex -j auto -d help/_build/cache -q help/source help/_build/latex
    pushd help/_build/latex
    latexmk -pdf -dvi- -ps- -interaction=nonstopmode -halt-on-error MzSTools.tex
    popd

# Sync deps and run a quick check of the local QGIS test environment
test-check-env:
    uv sync --no-group ci
    uv sync --group testing
    uv run pytest -v tests/integration/test_qgis_env.py::test_qgis_environment

# Run all tests locally with pytest and coverage info, without GUI display
test TESTS_TO_RUN="tests": test-check-env
    uv run pytest --cov={{ PLUGIN_SLUG }} --cov-report=term-missing --qgis_disable_gui -rs -v {{ TESTS_TO_RUN }}

# Run all tests locally with pytest and coverage info, with GUI display
test-gui TESTS_TO_RUN="tests" GUI_TIMEOUT="2": test-check-env
    GUI_TIMEOUT={{ GUI_TIMEOUT }} uv run pytest --cov={{ PLUGIN_SLUG }} --cov-report=term-missing -rs -v {{ TESTS_TO_RUN }}

# Run tests with all QGIS versions using tox and Docker
test-tox-all:
    uv sync --group testing
    uv run tox -e all

# Run tests with QGIS latest using tox and Docker
test-tox-latest:
    uv sync --group testing
    uv run tox -e qgis-latest

# Run tests with QGIS stable using tox and Docker
test-tox-stable:
    uv sync --group testing
    uv run tox -e qgis-stable

# Run tests with QGIS LTR using tox and Docker
test-tox-ltr:
    uv sync --group testing
    uv run tox -e qgis-ltr

# Run tests with QGIS Qt6 using tox and Docker
test-tox-qt6:
    uv sync --group testing
    uv run tox -e qgis-qt6-ubuntu

# Run tests with QGIS Qt6 using tox and Docker
test-tox-qt6-gui GUI_TIMEOUT="2":
    uv sync --group testing
    uv run tox -e qgis-qt6-ubuntu-gui

@package VERSION:
    #!/bin/bash
    uv sync --group ci
    cp --remove-destination LICENSE {{ PLUGIN_SLUG }}/
    cp --remove-destination CHANGELOG.md {{ PLUGIN_SLUG }}/
    cp --remove-destination CREDITS.md {{ PLUGIN_SLUG }}/
    git add .
    uv run qgis-plugin-ci package -c {{ VERSION }}

    # change the directory name in the zip file to MzSTools for compatibility with older versions of the plugin
    mkdir temp
    unzip {{ PLUGIN_SLUG }}.*.zip -d temp
    mv temp/{{ PLUGIN_SLUG }} temp/MzSTools
    cd temp
    zip -r $(cd ../ && ls -1 {{ PLUGIN_SLUG }}.*.zip) MzSTools
    cp *.zip ../
    cd ..
    rm -rf temp
    mv "$(find . -name '{{ PLUGIN_SLUG }}.*.zip')" "$(find . -name '{{ PLUGIN_SLUG }}.*.zip' | sed 's/{{ PLUGIN_SLUG }}/MzSTools/')"

    just dev-link
    git add .

@release-test VERSION:
    #!/bin/bash
    uv sync --group ci
    cp --remove-destination LICENSE {{ PLUGIN_SLUG }}/
    cp --remove-destination CHANGELOG.md {{ PLUGIN_SLUG }}/
    cp --remove-destination CREDITS.md {{ PLUGIN_SLUG }}/
    # enforce DEBUG_MODE to False
    sed -i 's/DEBUG_MODE: bool = True/DEBUG_MODE: bool = False/g' {{ PLUGIN_SLUG }}/__about__.py
    # change main plugin directory name to MzSTools for compatibility with older versions of the plugin
    mv {{ PLUGIN_SLUG }} MzSTools
    # change plugin_path in pyproject.toml
    sed -i 's/plugin_path = "{{ PLUGIN_SLUG }}"/plugin_path = "MzSTools"/g' pyproject.toml
    git add .

    # run qgis-plugin-ci release without github token and osgeo auth
    uv run qgis-plugin-ci release -c {{ VERSION }}

    # revert changes
    mv MzSTools {{ PLUGIN_SLUG }}
    sed -i 's/plugin_path = "MzSTools"/plugin_path = "{{ PLUGIN_SLUG }}"/g' pyproject.toml
    just dev-link
    git add .

pull-docker-qgis VERSION="ltr":
    docker pull qgis/qgis:{{ VERSION }}

run-docker-qgis VERSION="ltr" QGIS_PYTHON_PATH=".local/share/QGIS/QGIS3/profiles/default/python":
    #!/bin/bash
    just pull-docker-qgis {{ VERSION }}
    xhost +local:
    mkdir -p ${HOME}/{{ QGIS_PYTHON_PATH }}/plugins
    docker run --rm --name qgis_master \
        -it \
        -e DISPLAY=$DISPLAY \
        -v /tmp/.X11-unix:/tmp/.X11-unix \
        -v ${HOME}/{{ QGIS_PYTHON_PATH }}/plugins:/home/quser/.local/share/QGIS/QGIS3/profiles/default/python/plugins \
        -v $(pwd)/{{ PLUGIN_SLUG }}:/home/quser/.local/share/QGIS/QGIS3/profiles/default/python/plugins/{{ PLUGIN_SLUG }} \
        -v ${HOME}:/home/host \
        -e HOME=/home/quser \
        -e LC_ALL=C.utf8 \
        -e LANG=C.utf8 \
        -e PYTHONPATH=/usr/share/qgis/python \
        --user ${USER_ID}:${GROUP_ID} \
        qgis/qgis:{{ VERSION }} bash -c "apt update && apt install -y --no-install-recommends default-jre && qgis"

# build docker image for QGIS 4 (latest)
# until an official docker image for QGIS 4 is available,
# this is using qgis/qgis3-ubuntu-qt6-build-deps-bin-only (Ubuntu 25.10)
# use VERSION="nightly" to build with latest QGIS master branch (4.1), or VERSION="latest" to build with latest QGIS 4.0 release
build-docker-qgis4 VERSION="latest":
    #!/bin/bash
    cd docker
    # use sed to replace line in Dockerfile URIs: https://qgis.org/ubuntu\n\ with URIs: https://qgis.org/ubuntu-nightly\n\ if VERSION is "nightly", to build with latest QGIS master branch (4.1)
    if [ "{{ VERSION }}" = "nightly" ]; then
        sed -i 's/URIs: https:\/\/qgis.org\/ubuntu/URIs: https:\/\/qgis.org\/ubuntu-nightly/g' qgis-qt6-ubuntu.dockerfile
    fi
    docker build -t qgis4-ubuntu:{{ VERSION }} -f ./qgis-qt6-ubuntu.dockerfile .
    # restore original Dockerfile if it was modified
    if [ "{{ VERSION }}" = "nightly" ]; then
        sed -i 's/URIs: https:\/\/qgis.org\/ubuntu-nightly/URIs: https:\/\/qgis.org\/ubuntu/g' qgis-qt6-ubuntu.dockerfile
    fi
    # git checkout -- docker/qgis-qt6-ubuntu.dockerfile

# start QGIS 4 version with docker on Linux, mounting plugin and host home directory for config and data persistence
# use VERSION="nightly" to run with latest QGIS master branch (4.1), or VERSION="latest" to run with latest QGIS release
run-docker-qgis4 VERSION="latest" QGIS_PYTHON_PATH=".local/share/QGIS/QGIS4/profiles/default/python":
    #!/bin/bash
    xhost +local:
    mkdir -p ${HOME}/{{ QGIS_PYTHON_PATH }}/plugins
    docker run --rm --name qgis_master \
        -it \
        -e DISPLAY=$DISPLAY \
        -v /tmp/.X11-unix:/tmp/.X11-unix \
        -v ${HOME}/{{ QGIS_PYTHON_PATH }}/plugins:/home/quser/.local/share/QGIS/QGIS4/profiles/default/python/plugins \
        -v $(pwd)/{{ PLUGIN_SLUG }}:/home/quser/.local/share/QGIS/QGIS4/profiles/default/python/plugins/{{ PLUGIN_SLUG }} \
        -v ${HOME}:/home/host \
        -e HOME=/home/quser \
        -e LC_ALL=C.utf8 \
        -e LANG=C.utf8 \
        -e PYTHONPATH=/usr/share/qgis/python \
        --user ${USER_ID}:${GROUP_ID} \
        qgis4-ubuntu:{{ VERSION }} qgis

# build docker image for QGIS 3.44 with Qt6 on Linux, compiling QGIS from source
# build-image-qgis-qt6-linux-build:
#     #!/bin/bash
#     cd docker
#     docker build -t qgis-qt6-linux:3_44 -f ./qgis-qt6-linux-build.dockerfile .

# build docker image for QGIS 3.44 with Qt6 on Linux, without compiling QGIS from source, for use with mounted QGIS build
# build-image-qgis-qt6-linux-deps-only:
#     #!/bin/bash
#     cd docker
#     docker build -t qgis-qt6-linux-deps-only:3_44 -f ./qgis-qt6-linux-deps-only.dockerfile .

# start QGIS 3.44 with Qt6 from docker image with compiled QGIS
# run-qgis-qt6-linux QGIS_PROFILE_PATH=".local/share/QGIS/QGIS3/profiles/default":
#     #!/bin/bash
#     xhost +local:
#     cd docker
#     docker run -it --rm \
#         -e DISPLAY=$DISPLAY \
#         -e LC_ALL=C.utf8 \
#         -e LANG=C.utf8 \
#         -v /tmp/.X11-unix:/tmp/.X11-unix \
#         -v ${HOME}/{{ QGIS_PROFILE_PATH }}:/home/quser/.local/share/QGIS/QGIS3/profiles/default \
#         -v ${HOME}/GIT/mzs-tools/mzs_tools:/home/quser/.local/share/QGIS/QGIS3/profiles/default/python/plugins/mzs_tools \
#         qgis-qt6-linux:3_44 \
#         ./QGIS/build/output/bin/qgis

# start QGIS 3.44 with Qt6 from docker image with mounted QGIS build directory
# run-qgis-qt6-linux-binmount QGIS_PROFILE_PATH=".local/share/QGIS/QGIS3/profiles/default":
#     #!/bin/bash
#     xhost +local:
#     cd docker
#     docker run -it --rm \
#         -e DISPLAY=$DISPLAY \
#         -e LC_ALL=C.utf8 \
#         -e LANG=C.utf8 \
#         -v /tmp/.X11-unix:/tmp/.X11-unix \
#         -v ${HOME}/QGIS:/home/quser/QGIS \
#         -v ${HOME}/{{ QGIS_PROFILE_PATH }}:/home/quser/.local/share/QGIS/QGIS3/profiles/default \
#         -v ${HOME}/GIT/mzs-tools/mzs_tools:/home/quser/.local/share/QGIS/QGIS3/profiles/default/python/plugins/mzs_tools \
#         -v ${HOME}/temp:/home/quser/temp \
#         qgis-qt6-linux-deps-only:3_44 \
#         ./QGIS/build/output/bin/qgis

# run-qgis-qt6-ubuntu-binmount QGIS_PROFILE_PATH=".local/share/QGIS/QGIS3/profiles/default":
#     #!/bin/bash
#     xhost +local:
#     cd docker
#     docker run -it --rm \
#         -e DISPLAY=$DISPLAY \
#         -e QT_X11_NO_MITSHM=1 \
#         --network host \
#         -e LC_ALL=C.utf8 \
#         -e LANG=C.utf8 \
#         -e QGIS_PREFIX_PATH=/home/quser/QGIS/build/output \
#         -v /tmp/.X11-unix:/tmp/.X11-unix:rw \
#         -v ${HOME}/{{ QGIS_PROFILE_PATH }}:/home/quser/.local/share/QGIS/QGIS3/profiles/default \
#         -v ${HOME}/GIT/mzs-tools/mzs_tools:/home/quser/.local/share/QGIS/QGIS3/profiles/default/python/plugins/mzs_tools \
#         -v ${HOME}/temp:/home/quser/temp \
#         qgis-qt6-ubuntu-build:master \
#         ./QGIS/build/output/bin/qgis

# run pyqt6 migration script: https://github.com/qgis/QGIS/wiki/Plugin-migration-to-be-compatible-with-Qt5-and-Qt6
# pyqt5-to-pyqt6:
#     #!/bin/bash
#     docker pull registry.gitlab.com/oslandia/qgis/pyqgis-4-checker/pyqgis-qt-checker:latest
#     docker run --rm -v "$(pwd):/home/pyqgisdev/" registry.gitlab.com/oslandia/qgis/pyqgis-4-checker/pyqgis-qt-checker:latest pyqt5_to_pyqt6.py --logfile /home/pyqgisdev/pyqt6_checker.log .
