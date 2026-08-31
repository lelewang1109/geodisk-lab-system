from __future__ import annotations

import pandas as pd

from common import ROOT, ensure_output_dirs, geometry_config, project_boundaries
from geodisk_paper.data.regions import load_region_reference
from geodisk_paper.geometry.serialization import load_geometry
from geodisk_paper.metrics.geometry import display_adjacency, edge_jaccard, geometry_validity
from geodisk_paper.metrics.spatial import evaluate_spatial
from geodisk_paper.utils.io import write_csv
from geodisk_paper.visualization.figures import comparison_figure


FILES = [
    "direct_polar_disk.geojson", "direct_polar_annulus.geojson",
    "harmonic_disk.geojson", "harmonic_annulus.geojson",
    "area_balanced_disk.geojson", "area_balanced_annulus.geojson",
    "regular_topology_disk.geojson", "regular_topology_annulus.geojson",
    "proposed_disk.geojson", "proposed_annulus.geojson",
]


def _summary_rows(frame: pd.DataFrame, metrics: list[str]) -> pd.DataFrame:
    groups = []
    for (method, view), group in frame.groupby(["method", "view"], sort=False):
        for statistic in ("mean", "median", "std"):
            values = getattr(group[metrics], statistic)(numeric_only=True)
            row = {"region": f"OVERALL_{statistic}", "method": method, "view": view,
                   "cell_count": int(group.cell_count.mean())}
            row.update(values.to_dict())
            groups.append(row)
    return pd.DataFrame(groups)


def main():
    ensure_output_dirs(); config = geometry_config(); boundaries, english = project_boundaries()
    inner, outer = float(config["annulus_inner"]), float(config["annulus_outer"])
    spatial_rows, geometry_rows, consistency_rows = [], [], []
    for region in config["regions"]:
        reference = load_region_reference(ROOT / "data/processed/regions", region)
        source_centroids = {str(r.cell_id): (float(r.longitude), float(r.latitude)) for r in reference.cells.itertuples()}
        theta = {str(r.cell_id): float(r.theta) for r in reference.cells.itertuples()}
        rho = {str(r.cell_id): float(r.rho) for r in reference.cells.itertuples()}
        loaded, edges_by_key = {}, {}
        for filename in FILES:
            path = ROOT / "results/spatial" / region / filename
            if not path.exists():
                raise FileNotFoundError(f"Missing geometry output: {path}. Run E2 and E3 first.")
            result = load_geometry(path, inner, outer)
            expected = set(reference.cells.cell_id.astype(str))
            if set(result.cell_ids) != expected or len(result.cell_ids) != len(expected):
                raise ValueError(f"cell_id mismatch for {path}")
            display_edges = display_adjacency(result.cell_ids, result.geometries)
            display_centroids = {cell_id: (float(geometry.centroid.x), float(geometry.centroid.y))
                                 for cell_id, geometry in zip(result.cell_ids, result.geometries)}
            scores = evaluate_spatial(result.cell_ids, reference.edges, display_edges, source_centroids,
                                      display_centroids, theta, rho, reference.anchor[1])
            spatial_rows.append({"region": region, "method": result.method, "view": result.view,
                                 "cell_count": len(result.cell_ids), **scores})
            validity = geometry_validity(result.geometries, result.domain)
            geometry_rows.append({"region": region, "method": result.method, "view": result.view,
                                  "cell_count": len(result.cell_ids), **validity})
            key = filename.removesuffix(".geojson")
            loaded[key], edges_by_key[key] = result, display_edges
            status_rows = []
            for edge in sorted(reference.edges | display_edges):
                status_rows.append({"source": edge[0], "target": edge[1],
                                    "status": "preserved" if edge in reference.edges and edge in display_edges
                                    else "lost" if edge in reference.edges else "new"})
            write_csv(pd.DataFrame(status_rows), path.with_name(path.stem + "_edge_status.csv"))
        consistency_rows.append({
            "region": region,
            "disk_annulus_edge_jaccard": edge_jaccard(edges_by_key["proposed_disk"], edges_by_key["proposed_annulus"]),
        })
        figure_inputs = {
            "Direct Polar": loaded["direct_polar_annulus"], "Harmonic": loaded["harmonic_annulus"],
            "Area-balanced": loaded["area_balanced_annulus"], "Regular Topology": loaded["regular_topology_annulus"],
            "GeoDisk": loaded["proposed_disk"], "GeoAnnulus": loaded["proposed_annulus"],
        }
        comparison_figure(reference, boundaries[region], figure_inputs,
                          ROOT / "results/figures" / f"Fig_spatial_comparison_{english[region]}.png", english[region])
        print("[evaluate]", region, flush=True)

    spatial = pd.DataFrame(spatial_rows)
    geometry = pd.DataFrame(geometry_rows)
    spatial_metrics = ["adj_precision", "adj_recall", "adj_f1", "original_edge_count", "display_edge_count",
                       "preserved_edge_count", "lost_edge_count", "new_edge_count", "np2", "np3",
                       "local_direction_error_deg", "angular_error_deg", "radial_spearman"]
    geometry_metrics = ["area_cv", "overlap_ratio", "gap_ratio", "invalid_polygon_count"]
    spatial_table = pd.concat([spatial, _summary_rows(spatial, spatial_metrics)], ignore_index=True)
    geometry_table = pd.concat([geometry, _summary_rows(geometry, geometry_metrics)], ignore_index=True)
    write_csv(spatial_table, ROOT / "results/tables/Table_spatial_fidelity.csv")
    write_csv(spatial_table, ROOT / "paper/tables/Table_spatial_fidelity.csv")
    write_csv(geometry_table, ROOT / "results/tables/Table_geometry_validity.csv")
    write_csv(geometry_table, ROOT / "paper/tables/Table_geometry_validity.csv")
    write_csv(pd.DataFrame(consistency_rows), ROOT / "results/tables/Table_cross_view_consistency.csv")
    # Paper-facing figure aliases are copies of canonical, already-generated files.
    for region in config["regions"]:
        source = ROOT / "results/figures" / f"Fig_spatial_comparison_{english[region]}.png"
        target = ROOT / "paper/figures" / source.name
        target.write_bytes(source.read_bytes())
    print(spatial_table[spatial_table.region == "OVERALL_mean"].to_string(index=False))


if __name__ == "__main__":
    main()
