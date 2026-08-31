from shapely.ops import unary_union

from common import ROOT, ensure_output_dirs, geometry_config, seed_everything
from geodisk_paper.data.regions import load_region_reference
from geodisk_paper.geometry.mappings import (GeometryResult, direct_polar, geographic_area_balanced,
                                             harmonic_continuous, proposed_irregular)
from geodisk_paper.geometry.power import circular_domain
from geodisk_paper.geometry.serialization import save_geometry
from geodisk_paper.topology.embedding import build_topology_embedding, regular_polygons


DATASETS = ["NE-Admin0-Africa", "NCEP-AirTemp-Africa-2000"]


def main():
    ensure_output_dirs(); config = geometry_config(); external = config["external"]; seed = seed_everything()
    inner, outer = float(config["annulus_inner"]), float(config["annulus_outer"])
    for dataset_id in DATASETS:
        reference = load_region_reference(ROOT / "data/processed/external_regions", dataset_id)
        boundary = unary_union(list(reference.polygons.values()))
        embedding = build_topology_embedding(
            reference, layer_count=int(external["layer_count"]), optimize_passes=int(external["optimize_passes"]),
            seed=seed, weights=dict(config["topology_weights"]), radial_constraint=True)
        output = ROOT / "results/external_spatial" / dataset_id
        for view in ("disk", "annulus"):
            baseline_results = {
                "direct_polar": direct_polar(reference, boundary, view, inner, outer),
                "harmonic": harmonic_continuous(reference, view, inner, outer),
                "area_balanced": geographic_area_balanced(reference, view, inner, outer, int(external["power_iterations"])),
            }
            for name, result in baseline_results.items():
                save_geometry(result, output / f"{name}_{view}.geojson")
            regular = regular_polygons(embedding, view, inner, outer); ids = embedding.cell_ids
            save_geometry(GeometryResult("Regular Topology", view, ids, [regular[cell_id] for cell_id in ids],
                                         circular_domain(view, inner, outer),
                                         {"topology_objective_initial": embedding.initial_objective,
                                          "topology_objective_final": embedding.final_objective}),
                          output / f"regular_topology_{view}.geojson")
            warp = float(config["disk_warp_strength"] if view == "disk" else config["annulus_warp_strength"])
            save_geometry(proposed_irregular(reference, embedding, view, inner=inner, outer=outer,
                                             iterations=int(external["power_iterations"]), warp_strength=warp),
                          output / f"proposed_{view}.geojson")
            print("[external geometry]", dataset_id, view, flush=True)


if __name__ == "__main__":
    main()

