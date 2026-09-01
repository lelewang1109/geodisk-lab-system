from __future__ import annotations

import pandas as pd

from common import ROOT, geometry_config
from geodisk_paper.data.regions import load_region_reference
from geodisk_paper.geometry.serialization import load_geometry
from geodisk_paper.metrics.geometry import display_adjacency
from geodisk_paper.metrics.spatial import adjacency_scores, neighborhood_preservation
from geodisk_paper.utils.io import write_csv


TOLERANCES = [1e-6, 5e-6, 2e-5, 1e-4, 5e-4]
CEG_REGIONS = ["湖北", "湖南", "江西", "广东", "福建", "广西", "安徽", "浙江"]
EXTERNAL = ["NE-Admin0-Africa", "NCEP-AirTemp-Africa-2000"]
FILES = ["direct_polar_disk", "direct_polar_annulus", "harmonic_disk", "harmonic_annulus",
         "area_balanced_disk", "area_balanced_annulus", "regular_topology_disk", "regular_topology_annulus",
         "proposed_disk", "proposed_annulus"]
FINAL_FILES = ["final_refined_disk", "final_refined_annulus"]


def _evaluate(dataset, reference_root, geometry_root, rows, inner, outer, refined_root=None):
    reference = load_region_reference(reference_root, dataset)
    ids = reference.cells.cell_id.astype(str).tolist()
    paths = [geometry_root / dataset / f"{stem}.geojson" for stem in FILES]
    if refined_root is not None:
        paths.extend(refined_root / dataset / f"{stem}.geojson" for stem in FINAL_FILES)
    for path in paths:
        if not path.exists():
            continue
        result = load_geometry(path, inner, outer)
        for tolerance in TOLERANCES:
            edges = display_adjacency(result.cell_ids, result.geometries, tolerance=tolerance)
            rows.append({"dataset": dataset, "method": result.method, "view": result.view, "tolerance": tolerance,
                         **adjacency_scores(reference.edges, edges),
                         "np2": neighborhood_preservation(ids, reference.edges, edges, 2)})


def main():
    config = geometry_config(); inner = float(config["annulus_inner"]); outer = float(config["annulus_outer"])
    rows = []
    for region in CEG_REGIONS:
        _evaluate(region, ROOT / "data/processed/regions", ROOT / "results/spatial", rows, inner, outer,
                  ROOT / "results/spatial_refined")
    for dataset in EXTERNAL:
        _evaluate(dataset, ROOT / "data/processed/external_regions", ROOT / "results/external_spatial", rows, inner, outer,
                  ROOT / "results/external_refined")
    _evaluate("NASA-Exoplanet-SkyGrid", ROOT / "data/processed/external_regions",
              ROOT / "results/astronomy_spatial", rows, inner, outer, ROOT / "results/astronomy_spatial")
    synthetic_root = ROOT / "data/processed/synthetic_regions"
    for directory in sorted(path for path in synthetic_root.iterdir() if path.is_dir() and path.name.startswith("Synthetic-")):
        _evaluate(directory.name, synthetic_root, ROOT / "results/synthetic_spatial", rows, inner, outer,
                  ROOT / "results/synthetic_refined")
    frame = pd.DataFrame(rows)
    write_csv(frame, ROOT / "results/tables/Table_contact_tolerance_sensitivity.csv")
    summary = frame.groupby(["method", "view", "tolerance"], as_index=False).agg(
        dataset_count=("dataset", "count"), adj_precision=("adj_precision", "mean"),
        adj_recall=("adj_recall", "mean"), adj_f1=("adj_f1", "mean"), np2=("np2", "mean"))
    write_csv(summary, ROOT / "paper/tables/Table_contact_tolerance_sensitivity.csv")
    print(summary.to_string(index=False))


if __name__ == "__main__":
    main()
