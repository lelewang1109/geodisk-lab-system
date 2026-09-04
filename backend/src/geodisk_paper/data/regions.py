from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass
from pathlib import Path
import math

import numpy as np
import pandas as pd
import xarray as xr
from shapely.geometry import LineString, Point, Polygon, shape

from .adapters import DailyNetCDFAdapter, DatasetSchema
from geodisk_paper.utils.io import read_json, write_csv, write_geojson, write_json

EARTH_RADIUS_KM = 6371.0088


def load_boundaries(path: str | Path) -> tuple[dict[str, Polygon], dict[str, str]]:
    obj = read_json(path)
    geometries, english = {}, {}
    for feature in obj["features"]:
        name = str(feature["properties"]["name"])
        geom = shape(feature["geometry"])
        if not geom.is_valid or geom.is_empty:
            raise ValueError(f"Invalid boundary for {name}")
        geometries[name] = geom
        english[name] = str(feature["properties"].get("name_en", name))
    return geometries, english


def _local_xy(lon, lat, lon0: float, lat0: float):
    x = (np.asarray(lon, float) - lon0) * math.cos(math.radians(lat0))
    y = np.asarray(lat, float) - lat0
    return x, y


def _boundary_radius(polygon: Polygon, anchor: tuple[float, float], theta: float) -> float:
    lon0, lat0 = anchor
    c = max(math.cos(math.radians(lat0)), 1e-8)
    far = (lon0 + 40.0 * math.cos(theta) / c, lat0 + 40.0 * math.sin(theta))
    intersection = LineString([anchor, far]).intersection(polygon.boundary)
    candidates = []
    for geom in getattr(intersection, "geoms", [intersection]):
        if geom.is_empty:
            continue
        coords = []
        if geom.geom_type == "Point":
            coords = [(geom.x, geom.y)]
        elif geom.geom_type == "LineString":
            coords = [geom.coords[0], geom.coords[-1]]
        for lon, lat in coords:
            x, y = _local_xy(lon, lat, lon0, lat0)
            radius = float(np.hypot(x, y))
            if radius > 1e-9:
                candidates.append(radius)
    if not candidates:
        return max(float(math.sqrt(polygon.area / math.pi)), 1e-8)
    return max(candidates)


def grid_edges(cells: pd.DataFrame) -> set[tuple[str, str]]:
    by_position = {(int(r.block_row), int(r.block_col)): str(r.cell_id) for r in cells.itertuples()}
    edges: set[tuple[str, str]] = set()
    for (row, col), cell_id in by_position.items():
        for key in ((row + 1, col), (row, col + 1)):
            other = by_position.get(key)
            if other is not None:
                edges.add(tuple(sorted((cell_id, other))))
    return edges


def boundary_flags(
    cells: pd.DataFrame,
    polygons: dict[str, Polygon],
    edges: set[tuple[str, str]],
    geographic_boundary,
    *,
    geographic_tolerance: float,
) -> tuple[dict[str, bool], dict[str, bool]]:
    """Return frozen topological and geographic boundary classifications.

    Topological boundary is defined against the default four-neighbor reference
    graph. Geographic boundary means that the (unclipped) stable macro-cell
    intersects, touches, or lies within the declared numerical tolerance of the
    real region boundary. Both definitions are deterministic and are stored at
    preprocessing time rather than inferred during evaluation.
    """
    degree = {str(cell_id): 0 for cell_id in cells.cell_id.astype(str)}
    for left, right in sorted(edges):
        degree[left] += 1
        degree[right] += 1
    topological = {cell_id: value < 4 for cell_id, value in degree.items()}
    boundary_line = geographic_boundary.boundary
    geographic = {
        cell_id: bool(
            polygons[cell_id].intersects(boundary_line)
            or polygons[cell_id].distance(boundary_line) <= geographic_tolerance
        )
        for cell_id in degree
    }
    return topological, geographic


def k_hop_neighborhoods(cell_ids: list[str], edges: set[tuple[str, str]], maximum: int = 3) -> dict[str, dict[str, list[str]]]:
    graph = {cell_id: set() for cell_id in cell_ids}
    for left, right in sorted(edges):
        graph[left].add(right)
        graph[right].add(left)
    output: dict[str, dict[str, list[str]]] = {}
    for start in cell_ids:
        distance = {start: 0}
        queue = deque([start])
        while queue:
            current = queue.popleft()
            if distance[current] == maximum:
                continue
            for nxt in sorted(graph[current]):
                if nxt not in distance:
                    distance[nxt] = distance[current] + 1
                    queue.append(nxt)
        output[start] = {
            f"hop_{k}": sorted(node for node, d in distance.items() if 0 < d <= k)
            for k in range(1, maximum + 1)
        }
    return output


@dataclass
class RegionReference:
    name: str
    cells: pd.DataFrame
    polygons: dict[str, Polygon]
    edges: set[tuple[str, str]]
    anchor: tuple[float, float]


def prepare_region_references(
    adapter: DailyNetCDFAdapter,
    schema: DatasetSchema,
    boundaries: dict[str, Polygon],
    region_names: list[str],
    output_root: str | Path,
    *,
    coarsen_factor: int,
    min_valid_fraction: float,
) -> dict[str, RegionReference]:
    output_root = Path(output_root)
    files = adapter.files()
    lat, lon = adapter.coordinates(files[0], schema)
    dlat = float(np.median(np.diff(lat)))
    dlon = float(np.median(np.diff(lon)))
    lon_grid, lat_grid = np.meshgrid(lon, lat)
    first = adapter.read_scalar(files[0], schema)

    definitions: dict[str, dict] = {}
    for region in region_names:
        polygon = boundaries[region]
        minx, miny, maxx, maxy = polygon.bounds
        candidate = ((lon_grid >= minx) & (lon_grid <= maxx) & (lat_grid >= miny) & (lat_grid <= maxy))
        inside = np.zeros(candidate.shape, dtype=bool)
        for row, col in np.argwhere(candidate):
            point = Point(float(lon_grid[row, col]), float(lat_grid[row, col]))
            inside[row, col] = polygon.contains(point) or polygon.touches(point)
        inside &= np.isfinite(first)
        groups: dict[tuple[int, int], list[tuple[int, int]]] = defaultdict(list)
        for row, col in np.argwhere(inside):
            groups[(int(row // coarsen_factor), int(col // coarsen_factor))].append((int(row), int(col)))
        kept = {}
        for (block_row, block_col), indices in groups.items():
            denominator = coarsen_factor * coarsen_factor
            if len(indices) / denominator >= min_valid_fraction:
                kept[(block_row, block_col)] = indices
        if not kept:
            raise ValueError(f"No stable macro-cells remain for {region}")
        definitions[region] = {"polygon": polygon, "blocks": kept}

    accumulators: dict[str, dict[tuple[int, int], list[float]]] = {
        region: {key: [] for key in value["blocks"]} for region, value in definitions.items()
    }
    monthly: dict[str, dict[tuple[int, int], dict[int, list[float]]]] = {
        region: {key: defaultdict(list) for key in value["blocks"]} for region, value in definitions.items()
    }
    for file_index, path in enumerate(files):
        field = adapter.read_scalar(path, schema)
        month = int(path.stem[4:6])
        for region, definition in definitions.items():
            for key, indices in definition["blocks"].items():
                values = np.asarray([field[row, col] for row, col in indices], float)
                value = float(np.nanmean(values)) if np.isfinite(values).any() else np.nan
                accumulators[region][key].append(value)
                monthly[region][key][month].append(value)
        if (file_index + 1) % 75 == 0:
            print(f"[prepare] PM2.5 aggregation {file_index + 1}/{len(files)} files", flush=True)

    references = {}
    for region, definition in definitions.items():
        polygon: Polygon = definition["polygon"]
        rp = polygon.representative_point()
        anchor = (float(rp.x), float(rp.y))
        rows, polygons = [], {}
        for (block_row, block_col), indices in sorted(definition["blocks"].items()):
            values = np.asarray(accumulators[region][(block_row, block_col)], float)
            if not np.isfinite(values).all():
                raise ValueError(f"Temporal missing value in retained cell {region}/{block_row}/{block_col}")
            raw_rows = np.asarray([item[0] for item in indices])
            raw_cols = np.asarray([item[1] for item in indices])
            center_lon = float(np.mean(lon[raw_cols]))
            center_lat = float(np.mean(lat[raw_rows]))
            left = float(lon[block_col * coarsen_factor] - dlon / 2)
            right_index = min((block_col + 1) * coarsen_factor - 1, len(lon) - 1)
            right = float(lon[right_index] + dlon / 2)
            bottom = float(lat[block_row * coarsen_factor] - dlat / 2)
            top_index = min((block_row + 1) * coarsen_factor - 1, len(lat) - 1)
            top = float(lat[top_index] + dlat / 2)
            cell_polygon = Polygon([(left, bottom), (right, bottom), (right, top), (left, top)])
            cell_id = f"CEG2000_f{coarsen_factor}_r{block_row:04d}_c{block_col:04d}"
            x, y = _local_xy(center_lon, center_lat, *anchor)
            theta = float(math.atan2(float(y), float(x)))
            radius = float(np.hypot(x, y))
            rho = float(np.clip(radius / _boundary_radius(polygon, anchor, theta), 0, 1))
            area = EARTH_RADIUS_KM**2 * math.radians(abs(right - left)) * abs(
                math.sin(math.radians(top)) - math.sin(math.radians(bottom))
            )
            month_values = {
                f"month_{m:02d}_pm25": float(np.mean(monthly[region][(block_row, block_col)][m]))
                for m in range(1, 13)
            }
            rows.append({
                "cell_id": cell_id, "region_id": region, "block_row": block_row, "block_col": block_col,
                "longitude": center_lon, "latitude": center_lat, "theta": theta, "rho": rho,
                "original_area_km2": area, "annual_mean_pm25": float(np.mean(values)),
                "fine_point_count": len(indices), **month_values,
            })
            polygons[cell_id] = cell_polygon
        cells = pd.DataFrame(rows)
        edges = grid_edges(cells)
        geographic_tolerance = max(abs(dlon), abs(dlat), 1.0) * 1e-9
        topological_boundary, geographic_boundary = boundary_flags(
            cells, polygons, edges, polygon, geographic_tolerance=geographic_tolerance,
        )
        cells["reference_degree"] = cells.cell_id.astype(str).map(
            {cell_id: sum(cell_id in edge for edge in edges) for cell_id in cells.cell_id.astype(str)}
        ).astype(int)
        cells["is_topological_boundary"] = cells.cell_id.astype(str).map(topological_boundary).astype(bool)
        cells["is_geographic_boundary"] = cells.cell_id.astype(str).map(geographic_boundary).astype(bool)
        ids = cells.cell_id.astype(str).tolist()
        neighborhoods = k_hop_neighborhoods(ids, edges, 3)
        centroid_by_id = {str(row.cell_id): (float(row.longitude), float(row.latitude)) for row in cells.itertuples()}
        direction_rows = []
        for left_id, right_id in sorted(edges):
            for source, target in ((left_id, right_id), (right_id, left_id)):
                sx, sy = centroid_by_id[source]
                tx, ty = centroid_by_id[target]
                dx, dy = _local_xy(tx, ty, sx, sy)
                direction_rows.append({"source": source, "target": target, "angle_rad": math.atan2(float(dy), float(dx))})

        region_dir = output_root / region
        write_csv(cells.assign(polygon_wkt=cells.cell_id.map(lambda i: polygons[i].wkt)), region_dir / "cells.csv")
        write_geojson(((i, polygons[i], {"region_id": region}) for i in ids), region_dir / "original_geometry.geojson")
        write_csv(pd.DataFrame(sorted(edges), columns=["source", "target"]), region_dir / "original_adjacency.csv")
        write_csv(pd.DataFrame(direction_rows), region_dir / "original_local_directions.csv")
        write_json(neighborhoods, region_dir / "neighborhoods.json")
        write_json({
            "region": region, "cell_count": len(ids), "edge_count": len(edges),
            "anchor": {"longitude": anchor[0], "latitude": anchor[1]},
            "coarsen_factor": coarsen_factor, "source_grid_resolution": {"longitude": dlon, "latitude": dlat},
            "boundary_definitions": {
                "topological": "reference_degree < 4 in the default four-neighbor macro-cell graph",
                "geographic": "unclipped macro-cell intersects/touches or is within tolerance of the real region boundary",
                "geographic_tolerance_degrees": geographic_tolerance,
            },
        }, region_dir / "reference_metadata.json")
        references[region] = RegionReference(region, cells, polygons, edges, anchor)
    return references


def load_region_reference(root: str | Path, region: str) -> RegionReference:
    root = Path(root) / region
    cells = pd.read_csv(root / "cells.csv")
    polygons = {str(row.cell_id): Polygon() for row in cells.itertuples()}
    from shapely import wkt
    polygons = {str(row.cell_id): wkt.loads(row.polygon_wkt) for row in cells.itertuples()}
    edge_frame = pd.read_csv(root / "original_adjacency.csv", dtype=str)
    edges = {tuple(sorted((str(r.source), str(r.target)))) for r in edge_frame.itertuples()}
    metadata = read_json(root / "reference_metadata.json")
    anchor = (float(metadata["anchor"]["longitude"]), float(metadata["anchor"]["latitude"]))
    return RegionReference(region, cells, polygons, edges, anchor)
