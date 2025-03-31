# default recipe to display help information
default:
  @just --list

# create venv with uv on linux, assuming qgis is installed with libs in system python dist-packages and shared libraries in /usr/share/qgis/python
create-venv PYTHON_VERSION="3.12" QGIS_PYTHON_LIB_PATH="/usr/share/qgis/python":
    rm -rf .venv
    uv venv --system-site-packages --python "{{ PYTHON_VERSION }}"
    echo "{{ QGIS_PYTHON_LIB_PATH }}" > .venv/lib/python{{ PYTHON_VERSION }}/site-packages/qgis.pth
    uv sync --all-groups
    uv run qgis-plugin-ci changelog latest

# create symbolic links for development
dev-link QGIS_PLUGIN_PATH="/home/francesco/.local/share/QGIS/QGIS3/profiles/default/python/plugins":
    #!/bin/bash
    # Ensure the target directory exists
    mkdir -p {{ QGIS_PLUGIN_PATH }}
    rm -rf {{ QGIS_PLUGIN_PATH }}/mzs_tools
    
    # Create a relative path symlink
    PLUGIN_SOURCE=$(pwd)/mzs_tools
    cd {{ QGIS_PLUGIN_PATH }}
    ln -sf $(python3 -c "import os; print(os.path.relpath('$PLUGIN_SOURCE', os.getcwd()))")
    cd -
    
    # Create symlinks for supporting files
    ln -sf $(pwd)/LICENSE $(pwd)/mzs_tools/LICENSE
    ln -sf $(pwd)/CREDITS.md $(pwd)/mzs_tools/CREDITS.md
    ln -sf $(pwd)/CHANGELOG.md $(pwd)/mzs_tools/CHANGELOG.md
    
    # Show success message
    echo "Plugin symlink created at {{ QGIS_PLUGIN_PATH }}/mzs_tools"

@bootstrap-dev: create-venv dev-link

@update-deps:
    uv lock --upgrade

trans-update:
    uv run pylupdate5 ./mzs_tools/mzs_tools.pro

trans-compile:
    uv run lrelease ./mzs_tools/i18n/MzSTools_it.ts

build-docs-html:
    uv run sphinx-build -b html -j auto -d help/_build/cache -q help/source help/_build/html

build-docs-pdf:
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
    uv run pytest -v --cov=mzs_tools --cov-report=term-missing

@package VERSION:
    #!/bin/bash
    uv sync --group ci
    cp --remove-destination LICENSE mzs_tools/
    cp --remove-destination CHANGELOG.md mzs_tools/
    cp --remove-destination CREDITS.md mzs_tools/
    git add .
    uv run qgis-plugin-ci package -c {{ VERSION }}

    # change the directory name in the zip file to MzSTools for compatibility with older versions of the plugin
    mkdir temp
    unzip mzs_tools.*.zip -d temp
    mv temp/mzs_tools temp/MzSTools
    cd temp
    zip -r $(cd ../ && ls -1 mzs_tools.*.zip) MzSTools
    cp *.zip ../
    cd ..
    rm -rf temp
    mv "$(find . -name 'mzs_tools.*.zip')" "$(find . -name 'mzs_tools.*.zip' | sed 's/mzs_tools/MzSTools/')"

    just dev-link
    git add .

@release-test VERSION:
    #!/bin/bash
    uv sync --group ci
    cp --remove-destination LICENSE mzs_tools/
    cp --remove-destination CHANGELOG.md mzs_tools/
    cp --remove-destination CREDITS.md mzs_tools/
    # enforce DEBUG_MODE to False
    sed -i 's/DEBUG_MODE: bool = True/DEBUG_MODE: bool = False/g' mzs_tools/__about__.py
    # change main plugin directory name to MzSTools for compatibility with older versions of the plugin
    mv mzs_tools MzSTools
    # change plugin_path in pyproject.toml
    sed -i 's/plugin_path = "mzs_tools"/plugin_path = "MzSTools"/g' pyproject.toml
    git add .

    # run qgis-plugin-ci release without github token and osgeo auth
    uv run qgis-plugin-ci release -c {{ VERSION }}

    # revert changes
    mv MzSTools mzs_tools
    sed -i 's/plugin_path = "MzSTools"/plugin_path = "mzs_tools"/g' pyproject.toml
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
        -v $(pwd)/mzs_tools:/home/qgis/.local/share/QGIS/QGIS3/profiles/default/python/plugins/mzs_tools \
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
    docker run --rm -v "$(pwd):/home/pyqgisdev/" registry.gitlab.com/oslandia/qgis/pyqgis-4-checker/pyqgis-qt-checker:latest pyqt5_to_pyqt6.py --logfile /home/pyqgisdev/pyqt6_checker.log .