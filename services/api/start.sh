#!/bin/bash
# CoachByte API Service Start Script
# Receives port as first argument from supervisor

PORT=$1

if [ -z "$PORT" ]; then
    echo "[ERROR] Port not provided"
    exit 1
fi

# Get the directory where this script is located
SERVICE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SERVICE_DIR/../../../.." && pwd)"

# Ensure we're using the virtualenv Python
PYTHON_BIN="$REPO_ROOT/.venv/bin/python3"

if [ ! -f "$PYTHON_BIN" ]; then
    echo "[ERROR] Python virtualenv not found at $PYTHON_BIN"
    exit 1
fi

# Run the server
exec "$PYTHON_BIN" "$SERVICE_DIR/server.py" --host 127.0.0.1 --port "$PORT"
