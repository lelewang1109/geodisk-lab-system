from __future__ import annotations

import math
from typing import Iterable
import numpy as np
from shapely import make_valid
from shapely.geometry import GeometryCollection, MultiPolygon, Point, Polygon


def polygon_parts(geometry) -> list[Polygon]:
    if geometry.is_empty:
        return []
    if isinstance(geometry, Polygon):
        return [geometry]
    if isinstance(geometry, MultiPolygon):
        return list(geometry.geoms)
    if isinstance(geometry, GeometryCollection):
        return [part for item in geometry.geoms for part in polygon_parts(item)]
    return []


def _clip_half_plane(vertices: np.ndarray, normal: np.ndarray, offset: float) -> np.ndarray:
    if not len(vertices):
        return vertices
    output = []
    start = vertices[-1]
    start_inside = float(normal @ start) <= offset + 1e-11
    for end in vertices:
        end_inside = float(normal @ end) <= offset + 1e-11
        if end_inside != start_inside:
            direction = end - start
            denominator = float(normal @ direction)
            if abs(denominator) > 1e-15:
                output.append(start + direction * ((offset - float(normal @ start)) / denominator))
        if end_inside:
            output.append(end)
        start, start_inside = end, end_inside
    return np.asarray(output, float)


def power_cells(points: np.ndarray, weights: np.ndarray, domain, outer_radius: float = 1.0) -> list:
    if len(points) != len(weights):
        raise ValueError("points and weights differ in length")
    squared = np.sum(points * points, axis=1)
    extent = 2.6 * outer_radius
    box = np.asarray([[-extent, -extent], [extent, -extent], [extent, extent], [-extent, extent]], float)
    cells = []
    for index, point in enumerate(points):
        vertices = box.copy()
        for other_index, other in enumerate(points):
            if index == other_index:
                continue
            normal = 2.0 * (other - point)
            offset = squared[other_index] - weights[other_index] - squared[index] + weights[index]
            vertices = _clip_half_plane(vertices, normal, float(offset))
            if len(vertices) < 3:
                break
        if len(vertices) >= 3:
            candidate = Polygon(vertices)
            if not candidate.is_valid:
                candidate = make_valid(candidate)
            try:
                cells.append(candidate.intersection(domain))
            except Exception:
                # A zero-width numerical sliver can survive make_valid in GEOS;
                # convex_hull is equivalent for an intersection of half-planes.
                cells.append(candidate.convex_hull.intersection(domain))
        else:
            cells.append(GeometryCollection())
    return cells


def balanced_power_cells(
    points: np.ndarray, domain, *, iterations: int = 6, learning_rate: float = 0.18,
    weight_clip: float = 0.08, balance: bool = True,
) -> tuple[list, np.ndarray, list[dict]]:
    weights = np.zeros(len(points), float)
    best_weights = weights.copy()
    best_cv = float("inf")
    history = []
    steps = iterations if balance else 0
    target = domain.area / max(len(points), 1)
    for iteration in range(steps + 1):
        cells = power_cells(points, weights, domain)
        areas = np.asarray([cell.area for cell in cells], float)
        if np.any(areas <= 1e-12):
            break
        cv = float(np.std(areas) / max(np.mean(areas), 1e-12))
        history.append({"iteration": iteration, "area_cv": cv})
        if cv < best_cv:
            best_cv, best_weights = cv, weights.copy()
        if iteration == steps:
            break
        rate = learning_rate if iteration < max(2, steps // 2) else learning_rate * 0.5
        weights += rate * (target - areas)
        weights -= weights.mean()
        weights = np.clip(weights, -weight_clip, weight_clip)
    cells = power_cells(points, best_weights, domain)
    if any(cell.is_empty or cell.area <= 1e-12 for cell in cells):
        best_weights = np.zeros(len(points), float)
        cells = power_cells(points, best_weights, domain)
        if any(cell.is_empty or cell.area <= 1e-12 for cell in cells):
            raise ValueError("Power partition contains an empty cell even after the unweighted fallback")
        history.append({"iteration": -1, "area_cv": float(np.std([c.area for c in cells]) / np.mean([c.area for c in cells]))})
    return cells, best_weights, history


def _densify(coords: Iterable[tuple[float, float]], max_step: float) -> np.ndarray:
    values = np.asarray(list(coords), float)
    output = []
    for start, end in zip(values[:-1], values[1:]):
        count = max(1, int(math.ceil(float(np.linalg.norm(end - start)) / max_step)))
        output.extend(start + (end - start) * (index / count) for index in range(count))
    output.append(values[-1])
    return np.asarray(output, float)


def _warp_points(points: np.ndarray, inner: float, outer: float, strength: float) -> np.ndarray:
    x, y = points[:, 0], points[:, 1]
    radius = np.hypot(x, y)
    theta = np.arctan2(y, x)
    t = np.clip((radius - inner) / max(outer - inner, 1e-12), 0, 1)
    window = np.sin(np.pi * t) ** 2
    fx = 0.58*np.sin(3.1*x + 1.7*y + .4) + .29*np.sin(-4.2*x + 2.6*y + 1.3) + .13*np.sin(7.4*x + 5.1*y - .8)
    fy = .55*np.sin(-2.4*x + 3.7*y + 2.0) + .30*np.sin(4.9*x + 1.9*y - .3) + .15*np.sin(-6.6*x + 5.8*y + .7)
    dr = strength * window * (fx*np.cos(theta) + fy*np.sin(theta))
    dt = .55 * strength * window * (-fx*np.sin(theta) + fy*np.cos(theta))
    rr = np.clip(radius + dr, inner, outer)
    tt = theta + dt
    return np.column_stack([rr*np.cos(tt), rr*np.sin(tt)])


def warp_geometry(geometry, inner: float, outer: float, strength: float, max_step: float = .014):
    if abs(strength) < 1e-15:
        return geometry
    parts = []
    for polygon in polygon_parts(geometry):
        exterior = _warp_points(_densify(polygon.exterior.coords, max_step), inner, outer, strength)
        holes = [_warp_points(_densify(ring.coords, max_step), inner, outer, strength) for ring in polygon.interiors]
        parts.extend(polygon_parts(make_valid(Polygon(exterior, holes))))
    if not parts:
        return GeometryCollection()
    return parts[0] if len(parts) == 1 else MultiPolygon(parts)


def circular_domain(view: str, inner: float = .48, outer: float = 1.0):
    outside = Point(0, 0).buffer(outer, quad_segs=192)
    return outside if view == "disk" else outside.difference(Point(0, 0).buffer(inner, quad_segs=192))
