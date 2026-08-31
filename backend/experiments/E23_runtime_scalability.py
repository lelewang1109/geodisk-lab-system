from __future__ import annotations

import platform
import time

import numpy as np
import pandas as pd
import shapely

from common import ROOT, ensure_output_dirs, geometry_config, seed_everything
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


def main() -> None:
    ensure_output_dirs(); config = geometry_config(); seed = seed_everything(); rows = []
    revision = config["method_revision"]; refinement = config["final_power_refinement"]
    for dataset, root in DATASETS:
        reference = load_region_reference(root, dataset)
        started = time.perf_counter()
        embedding = build_topology_embedding(
            reference, layer_count=int(revision["layer_count"]), optimize_passes=3, seed=seed,
            weights=dict(revision["topology_weights"]), radial_constraint=True,
            search_mode="expanded_cross", candidate_budget=120,
        )
        embedding_seconds = time.perf_counter() - started
        started = time.perf_counter()
        proposed_irregular(reference, embedding, "disk", iterations=3, warp_strength=0.0)
        original_seconds = time.perf_counter() - started
        large = len(reference.cells) >= int(refinement["large_dataset_cell_threshold"])
        started = time.perf_counter()
        refine_final_power_adjacency(
            reference, embedding, "disk", power_iterations=int(refinement["power_iterations_large"] if large else refinement["power_iterations_small"]),
            force_iterations=int(refinement["force_iterations_large"] if large else refinement["force_iterations_small"]),
            objective_weights=dict(refinement["objective_weights"]),
        )
        refined_seconds = time.perf_counter() - started
        rows.append({
            "dataset": dataset, "cell_count": len(reference.cells), "reference_edge_count": len(reference.edges),
            "embedding_seconds": embedding_seconds, "original_power_seconds": original_seconds,
            "final_refinement_seconds": refined_seconds,
            "refinement_over_original_ratio": refined_seconds / max(original_seconds, 1e-12),
            "repeat_count": 1,
        })
        print("[runtime]", dataset, rows[-1], flush=True)
    frame = pd.DataFrame(rows)
    write_csv(frame, ROOT / "results/tables/Table_runtime_scalability.csv")
    write_csv(frame, ROOT / "paper/tables/Table_runtime_scalability.csv")
    write_json({
        "timing_scope": "single-process wall-clock seconds; one run per predeclared dataset size",
        "warning": "Use as an order-of-magnitude scalability report, not a confidence interval.",
        "platform": platform.platform(), "processor": platform.processor(),
        "python": platform.python_version(), "numpy": np.__version__, "shapely": shapely.__version__,
    }, ROOT / "results/spatial_refined/runtime_environment.json")
    print(frame.to_string(index=False))


if __name__ == "__main__":
    main()
