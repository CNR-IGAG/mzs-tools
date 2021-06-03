#!/bin/bash
# Update project template package data/progetto_MS.zip
set -e

# keep track of the last executed command
trap 'last_command=$current_command; current_command=$BASH_COMMAND' DEBUG
# echo an error message before exiting
trap 'echo "\"${last_command}\" command failed with exit code $?."' EXIT

printf "\n\nExtracting template archive...\n"
printf "##############################\n\n"

# unzip old template archive
unzip -q -d ./data/ ./data/progetto_MS.zip

printf "OK"

printf "\n\nUpdating template code...\n"
printf "#########################\n\n"

# overwrite template archive content with new template_code
cp -rvu ./template_code/* ./data/progetto_MS/

printf "OK"

printf "\n\nCreating new template archive...\n"
printf "#################################\n\n"

rm ./data/progetto_MS.zip
pushd ./data/
zip -rq ./progetto_MS.zip ./progetto_MS/ -x '*.qgs~'
popd

printf "OK"

printf "\n\nCleanup...\n"
printf "###########\n\n"

rm -rf ./data/progetto_MS/

printf "OK"

trap : 0

exit 0
