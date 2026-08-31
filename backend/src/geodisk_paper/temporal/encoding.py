from __future__ import annotations

import numpy as np
import pandas as pd


def monthly_columns(frame: pd.DataFrame) -> tuple[list[str], str, str]:
    pm25 = sorted(column for column in frame.columns if column.startswith("month_") and column.endswith("_pm25"))
    air = sorted(column for column in frame.columns if column.startswith("month_") and column.endswith("_air_temp_c"))
    if len(pm25) == 12:
        return pm25, "PM2.5", "µg/m³"
    if len(air) == 12:
        return air, "air_temperature", "°C"
    raise ValueError("Expected exactly 12 monthly PM2.5 or air-temperature columns")


def _bin(values: np.ndarray, low: float, high: float, count: int) -> tuple[np.ndarray, np.ndarray]:
    edges = np.linspace(low, high, count + 1)
    clipped = np.clip(values, low, high)
    indexes = np.clip(np.searchsorted(edges, clipped, side="right") - 1, 0, count - 1)
    centers = .5 * (edges[:-1] + edges[1:])
    return indexes.astype(int), centers[indexes]


def encode_temporal(reference, dataset: str, *, bin_count: int = 9) -> tuple[pd.DataFrame, dict]:
    columns, variable, units = monthly_columns(reference.cells)
    ids = reference.cells.cell_id.astype(str).tolist()
    matrix = reference.cells[columns].to_numpy(float)
    low, high = [float(value) for value in np.nanquantile(matrix, [.02, .98])]
    if high <= low:
        low, high = float(np.nanmin(matrix)), float(np.nanmax(matrix) + 1e-9)
    value_bins, reconstructed = _bin(matrix.ravel(), low, high, bin_count)
    value_bins = value_bins.reshape(matrix.shape); reconstructed = reconstructed.reshape(matrix.shape)
    delta = np.full_like(matrix, np.nan); delta[:, 1:] = np.diff(matrix, axis=1)
    delta_limit = float(np.nanquantile(np.abs(delta[:, 1:]), .95))
    delta_limit = max(delta_limit, 1e-9)
    delta_bins, delta_reconstructed = _bin(np.nan_to_num(delta, nan=0.0).ravel(), -delta_limit, delta_limit, bin_count)
    delta_bins = delta_bins.reshape(matrix.shape); delta_reconstructed = delta_reconstructed.reshape(matrix.shape)
    rows = []
    for cell_index, cell_id in enumerate(ids):
        for month in range(12):
            previous = matrix[cell_index, month - 1] if month else np.nan
            rows.append({
                "dataset": dataset, "cell_id": cell_id, "month": month + 1,
                "value": matrix[cell_index, month], "previous_value": previous,
                "delta": delta[cell_index, month],
                "relative_delta": delta[cell_index, month] / max(abs(previous), 1e-9) if month else np.nan,
                "value_bin": int(value_bins[cell_index, month]),
                "value_reconstructed": float(reconstructed[cell_index, month]),
                "delta_bin": int(delta_bins[cell_index, month]),
                "delta_reconstructed": float(delta_reconstructed[cell_index, month]) if month else np.nan,
                "theta": float(reference.cells.iloc[cell_index].theta),
                "rho": float(reference.cells.iloc[cell_index].rho),
            })
    manifest = {
        "dataset": dataset, "variable": variable, "units": units, "month_count": 12,
        "cell_count": len(ids), "bin_count": bin_count,
        "value_clip_quantiles": [0.02, 0.98], "value_clip_range": [low, high],
        "delta_symmetric_quantile": 0.95, "delta_symmetric_limit": delta_limit,
        "geometry_policy": "one fixed final-refined annulus partition reused for every month",
        "identity_policy": "cell_id is unchanged across all months",
    }
    return pd.DataFrame(rows), manifest
