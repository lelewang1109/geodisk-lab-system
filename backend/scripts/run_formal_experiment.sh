#!/usr/bin/env bash
set -euo pipefail
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"
export PYTHONPATH="$PROJECT_DIR/src"

bash scripts/run_spatial_experiment.sh
bash scripts/download_external_datasets.sh
python3 experiments/E10_prepare_external_datasets.py
python3 experiments/E11_external_spatial_geometry.py
python3 experiments/E12_external_spatial_fidelity.py
python3 experiments/E13_synthetic_stress.py
python3 experiments/E14_contact_tolerance.py
python3 experiments/E15_bootstrap_statistics.py
python3 experiments/E16_method_revision.py
python3 experiments/E18_reference_sensitivity.py
python3 experiments/E19_final_power_refinement.py
python3 experiments/E22_astronomy_generalization.py
python3 experiments/E17_advanced_spatial_errors.py
python3 experiments/E20_refined_statistics.py
python3 experiments/E24_refinement_ablation.py
python3 experiments/E23_runtime_scalability.py
python3 experiments/E5_temporal_delta.py
python3 experiments/E6_change_metrics.py
python3 experiments/E21_user_study_materials.py
python3 -m unittest discover -s tests -v
