from __future__ import annotations

import shutil

import pandas as pd

from common import ROOT, ensure_output_dirs, geometry_config, project_boundaries
from evaluation_helpers import evaluate_result
from geodisk_paper.data.regions import load_region_reference
from geodisk_paper.geometry.serialization import load_geometry
from geodisk_paper.metrics.geometry import shared_boundary_lengths
from geodisk_paper.metrics.spatial import weighted_adjacency_scores
from geodisk_paper.utils.io import write_csv, write_json
from geodisk_paper.visualization.figures import comparison_figure


BASELINES = {
    "Direct Polar": "direct_polar_annulus.geojson",
    "Harmonic": "harmonic_annulus.geojson",
    "Area-balanced": "area_balanced_annulus.geojson",
    "Regular Topology": "regular_topology_annulus.geojson",
}


def _reference_lengths(reference) -> dict[tuple[str, str], float]:
    return {
        edge: max(float(reference.polygons[edge[0]].boundary.intersection(
            reference.polygons[edge[1]].boundary).length), 1e-12)
        for edge in sorted(reference.edges)
    }


def main() -> None:
    ensure_output_dirs(); config = geometry_config(); boundaries, english = project_boundaries()
    inner, outer = float(config["annulus_inner"]), float(config["annulus_outer"])
    rows: list[dict] = []; provenance: list[dict] = []
    for region in config["regions"]:
        reference = load_region_reference(ROOT / "data/processed/regions", region)
        expected = set(reference.cells.cell_id.astype(str)); reference_lengths = _reference_lengths(reference)
        inputs = {}
        paths = {
            **{label: ROOT / "results/spatial" / region / filename for label, filename in BASELINES.items()},
            "GeoDisk-Final": ROOT / "results/spatial_refined" / region / "final_refined_disk.geojson",
            "GeoAnnulus-Final": ROOT / "results/spatial_refined" / region / "final_refined_annulus.geojson",
        }
        for label, path in paths.items():
            if not path.exists():
                prerequisite = "E19" if label.endswith("Final") else "E2/E3"
                raise FileNotFoundError(f"Missing {path}; run {prerequisite} first")
            result = load_geometry(path, inner, outer)
            if set(result.cell_ids) != expected or len(result.cell_ids) != len(expected):
                raise ValueError(f"Cell identity mismatch: {path}")
            scores = evaluate_result(reference, result)
            display_lengths = shared_boundary_lengths(result.cell_ids, result.geometries)
            weighted = weighted_adjacency_scores(reference_lengths, display_lengths)
            rows.append({
                "region": region, "method": result.method, "view": result.view,
                "cell_count": len(result.cell_ids),
                **scores, **weighted,
                "source_geojson": str(path.relative_to(ROOT)),
            })
            inputs[label] = result
        output = ROOT / "results/figures" / f"Fig_final_spatial_comparison_{english[region]}.png"
        comparison_figure(
            reference, boundaries[region], inputs, output, english[region],
            labels=["Geographic Reference", *BASELINES, "GeoDisk-Final", "GeoAnnulus-Final"],
            dpi=300,
        )
        shutil.copy2(output, ROOT / "paper/figures" / output.name)
        provenance.append({"region": region, "figure": str(output.relative_to(ROOT)),
                           "inputs": [str(path.relative_to(ROOT)) for path in paths.values()]})
        print("[final spatial figure]", region, flush=True)
    table = pd.DataFrame(rows)
    ordered = [
        "region", "method", "view", "cell_count", "adj_precision", "adj_recall", "adj_f1",
        "weighted_adj_f1", "np2", "local_direction_error_deg", "angular_error_deg",
        "radial_spearman", "area_cv", "invalid_polygon_count", "overlap_ratio", "gap_ratio",
        "source_geojson",
    ]
    table = table[ordered]
    write_csv(table, ROOT / "results/tables/Table_final_spatial_comparison.csv")
    write_csv(table, ROOT / "paper/tables/Table_final_spatial_comparison.csv")
    write_json({"producer": "E31_final_spatial_figures.py", "figures": provenance,
                "visual_policy": "identical scalar, colormap, normalization, boundaries, typography, size and 300 dpi within every figure"},
               ROOT / "results/figures/final_spatial_figures_manifest.json")
    print(table.groupby(["method", "view"])[["adj_f1", "weighted_adj_f1", "np2"]].mean().to_string())


if __name__ == "__main__":
    main()
