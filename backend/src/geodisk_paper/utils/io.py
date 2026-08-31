from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

import pandas as pd
from shapely.geometry import mapping, shape


def write_json(value, path: str | Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, default=str), encoding="utf-8")


def read_json(path: str | Path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_csv(frame: pd.DataFrame, path: str | Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False, encoding="utf-8-sig")


def write_geojson(records: Iterable[tuple[str, object, dict]], path: str | Path) -> None:
    features = []
    for cell_id, geometry, properties in records:
        props = {"cell_id": str(cell_id), **properties}
        features.append({"type": "Feature", "properties": props, "geometry": mapping(geometry)})
    write_json({"type": "FeatureCollection", "features": features}, path)


def read_geojson(path: str | Path) -> tuple[list[str], list, list[dict]]:
    obj = read_json(path)
    ids, geometries, properties = [], [], []
    for feature in obj["features"]:
        props = dict(feature.get("properties") or {})
        ids.append(str(props.pop("cell_id")))
        geometries.append(shape(feature["geometry"]))
        properties.append(props)
    return ids, geometries, properties

