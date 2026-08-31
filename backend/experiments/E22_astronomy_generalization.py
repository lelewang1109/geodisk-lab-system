from __future__ import annotations

import pandas as pd

from common import ROOT, ensure_output_dirs, geometry_config, seed_everything
from evaluation_helpers import evaluate_result
from geodisk_paper.data.external_datasets import prepare_exoplanet_sky_reference
from geodisk_paper.geometry.mappings import (GeometryResult, direct_polar, geographic_area_balanced,
                                             harmonic_continuous, proposed_irregular)
from geodisk_paper.geometry.power import circular_domain
from geodisk_paper.geometry.serialization import save_geometry
from geodisk_paper.topology.embedding import build_topology_embedding, regular_polygons
from geodisk_paper.topology.power_refinement import refine_final_power_adjacency
from geodisk_paper.utils.io import write_csv, write_json
from geodisk_paper.visualization.figures import comparison_figure


def main() -> None:
    ensure_output_dirs(); config = geometry_config(); seed = seed_everything()
    reference, domain, metadata = prepare_exoplanet_sky_reference(
        ROOT / "data/external/nasa_exoplanet/pscomppars_sky.csv",
        ROOT / "data/processed/external_regions",
    )
    inner, outer = float(config["annulus_inner"]), float(config["annulus_outer"])
    revision = config["method_revision"]
    embedding = build_topology_embedding(
        reference, layer_count=int(revision["layer_count"]), optimize_passes=4, seed=seed,
        weights=dict(revision["topology_weights"]), radial_constraint=True,
        search_mode="expanded_cross", candidate_budget=180,
    )
    output = ROOT / "results/astronomy_spatial" / reference.name; results = {}
    for view in ("disk", "annulus"):
        baseline_results = [
            direct_polar(reference, domain, view, inner, outer),
            harmonic_continuous(reference, view, inner, outer),
            geographic_area_balanced(reference, view, inner, outer, iterations=4),
        ]
        regular = regular_polygons(embedding, view, inner, outer)
        ids = embedding.cell_ids
        baseline_results.append(GeometryResult(
            "Regular Topology", view, ids, [regular[cell_id] for cell_id in ids],
            circular_domain(view, inner, outer), {"source": "slot_embedding"},
        ))
        baseline_results.append(proposed_irregular(
            reference, embedding, view, inner=inner, outer=outer, iterations=4,
            warp_strength=float(config["disk_warp_strength"] if view == "disk" else config["annulus_warp_strength"]),
        ))
        baseline_results.append(refine_final_power_adjacency(
            reference, embedding, view, inner=inner, outer=outer, power_iterations=3, force_iterations=4,
            objective_weights=dict(config["final_power_refinement"]["objective_weights"]),
        ))
        stems = ["direct_polar", "harmonic", "area_balanced", "regular_topology", "proposed", "final_refined"]
        for stem, result in zip(stems, baseline_results):
            save_geometry(result, output / f"{stem}_{view}.geojson")
            results[(result.method, view)] = result
    rows = []
    for result in results.values():
        rows.append({"dataset": reference.name, "method": result.method, "view": result.view,
                     "cell_count": len(result.cell_ids), **evaluate_result(reference, result)})
    table = pd.DataFrame(rows)
    write_csv(table, ROOT / "results/tables/Table_astronomy_generalization.csv")
    write_csv(table, ROOT / "paper/tables/Table_astronomy_generalization.csv")
    figure_inputs = {
        "Direct Polar": results[("Direct Polar", "annulus")],
        "Harmonic": results[("Harmonic", "annulus")],
        "Area-balanced": results[("Area-balanced", "annulus")],
        "Regular Topology": results[("Regular Topology", "annulus")],
        "GeoDisk": results[("GeoDisk-Final", "disk")],
        "GeoAnnulus": results[("GeoAnnulus-Final", "annulus")],
    }
    figure_path = ROOT / "results/figures/Fig_external_NASA-Exoplanet-SkyGrid.png"
    comparison_figure(reference, domain, figure_inputs, figure_path, "NASA Exoplanet Sky Grid",
                      value_column="scalar_value", value_label="log1p confirmed planet count")
    (ROOT / "paper/figures" / figure_path.name).write_bytes(figure_path.read_bytes())
    write_json({**metadata, "evaluation_methods": sorted(table.method.unique().tolist()),
                "outcome_policy": "all methods evaluated; final method chosen by the same fixed Power-refinement schedule"},
               ROOT / "results/data_audit/nasa_exoplanet_dataset_summary.json")
    print(table[["method", "view", "adj_f1", "np2", "radial_spearman", "area_cv", "invalid_polygon_count"]].to_string(index=False))


if __name__ == "__main__":
    main()
