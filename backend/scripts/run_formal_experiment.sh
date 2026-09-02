#!/usr/bin/env bash
set -euo pipefail
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"
export PYTHONPATH="$PROJECT_DIR/src"
exec python3 scripts/run_formal_pipeline.py "$@"
