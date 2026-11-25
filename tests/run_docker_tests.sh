#!/usr/bin/env bash
# Run the test suite inside an official qgis/qgis Docker image.
# Used by the Tester workflow, `just test-docker` and `just test-act`.
# Usage: tests/run_docker_tests.sh [extra pytest args...]
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OWNER="$(stat -c %u:%g "$REPO_DIR")"

# files created by root in the mounted repository are given back to the repository owner
restore_owner() {
    if [ "$(id -u)" = 0 ] && [ "$OWNER" != "0:0" ]; then
        find "$REPO_DIR" -path "$REPO_DIR/.git" -prune -o -path "$REPO_DIR/.venv" -prune -o -user 0 -exec chown -h "$OWNER" {} +
    fi
}
trap restore_owner EXIT

export QT_QPA_PLATFORM="${QT_QPA_PLATFORM:-offscreen}"
export QGIS_PREFIX_PATH="${QGIS_PREFIX_PATH:-/usr}"
export PYTHONPATH="/usr/share/qgis/python/plugins:/usr/share/qgis/python:$REPO_DIR"
export PYTHONDONTWRITEBYTECODE=1
export UV_PROJECT_ENVIRONMENT="${UV_PROJECT_ENVIRONMENT:-/tmp/mzs-tools-venv}"
export UV_LINK_MODE=copy

apt-get update -qq
DEBIAN_FRONTEND=noninteractive apt-get install -y -qq --no-install-recommends \
    default-jre-headless curl ca-certificates python3-venv
if ! command -v uv >/dev/null 2>&1; then
    curl -LsSf https://astral.sh/uv/install.sh | env UV_INSTALL_DIR=/usr/local/bin sh
fi

cd "$REPO_DIR"
qgis --version || true
python3 --version

uv venv "$UV_PROJECT_ENVIRONMENT" --clear --system-site-packages --python /usr/bin/python3
uv sync --locked --only-group testing
uv run --no-sync python -m pytest tests/ -v -rs --qgis_disable_gui -p no:cacheprovider \
    --basetemp=/tmp/mzs-tools-pytest "$@"
