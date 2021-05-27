#!/bin/bash
# Crea il pacchetto zip dal branch specificato in riga di comando (default: master) 

BRANCH=${1:-master}

git archive --prefix mzs-tools/ --format=zip -o mzs-tool-qgis3.zip $BRANCH

