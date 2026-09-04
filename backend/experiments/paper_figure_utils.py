from __future__ import annotations

import hashlib
import math
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.collections import PatchCollection
from matplotlib.colors import Normalize
from matplotlib.patches import Polygon as MplPolygon
import numpy as np
from shapely.ops import transform

from geodisk_paper.geometry.power import polygon_parts


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def add_polygons(axis, polygons: dict, values: dict[str, float] | None = None, *,
                 cmap="viridis", norm=None, facecolor="#edf2f0", edgecolor="#394a45",
                 linewidth=.22, alpha=1.0):
    patches, colors = [], []
    for cell_id, geometry in polygons.items():
        for part in polygon_parts(geometry):
            patches.append(MplPolygon(np.asarray(part.exterior.coords), closed=True))
            if values is not None:
                colors.append(float(values[cell_id]))
    collection = PatchCollection(patches, cmap=cmap if values is not None else None,
                                 norm=norm, facecolor=facecolor if values is None else None,
                                 edgecolor=edgecolor, linewidth=linewidth, alpha=alpha)
    if values is not None:
        collection.set_array(np.asarray(colors))
    axis.add_collection(collection)
    return collection


def set_geometry_extent(axis, geometries, margin=.04):
    bounds = np.asarray([geometry.bounds for geometry in geometries if not geometry.is_empty], float)
    minx, miny = bounds[:, :2].min(axis=0); maxx, maxy = bounds[:, 2:].max(axis=0)
    dx, dy = max(maxx - minx, 1e-9), max(maxy - miny, 1e-9)
    axis.set_xlim(minx - margin * dx, maxx + margin * dx)
    axis.set_ylim(miny - margin * dy, maxy + margin * dy)
    axis.set_aspect("equal"); axis.set_xticks([]); axis.set_yticks([]); axis.set_frame_on(False)


def centroid_map(polygons: dict) -> dict[str, tuple[float, float]]:
    return {cell_id: (float(geometry.centroid.x), float(geometry.centroid.y))
            for cell_id, geometry in polygons.items()}


def draw_edges(axis, positions: dict[str, tuple[float, float]], edges, *, color="#78908a",
               linewidth=.35, alpha=.6, zorder=3):
    for left, right in sorted(edges):
        if left not in positions or right not in positions:
            continue
        axis.plot([positions[left][0], positions[right][0]],
                  [positions[left][1], positions[right][1]],
                  color=color, linewidth=linewidth, alpha=alpha, zorder=zorder)


def radial_remap_geometry(geometry, source_inner: float, source_outer: float,
                          target_inner: float, target_outer: float):
    """Radially remap one canonical annulus without changing angular order."""
    source_span = max(source_outer - source_inner, 1e-12)

    def mapping(x, y, z=None):
        x = np.asarray(x, float); y = np.asarray(y, float)
        radius = np.hypot(x, y); theta = np.arctan2(y, x)
        fraction = np.clip((radius - source_inner) / source_span, 0.0, 1.0)
        target = target_inner + fraction * (target_outer - target_inner)
        mapped = (target * np.cos(theta), target * np.sin(theta))
        return (*mapped, z) if z is not None else mapped

    return transform(mapping, geometry)


def integrated_band_geometries(polygons: dict, source_inner: float, source_outer: float,
                               band_inner: float, band_outer: float) -> dict:
    return {cell_id: radial_remap_geometry(geometry, source_inner, source_outer, band_inner, band_outer)
            for cell_id, geometry in polygons.items()}


def polar_label_position(radius: float, angle: float) -> tuple[float, float]:
    return radius * math.cos(angle), radius * math.sin(angle)
