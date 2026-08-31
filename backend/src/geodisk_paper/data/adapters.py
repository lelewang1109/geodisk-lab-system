from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
import re

import numpy as np
import xarray as xr


@dataclass(frozen=True)
class DatasetSchema:
    latitude: str
    longitude: str
    scalar: str
    time: str | None


class DatasetAdapter(ABC):
    """Dataset-neutral interface reserved for later scalar-field datasets."""

    @abstractmethod
    def files(self) -> list[Path]: ...

    @abstractmethod
    def inspect_schema(self, path: Path | None = None) -> DatasetSchema: ...

    @abstractmethod
    def read_scalar(self, path: Path, schema: DatasetSchema) -> np.ndarray: ...


class DailyNetCDFAdapter(DatasetAdapter):
    def __init__(self, raw_dir: str | Path, pattern: str = "*.nc", scalar_hint: str | None = None):
        self.raw_dir = Path(raw_dir)
        self.pattern = pattern
        self.scalar_hint = scalar_hint

    def files(self) -> list[Path]:
        files = sorted(self.raw_dir.glob(self.pattern))
        if not files:
            raise FileNotFoundError(f"No NetCDF files match {self.raw_dir / self.pattern}")
        return files

    @staticmethod
    def _coord_name(ds: xr.Dataset, aliases: tuple[str, ...], role: str) -> str:
        lower = {name.lower(): name for name in ds.variables}
        for alias in aliases:
            if alias in lower:
                return lower[alias]
        for name, var in ds.variables.items():
            std = str(var.attrs.get("standard_name", "")).lower()
            if std in aliases:
                return name
        raise ValueError(f"Cannot resolve {role} coordinate from variables: {list(ds.variables)}")

    def inspect_schema(self, path: Path | None = None) -> DatasetSchema:
        path = path or self.files()[0]
        with xr.open_dataset(path, decode_times=True) as ds:
            lat = self._coord_name(ds, ("lat", "latitude"), "latitude")
            lon = self._coord_name(ds, ("lon", "longitude"), "longitude")
            time = next((n for n in ds.coords if n.lower() == "time"), None)
            candidates = []
            for name, var in ds.data_vars.items():
                token = re.sub(r"[^a-z0-9]", "", name.lower())
                if token in {"pm25", "particulatematter25", "particulatematter25um"}:
                    candidates.append(name)
            if self.scalar_hint:
                exact = [n for n in ds.data_vars if n == self.scalar_hint]
                if not exact:
                    raise ValueError(f"Configured scalar {self.scalar_hint!r} is absent from {path.name}")
                scalar = exact[0]
            elif len(candidates) == 1:
                scalar = candidates[0]
            else:
                raise ValueError(f"Expected exactly one PM2.5-like variable in {path.name}; found {candidates}")
            if tuple(ds[scalar].dims) != (lat, lon):
                raise ValueError(f"Scalar dimensions must be ({lat}, {lon}); got {ds[scalar].dims}")
        return DatasetSchema(lat, lon, scalar, time)

    def coordinates(self, path: Path, schema: DatasetSchema) -> tuple[np.ndarray, np.ndarray]:
        with xr.open_dataset(path, decode_times=True) as ds:
            return ds[schema.latitude].values.astype(float), ds[schema.longitude].values.astype(float)

    def read_scalar(self, path: Path, schema: DatasetSchema) -> np.ndarray:
        with xr.open_dataset(path, decode_times=True) as ds:
            return ds[schema.scalar].values.astype(float)

