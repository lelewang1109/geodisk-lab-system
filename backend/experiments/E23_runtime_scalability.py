from __future__ import annotations

import platform
import resource
import sys
import time

import numpy as np
import pandas as pd
import shapely

from common import ROOT, ensure_output_dirs, experiment_config, geometry_config, seed_everything
from geodisk_paper.data.regions import load_region_reference
from geodisk_paper.geometry.mappings import proposed_irregular
from geodisk_paper.topology.embedding import build_topology_embedding
from geodisk_paper.topology.power_refinement import refine_final_power_adjacency
from geodisk_paper.utils.io import write_csv, write_json


DATASETS = [
    ("NE-Admin0-Africa", ROOT / "data/processed/external_regions"),
    ("湖北", ROOT / "data/processed/regions"),
    ("NASA-Exoplanet-SkyGrid", ROOT / "data/processed/external_regions"),
    ("NCEP-AirTemp-Africa-2000", ROOT / "data/processed/external_regions"),
]


def _peak_rss_mb() -> float:
    """Return process high-water RSS including native NumPy/GEOS allocations."""
    value = float(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    return value / (1024.0 * 1024.0) if sys.platform == "darwin" else value / 1024.0


def main() -> None:
    ensure_output_dirs(); config = geometry_config(); experiment = experiment_config(); seed = seed_everything(); rows = []
    revision = config["method_revision"]; refinement = config["final_power_refinement"]
    formal = experiment["formal_evaluation"]
    warmups = int(formal["runtime_warmup_repetitions"])
    repetitions = int(formal["runtime_measured_repetitions"])
    for dataset, root in DATASETS:
        reference = load_region_reference(root, dataset)
        large = len(reference.cells) >= int(refinement["large_dataset_cell_threshold"])
        for repeat in range(warmups + repetitions):
            started = time.perf_counter()
            embedding = build_topology_embedding(
                reference, layer_count=int(revision["layer_count"]),
                optimize_passes=int(refinement["embedding_optimize_passes"]["other"]), seed=seed,
                weights=dict(revision["topology_weights"]), radial_constraint=True,
                search_mode="expanded_cross", candidate_budget=int(refinement["embedding_candidate_budget"]["other"]),
            )
            embedding_seconds = time.perf_counter() - started
            started = time.perf_counter()
            proposed_irregular(reference, embedding, "disk", iterations=3, warp_strength=0.0)
            original_seconds = time.perf_counter() - started
            started = time.perf_counter()
            refine_final_power_adjacency(
                reference, embedding, "disk", power_iterations=int(refinement["power_iterations_large"] if large else refinement["power_iterations_small"]),
                force_iterations=int(refinement["force_iterations_large"] if large else refinement["force_iterations_small"]),
                objective_weights=dict(refinement["objective_weights"]),
                candidate_schedule=list(refinement["candidate_schedule"]),
                contact_tolerance=float(refinement["contact_tolerance"]),
            )
            refined_seconds = time.perf_counter() - started
            if repeat >= warmups:
                rows.append({
                    "dataset": dataset, "cell_count": len(reference.cells), "reference_edge_count": len(reference.edges),
                    "repeat": repeat - warmups + 1, "embedding_seconds": embedding_seconds,
                    "original_power_seconds": original_seconds, "final_refinement_seconds": refined_seconds,
                    "refinement_over_original_ratio": refined_seconds / max(original_seconds, 1e-12),
                    "process_high_water_rss_mb": _peak_rss_mb(),
                })
            print("[runtime]", dataset, repeat + 1, "/", warmups + repetitions, flush=True)
    raw = pd.DataFrame(rows)
    write_csv(raw, ROOT / "results/tables/Table_runtime_scalability_raw.csv")
    metrics = ["embedding_seconds", "original_power_seconds", "final_refinement_seconds",
               "refinement_over_original_ratio", "process_high_water_rss_mb"]
    summary_rows = []
    for dataset, group in raw.groupby("dataset", sort=False):
        row = {"dataset": dataset, "cell_count": int(group.cell_count.iloc[0]),
               "reference_edge_count": int(group.reference_edge_count.iloc[0]), "repeat_count": len(group)}
        for metric in metrics:
            values = group[metric].to_numpy(float)
            row.update({f"{metric}_median": float(np.median(values)), f"{metric}_q1": float(np.quantile(values, .25)),
                        f"{metric}_q3": float(np.quantile(values, .75)), f"{metric}_mean": float(np.mean(values)),
                        f"{metric}_std": float(np.std(values, ddof=1)) if len(values) > 1 else 0.0})
        summary_rows.append(row)
    frame = pd.DataFrame(summary_rows)
    write_csv(frame, ROOT / "results/tables/Table_runtime_scalability.csv")
    write_csv(frame, ROOT / "paper/tables/Table_runtime_scalability.csv")
    write_json({
        "timing_scope": "single-process wall-clock seconds after a per-dataset warm-up",
        "memory_scope": "suite-process cumulative high-water RSS; includes native allocations and is an upper bound rather than an isolated per-method delta",
        "warmup_repetitions": warmups, "measured_repetitions": repetitions,
        "summary": "median, IQR, mean and sample standard deviation",
        "platform": platform.platform(), "processor": platform.processor(),
        "python": platform.python_version(), "numpy": np.__version__, "shapely": shapely.__version__,
    }, ROOT / "results/spatial_refined/runtime_environment.json")
    print(frame.to_string(index=False))


if __name__ == "__main__":
    main()
