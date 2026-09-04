from __future__ import annotations

from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import PatchCollection
from matplotlib.patches import Polygon as PolygonPatch
from matplotlib.colors import Normalize

from geodisk_paper.geometry.power import polygon_parts


def _patches(geometries, values, cmap, norm):
    patches, colors = [], []
    for geometry, value in zip(geometries, values):
        for polygon in polygon_parts(geometry):
            patches.append(PolygonPatch(np.asarray(polygon.exterior.coords), closed=True))
            colors.append(value)
    return PatchCollection(patches, cmap=cmap, norm=norm, array=np.asarray(colors),
                           edgecolor="#555555", linewidth=.22)


def comparison_figure(reference, boundary, results_by_label: dict, output: str | Path, english_name: str,
                      value_column: str = "annual_mean_pm25", value_label: str = "Annual mean PM2.5 (µg/m³)",
                      labels: list[str] | None = None, dpi: int = 260) -> None:
    labels = labels or ["Original Geographic Grid", "Direct Polar", "Harmonic", "Area-balanced",
                        "Regular Topology", "GeoDisk", "GeoAnnulus"]
    if len(labels) != 7:
        raise ValueError("comparison_figure requires exactly seven panel labels")
    if value_column not in reference.cells.columns:
        raise ValueError(f"Missing figure value column {value_column!r}")
    values_by_id = {str(row.cell_id): float(getattr(row, value_column)) for row in reference.cells.itertuples()}
    all_values = np.asarray(list(values_by_id.values()))
    norm = Normalize(float(np.nanpercentile(all_values, 2)), float(np.nanpercentile(all_values, 98)))
    cmap = "viridis"
    fig, axes = plt.subplots(2, 4, figsize=(13.2, 7.0), facecolor="white", constrained_layout=True)
    axes = axes.ravel()
    original_ids = reference.cells.cell_id.astype(str).tolist()
    original_geometries = [reference.polygons[cell_id] for cell_id in original_ids]
    collection = _patches(original_geometries, [values_by_id[i] for i in original_ids], cmap, norm)
    axes[0].add_collection(collection)
    boundary_parts = [boundary] if boundary.geom_type == "Polygon" else list(getattr(boundary, "geoms", []))
    for part in boundary_parts:
        if part.geom_type == "Polygon":
            bx, by = part.exterior.xy
            axes[0].plot(bx, by, color="black", linewidth=.8)
    axes[0].autoscale_view(); axes[0].set_aspect("equal")
    axes[0].set_title(f"A  {labels[0]}", fontsize=9)
    for index, label in enumerate(labels[1:], start=1):
        result = results_by_label[label]
        collection = _patches(result.geometries, [values_by_id[i] for i in result.cell_ids], cmap, norm)
        axes[index].add_collection(collection)
        axes[index].set_xlim(-1.06, 1.06); axes[index].set_ylim(-1.06, 1.06); axes[index].set_aspect("equal")
        axes[index].set_title(f"{chr(65+index)}  {label}", fontsize=9)
    for ax in axes[:7]:
        ax.set_xticks([]); ax.set_yticks([]); ax.set_frame_on(False)
    axes[7].axis("off")
    cbar = fig.colorbar(collection, ax=axes.tolist(), location="bottom", shrink=.45, pad=.03)
    cbar.set_label(f"{value_label}; identical scale in every panel", fontsize=8)
    fig.suptitle(f"{english_name}: identical cells and scalar encoding", fontsize=12)
    output = Path(output); output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=dpi, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def sensitivity_figure(frame, output: str | Path) -> None:
    metrics = [("adj_f1", "Adjacency F1 ↑"), ("np2", "NP2 ↑"),
               ("local_direction_error_deg", "LDE ↓"), ("area_cv", "Area CV ↓")]
    parameters = list(frame.parameter.drop_duplicates())
    fig, axes = plt.subplots(len(parameters), len(metrics), figsize=(12, 2.6*len(parameters)), constrained_layout=True)
    axes = np.atleast_2d(axes)
    for row_index, parameter in enumerate(parameters):
        subset = frame[frame.parameter == parameter]
        for col_index, (metric, title) in enumerate(metrics):
            ax = axes[row_index, col_index]
            for view, group in subset.groupby("view"):
                summary = group.groupby("value", as_index=False)[metric].mean().sort_values("value")
                ax.plot(summary.value.astype(str), summary[metric], "-o", label=view)
            ax.set_title(f"{parameter}: {title}", fontsize=9); ax.grid(alpha=.2)
            if col_index == 0: ax.legend(frameon=False, fontsize=7)
    output = Path(output); output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=240, bbox_inches="tight", facecolor="white")
    plt.close(fig)
