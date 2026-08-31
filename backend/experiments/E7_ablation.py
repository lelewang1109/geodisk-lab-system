from __future__ import annotations

import pandas as pd

from common import ROOT, ensure_output_dirs, experiment_config, geometry_config, seed_everything
from evaluation_helpers import evaluate_result
from geodisk_paper.data.regions import load_region_reference
from geodisk_paper.geometry.mappings import proposed_irregular
from geodisk_paper.topology.embedding import build_topology_embedding
from geodisk_paper.utils.io import write_csv


VARIANTS = {
    "Full": {},
    "No topology optimization": {"optimize_passes": 0},
    "No angular constraint": {"angular_weight": 0.0},
    "No radial constraint": {"radial_constraint": False},
    "No area balancing": {"balance": False},
    "No warp": {"warp_strength": 0.0},
}


def main():
    ensure_output_dirs(); geometry = geometry_config(); experiment = experiment_config(); seed = seed_everything()
    inner, outer = float(geometry["annulus_inner"]), float(geometry["annulus_outer"])
    rows = []
    for region in experiment["ablation_regions"]:
        reference = load_region_reference(ROOT / "data/processed/regions", region)
        for variant, changes in VARIANTS.items():
            weights = dict(geometry["topology_weights"])
            if "angular_weight" in changes: weights["angular"] = changes["angular_weight"]
            embedding = build_topology_embedding(
                reference, layer_count=int(geometry["layer_count"]),
                optimize_passes=int(changes.get("optimize_passes", geometry["optimize_passes"])),
                seed=seed, weights=weights, radial_constraint=bool(changes.get("radial_constraint", True)),
            )
            for view in ("disk", "annulus"):
                default_warp = float(geometry["disk_warp_strength"] if view == "disk" else geometry["annulus_warp_strength"])
                result = proposed_irregular(
                    reference, embedding, view, inner=inner, outer=outer,
                    iterations=int(geometry["power_iterations"]),
                    warp_strength=float(changes.get("warp_strength", default_warp)),
                    balance=bool(changes.get("balance", True)),
                )
                rows.append({"region": region, "variant": variant, "view": view,
                             "cell_count": len(result.cell_ids), **evaluate_result(reference, result)})
            print("[ablation]", region, variant, flush=True)
    frame = pd.DataFrame(rows)
    metrics = ["adj_precision", "adj_recall", "adj_f1", "original_edge_count", "display_edge_count",
               "preserved_edge_count", "lost_edge_count", "new_edge_count", "np2", "np3", "local_direction_error_deg",
               "angular_error_deg", "radial_spearman", "area_cv", "overlap_ratio", "gap_ratio",
               "invalid_polygon_count"]
    summaries = []
    for (variant, view), group in frame.groupby(["variant", "view"], sort=False):
        for statistic in ("mean", "median", "std"):
            row = {"region": f"OVERALL_{statistic}", "variant": variant, "view": view,
                   "cell_count": int(group.cell_count.mean())}
            row.update(getattr(group[metrics], statistic)(numeric_only=True).to_dict())
            summaries.append(row)
    output = pd.concat([frame, pd.DataFrame(summaries)], ignore_index=True)
    write_csv(output, ROOT / "results/ablation/Table_ablation.csv")
    write_csv(output, ROOT / "paper/tables/Table_ablation.csv")
    print(output[output.region == "OVERALL_mean"].to_string(index=False))


if __name__ == "__main__":
    main()
