from __future__ import annotations

import pandas as pd
from shapely.ops import unary_union

from common import ROOT, ensure_output_dirs, geometry_config, seed_everything
from evaluation_helpers import evaluate_result
from geodisk_paper.data.external_datasets import synthetic_masks
from geodisk_paper.data.regions import load_region_reference
from geodisk_paper.geometry.mappings import (GeometryResult, direct_polar, geographic_area_balanced,
                                             harmonic_continuous, proposed_irregular)
from geodisk_paper.geometry.power import circular_domain
from geodisk_paper.topology.embedding import build_topology_embedding, regular_polygons
from geodisk_paper.utils.io import write_csv


def main():
    ensure_output_dirs(); config = geometry_config(); settings = config["synthetic"]; seed = seed_everything()
    inner, outer = float(config["annulus_inner"]), float(config["annulus_outer"])
    spatial, validity = [], []
    for case in synthetic_masks():
        name = f"Synthetic-{case}"
        reference = load_region_reference(ROOT / "data/processed/synthetic_regions", name)
        boundary = unary_union(list(reference.polygons.values()))
        embedding = build_topology_embedding(reference, layer_count=int(settings["layer_count"]),
                                             optimize_passes=int(settings["optimize_passes"]), seed=seed,
                                             weights=dict(config["topology_weights"]), radial_constraint=True)
        for view in ("disk", "annulus"):
            regular = regular_polygons(embedding, view, inner, outer); ids = embedding.cell_ids
            results = [
                direct_polar(reference, boundary, view, inner, outer),
                harmonic_continuous(reference, view, inner, outer),
                geographic_area_balanced(reference, view, inner, outer, int(settings["power_iterations"])),
                GeometryResult("Regular Topology", view, ids, [regular[cell_id] for cell_id in ids], circular_domain(view, inner, outer), {}),
                proposed_irregular(reference, embedding, view, inner=inner, outer=outer,
                                   iterations=int(settings["power_iterations"]),
                                   warp_strength=float(config["disk_warp_strength"] if view == "disk" else config["annulus_warp_strength"])),
            ]
            for result in results:
                scores = evaluate_result(reference, result)
                base = {"case": case, "method": result.method, "view": view, "cell_count": len(result.cell_ids)}
                spatial.append({**base, **{key: scores[key] for key in ["adj_precision", "adj_recall", "adj_f1", "np2", "np3",
                                                                        "local_direction_error_deg", "angular_error_deg", "radial_spearman"]}})
                validity.append({**base, **{key: scores[key] for key in ["area_cv", "overlap_ratio", "gap_ratio", "invalid_polygon_count"]}})
        print("[synthetic]", case, flush=True)
    write_csv(pd.DataFrame(spatial), ROOT / "results/tables/Table_synthetic_spatial_fidelity.csv")
    write_csv(pd.DataFrame(validity), ROOT / "results/tables/Table_synthetic_geometry_validity.csv")
    write_csv(pd.DataFrame(spatial), ROOT / "paper/tables/Table_synthetic_spatial_fidelity.csv")


if __name__ == "__main__":
    main()

