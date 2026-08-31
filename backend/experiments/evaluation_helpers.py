from __future__ import annotations

from geodisk_paper.metrics.geometry import display_adjacency, geometry_validity
from geodisk_paper.metrics.spatial import evaluate_spatial


def evaluate_result(reference, result) -> dict:
    edges = display_adjacency(result.cell_ids, result.geometries)
    source = {str(r.cell_id): (float(r.longitude), float(r.latitude)) for r in reference.cells.itertuples()}
    target = {cell_id: (float(geometry.centroid.x), float(geometry.centroid.y))
              for cell_id, geometry in zip(result.cell_ids, result.geometries)}
    theta = {str(r.cell_id): float(r.theta) for r in reference.cells.itertuples()}
    rho = {str(r.cell_id): float(r.rho) for r in reference.cells.itertuples()}
    return {
        **evaluate_spatial(result.cell_ids, reference.edges, edges, source, target, theta, rho, reference.anchor[1]),
        **geometry_validity(result.geometries, result.domain),
    }

