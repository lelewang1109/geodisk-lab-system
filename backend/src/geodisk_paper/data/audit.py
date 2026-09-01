from __future__ import annotations

from datetime import datetime
import hashlib
from pathlib import Path
import re

import numpy as np
import pandas as pd
import xarray as xr

from .adapters import DailyNetCDFAdapter
from geodisk_paper.utils.io import write_csv, write_json


def _sha256(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _date_from_file(path: Path, ds: xr.Dataset) -> str:
    match = re.search(r"(\d{8})", path.stem)
    filename_date = datetime.strptime(match.group(1), "%Y%m%d").date().isoformat() if match else None
    if "time" in ds.coords:
        time_date = str(np.asarray(ds["time"].values).astype("datetime64[D]"))
        if filename_date and filename_date != time_date:
            raise ValueError(f"Filename/time disagreement in {path.name}: {filename_date} != {time_date}")
        return time_date
    if filename_date:
        return filename_date
    raise ValueError(f"Cannot resolve date for {path}")


def audit_dataset(adapter: DailyNetCDFAdapter, output_dir: str | Path, dataset_metadata: dict) -> dict:
    output_dir = Path(output_dir)
    files = adapter.files()
    schema = adapter.inspect_schema(files[0])
    lat0, lon0 = adapter.coordinates(files[0], schema)
    if len(lat0) < 2 or len(lon0) < 2:
        raise ValueError("Latitude and longitude coordinates must each contain at least two values")
    manifests, missing_rows = [], []
    variable_meta: dict[str, dict] = {}
    schemas_seen = set()

    for index, path in enumerate(files):
        with xr.open_dataset(path, decode_times=True) as ds:
            date = _date_from_file(path, ds)
            lat = ds[schema.latitude].values
            lon = ds[schema.longitude].values
            same_grid = bool(np.array_equal(lat, lat0) and np.array_equal(lon, lon0))
            variables = tuple(sorted(ds.data_vars))
            schemas_seen.add((tuple(ds.sizes.items()), variables))
            if schema.scalar not in ds.data_vars:
                raise ValueError(f"{schema.scalar!r} is absent from {path.name}")
            manifests.append({
                "file": path.name, "date": date, "bytes": path.stat().st_size,
                "sha256": _sha256(path),
                "latitude_count": len(lat), "longitude_count": len(lon),
                "same_grid_as_first": same_grid, "scalar_variable": schema.scalar,
            })
            if not same_grid:
                raise ValueError(f"Grid mismatch in {path.name}")
            for name, var in ds.data_vars.items():
                arr = np.asarray(var.values)
                numeric = np.issubdtype(arr.dtype, np.number)
                missing = int(np.isnan(arr).sum()) if numeric else 0
                finite = arr[np.isfinite(arr)] if numeric else np.asarray([])
                missing_rows.append({
                    "file": path.name, "date": date, "variable": name,
                    "value_count": int(arr.size), "missing_count": missing,
                    "missing_fraction": missing / max(arr.size, 1),
                })
                meta = variable_meta.setdefault(name, {
                    "variable": name, "dimensions": "|".join(var.dims), "dtype": str(var.dtype),
                    "units": str(var.attrs.get("units", "")), "files_present": 0,
                    "global_min": np.inf, "global_max": -np.inf,
                })
                meta["files_present"] += 1
                if finite.size:
                    meta["global_min"] = min(meta["global_min"], float(finite.min()))
                    meta["global_max"] = max(meta["global_max"], float(finite.max()))
        if (index + 1) % 50 == 0:
            print(f"[audit] {index + 1}/{len(files)} files", flush=True)

    manifest = pd.DataFrame(manifests).sort_values("date")
    missing_daily = pd.DataFrame(missing_rows)
    missing_summary = (missing_daily.groupby("variable", as_index=False)
                       .agg(file_count=("file", "count"), value_count=("value_count", "sum"),
                            missing_count=("missing_count", "sum")))
    missing_summary["missing_fraction"] = missing_summary.missing_count / missing_summary.value_count
    variable_summary = pd.DataFrame(variable_meta.values()).sort_values("variable")
    for col in ("global_min", "global_max"):
        variable_summary[col] = variable_summary[col].replace([np.inf, -np.inf], np.nan)

    summary = {
        "dataset_id": dataset_metadata["id"],
        "full_name": dataset_metadata["full_name"],
        "dataset_name_status": dataset_metadata["naming_note"],
        "file_count": len(files), "date_start": manifest.date.min(), "date_end": manifest.date.max(),
        "date_count": int(manifest.date.nunique()), "schema_count": len(schemas_seen),
        "latitude_field": schema.latitude, "longitude_field": schema.longitude,
        "pm25_field": schema.scalar, "time_field": schema.time,
        "dimensions": {"latitude": len(lat0), "longitude": len(lon0)},
        "coordinate_order": {
            "latitude": "ascending" if np.all(np.diff(lat0) > 0) else "descending_or_irregular",
            "longitude": "ascending" if np.all(np.diff(lon0) > 0) else "descending_or_irregular",
        },
        "resolution_degrees": {"latitude": float(np.median(np.diff(lat0))), "longitude": float(np.median(np.diff(lon0)))},
        "all_files_same_grid": bool(manifest.same_grid_as_first.all()),
        "file_hash_algorithm": "sha256",
        "dataset_manifest_sha256": hashlib.sha256("\n".join(
            f"{row.file}\t{row.date}\t{row.bytes}\t{row.sha256}" for row in manifest.itertuples()
        ).encode("utf-8")).hexdigest(),
        "pm25_units": str(variable_summary.loc[variable_summary.variable == schema.scalar, "units"].iloc[0]),
    }
    write_json(summary, output_dir / "dataset_summary.json")
    write_csv(manifest, output_dir / "daily_file_manifest.csv")
    write_csv(variable_summary, output_dir / "variable_summary.csv")
    write_csv(missing_summary, output_dir / "missing_value_summary.csv")
    write_csv(missing_daily, output_dir / "missing_value_daily.csv")
    return summary
