PLUGIN_SLUG:="mzs_tools"

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
dev-link QGIS_PLUGIN_PATH="~/.local/share/QGIS/QGIS3/profiles/default/python/plugins":
    #!/bin/bash
    # Ensure the target directory exists
    mkdir -p {{ QGIS_PLUGIN_PATH }}
    rm -rf {{ QGIS_PLUGIN_PATH }}/{{ PLUGIN_SLUG }}

    # Create a relative path symlink
    PLUGIN_SOURCE=$(pwd)/{{ PLUGIN_SLUG }}
    cd {{ QGIS_PLUGIN_PATH }}
    ln -sf $(python3 -c "import os; print(os.path.relpath('$PLUGIN_SOURCE', os.getcwd()))")
    cd -

    # Create symlinks for supporting files
    ln -sf $(pwd)/LICENSE $(pwd)/{{ PLUGIN_SLUG }}/LICENSE
    ln -sf $(pwd)/CREDITS.md $(pwd)/{{ PLUGIN_SLUG }}/CREDITS.md
    ln -sf $(pwd)/CHANGELOG.md $(pwd)/{{ PLUGIN_SLUG }}/CHANGELOG.md

    # Show success message
    echo "Plugin symlink created at {{ QGIS_PLUGIN_PATH }}/{{ PLUGIN_SLUG }}"

@bootstrap-dev: create-venv dev-link

@update-deps:
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

# Run tests with pytest and coverage info
test:
    uv sync --no-group ci
    uv sync --group testing
    uv run pytest -v --cov={{ PLUGIN_SLUG }} --cov-report=term-missing

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

qgis-ltr-pull:
    docker pull qgis/qgis:ltr

# start latest QGIS LTR version with docker on Linux
qgis-docker VERSION="ltr" QGIS_PYTHON_PATH=".local/share/QGIS/QGIS3/profiles/default/python":
    #!/bin/bash
    # Allow local X server connections
    xhost +local:

    # Define paths and variables
    USER_ID=$(id -u)
    GROUP_ID=$(id -g)

    # Create necessary directories with correct permissions
    TEMP_DIR=$(mktemp -d)
    mkdir -p ${TEMP_DIR}/certificates
    mkdir -p ${TEMP_DIR}/qgis_config/{processing,profile,cache,data/expressions}
    mkdir -p ${TEMP_DIR}/qgis_config/python/expressions

    # Copy and set permissions for certificates
    cp -L /etc/ssl/certs/ca-certificates.crt ${TEMP_DIR}/certificates/
    chmod 644 ${TEMP_DIR}/certificates/ca-certificates.crt

    # Set permissions for QGIS config directories
    chmod -R 777 ${TEMP_DIR}/qgis_config

    # Create an empty qgis.db file that QGIS can write to
    touch ${TEMP_DIR}/qgis_config/data/qgis.db
    chmod 666 ${TEMP_DIR}/qgis_config/data/qgis.db

    # Ensure plugin directory exists in host
    mkdir -p ${HOME}/{{ QGIS_PYTHON_PATH }}/plugins

    # Run QGIS in container with proper mounts and environment
    docker run --rm --name qgis_ltr \
        -it \
        -e DISPLAY=unix$DISPLAY \
        -v /tmp/.X11-unix:/tmp/.X11-unix \
        -v ${HOME}/{{ QGIS_PYTHON_PATH }}/plugins:/home/qgis/.local/share/QGIS/QGIS3/profiles/default/python/plugins \
        -v $(pwd)/{{ PLUGIN_SLUG }}:/home/qgis/.local/share/QGIS/QGIS3/profiles/default/python/plugins/{{ PLUGIN_SLUG }} \
        -v ${HOME}:/home/host \
        -v ${TEMP_DIR}/certificates:/etc/ssl/certs:ro \
        -v ${TEMP_DIR}/qgis_config/processing:/home/qgis/.local/share/QGIS/QGIS3/profiles/default/processing \
        -v ${TEMP_DIR}/qgis_config/profile:/home/qgis/.config/QGIS \
        -v ${TEMP_DIR}/qgis_config/cache:/home/qgis/.cache/QGIS \
        -v ${TEMP_DIR}/qgis_config/data:/home/qgis/.local/share/QGIS/QGIS3/profiles/default \
        -v ${TEMP_DIR}/qgis_config/python/expressions:/home/qgis/.local/share/QGIS/QGIS3/profiles/default/python/expressions \
        -e HOME=/home/qgis \
        -e QT_X11_NO_MITSHM=1 \
        -e SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt \
        -e PYTHONHOME= \
        --user ${USER_ID}:${GROUP_ID} \
        qgis/qgis:{{ VERSION }} qgis

    # Clean up temporary directory
    rm -rf ${TEMP_DIR}

# run pyqt6 migration script: https://github.com/qgis/QGIS/wiki/Plugin-migration-to-be-compatible-with-Qt5-and-Qt6
pyqt5-to-pyqt6:
    #!/bin/bash
    docker pull registry.gitlab.com/oslandia/qgis/pyqgis-4-checker/pyqgis-qt-checker:latest
    docker run --rm -v "$(pwd):/home/pyqgisdev/" registry.gitlab.com/oslandia/qgis/pyqgis-4-checker/pyqgis-qt-checker:latest pyqt5_to_pyqt6.py --logfile /home/pyqgisdev/pyqt6_checker.log .

# build docker image for QGIS 3.44 with Qt6 on Linux, compiling QGIS from source
build-image-qgis-qt6-linux-build:
    #!/bin/bash
    cd docker
    docker build -t qgis-qt6-linux:3_44 -f ./qgis-qt6-linux-build.dockerfile .

# build docker image for QGIS 3.44 with Qt6 on Linux, without compiling QGIS from source, for use with mounted QGIS build
build-image-qgis-qt6-linux-deps-only:
    #!/bin/bash
    cd docker
    docker build -t qgis-qt6-linux-deps-only:3_44 -f ./qgis-qt6-linux-deps-only.dockerfile .

# start QGIS 3.44 with Qt6 from docker image with compiled QGIS
run-qgis-qt6-linux QGIS_PROFILE_PATH=".local/share/QGIS/QGIS3/profiles/default":
    #!/bin/bash
    xhost +local:
    cd docker
    docker run -it --rm \
        -e DISPLAY=$DISPLAY \
        -e LC_ALL=C.utf8 \
        -e LANG=C.utf8 \
        -v /tmp/.X11-unix:/tmp/.X11-unix \
        -v ${HOME}/{{ QGIS_PROFILE_PATH }}:/home/quser/.local/share/QGIS/QGIS3/profiles/default \
        -v ${HOME}/GIT/mzs-tools/mzs_tools:/home/quser/.local/share/QGIS/QGIS3/profiles/default/python/plugins/mzs_tools \
        qgis-qt6-linux:3_44 \
        ./QGIS/build/output/bin/qgis

# start QGIS 3.44 with Qt6 from docker image with mounted QGIS build directory
run-qgis-qt6-linux-binmount QGIS_PROFILE_PATH=".local/share/QGIS/QGIS3/profiles/default":
    #!/bin/bash
    xhost +local:
    cd docker
    docker run -it --rm \
        -e DISPLAY=$DISPLAY \
        -e LC_ALL=C.utf8 \
        -e LANG=C.utf8 \
        -v /tmp/.X11-unix:/tmp/.X11-unix \
        -v ${HOME}/QGIS:/home/quser/QGIS \
        -v ${HOME}/{{ QGIS_PROFILE_PATH }}:/home/quser/.local/share/QGIS/QGIS3/profiles/default \
        -v ${HOME}/GIT/mzs-tools/mzs_tools:/home/quser/.local/share/QGIS/QGIS3/profiles/default/python/plugins/mzs_tools \
        -v ${HOME}/temp:/home/quser/temp \
        qgis-qt6-linux-deps-only:3_44 \
        ./QGIS/build/output/bin/qgis
