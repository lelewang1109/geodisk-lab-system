from __future__ import annotations

from pathlib import Path

import pandas as pd

from common import ROOT, ensure_output_dirs, geometry_config, seed_everything
from evaluation_helpers import evaluate_result
from geodisk_paper.data.regions import load_region_reference
from geodisk_paper.geometry.serialization import save_geometry
from geodisk_paper.topology.embedding import build_topology_embedding
from geodisk_paper.topology.power_refinement import refine_final_power_adjacency
from geodisk_paper.utils.io import write_csv, write_json


def _run_dataset(dataset: str, reference_root: Path, output_root: Path, family: str, config: dict,
                 seed: int, rows: list[dict]) -> None:
    reference = load_region_reference(reference_root, dataset)
    revision = config["method_revision"]
    refinement = config["final_power_refinement"]
    embedding_group = "ceg" if family == "ceg" else "other"
    layer_count = int(revision["layer_count"] if family != "synthetic" else config["synthetic"]["layer_count"])
    embedding = build_topology_embedding(
        reference, layer_count=layer_count,
        optimize_passes=int(refinement["embedding_optimize_passes"][embedding_group]),
        seed=seed, weights=dict(revision["topology_weights"]), radial_constraint=True,
        search_mode="expanded_cross", candidate_budget=int(refinement["embedding_candidate_budget"][embedding_group]),
    )
    large = len(reference.cells) >= int(refinement["large_dataset_cell_threshold"])
    power_iterations = int(refinement["power_iterations_large"] if large else refinement["power_iterations_small"])
    force_iterations = int(refinement["force_iterations_large"] if large else refinement["force_iterations_small"])
    inner, outer = float(config["annulus_inner"]), float(config["annulus_outer"])
    for view in ("disk", "annulus"):
        result = refine_final_power_adjacency(
            reference, embedding, view, inner=inner, outer=outer,
            power_iterations=power_iterations, force_iterations=force_iterations,
            objective_weights=dict(refinement["objective_weights"]),
            candidate_schedule=list(refinement["candidate_schedule"]),
            contact_tolerance=float(refinement["contact_tolerance"]),
        )
        path = output_root / dataset / f"final_refined_{view}.geojson"
        save_geometry(result, path)
        scores = evaluate_result(reference, result)
        rows.append({
            "dataset": dataset, "dataset_family": family, "method": result.method, "view": view,
            "cell_count": len(reference.cells),
            "slot_objective_initial": embedding.initial_objective,
            "slot_objective_final": embedding.final_objective,
            "final_power_objective_initial": result.metadata["initial_final_power_objective"],
            "final_power_objective_optimized": result.metadata["optimized_final_power_objective"],
            "final_power_f1_before_refinement": result.metadata["initial_final_power_adj_f1"],
            "selected_candidate": result.metadata["selected_candidate"],
            **scores,
        })
    print("[final power refinement]", family, dataset, flush=True)


def main() -> None:
    ensure_output_dirs(); config = geometry_config(); seed = seed_everything(); rows: list[dict] = []
    for region in config["regions"]:
        _run_dataset(region, ROOT / "data/processed/regions", ROOT / "results/spatial_refined",
                     "ceg", config, seed, rows)
    for dataset in ("NE-Admin0-Africa", "NCEP-AirTemp-Africa-2000"):
        _run_dataset(dataset, ROOT / "data/processed/external_regions", ROOT / "results/external_refined",
                     "external", config, seed, rows)
    synthetic_root = ROOT / "data/processed/synthetic_regions"
    for directory in sorted(path for path in synthetic_root.iterdir() if path.is_dir() and path.name.startswith("Synthetic-")):
        _run_dataset(directory.name, synthetic_root, ROOT / "results/synthetic_refined",
                     "synthetic", config, seed, rows)
    frame = pd.DataFrame(rows)
    write_csv(frame, ROOT / "results/tables/Table_final_power_refinement.csv")
    write_csv(frame, ROOT / "paper/tables/Table_final_power_refinement.csv")
    summary = frame.groupby(["dataset_family", "method", "view"], as_index=False).agg(
        dataset_count=("dataset", "count"),
        before_adj_f1=("final_power_f1_before_refinement", "mean"),
        refined_adj_f1=("adj_f1", "mean"), np2=("np2", "mean"),
        local_direction_error_deg=("local_direction_error_deg", "mean"),
        radial_spearman=("radial_spearman", "mean"), area_cv=("area_cv", "mean"),
        invalid_polygon_count=("invalid_polygon_count", "sum"),
    )
    write_csv(summary, ROOT / "paper/tables/Table_final_power_refinement_summary.csv")
    write_json({
        "optimization_target": "adjacency and neighborhood recomputed from every final balanced Power partition",
        "candidate_policy": ["topology", "harmonic", "geographic", "two fixed 50/50 blends", "deterministic topology force iterations"],
        "selection_policy": "same deterministic multi-start schedule for every dataset; no dataset-specific hand tuning",
        "objective_weights": dict(config["final_power_refinement"]["objective_weights"]),
        "contact_tolerance": float(config["final_power_refinement"]["contact_tolerance"]),
        "embedding_optimize_passes": dict(config["final_power_refinement"]["embedding_optimize_passes"]),
        "embedding_candidate_budget": dict(config["final_power_refinement"]["embedding_candidate_budget"]),
        "seed": seed,
    }, ROOT / "results/spatial_refined/refinement_manifest.json")
    print(summary.to_string(index=False))


if __name__ == "__main__":
    main()
