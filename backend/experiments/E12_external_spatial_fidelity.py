from __future__ import annotations

import pandas as pd
from shapely.ops import unary_union

from common import ROOT, ensure_output_dirs, geometry_config
from evaluation_helpers import evaluate_result
from geodisk_paper.data.regions import load_region_reference
from geodisk_paper.geometry.serialization import load_geometry
from geodisk_paper.metrics.geometry import display_adjacency, edge_jaccard
from geodisk_paper.utils.io import write_csv
from geodisk_paper.visualization.figures import comparison_figure


DATASETS = {
    "NE-Admin0-Africa": ("Natural Earth Africa Admin-0", "log10 population estimate"),
    "NCEP-AirTemp-Africa-2000": ("NCEP Air Temperature Africa 2000", "annual mean air temperature (°C)"),
}
FILES = ["direct_polar_disk", "direct_polar_annulus", "harmonic_disk", "harmonic_annulus",
         "area_balanced_disk", "area_balanced_annulus", "regular_topology_disk", "regular_topology_annulus",
         "proposed_disk", "proposed_annulus"]


def main():
    ensure_output_dirs(); config = geometry_config(); inner = float(config["annulus_inner"]); outer = float(config["annulus_outer"])
    rows, validity_rows, cross_rows = [], [], []
    for dataset_id, (title, value_label) in DATASETS.items():
        reference = load_region_reference(ROOT / "data/processed/external_regions", dataset_id)
        boundary = unary_union(list(reference.polygons.values()))
        loaded, edge_sets = {}, {}
        for stem in FILES:
            result = load_geometry(ROOT / "results/external_spatial" / dataset_id / f"{stem}.geojson", inner, outer)
            scores = evaluate_result(reference, result)
            spatial_keys = ["adj_precision", "adj_recall", "adj_f1", "np2", "np3", "local_direction_error_deg",
                            "angular_error_deg", "radial_spearman", "original_edge_count", "display_edge_count",
                            "preserved_edge_count", "lost_edge_count", "new_edge_count"]
            geometry_keys = ["area_cv", "overlap_ratio", "gap_ratio", "invalid_polygon_count"]
            rows.append({"dataset": dataset_id, "method": result.method, "view": result.view,
                         "cell_count": len(result.cell_ids), **{key: scores[key] for key in spatial_keys}})
            validity_rows.append({"dataset": dataset_id, "method": result.method, "view": result.view,
                                  "cell_count": len(result.cell_ids), **{key: scores[key] for key in geometry_keys}})
            loaded[stem] = result; edge_sets[stem] = display_adjacency(result.cell_ids, result.geometries)
        cross_rows.append({"dataset": dataset_id,
                           "disk_annulus_edge_jaccard": edge_jaccard(edge_sets["proposed_disk"], edge_sets["proposed_annulus"])})
        figure_inputs = {"Direct Polar": loaded["direct_polar_annulus"], "Harmonic": loaded["harmonic_annulus"],
                         "Area-balanced": loaded["area_balanced_annulus"], "Regular Topology": loaded["regular_topology_annulus"],
                         "GeoDisk": loaded["proposed_disk"], "GeoAnnulus": loaded["proposed_annulus"]}
        comparison_figure(reference, boundary, figure_inputs, ROOT / "results/figures" / f"Fig_external_{dataset_id}.png",
                          title, value_column="scalar_value", value_label=value_label)
        print("[external evaluate]", dataset_id, flush=True)
    spatial = pd.DataFrame(rows); validity = pd.DataFrame(validity_rows)
    write_csv(spatial, ROOT / "results/tables/Table_external_spatial_fidelity.csv")
    write_csv(validity, ROOT / "results/tables/Table_external_geometry_validity.csv")
    write_csv(pd.DataFrame(cross_rows), ROOT / "results/tables/Table_external_cross_view.csv")
    write_csv(spatial, ROOT / "paper/tables/Table_external_spatial_fidelity.csv")
    write_csv(validity, ROOT / "paper/tables/Table_external_geometry_validity.csv")
    for dataset_id in DATASETS:
        source = ROOT / "results/figures" / f"Fig_external_{dataset_id}.png"
        (ROOT / "paper/figures" / source.name).write_bytes(source.read_bytes())
    print(spatial.to_string(index=False))


if __name__ == "__main__":
    main()

