#!/usr/bin/env bash
set -euo pipefail

SYSTEM_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_PYTHON="${GEODISK_PYTHON:-python3}"

cd "$SYSTEM_DIR/backend"
PYTHONPATH=src "$BACKEND_PYTHON" -m unittest discover -s tests -v

cd "$SYSTEM_DIR/frontend"
npm run lint
npm run build

echo "GeoDisk Lab verification complete."
