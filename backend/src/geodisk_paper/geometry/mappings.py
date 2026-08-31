from __future__ import annotations

from dataclasses import dataclass
import math
import numpy as np
from scipy.sparse import lil_matrix
from scipy.sparse.linalg import spsolve
from shapely.geometry import LineString, Point, Polygon

from geodisk_paper.data.regions import RegionReference
from geodisk_paper.geometry.power import balanced_power_cells, circular_domain, warp_geometry
from geodisk_paper.topology.embedding import TopologyEmbedding, topology_seed_positions


@dataclass
class GeometryResult:
    method: str
    view: str
    cell_ids: list[str]
    geometries: list
    domain: object
    metadata: dict


def _boundary_radius(polygon, anchor, theta):
    lon0, lat0 = anchor
    c = max(math.cos(math.radians(lat0)), 1e-8)
    far = (lon0 + 40*math.cos(theta)/c, lat0 + 40*math.sin(theta))
    intersection = LineString([anchor, far]).intersection(polygon.boundary)
    radii = []
    for geom in getattr(intersection, "geoms", [intersection]):
        if geom.is_empty:
            continue
        points = [(geom.x, geom.y)] if geom.geom_type == "Point" else list(geom.coords) if geom.geom_type == "LineString" else []
        for lon, lat in points:
            radii.append(math.hypot((lon-lon0)*c, lat-lat0))
    return max([value for value in radii if value > 1e-9], default=1.0)


def _map_points(points: np.ndarray, boundary, anchor, view, inner, outer):
    lon0, lat0 = anchor
    cosine = math.cos(math.radians(lat0))
    output = []
    for lon, lat in points:
        x, y = (lon-lon0)*cosine, lat-lat0
        theta = math.atan2(y, x)
        rho = float(np.clip(math.hypot(x, y) / _boundary_radius(boundary, anchor, theta), 0, 1))
        radius = rho if view == "disk" else inner + rho*(outer-inner)
        output.append((radius*math.cos(theta), radius*math.sin(theta)))
    return np.asarray(output, float)


def direct_polar(reference: RegionReference, boundary, view: str, inner=.48, outer=1.0) -> GeometryResult:
    ids = reference.cells.cell_id.astype(str).tolist()
    geometries = []
    for cell_id in ids:
        points = np.asarray(reference.polygons[cell_id].exterior.coords[:-1], float)
        geometries.append(Polygon(_map_points(points, boundary, reference.anchor, view, inner, outer)))
    return GeometryResult("Direct Polar", view, ids, geometries, circular_domain(view, inner, outer),
                          {"initialization": "four_vertex_boundary_ray", "balance": False, "warp": False})


def harmonic_seed_positions(reference: RegionReference, view: str, inner: float, outer: float) -> np.ndarray:
    frame = reference.cells.reset_index(drop=True)
    ids = frame.cell_id.astype(str).tolist()
    index = {cell_id: i for i, cell_id in enumerate(ids)}
    neighbors = [set() for _ in ids]
    for left, right in reference.edges:
        a, b = index[left], index[right]
        neighbors[a].add(b); neighbors[b].add(a)
    theta = frame.theta.to_numpy(float)
    rho = frame.rho.to_numpy(float)
    if "is_boundary" in frame.columns:
        outer_boundary = set(np.flatnonzero(frame.is_boundary.to_numpy(bool)))
    else:
        outer_boundary = {i for i, values in enumerate(neighbors) if len(values) < 4}
    inner_boundary = set()
    if view == "annulus":
        inner_boundary = set(np.argsort(rho)[:max(4, int(round(math.sqrt(len(ids)))))] ) - outer_boundary
    fixed = {}
    for i in outer_boundary:
        fixed[i] = np.asarray([.985*outer*math.cos(theta[i]), .985*outer*math.sin(theta[i])])
    for i in inner_boundary:
        fixed[i] = np.asarray([1.015*inner*math.cos(theta[i]), 1.015*inner*math.sin(theta[i])])
    free = [i for i in range(len(ids)) if i not in fixed]
    free_index = {node: row for row, node in enumerate(free)}
    matrix = lil_matrix((len(free), len(free)), dtype=float)
    rhs = np.zeros((len(free), 2), float)
    for node in free:
        row = free_index[node]
        degree = max(len(neighbors[node]), 1)
        matrix[row, row] = degree + 1e-8
        for other in neighbors[node]:
            if other in fixed:
                rhs[row] += fixed[other]
            else:
                matrix[row, free_index[other]] -= 1.0
    solved = spsolve(matrix.tocsr(), rhs) if free else np.empty((0, 2))
    points = np.zeros((len(ids), 2), float)
    for node, value in fixed.items(): points[node] = value
    for node, value in zip(free, np.asarray(solved)): points[node] = value
    radii = np.hypot(points[:, 0], points[:, 1])
    minimum = inner + .025 if view == "annulus" else .025
    target = np.clip(radii, minimum, outer-.025)
    zero = radii < 1e-9
    points[~zero] *= (target[~zero] / radii[~zero])[:, None]
    points[zero] = np.column_stack([.03*np.cos(theta[zero]), .03*np.sin(theta[zero])]) if zero.any() else points[zero]
    return points


def harmonic_continuous(reference: RegionReference, view: str, inner=.48, outer=1.0) -> GeometryResult:
    ids = reference.cells.cell_id.astype(str).tolist()
    domain = circular_domain(view, inner, outer)
    seeds = harmonic_seed_positions(reference, view, inner, outer)
    cells, _, history = balanced_power_cells(seeds, domain, iterations=0, balance=False)
    return GeometryResult("Harmonic", view, ids, cells, domain,
                          {"seed_mapping": "uniform_graph_laplacian", "partition": "unweighted_voronoi", "history": history})


def geographic_area_balanced(reference: RegionReference, view: str, inner=.48, outer=1.0, iterations=6) -> GeometryResult:
    frame = reference.cells.reset_index(drop=True)
    ids = frame.cell_id.astype(str).tolist()
    theta, rho = frame.theta.to_numpy(float), frame.rho.to_numpy(float)
    radius = rho if view == "disk" else inner + rho*(outer-inner)
    radius = np.clip(radius, .025 if view == "disk" else inner+.015, outer-.015)
    seeds = np.column_stack([radius*np.cos(theta), radius*np.sin(theta)])
    domain = circular_domain(view, inner, outer)
    cells, weights, history = balanced_power_cells(seeds, domain, iterations=iterations, balance=True)
    return GeometryResult("Area-balanced", view, ids, cells, domain,
                          {"initialization": "center_polar", "balance": True, "weight_range": [float(weights.min()), float(weights.max())], "history": history})


def proposed_irregular(
    reference: RegionReference, embedding: TopologyEmbedding, view: str, *, inner=.48, outer=1.0,
    iterations=6, warp_strength=.018, balance=True,
) -> GeometryResult:
    ids = embedding.cell_ids
    domain = circular_domain(view, inner, outer)
    seeds = topology_seed_positions(embedding, reference, view, inner, outer)
    cells, weights, history = balanced_power_cells(seeds, domain, iterations=iterations, balance=balance)
    warped = [warp_geometry(cell, 0.0 if view == "disk" else inner, outer, warp_strength) for cell in cells]
    if any(cell.is_empty or not cell.is_valid for cell in warped):
        warped = cells
        warp_fallback = True
    else:
        warp_fallback = False
    method = "GeoDisk" if view == "disk" else "GeoAnnulus"
    return GeometryResult(method, view, ids, warped, domain, {
        "topology_objective_initial": embedding.initial_objective,
        "topology_objective_final": embedding.final_objective,
        "balance": balance, "warp_strength": warp_strength, "warp_fallback": warp_fallback,
        "weight_range": [float(weights.min()), float(weights.max())], "history": history,
    })
