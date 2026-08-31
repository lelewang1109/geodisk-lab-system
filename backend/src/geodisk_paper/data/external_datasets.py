from __future__ import annotations

from collections import defaultdict
from io import BytesIO
import math
from pathlib import Path
from zipfile import ZipFile

import numpy as np
import pandas as pd
import shapefile
import xarray as xr
from shapely import make_valid
from shapely.geometry import Point, Polygon, shape
from shapely.ops import unary_union
from shapely.strtree import STRtree

from geodisk_paper.data.regions import RegionReference, _boundary_radius, _local_xy, grid_edges, k_hop_neighborhoods
from geodisk_paper.utils.io import write_csv, write_geojson, write_json


def _largest_polygon(geometry):
    geometry = make_valid(geometry)
    if geometry.geom_type == "Polygon":
        return geometry
    parts = [part for part in getattr(geometry, "geoms", []) if part.geom_type == "Polygon"]
    if not parts:
        raise ValueError("Feature contains no polygon component")
    return max(parts, key=lambda part: part.area)


def read_natural_earth_africa(zip_path: str | Path) -> tuple[dict[str, Polygon], dict[str, dict], dict]:
    with ZipFile(zip_path) as archive:
        shp_name = next(name for name in archive.namelist() if name.endswith(".shp"))
        stem = shp_name[:-4]
        reader = shapefile.Reader(
            shp=BytesIO(archive.read(stem + ".shp")),
            shx=BytesIO(archive.read(stem + ".shx")),
            dbf=BytesIO(archive.read(stem + ".dbf")), encoding="utf-8",
        )
        version_name = next(name for name in archive.namelist() if name.endswith(".VERSION.txt"))
        version = archive.read(version_name).decode("utf-8", errors="replace").strip()
        polygons, attributes = {}, {}
        for item in reader.iterShapeRecords():
            record = item.record.as_dict()
            if record.get("CONTINENT") != "Africa":
                continue
            cell_id = str(record["ADM0_A3"])
            polygons[cell_id] = _largest_polygon(shape(item.shape.__geo_interface__))
            attributes[cell_id] = {
                "name": str(record.get("NAME_EN") or record.get("NAME")),
                "type": str(record.get("TYPE", "")),
                "population_estimate": float(record.get("POP_EST", np.nan)),
                "population_year": int(record.get("POP_YEAR", -1)),
                "gdp_million_usd": float(record.get("GDP_MD", np.nan)),
                "gdp_year": int(record.get("GDP_YEAR", -1)),
            }
    return polygons, attributes, {"natural_earth_version": version, "feature_count_africa": len(polygons)}


def shared_boundary_edges(ids: list[str], polygons: list, minimum_length: float = .01) -> set[tuple[str, str]]:
    tree = STRtree(polygons)
    edges = set()
    for left, polygon in enumerate(polygons):
        for right in np.asarray(tree.query(polygon), dtype=int):
            right = int(right)
            if right <= left:
                continue
            length = polygon.boundary.intersection(polygons[right].boundary).length
            if length >= minimum_length:
                edges.add(tuple(sorted((ids[left], ids[right]))))
    return edges


def _largest_connected_component(ids: list[str], edges: set[tuple[str, str]]) -> set[str]:
    graph = {cell_id: set() for cell_id in ids}
    for left, right in edges:
        graph[left].add(right); graph[right].add(left)
    components, seen = [], set()
    for start in ids:
        if start in seen:
            continue
        stack, component = [start], set()
        while stack:
            node = stack.pop()
            if node in component:
                continue
            component.add(node); seen.add(node); stack.extend(graph[node] - component)
        components.append(component)
    return max(components, key=len)


def _write_reference(reference: RegionReference, output_dir: Path, metadata: dict) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    ids = reference.cells.cell_id.astype(str).tolist()
    cells = reference.cells.copy()
    cells["polygon_wkt"] = cells.cell_id.map(lambda cell_id: reference.polygons[str(cell_id)].wkt)
    write_csv(cells, output_dir / "cells.csv")
    write_geojson(((cell_id, reference.polygons[cell_id], {"region_id": reference.name}) for cell_id in ids),
                  output_dir / "original_geometry.geojson")
    write_csv(pd.DataFrame(sorted(reference.edges), columns=["source", "target"]), output_dir / "original_adjacency.csv")
    write_json(k_hop_neighborhoods(ids, reference.edges, 3), output_dir / "neighborhoods.json")
    by_id = {str(row.cell_id): (float(row.longitude), float(row.latitude)) for row in cells.itertuples()}
    directions = []
    for left, right in sorted(reference.edges):
        for source, target in ((left, right), (right, left)):
            sx, sy = by_id[source]; tx, ty = by_id[target]
            dx, dy = _local_xy(tx, ty, sx, sy)
            directions.append({"source": source, "target": target, "angle_rad": math.atan2(float(dy), float(dx))})
    write_csv(pd.DataFrame(directions), output_dir / "original_local_directions.csv")
    write_json({"region": reference.name, "cell_count": len(ids), "edge_count": len(reference.edges),
                "anchor": {"longitude": reference.anchor[0], "latitude": reference.anchor[1]}, **metadata},
               output_dir / "reference_metadata.json")


def prepare_natural_earth_reference(zip_path: str | Path, output_root: str | Path) -> tuple[RegionReference, object, dict]:
    all_polygons, attributes, source_meta = read_natural_earth_africa(zip_path)
    all_ids = sorted(all_polygons)
    all_edges = shared_boundary_edges(all_ids, [all_polygons[cell_id] for cell_id in all_ids])
    selected = _largest_connected_component(all_ids, all_edges)
    excluded = sorted(set(all_ids) - selected)
    ids = sorted(selected)
    polygons = {cell_id: all_polygons[cell_id] for cell_id in ids}
    edges = {edge for edge in all_edges if edge[0] in selected and edge[1] in selected}
    domain = unary_union(list(polygons.values()))
    anchor_point = domain.representative_point(); anchor = (float(anchor_point.x), float(anchor_point.y))
    rows = []
    for cell_id in ids:
        polygon = polygons[cell_id]
        point = polygon.representative_point()
        x, y = _local_xy(point.x, point.y, *anchor)
        theta = math.atan2(float(y), float(x))
        rho = float(np.clip(math.hypot(x, y) / _boundary_radius(domain, anchor, theta), 0, 1))
        boundary_length = polygon.boundary.intersection(domain.boundary).length
        attrs = attributes[cell_id]
        rows.append({"cell_id": cell_id, "region_id": "NE-Admin0-Africa", "block_row": -1, "block_col": -1,
                     "longitude": float(point.x), "latitude": float(point.y), "theta": theta, "rho": rho,
                     "original_area_degree2": float(polygon.area), "is_boundary": boundary_length > .01,
                     "scalar_value": math.log10(max(attrs["population_estimate"], 1.0)), **attrs})
    reference = RegionReference("NE-Admin0-Africa", pd.DataFrame(rows), polygons, edges, anchor)
    metadata = {**source_meta, "source_kind": "irregular_areal_polygons", "adjacency": "shared_boundary_length>=0.01_degree",
                "component_policy": "largest adjacency-connected component fixed before evaluation", "excluded_ids": excluded}
    _write_reference(reference, Path(output_root) / reference.name, metadata)
    return reference, domain, metadata


def prepare_ncep_africa_reference(netcdf_path: str | Path, africa_domain, output_root: str | Path) -> tuple[RegionReference, object, dict]:
    with xr.open_dataset(netcdf_path) as dataset:
        if "air" not in dataset.data_vars or tuple(dataset.air.dims) != ("time", "lat", "lon"):
            raise ValueError(f"Unexpected NCEP schema: {dataset}")
        if dataset.sizes["time"] != 12:
            raise ValueError(f"Expected 12 months, found {dataset.sizes['time']}")
        lats = dataset.lat.values.astype(float)
        lons = dataset.lon.values.astype(float)
        lons = np.where(lons > 180, lons - 360, lons)
        lon_order = np.argsort(lons); lat_order = np.argsort(lats)
        lons, lats = lons[lon_order], lats[lat_order]
        field = dataset.air.values[:, lat_order][:, :, lon_order].astype(float)
        units = str(dataset.air.attrs.get("units", ""))
        times = [str(value.astype("datetime64[M]")) for value in dataset.time.values]
    dlon, dlat = float(np.median(np.diff(lons))), float(np.median(np.diff(lats)))
    rows, polygons = [], {}
    for row, lat in enumerate(lats):
        for col, lon in enumerate(lons):
            point = Point(float(lon), float(lat))
            if not (africa_domain.contains(point) or africa_domain.touches(point)):
                continue
            cell_id = f"NCEP2000_r{row:03d}_c{col:03d}"
            polygon = Polygon([(lon-dlon/2, lat-dlat/2), (lon+dlon/2, lat-dlat/2),
                               (lon+dlon/2, lat+dlat/2), (lon-dlon/2, lat+dlat/2)])
            polygons[cell_id] = polygon
            values = field[:, row, col]
            rows.append({"cell_id": cell_id, "region_id": "NCEP-AirTemp-Africa-2000", "block_row": row, "block_col": col,
                         "longitude": lon, "latitude": lat, "scalar_value": float(np.mean(values)),
                         **{f"month_{month+1:02d}_air_temp_c": float(values[month]) for month in range(12)}})
    cells = pd.DataFrame(rows)
    edges = grid_edges(cells)
    connected = _largest_connected_component(cells.cell_id.astype(str).tolist(), edges)
    cells = cells[cells.cell_id.isin(connected)].copy().reset_index(drop=True)
    polygons = {cell_id: polygons[cell_id] for cell_id in cells.cell_id.astype(str)}
    edges = {edge for edge in edges if edge[0] in connected and edge[1] in connected}
    union = unary_union(list(polygons.values()))
    anchor_point = union.representative_point(); anchor = (float(anchor_point.x), float(anchor_point.y))
    theta_values, rho_values, boundary_values = [], [], []
    for row in cells.itertuples():
        x, y = _local_xy(row.longitude, row.latitude, *anchor)
        theta = math.atan2(float(y), float(x))
        theta_values.append(theta)
        rho_values.append(float(np.clip(math.hypot(x, y) / _boundary_radius(union, anchor, theta), 0, 1)))
        boundary_values.append(len([edge for edge in edges if row.cell_id in edge]) < 4)
    cells["theta"], cells["rho"], cells["is_boundary"] = theta_values, rho_values, boundary_values
    cells["original_area_degree2"] = dlon * dlat
    reference = RegionReference("NCEP-AirTemp-Africa-2000", cells, polygons, edges, anchor)
    metadata = {"source_kind": "regular_grid_netcdf", "variable": "air", "units": units, "time_values": times,
                "grid_resolution_degree": [dlat, dlon], "component_policy": "largest 4-neighbor component",
                "source_subset_shape": [12, len(lats), len(lons)]}
    _write_reference(reference, Path(output_root) / reference.name, metadata)
    return reference, union, metadata


def prepare_exoplanet_sky_reference(csv_path: str | Path, output_root: str | Path,
                                    ra_bins: int = 18, dec_bins: int = 9) -> tuple[RegionReference, object, dict]:
    source = pd.read_csv(csv_path)
    required = {"pl_name", "ra", "dec", "pl_rade", "disc_year", "discoverymethod"}
    if not required.issubset(source.columns):
        raise ValueError(f"Unexpected NASA Exoplanet Archive schema: {sorted(source.columns)}")
    source = source[np.isfinite(source.ra) & np.isfinite(source.dec)].copy()
    source["sky_lon"] = ((source.ra.astype(float) + 180.0) % 360.0) - 180.0
    ra_edges = np.linspace(-180.0, 180.0, ra_bins + 1)
    sin_edges = np.linspace(-1.0, 1.0, dec_bins + 1)
    dec_edges = np.degrees(np.arcsin(sin_edges))
    source["block_col"] = np.clip(np.searchsorted(ra_edges, source.sky_lon, side="right") - 1, 0, ra_bins - 1)
    source["block_row"] = np.clip(np.searchsorted(dec_edges, source.dec, side="right") - 1, 0, dec_bins - 1)
    rows, polygons = [], {}
    for row in range(dec_bins):
        sin_center = .5 * (sin_edges[row] + sin_edges[row + 1])
        dec_center = float(np.degrees(np.arcsin(sin_center)))
        for col in range(ra_bins):
            cell_id = f"NASA_EXO_r{row:02d}_c{col:02d}"
            subset = source[(source.block_row == row) & (source.block_col == col)]
            lon_left, lon_right = float(ra_edges[col]), float(ra_edges[col + 1])
            dec_bottom, dec_top = float(dec_edges[row]), float(dec_edges[row + 1])
            lon_center = .5 * (lon_left + lon_right)
            polygons[cell_id] = Polygon([(lon_left, dec_bottom), (lon_right, dec_bottom),
                                         (lon_right, dec_top), (lon_left, dec_top)])
            radii = pd.to_numeric(subset.pl_rade, errors="coerce")
            years = pd.to_numeric(subset.disc_year, errors="coerce")
            rows.append({
                "cell_id": cell_id, "region_id": "NASA-Exoplanet-SkyGrid",
                "block_row": row, "block_col": col, "longitude": lon_center, "latitude": dec_center,
                "planet_count": int(len(subset)), "scalar_value": float(np.log1p(len(subset))),
                "mean_planet_radius_earth": float(radii.mean()) if radii.notna().any() else np.nan,
                "median_discovery_year": float(years.median()) if years.notna().any() else np.nan,
                "transit_fraction": float((subset.discoverymethod == "Transit").mean()) if len(subset) else 0.0,
                "original_area_equal_solid_angle": float((ra_edges[col + 1] - ra_edges[col]) *
                                                         (sin_edges[row + 1] - sin_edges[row])),
                "is_boundary": row in {0, dec_bins - 1},
            })
    cells = pd.DataFrame(rows)
    edges: set[tuple[str, str]] = set()
    by_position = {(int(item.block_row), int(item.block_col)): str(item.cell_id) for item in cells.itertuples()}
    for (row, col), cell_id in by_position.items():
        east = by_position[(row, (col + 1) % ra_bins)]
        edges.add(tuple(sorted((cell_id, east))))
        if row + 1 < dec_bins:
            edges.add(tuple(sorted((cell_id, by_position[(row + 1, col)]))))
    domain = Polygon([(-180, -90), (180, -90), (180, 90), (-180, 90)])
    anchor = (0.0, 0.0); theta_values, rho_values = [], []
    for item in cells.itertuples():
        x, y = _local_xy(item.longitude, item.latitude, *anchor)
        theta = math.atan2(float(y), float(x))
        theta_values.append(theta)
        rho_values.append(float(np.clip(math.hypot(x, y) / _boundary_radius(domain, anchor, theta), 0, 1)))
    cells["theta"], cells["rho"] = theta_values, rho_values
    reference = RegionReference("NASA-Exoplanet-SkyGrid", cells, polygons, edges, anchor)
    metadata = {
        "source_kind": "astronomical_equal_area_sky_grid", "source_table": "pscomppars",
        "source_row_count": int(len(source)), "grid_dimensions": [dec_bins, ra_bins],
        "cell_count": int(len(cells)), "scalar": "log1p confirmed planet count",
        "right_ascension_wrap": True, "declination_bands": "equal increments in sin(dec)",
        "retrieval_is_dynamic_snapshot": True,
    }
    _write_reference(reference, Path(output_root) / reference.name, metadata)
    return reference, domain, metadata


def synthetic_masks() -> dict[str, np.ndarray]:
    yy, xx = np.mgrid[:17, :17]
    disk_like = (xx - 8) ** 2 + (yy - 8) ** 2 <= 7 ** 2
    elongated = np.ones((7, 29), dtype=bool)
    l_shape = np.zeros((17, 17), dtype=bool); l_shape[:5, :] = True; l_shape[:, :5] = True
    concave_u = np.zeros((17, 17), dtype=bool); concave_u[:, :4] = True; concave_u[:, -4:] = True; concave_u[-4:, :] = True
    hole = np.ones((17, 17), dtype=bool); hole[6:11, 6:11] = False
    disconnected = np.zeros((17, 25), dtype=bool); disconnected[2:12, 2:10] = True; disconnected[5:15, 15:23] = True
    return {"disk_like": disk_like, "elongated": elongated, "l_shape": l_shape,
            "concave_u": concave_u, "hole": hole, "disconnected": disconnected}


def prepare_synthetic_references(output_root: str | Path) -> dict[str, RegionReference]:
    output_root = Path(output_root); references = {}
    for case, mask in synthetic_masks().items():
        rows, polygons = [], {}
        height, width = mask.shape
        for row, col in np.argwhere(mask):
            cell_id = f"SYN_{case}_r{row:03d}_c{col:03d}"
            x, y = float(col), float(height - 1 - row)
            polygons[cell_id] = Polygon([(x-.5, y-.5), (x+.5, y-.5), (x+.5, y+.5), (x-.5, y+.5)])
            rows.append({"cell_id": cell_id, "region_id": f"Synthetic-{case}", "block_row": int(row), "block_col": int(col),
                         "longitude": x, "latitude": y, "scalar_value": float(np.sin(.35*x) + np.cos(.29*y)),
                         "original_area_degree2": 1.0})
        cells = pd.DataFrame(rows); edges = grid_edges(cells)
        domain = unary_union(list(polygons.values()))
        point = domain.representative_point(); anchor = (float(point.x), float(point.y))
        theta_values, rho_values, boundary_values = [], [], []
        degrees = defaultdict(int)
        for left, right in edges: degrees[left] += 1; degrees[right] += 1
        for item in cells.itertuples():
            x, y = _local_xy(item.longitude, item.latitude, *anchor)
            theta = math.atan2(float(y), float(x))
            theta_values.append(theta)
            rho_values.append(float(np.clip(math.hypot(x, y) / _boundary_radius(domain, anchor, theta), 0, 1)))
            boundary_values.append(degrees[str(item.cell_id)] < 4)
        cells["theta"], cells["rho"], cells["is_boundary"] = theta_values, rho_values, boundary_values
        reference = RegionReference(f"Synthetic-{case}", cells, polygons, edges, anchor)
        metadata = {"source_kind": "deterministic_synthetic_quad_grid", "case": case,
                    "connected_components_expected": 2 if case == "disconnected" else 1,
                    "has_hole": case == "hole", "dimensions": [height, width]}
        _write_reference(reference, output_root / reference.name, metadata)
        references[case] = reference
    return references
