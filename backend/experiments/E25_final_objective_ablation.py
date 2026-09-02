from __future__ import annotations

import pandas as pd

from common import ROOT, ensure_output_dirs, experiment_config, geometry_config, seed_everything
from evaluation_helpers import evaluate_result
from geodisk_paper.data.regions import load_region_reference
from geodisk_paper.topology.embedding import build_topology_embedding
from geodisk_paper.topology.power_refinement import refine_final_power_adjacency
from geodisk_paper.utils.io import write_csv, write_json


REMOVED_TERMS = {
    "Full objective": None,
    "No NP@2": "neighborhood",
    "No local direction": "local_direction",
    "No angular": "angular",
    "No radial": "radial",
    "No area CV": "area_cv",
}


def main() -> None:
    ensure_output_dirs(); geometry = geometry_config(); experiment = experiment_config(); seed = seed_everything()
    formal = experiment["formal_evaluation"]; refinement = geometry["final_power_refinement"]
    revision = geometry["method_revision"]; rows: list[dict] = []
    for region in formal["objective_ablation_regions"]:
        reference = load_region_reference(ROOT / "data/processed/regions", region)
        embedding = build_topology_embedding(
            reference, layer_count=int(revision["layer_count"]),
            optimize_passes=int(refinement["embedding_optimize_passes"]["ceg"]), seed=seed,
            weights=dict(revision["topology_weights"]), radial_constraint=True,
            search_mode="expanded_cross", candidate_budget=int(refinement["embedding_candidate_budget"]["ceg"]),
        )
        for variant, removed in REMOVED_TERMS.items():
            weights = dict(refinement["objective_weights"])
            if removed is not None:
                weights[removed] = 0.0
            for view in ("disk", "annulus"):
                result = refine_final_power_adjacency(
                    reference, embedding, view, inner=float(geometry["annulus_inner"]),
                    outer=float(geometry["annulus_outer"]),
                    power_iterations=int(refinement["power_iterations_small"]),
                    force_iterations=int(refinement["force_iterations_small"]), objective_weights=weights,
                    candidate_schedule=list(refinement["candidate_schedule"]),
                    contact_tolerance=float(refinement["contact_tolerance"]),
                )
                rows.append({
                    "region": region, "variant": variant, "removed_objective_term": removed or "none",
                    "view": view, "seed": seed, "cell_count": len(reference.cells),
                    "selected_candidate": result.metadata["selected_candidate"],
                    **evaluate_result(reference, result),
                })
        print("[final objective ablation]", region, flush=True)
    frame = pd.DataFrame(rows)
    write_csv(frame, ROOT / "results/tables/Table_final_objective_ablation.csv")
    summary = frame.groupby(["variant", "removed_objective_term", "view"], as_index=False).agg(
        region_count=("region", "count"), adj_f1=("adj_f1", "mean"), np2=("np2", "mean"),
        local_direction_error_deg=("local_direction_error_deg", "mean"), angular_error_deg=("angular_error_deg", "mean"),
        radial_spearman=("radial_spearman", "mean"), area_cv=("area_cv", "mean"),
        invalid_polygon_count=("invalid_polygon_count", "sum"),
    )
    write_csv(summary, ROOT / "paper/tables/Table_final_objective_ablation.csv")
    write_json({
        "regions": list(formal["objective_ablation_regions"]), "seed": seed,
        "policy": "leave one final-Power objective term at zero; all schedules and budgets remain fixed",
        "variants": REMOVED_TERMS,
        "guardrail": "objectives differ across variants; compare external metric columns, not raw objective values",
    }, ROOT / "results/spatial_refined/final_objective_ablation_manifest.json")
    print(summary.to_string(index=False))


if __name__ == "__main__":
    main()
