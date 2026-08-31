#!/usr/bin/env bash
set -euo pipefail
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"
export PYTHONPATH="$PROJECT_DIR/src"

python3 experiments/E5_temporal_delta.py
python3 experiments/E6_change_metrics.py
python3 experiments/E21_user_study_materials.py
