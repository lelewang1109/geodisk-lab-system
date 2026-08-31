from __future__ import annotations

import pandas as pd

from common import ROOT, geometry_config, seed_everything
from evaluation_helpers import evaluate_result
from geodisk_paper.data.regions import load_region_reference
from geodisk_paper.geometry.mappings import proposed_irregular
from geodisk_paper.topology.embedding import build_topology_embedding
from geodisk_paper.utils.io import write_csv


REGIONS = ["湖北", "湖南", "江西", "广东", "福建", "广西", "安徽", "浙江"]


def main():
    config = geometry_config(); revision = config["method_revision"]; seed = seed_everything()
    inner, outer = float(config["annulus_inner"]), float(config["annulus_outer"])
    rows = []
    for region in REGIONS:
        reference = load_region_reference(ROOT / "data/processed/regions", region)
        embedding = build_topology_embedding(
            reference, layer_count=int(revision["layer_count"]), optimize_passes=int(revision["optimize_passes"]),
            seed=seed, weights=dict(revision["topology_weights"]), radial_constraint=True,
            search_mode="expanded_cross", candidate_budget=int(revision["candidate_budget"]),
        )
        for view in ("disk", "annulus"):
            result = proposed_irregular(reference, embedding, view, inner=inner, outer=outer,
                                        iterations=int(config["power_iterations"]),
                                        warp_strength=float(config["disk_warp_strength"] if view == "disk" else config["annulus_warp_strength"]))
            scores = evaluate_result(reference, result)
            rows.append({"region": region, "variant": "Expanded-NP2-CrossLayer", "view": view,
                         "cell_count": len(result.cell_ids), "objective_initial": embedding.initial_objective,
                         "objective_final": embedding.final_objective, **scores})
        print("[revision]", region, embedding.initial_objective, "->", embedding.final_objective, flush=True)
    frame = pd.DataFrame(rows)
    write_csv(frame, ROOT / "results/tables/Table_method_revision.csv")
    summary = frame.groupby("view", as_index=False).agg(
        adj_f1=("adj_f1", "mean"), np2=("np2", "mean"),
        local_direction_error_deg=("local_direction_error_deg", "mean"),
        angular_error_deg=("angular_error_deg", "mean"), radial_spearman=("radial_spearman", "mean"),
        area_cv=("area_cv", "mean"), invalid_polygon_count=("invalid_polygon_count", "sum"))
    write_csv(summary, ROOT / "paper/tables/Table_method_revision.csv")
    print(summary.to_string(index=False))


if __name__ == "__main__":
    main()

