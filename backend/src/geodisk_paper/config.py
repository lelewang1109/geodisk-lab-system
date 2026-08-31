from __future__ import annotations

from pathlib import Path
import random
import numpy as np
import yaml

ROOT = Path(__file__).resolve().parents[2]


def load_yaml(name: str) -> dict:
    path = ROOT / "config" / name
    with path.open(encoding="utf-8") as stream:
        value = yaml.safe_load(stream)
    if not isinstance(value, dict):
        raise ValueError(f"Configuration must be a mapping: {path}")
    return value


def dataset_config() -> dict:
    return load_yaml("datasets.yaml")["dataset"]


def geometry_config() -> dict:
    return load_yaml("geometry.yaml")


def experiment_config() -> dict:
    return load_yaml("experiment.yaml")


def resolve_project_path(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else (ROOT / path).resolve()


def seed_everything() -> int:
    seed = int(experiment_config()["seed"])
    random.seed(seed)
    np.random.seed(seed)
    return seed


def ensure_output_dirs() -> None:
    for relative in (
        "results/data_audit", "results/spatial", "results/ablation",
        "results/sensitivity", "results/tables", "results/figures",
        "results/cache", "paper/figures", "paper/tables", "data/processed",
        "data/metadata",
    ):
        (ROOT / relative).mkdir(parents=True, exist_ok=True)

