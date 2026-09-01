from __future__ import annotations

from itertools import combinations
import numpy as np
from shapely import make_valid
from shapely.errors import GEOSException
from shapely.geometry import Point
from shapely.ops import unary_union
from shapely.strtree import STRtree


def display_adjacency(cell_ids: list[str], geometries: list, tolerance: float = 2e-5) -> set[tuple[str, str]]:
    if len(cell_ids) != len(geometries):
        raise ValueError("cell_ids and geometries differ in length")
    tree = STRtree(geometries)
    edges: set[tuple[str, str]] = set()
    for left, geom in enumerate(geometries):
        if geom is None or geom.is_empty or geom.boundary is None:
            continue
        query = tree.query(geom.buffer(tolerance))
        for right in np.sort(np.asarray(query, dtype=int)):
            if int(right) <= left:
                continue
            other = geometries[int(right)]
            if other is None or other.is_empty or other.boundary is None:
                continue
            if geom.boundary.distance(other.boundary) <= tolerance:
                shared = geom.boundary.buffer(tolerance, cap_style=2).intersection(
                    other.boundary.buffer(tolerance, cap_style=2)
                ).area
                if shared > 4 * tolerance * tolerance:
                    edges.add(tuple(sorted((cell_ids[left], cell_ids[int(right)]))))
    return edges


def shared_boundary_lengths(
    cell_ids: list[str], geometries: list, tolerance: float = 2e-5,
) -> dict[tuple[str, str], float]:
    """Return internal shared-boundary length for every displayed contact.

    Exact boundary intersections are used whenever possible.  A buffer-area
    approximation is used only for numerically separated boundaries that are
    still within the declared contact tolerance.
    """
    if len(cell_ids) != len(geometries):
        raise ValueError("cell_ids and geometries differ in length")
    safe_geometries = [make_valid(geometry) if geometry is not None and not geometry.is_empty and not geometry.is_valid else geometry
                       for geometry in geometries]
    tree = STRtree(safe_geometries)
    lengths: dict[tuple[str, str], float] = {}
    for left, geom in enumerate(safe_geometries):
        if geom is None or geom.is_empty or geom.boundary is None:
            continue
        for right in np.sort(np.asarray(tree.query(geom.buffer(tolerance)), dtype=int)):
            right = int(right)
            if right <= left:
                continue
            other = safe_geometries[right]
            if other is None or other.is_empty or other.boundary is None:
                continue
            exact = float(geom.boundary.intersection(other.boundary).length)
            if exact <= tolerance and geom.boundary.distance(other.boundary) <= tolerance:
                overlap_area = float(
                    geom.boundary.buffer(tolerance, cap_style=2).intersection(
                        other.boundary.buffer(tolerance, cap_style=2)
                    ).area
                )
                approximate = max(0.0, overlap_area / max(2.0 * tolerance, 1e-12))
                length = max(exact, approximate)
            else:
                length = exact
            if length > 2.0 * tolerance:
                lengths[tuple(sorted((cell_ids[left], cell_ids[right])))] = length
    return lengths


def geometry_validity(geometries: list, domain) -> dict[str, float]:
    areas = np.asarray([geom.area for geom in geometries], float)
    invalid = sum(geom.is_empty or not geom.is_valid or geom.area <= 1e-12 for geom in geometries)
    valid_geometries = [make_valid(geom) if not geom.is_valid else geom for geom in geometries if not geom.is_empty]
    union = unary_union(valid_geometries) if valid_geometries else Point().buffer(0)
    domain_area = max(float(domain.area), 1e-12)
    overlap = max(0.0, float(areas.sum()) - float(union.area))
    try:
        covered = union.intersection(domain).area
    except GEOSException:
        repaired_union = make_valid(union)
        repaired_domain = make_valid(domain)
        try:
            covered = repaired_union.intersection(repaired_domain).area
        except GEOSException:
            covered = repaired_union.buffer(0).intersection(repaired_domain.buffer(0)).area
    gap = max(0.0, domain.area - covered)
    return {
        "area_cv": float(np.std(areas) / max(np.mean(areas), 1e-12)),
        "overlap_ratio": float(overlap / domain_area),
        "gap_ratio": float(gap / domain_area),
        "invalid_polygon_count": int(invalid),
    }


def edge_jaccard(left: set[tuple[str, str]], right: set[tuple[str, str]]) -> float:
    union = left | right
    return len(left & right) / len(union) if union else 1.0
