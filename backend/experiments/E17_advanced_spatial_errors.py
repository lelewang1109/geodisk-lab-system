from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from common import ROOT, ensure_output_dirs, geometry_config
from geodisk_paper.data.regions import load_region_reference
from geodisk_paper.geometry.serialization import load_geometry
from geodisk_paper.metrics.geometry import display_adjacency, shared_boundary_lengths
from geodisk_paper.metrics.spatial import node_level_fidelity, weighted_adjacency_scores
from geodisk_paper.utils.io import write_csv


GEOMETRY_FILES = [
    "direct_polar_disk.geojson", "direct_polar_annulus.geojson",
    "harmonic_disk.geojson", "harmonic_annulus.geojson",
    "area_balanced_disk.geojson", "area_balanced_annulus.geojson",
    "regular_topology_disk.geojson", "regular_topology_annulus.geojson",
    "proposed_disk.geojson", "proposed_annulus.geojson",
]


def _reference_lengths(reference) -> dict[tuple[str, str], float]:
    output = {}
    for edge in reference.edges:
        left, right = edge
        length = float(reference.polygons[left].boundary.intersection(reference.polygons[right].boundary).length)
        output[edge] = max(length, 1e-12)
    return output


def _boundary_map(reference) -> dict[str, bool]:
    if "is_boundary" in reference.cells.columns:
        return {str(row.cell_id): bool(row.is_boundary) for row in reference.cells.itertuples()}
    degree = {str(cell_id): 0 for cell_id in reference.cells.cell_id}
    for left, right in reference.edges:
        degree[left] += 1; degree[right] += 1
    return {cell_id: value < 4 for cell_id, value in degree.items()}


def _evaluate_dataset(dataset: str, reference_root: Path, geometry_root: Path, refined_root: Path | None,
                      inner: float, outer: float,
                      node_rows: list[dict], group_rows: list[dict], weight_rows: list[dict]) -> None:
    reference = load_region_reference(reference_root, dataset)
    ids = reference.cells.cell_id.astype(str).tolist()
    source = {str(row.cell_id): (float(row.longitude), float(row.latitude)) for row in reference.cells.itertuples()}
    theta = {str(row.cell_id): float(row.theta) for row in reference.cells.itertuples()}
    rho = {str(row.cell_id): float(row.rho) for row in reference.cells.itertuples()}
    boundary = _boundary_map(reference)
    reference_lengths = _reference_lengths(reference)
    paths = [geometry_root / dataset / filename for filename in GEOMETRY_FILES]
    if refined_root is not None:
        paths.extend(refined_root / dataset / f"final_refined_{view}.geojson" for view in ("disk", "annulus"))
    for path in paths:
        if not path.exists():
            continue
        result = load_geometry(path, inner, outer)
        display_edges = display_adjacency(result.cell_ids, result.geometries)
        display_lengths = shared_boundary_lengths(result.cell_ids, result.geometries)
        target = {cell_id: (float(geometry.centroid.x), float(geometry.centroid.y))
                  for cell_id, geometry in zip(result.cell_ids, result.geometries)}
        weighted = weighted_adjacency_scores(reference_lengths, display_lengths)
        weight_rows.append({"dataset": dataset, "method": result.method, "view": result.view,
                            "cell_count": len(ids), **weighted})
        local = node_level_fidelity(ids, reference.edges, display_edges, source, target, theta, rho,
                                    reference.anchor[1], boundary)
        for row in local:
            node_rows.append({"dataset": dataset, "method": result.method, "view": result.view, **row})
        local_frame = pd.DataFrame(local)
        for label, subset in [("boundary", local_frame[local_frame.is_boundary]),
                              ("interior", local_frame[~local_frame.is_boundary]),
                              ("all", local_frame)]:
            if subset.empty:
                continue
            group_rows.append({
                "dataset": dataset, "method": result.method, "view": result.view, "node_group": label,
                "node_count": len(subset), "mean_reference_degree": float(subset.reference_degree.mean()),
                "mean_display_degree": float(subset.display_degree.mean()),
                "degree_absolute_error": float(subset.degree_absolute_error.mean()),
                "node_adj_precision": float(subset.node_adj_precision.mean()),
                "node_adj_recall": float(subset.node_adj_recall.mean()),
                "node_adj_f1": float(subset.node_adj_f1.mean()),
                "node_neighbor_jaccard": float(subset.node_neighbor_jaccard.mean()),
                "node_angular_error_deg": float(subset.node_angular_error_deg.mean()),
                "node_radial_rank_error": float(subset.node_radial_rank_error.mean()),
                "node_direction_error_deg": float(np.nanmean(subset.node_direction_error_deg)),
                "node_neighbor_order_accuracy": float(np.nanmean(subset.node_neighbor_order_accuracy)),
            })
    print("[advanced spatial errors]", dataset, flush=True)


def main() -> None:
    ensure_output_dirs(); config = geometry_config()
    inner, outer = float(config["annulus_inner"]), float(config["annulus_outer"])
    node_rows: list[dict] = []; group_rows: list[dict] = []; weight_rows: list[dict] = []
    for region in config["regions"]:
        _evaluate_dataset(region, ROOT / "data/processed/regions", ROOT / "results/spatial", ROOT / "results/spatial_refined",
                          inner, outer, node_rows, group_rows, weight_rows)
    for dataset in ("NE-Admin0-Africa", "NCEP-AirTemp-Africa-2000"):
        _evaluate_dataset(dataset, ROOT / "data/processed/external_regions", ROOT / "results/external_spatial", ROOT / "results/external_refined",
                          inner, outer, node_rows, group_rows, weight_rows)
    _evaluate_dataset("NASA-Exoplanet-SkyGrid", ROOT / "data/processed/external_regions",
                      ROOT / "results/astronomy_spatial", ROOT / "results/astronomy_spatial",
                      inner, outer, node_rows, group_rows, weight_rows)
    synthetic_root = ROOT / "data/processed/synthetic_regions"
    for directory in sorted(path for path in synthetic_root.iterdir() if path.is_dir() and path.name.startswith("Synthetic-")):
        _evaluate_dataset(directory.name, synthetic_root, ROOT / "results/synthetic_spatial",
                          ROOT / "results/synthetic_refined", inner, outer,
                          node_rows, group_rows, weight_rows)
    node = pd.DataFrame(node_rows); grouped = pd.DataFrame(group_rows); weighted = pd.DataFrame(weight_rows)
    write_csv(node, ROOT / "results/tables/Table_node_level_errors.csv")
    write_csv(grouped, ROOT / "results/tables/Table_boundary_interior_errors.csv")
    write_csv(weighted, ROOT / "results/tables/Table_weighted_adjacency.csv")
    write_csv(grouped, ROOT / "paper/tables/Table_boundary_interior_errors.csv")
    write_csv(weighted, ROOT / "paper/tables/Table_weighted_adjacency.csv")
    summary = grouped[grouped.node_group != "all"].groupby(
        ["method", "view", "node_group"], as_index=False
    ).agg(node_adj_f1=("node_adj_f1", "mean"), node_neighbor_jaccard=("node_neighbor_jaccard", "mean"),
          degree_absolute_error=("degree_absolute_error", "mean"),
          node_direction_error_deg=("node_direction_error_deg", "mean"),
          node_neighbor_order_accuracy=("node_neighbor_order_accuracy", "mean"))
    write_csv(summary, ROOT / "paper/tables/Table_boundary_interior_summary.csv")
    print(summary.to_string(index=False))


if __name__ == "__main__":
    main()
