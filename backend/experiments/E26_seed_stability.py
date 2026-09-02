from __future__ import annotations

import pandas as pd

from common import ROOT, ensure_output_dirs, experiment_config, geometry_config
from evaluation_helpers import evaluate_result
from geodisk_paper.data.regions import load_region_reference
from geodisk_paper.topology.embedding import build_topology_embedding
from geodisk_paper.topology.power_refinement import refine_final_power_adjacency
from geodisk_paper.utils.io import write_csv, write_json


def main() -> None:
    ensure_output_dirs(); geometry = geometry_config(); formal = experiment_config()["formal_evaluation"]
    refinement = geometry["final_power_refinement"]; revision = geometry["method_revision"]; rows: list[dict] = []
    seeds = [int(value) for value in formal["seed_stability_seeds"]]
    for region in formal["seed_stability_regions"]:
        reference = load_region_reference(ROOT / "data/processed/regions", region)
        for seed in seeds:
            embedding = build_topology_embedding(
                reference, layer_count=int(revision["layer_count"]),
                optimize_passes=int(refinement["embedding_optimize_passes"]["ceg"]), seed=seed,
                weights=dict(revision["topology_weights"]), radial_constraint=True,
                search_mode="expanded_cross", candidate_budget=int(refinement["embedding_candidate_budget"]["ceg"]),
            )
            for view in ("disk", "annulus"):
                result = refine_final_power_adjacency(
                    reference, embedding, view, inner=float(geometry["annulus_inner"]),
                    outer=float(geometry["annulus_outer"]), power_iterations=int(refinement["power_iterations_small"]),
                    force_iterations=int(refinement["force_iterations_small"]),
                    objective_weights=dict(refinement["objective_weights"]),
                    candidate_schedule=list(refinement["candidate_schedule"]),
                    contact_tolerance=float(refinement["contact_tolerance"]),
                )
                rows.append({"region": region, "seed": seed, "view": view, "cell_count": len(reference.cells),
                             "selected_candidate": result.metadata["selected_candidate"],
                             **evaluate_result(reference, result)})
        print("[seed stability]", region, len(seeds), "seeds", flush=True)
    frame = pd.DataFrame(rows)
    write_csv(frame, ROOT / "results/tables/Table_seed_stability.csv")
    per_seed = frame.groupby(["seed", "view"], as_index=False).agg(
        region_count=("region", "count"), adj_f1=("adj_f1", "mean"), np2=("np2", "mean"),
        local_direction_error_deg=("local_direction_error_deg", "mean"), area_cv=("area_cv", "mean"),
        invalid_polygon_count=("invalid_polygon_count", "sum"))
    write_csv(per_seed, ROOT / "paper/tables/Table_seed_stability_per_seed.csv")
    summary = per_seed.groupby("view", as_index=False).agg(
        seed_count=("seed", "count"), adj_f1_mean=("adj_f1", "mean"), adj_f1_std=("adj_f1", "std"),
        adj_f1_min=("adj_f1", "min"), adj_f1_max=("adj_f1", "max"), np2_mean=("np2", "mean"),
        np2_std=("np2", "std"), direction_error_mean=("local_direction_error_deg", "mean"),
        direction_error_std=("local_direction_error_deg", "std"), area_cv_mean=("area_cv", "mean"),
        invalid_polygon_count=("invalid_polygon_count", "sum"))
    write_csv(summary, ROOT / "paper/tables/Table_seed_stability_summary.csv")
    write_json({"seeds": seeds, "regions": list(formal["seed_stability_regions"]),
                "aggregation": "region means are computed within each seed; variability is reported across seeds"},
               ROOT / "results/spatial_refined/seed_stability_manifest.json")
    print(summary.to_string(index=False))


if __name__ == "__main__":
    main()
