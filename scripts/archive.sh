#!/bin/bash
# Crea il pacchetto zip dal branch specificato in riga di comando (default: master) 
set -e

BRANCH=${1:-master}

if [ -n "$(git status --porcelain)" ]; then 
    echo "Commit all changes before creating archive!"
    exit 1
fi

git archive --prefix mzs-tools/ --format=zip -o mzs-tool-qgis3.zip $BRANCH

