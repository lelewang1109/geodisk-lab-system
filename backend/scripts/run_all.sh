#!/usr/bin/env bash
set -euo pipefail
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
bash "$PROJECT_DIR/scripts/run_formal_experiment.sh"
