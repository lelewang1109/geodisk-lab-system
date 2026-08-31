#!/usr/bin/env bash
set -euo pipefail
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"
export PYTHONPATH="$PROJECT_DIR/src"
python3 experiments/E0_data_audit.py
python3 experiments/E1_prepare_regions.py
python3 experiments/E2_baseline_geometry.py
python3 experiments/E3_geodisk_geoannulus.py
python3 experiments/E4_spatial_fidelity.py
python3 experiments/E7_ablation.py
python3 experiments/E8_sensitivity.py
python3 -m unittest discover -s tests -v

