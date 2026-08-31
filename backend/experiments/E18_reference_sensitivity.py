from __future__ import annotations

from pathlib import Path

import pandas as pd

from common import ROOT, ensure_output_dirs, experiment_config, geometry_config, project_boundaries
from geodisk_paper.data.regions import grid_edges, load_region_reference
from geodisk_paper.geometry.serialization import load_geometry
from geodisk_paper.metrics.geometry import display_adjacency, shared_boundary_lengths
from geodisk_paper.metrics.spatial import adjacency_scores, neighborhood_preservation
from geodisk_paper.utils.io import write_csv, write_json


FILES = [
    "direct_polar_disk.geojson", "direct_polar_annulus.geojson",
    "harmonic_disk.geojson", "harmonic_annulus.geojson",
    "area_balanced_disk.geojson", "area_balanced_annulus.geojson",
    "regular_topology_disk.geojson", "regular_topology_annulus.geojson",
    "proposed_disk.geojson", "proposed_annulus.geojson",
]


def grid_edges_8(cells: pd.DataFrame) -> set[tuple[str, str]]:
    by_position = {(int(row.block_row), int(row.block_col)): str(row.cell_id) for row in cells.itertuples()}
    edges: set[tuple[str, str]] = set()
    for (row, col), cell_id in by_position.items():
        for delta_row, delta_col in ((0, 1), (1, -1), (1, 0), (1, 1)):
            other = by_position.get((row + delta_row, col + delta_col))
            if other is not None:
                edges.add(tuple(sorted((cell_id, other))))
    return edges


def _neighbor_sensitivity(dataset: str, reference_root: Path, geometry_root: Path, refined_root: Path | None,
                          inner: float, outer: float, rows: list[dict]) -> None:
    reference = load_region_reference(reference_root, dataset)
    ids = reference.cells.cell_id.astype(str).tolist()
    references = {"4-neighbor": grid_edges(reference.cells), "8-neighbor": grid_edges_8(reference.cells)}
    paths = [geometry_root / dataset / filename for filename in FILES]
    if refined_root is not None:
        paths.extend(refined_root / dataset / f"final_refined_{view}.geojson" for view in ("disk", "annulus"))
    for path in paths:
        if not path.exists():
            continue
        result = load_geometry(path, inner, outer)
        display = display_adjacency(result.cell_ids, result.geometries)
        for model, reference_edges in references.items():
            rows.append({"dataset": dataset, "method": result.method, "view": result.view,
                         "neighbor_model": model, "cell_count": len(ids),
                         **adjacency_scores(reference_edges, display),
                         "np2": neighborhood_preservation(ids, reference_edges, display, 2)})


def _subset_result(result, selected: set[str]):
    pairs = [(cell_id, geometry) for cell_id, geometry in zip(result.cell_ids, result.geometries) if cell_id in selected]
    return [item[0] for item in pairs], [item[1] for item in pairs]


def _clipping_sensitivity(region: str, boundary, inner: float, outer: float,
                          thresholds: list[float], rows: list[dict]) -> None:
    reference = load_region_reference(ROOT / "data/processed/regions", region)
    fraction = {cell_id: float(polygon.intersection(boundary).area / max(polygon.area, 1e-12))
                for cell_id, polygon in reference.polygons.items()}
    for threshold in thresholds:
        selected = {cell_id for cell_id, value in fraction.items() if value + 1e-12 >= threshold}
        cells = reference.cells[reference.cells.cell_id.astype(str).isin(selected)].copy()
        if len(cells) < 3:
            continue
        variants = {
            "full_macro_cell": {cell_id: reference.polygons[cell_id] for cell_id in selected},
            "province_clipped": {cell_id: reference.polygons[cell_id].intersection(boundary) for cell_id in selected},
        }
        for reference_policy, polygons in variants.items():
            ids = cells.cell_id.astype(str).tolist()
            if reference_policy == "full_macro_cell":
                reference_edges = grid_edges(cells)
            else:
                lengths = shared_boundary_lengths(ids, [polygons[cell_id] for cell_id in ids], tolerance=1e-8)
                reference_edges = set(lengths)
            paths = [ROOT / "results/spatial" / region / filename for filename in FILES]
            paths.extend(ROOT / "results/spatial_refined" / region / f"final_refined_{view}.geojson"
                         for view in ("disk", "annulus"))
            for path in paths:
                result = load_geometry(path, inner, outer)
                result_ids, result_geometries = _subset_result(result, selected)
                display = display_adjacency(result_ids, result_geometries)
                rows.append({
                    "region": region, "method": result.method, "view": result.view,
                    "reference_policy": reference_policy, "inclusion_threshold": threshold,
                    "cell_count": len(ids), "mean_inclusion_fraction": float(cells.cell_id.astype(str).map(fraction).mean()),
                    **adjacency_scores(reference_edges, display),
                    "np2": neighborhood_preservation(ids, reference_edges, display, 2),
                })


def main() -> None:
    ensure_output_dirs(); config = geometry_config(); phase2 = experiment_config()["phase2"]; boundaries, _ = project_boundaries()
    inner, outer = float(config["annulus_inner"]), float(config["annulus_outer"])
    neighbor_rows: list[dict] = []; clipping_rows: list[dict] = []
    for region in config["regions"]:
        _neighbor_sensitivity(region, ROOT / "data/processed/regions", ROOT / "results/spatial", ROOT / "results/spatial_refined",
                              inner, outer, neighbor_rows)
        _clipping_sensitivity(region, boundaries[region], inner, outer,
                              [float(value) for value in phase2["inclusion_thresholds"]], clipping_rows)
        print("[reference sensitivity]", region, flush=True)
    _neighbor_sensitivity("NCEP-AirTemp-Africa-2000", ROOT / "data/processed/external_regions",
                          ROOT / "results/external_spatial", ROOT / "results/external_refined", inner, outer, neighbor_rows)
    neighbor = pd.DataFrame(neighbor_rows); clipping = pd.DataFrame(clipping_rows)
    write_csv(neighbor, ROOT / "results/tables/Table_neighbor_model_sensitivity.csv")
    write_csv(clipping, ROOT / "results/tables/Table_reference_clipping_sensitivity.csv")
    neighbor_summary = neighbor.groupby(["method", "view", "neighbor_model"], as_index=False).agg(
        adj_precision=("adj_precision", "mean"), adj_recall=("adj_recall", "mean"),
        adj_f1=("adj_f1", "mean"), np2=("np2", "mean"))
    clipping_summary = clipping.groupby(
        ["method", "view", "reference_policy", "inclusion_threshold"], as_index=False
    ).agg(cell_count=("cell_count", "mean"), adj_f1=("adj_f1", "mean"), np2=("np2", "mean"))
    write_csv(neighbor_summary, ROOT / "paper/tables/Table_neighbor_model_sensitivity.csv")
    write_csv(clipping_summary, ROOT / "paper/tables/Table_reference_clipping_sensitivity.csv")
    write_json({
        "neighbor_models": {"4-neighbor": "rook/grid-edge contact", "8-neighbor": "rook plus diagonal queen contact"},
        "inclusion_thresholds": phase2["inclusion_thresholds"],
        "reference_policies": phase2["reference_policies"],
        "selection_note": "All thresholds and both reference policies were declared before comparing outcomes.",
    }, ROOT / "results/sensitivity/reference_sensitivity_manifest.json")
    print(neighbor_summary.to_string(index=False))


if __name__ == "__main__":
    main()
