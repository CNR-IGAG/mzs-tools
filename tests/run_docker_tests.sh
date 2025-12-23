#!/bin/bash
# Test runner script for running pytest inside QGIS Docker containers
# This script is designed to be executed inside a QGIS Docker container

set -e

# Default values
DISPLAY="${DISPLAY:-:99}"
QT_QPA_PLATFORM="${QT_QPA_PLATFORM:-offscreen}"
TEST_DIR="${TEST_DIR:-/tests_directory}"
PLUGIN_NAME="${PLUGIN_NAME:-mzs_tools}"

# Export environment variables
export DISPLAY
export QT_QPA_PLATFORM
export PYTHONPATH="${TEST_DIR}:${TEST_DIR}/${PLUGIN_NAME}:${PYTHONPATH:-}"
export QGIS_PREFIX_PATH="${QGIS_PREFIX_PATH:-/usr}"

# Print environment info
echo "========================================"
echo "QGIS Test Runner"
echo "========================================"
echo "QGIS Version: $(qgis --version 2>/dev/null || echo 'Unable to detect')"
echo "Python Version: $(python3 --version)"
echo "Display: ${DISPLAY}"
echo "Platform: ${QT_QPA_PLATFORM}"
echo "Test Directory: ${TEST_DIR}"
echo "Plugin Name: ${PLUGIN_NAME}"
echo "========================================"
echo ""

# Change to test directory
cd "${TEST_DIR}"

# Check if pytest is available, if not try to install it
if ! python3 -c "import pytest" 2>/dev/null; then
    echo "pytest not found, installing test dependencies..."
    python3 -m pip install --break-system-packages pytest pytest-cov pytest-qt pytest-qgis pytest-sugar factory-boy
fi

# Start Xvfb if needed and not already running (for non-offscreen testing)
if [ "${QT_QPA_PLATFORM}" != "offscreen" ] && ! pgrep -x "Xvfb" > /dev/null; then
    echo "Starting Xvfb on ${DISPLAY}..."
    Xvfb "${DISPLAY}" -screen 0 1024x768x24 -ac +extension GLX +render -noreset -nolisten tcp &
    XVFB_PID=$!
    sleep 2
    trap "kill ${XVFB_PID} 2>/dev/null || true" EXIT
fi

# Run tests with pytest
echo "Running tests..."
python3 -m pytest tests/ "$@"

# Capture exit code
TEST_EXIT_CODE=$?

echo ""
echo "========================================"
if [ ${TEST_EXIT_CODE} -eq 0 ]; then
    echo "Tests completed successfully!"
else
    echo "Tests failed with exit code: ${TEST_EXIT_CODE}"
fi
echo "========================================"

exit ${TEST_EXIT_CODE}
