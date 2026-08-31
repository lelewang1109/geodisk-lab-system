from __future__ import annotations

from pathlib import Path
from geodisk_paper.geometry.mappings import GeometryResult
from geodisk_paper.geometry.power import circular_domain
from geodisk_paper.utils.io import read_geojson, read_json, write_geojson, write_json


def save_geometry(result: GeometryResult, path: str | Path) -> None:
    path = Path(path)
    records = (
        (cell_id, geometry, {"method": result.method, "view": result.view})
        for cell_id, geometry in zip(result.cell_ids, result.geometries)
    )
    write_geojson(records, path)
    write_json({"method": result.method, "view": result.view, "cell_count": len(result.cell_ids), **result.metadata},
               path.with_suffix(".metadata.json"))


def load_geometry(path: str | Path, inner: float = .48, outer: float = 1.0) -> GeometryResult:
    path = Path(path)
    ids, geometries, properties = read_geojson(path)
    if not properties:
        raise ValueError(f"No features in {path}")
    method, view = str(properties[0]["method"]), str(properties[0]["view"])
    if any(str(p["method"]) != method or str(p["view"]) != view for p in properties):
        raise ValueError(f"Mixed method/view properties in {path}")
    metadata_path = path.with_suffix(".metadata.json")
    metadata = read_json(metadata_path) if metadata_path.exists() else {}
    return GeometryResult(method, view, ids, geometries, circular_domain(view, inner, outer), metadata)

