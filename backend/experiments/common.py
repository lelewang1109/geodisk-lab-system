from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from geodisk_paper.config import (dataset_config, ensure_output_dirs, experiment_config,
                                  geometry_config, resolve_project_path, seed_everything)
from geodisk_paper.data.adapters import DailyNetCDFAdapter
from geodisk_paper.data.regions import load_boundaries
from geodisk_paper.utils.io import read_json


def adapter_from_audit() -> DailyNetCDFAdapter:
    config = dataset_config()
    summary_path = ROOT / "results/data_audit/dataset_summary.json"
    if not summary_path.exists():
        raise FileNotFoundError("Run experiments/E0_data_audit.py before this stage")
    summary = read_json(summary_path)
    return DailyNetCDFAdapter(resolve_project_path(config["raw_dir"]), config["filename_glob"], summary["pm25_field"])


def project_boundaries():
    return load_boundaries(ROOT / "data/boundaries/selected_real_provinces.geojson")

