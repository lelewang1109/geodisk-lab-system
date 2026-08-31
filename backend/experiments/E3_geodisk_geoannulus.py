from common import ROOT, ensure_output_dirs, geometry_config, seed_everything
from geodisk_paper.data.regions import load_region_reference
from geodisk_paper.geometry.mappings import GeometryResult, proposed_irregular
from geodisk_paper.geometry.power import circular_domain
from geodisk_paper.geometry.serialization import save_geometry
from geodisk_paper.topology.embedding import build_topology_embedding, regular_polygons


def main():
    ensure_output_dirs(); config = geometry_config(); seed = seed_everything()
    inner, outer = float(config["annulus_inner"]), float(config["annulus_outer"])
    for region in config["regions"]:
        reference = load_region_reference(ROOT / "data/processed/regions", region)
        embedding = build_topology_embedding(
            reference, layer_count=int(config["layer_count"]), optimize_passes=int(config["optimize_passes"]),
            seed=seed, weights=dict(config["topology_weights"]), radial_constraint=True,
        )
        output = ROOT / "results/spatial" / region
        for view in ("disk", "annulus"):
            regular = regular_polygons(embedding, view, inner, outer)
            ids = embedding.cell_ids
            regular_result = GeometryResult("Regular Topology", view, ids, [regular[i] for i in ids],
                                            circular_domain(view, inner, outer),
                                            {"topology_objective_initial": embedding.initial_objective,
                                             "topology_objective_final": embedding.final_objective})
            save_geometry(regular_result, output / f"regular_topology_{view}.geojson")
            warp = float(config["disk_warp_strength"] if view == "disk" else config["annulus_warp_strength"])
            proposed = proposed_irregular(reference, embedding, view, inner=inner, outer=outer,
                                          iterations=int(config["power_iterations"]), warp_strength=warp)
            save_geometry(proposed, output / f"proposed_{view}.geojson")
        print("[proposed]", region, embedding.initial_objective, "->", embedding.final_objective, flush=True)


if __name__ == "__main__":
    main()

