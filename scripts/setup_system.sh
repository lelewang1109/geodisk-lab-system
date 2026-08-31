#!/usr/bin/env bash
set -euo pipefail

SYSTEM_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

python3 -m venv "$SYSTEM_DIR/backend/.venv"
"$SYSTEM_DIR/backend/.venv/bin/python" -m pip install --upgrade pip
"$SYSTEM_DIR/backend/.venv/bin/python" -m pip install -r "$SYSTEM_DIR/backend/requirements.txt"
npm --prefix "$SYSTEM_DIR/frontend" install

echo "Setup complete. Start with: bash scripts/start_system.sh"

