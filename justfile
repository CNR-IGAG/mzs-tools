# default recipe to display help information
default:
  @just --list

# create venv with uv on linux, assuming qgis is installed with libs in system python dist-packages and shared libraries in /usr/share/qgis/python
create-venv PYTHON_VERSION="3.12" QGIS_PYTHON_LIB_PATH="/usr/share/qgis/python":
    rm -rf .venv
    uv venv --system-site-packages --python ">={{ PYTHON_VERSION }}"
    echo "{{ QGIS_PYTHON_LIB_PATH }}" > .venv/lib/python{{ PYTHON_VERSION }}/site-packages/qgis.pth
    uv sync --all-groups
    uv run qgis-plugin-ci changelog latest

# create symbolic links for development
dev-link QGIS_PLUGIN_PATH="/home/francesco/.local/share/QGIS/QGIS3/profiles/default/python/plugins":
    ln -sf $(pwd)/mzs_tools/ {{ QGIS_PLUGIN_PATH }}/
    ln -sf $(pwd)/LICENSE $(pwd)/mzs_tools/LICENSE
    ln -sf $(pwd)/CREDITS.md $(pwd)/mzs_tools/CREDITS.md
    ln -sf $(pwd)/CHANGELOG.md $(pwd)/mzs_tools/CHANGELOG.md

@bootstrap-dev: create-venv dev-link

@update-deps:
    uv lock --upgrade

trans-update:
    uv run pylupdate5 ./mzs_tools/mzs_tools.pro

trans-compile:
    uv run lrelease ./mzs_tools/i18n/MzSTools_it.ts

# Update project template package data/progetto_MS.zip
update-project-template:
    #!/bin/bash
    set -e

    # keep track of the last executed command
    trap 'last_command=$current_command; current_command=$BASH_COMMAND' DEBUG
    # echo an error message before exiting
    trap 'echo "\"${last_command}\" command failed with exit code $?."' EXIT

    printf "\n\nExtracting template archive...\n"
    printf "##############################\n\n"

    # unzip old template archive
    unzip -q -d ./mzs_tools/data/ ./mzs_tools/data/progetto_MS.zip

    printf "OK\n\nUpdating template code...\n"
    printf "#########################\n\n"

    # overwrite template archive content with new template_code
    cp -rvu ./template_code/* ./mzs_tools/data/progetto_MS/

    printf "OK\n\nCreating new template archive...\n"
    printf "#################################\n\n"

    rm ./mzs_tools/data/progetto_MS.zip
    pushd ./mzs_tools/data/
    zip -rq ./progetto_MS.zip ./progetto_MS/ -x '*.qgs~'
    popd

    printf "OK\n\nCleanup...\n"
    printf "###########\n\n"

    rm -rf ./mzs_tools/data/progetto_MS/

    printf "OK"

    trap : 0
    exit 0

# Run tests with pytest and coverage info
test:
    uv sync --no-group ci
    uv sync --group testing
    uv run pytest -v --cov=mzs_tools --cov-report=term-missing

@package VERSION:
    uv sync --group ci
    cp --remove-destination LICENSE mzs_tools/
    cp --remove-destination CHANGELOG.md mzs_tools/
    cp --remove-destination CREDITS.md mzs_tools/
    git add .
    uv run qgis-plugin-ci package -c {{ VERSION }}
    just dev-link
    git add .