from __future__ import annotations

import math
import shutil

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import Normalize
from matplotlib.patches import Arc
import numpy as np

from common import ROOT, ensure_output_dirs, project_boundaries
from geodisk_paper.data.regions import _boundary_radius, load_region_reference
from geodisk_paper.utils.io import read_json, write_json
from paper_figure_utils import add_polygons, draw_edges, set_geometry_extent


REQUIRED = ["cells.csv", "original_geometry.geojson", "original_adjacency.csv",
            "original_local_directions.csv", "neighborhoods.json", "reference_metadata.json"]


def _draw_boundary(axis, boundary, **kwargs):
    for part in getattr(boundary, "geoms", [boundary]):
        if part.geom_type == "Polygon":
            axis.plot(*part.exterior.xy, **kwargs)


def main() -> None:
    ensure_output_dirs(); region = "湖北"; source = ROOT / "data/processed/regions" / region
    missing = [str(source / name) for name in REQUIRED if not (source / name).exists()]
    if missing:
        raise FileNotFoundError(f"Missing reference inputs {missing}; run E1 first")
    reference = load_region_reference(ROOT / "data/processed/regions", region)
    metadata = read_json(source / "reference_metadata.json")
    required_columns = {"is_topological_boundary", "is_geographic_boundary", "reference_degree"}
    if not required_columns.issubset(reference.cells.columns):
        raise ValueError(f"Missing {sorted(required_columns - set(reference.cells.columns))}; rerun E1 after boundary update")
    boundaries, _ = project_boundaries(); boundary = boundaries[region]
    values = dict(zip(reference.cells.cell_id.astype(str), reference.cells.annual_mean_pm25.astype(float)))
    raw = np.asarray(list(values.values()), float); norm = Normalize(*np.quantile(raw, [.02, .98]))
    positions = {str(row.cell_id): (float(row.longitude), float(row.latitude)) for row in reference.cells.itertuples()}
    figure, axes = plt.subplots(2, 2, figsize=(13.2, 10.0), constrained_layout=True)

    collection = add_polygons(axes[0, 0], reference.polygons, values, norm=norm, linewidth=.25)
    _draw_boundary(axes[0, 0], boundary, color="black", linewidth=1.15, zorder=5)
    set_geometry_extent(axes[0, 0], reference.polygons.values())
    axes[0, 0].set_title("(a) Original Geographic Scalar Field", loc="left", fontweight="semibold")
    figure.colorbar(collection, ax=axes[0, 0], shrink=.76, label="Annual mean PM2.5 (µg/m³)")

    add_polygons(axes[0, 1], reference.polygons, facecolor="#e7eeeb", linewidth=.45)
    _draw_boundary(axes[0, 1], boundary, color="#172622", linewidth=1.1, zorder=5)
    ordered = reference.cells.sort_values(["block_row", "block_col"])
    for index in np.linspace(0, len(ordered) - 1, 6, dtype=int):
        row = ordered.iloc[index]; short = f"r{int(row.block_row):02d}c{int(row.block_col):02d}"
        axes[0, 1].text(row.longitude, row.latitude, short, fontsize=6.7, ha="center", va="center",
                        bbox={"boxstyle": "round,pad=.12", "fc": "white", "ec": "none", "alpha": .82})
    axes[0, 1].text(.02, .02, "fine grid  →  coarsen factor 4  →  stable macro-cells\n"
                                "permanent Cell ID (only six examples labeled)",
                        transform=axes[0, 1].transAxes, fontsize=8.2,
                        bbox={"boxstyle": "round,pad=.3", "fc": "white", "ec": "#b8c7c2", "alpha": .94})
    set_geometry_extent(axes[0, 1], reference.polygons.values())
    axes[0, 1].set_title("(b) Stable Macro-cell Representation", loc="left", fontweight="semibold")

    add_polygons(axes[1, 0], reference.polygons, facecolor="#f7faf9", edgecolor="#cad5d1", linewidth=.18)
    draw_edges(axes[1, 0], positions, reference.edges, color="#3d7165", linewidth=.55, alpha=.72)
    xy = np.asarray(list(positions.values()))
    axes[1, 0].scatter(xy[:, 0], xy[:, 1], s=4.5, c="#163c34", alpha=.8, zorder=4)
    _draw_boundary(axes[1, 0], boundary, color="black", linewidth=.9, zorder=5)
    set_geometry_extent(axes[1, 0], reference.polygons.values())
    axes[1, 0].set_title("(c) Reference Adjacency Graph (4-neighbor)", loc="left", fontweight="semibold")
    axes[1, 0].text(.02, .02, f"{len(reference.cells)} cells · {len(reference.edges)} frozen reference edges",
                        transform=axes[1, 0].transAxes, fontsize=8,
                        bbox={"boxstyle": "round,pad=.25", "fc": "white", "ec": "none", "alpha": .9})

    add_polygons(axes[1, 1], reference.polygons, facecolor="#f4f7f6", edgecolor="#d3dcda", linewidth=.16)
    _draw_boundary(axes[1, 1], boundary, color="#172622", linewidth=1.0, zorder=4)
    anchor = reference.anchor; axes[1, 1].scatter(*anchor, marker="*", s=110, c="#ef8a17", edgecolor="white", zorder=8)
    axes[1, 1].text(anchor[0], anchor[1], " anchor", fontsize=8, va="bottom")
    exemplars = reference.cells.iloc[np.argsort(np.abs(reference.cells.rho.to_numpy() - np.asarray([.25, .6, .9])[:, None]), axis=1)[:, 0]]
    exemplar_ids = list(dict.fromkeys(exemplars.cell_id.astype(str)))
    colors = ["#2b8cbe", "#7b3294", "#d95f0e"]
    for color, cell_id in zip(colors, exemplar_ids):
        row = reference.cells[reference.cells.cell_id.astype(str) == cell_id].iloc[0]
        radius = _boundary_radius(boundary, anchor, float(row.theta))
        cosine = math.cos(math.radians(anchor[1]))
        endpoint = (anchor[0] + radius * math.cos(row.theta) / cosine,
                    anchor[1] + radius * math.sin(row.theta))
        axes[1, 1].plot([anchor[0], endpoint[0]], [anchor[1], endpoint[1]], color=color, linewidth=.9, alpha=.8)
        axes[1, 1].scatter(row.longitude, row.latitude, s=35, c=color, edgecolor="white", zorder=7)
        axes[1, 1].text(row.longitude, row.latitude, f"  ρ={row.rho:.2f}", fontsize=7.4, color=color)
    median = reference.cells.iloc[(reference.cells.rho - reference.cells.rho.median()).abs().argmin()]
    theta_deg = math.degrees(float(median.theta))
    axes[1, 1].add_patch(Arc(anchor, .9, .9, theta1=min(0, theta_deg), theta2=max(0, theta_deg),
                              color="#5b6870", linewidth=1.0))
    axes[1, 1].text(anchor[0] + .45, anchor[1] + .12, "θ", fontsize=10)
    topo = reference.cells.is_topological_boundary.to_numpy(bool)
    geo = reference.cells.is_geographic_boundary.to_numpy(bool)
    axes[1, 1].scatter(reference.cells.longitude[topo], reference.cells.latitude[topo], s=9,
                       facecolors="none", edgecolors="#2166ac", linewidths=.55, label="topological boundary")
    axes[1, 1].scatter(reference.cells.longitude[geo], reference.cells.latitude[geo], s=16,
                       facecolors="none", edgecolors="#b2182b", linewidths=.65, label="geographic boundary")
    axes[1, 1].legend(loc="lower right", frameon=False, fontsize=7)
    axes[1, 1].text(.02, .02, "θ: direction from anchor\nρ: cell–anchor distance / anchor–boundary distance on the same ray",
                        transform=axes[1, 1].transAxes, fontsize=7.7,
                        bbox={"boxstyle": "round,pad=.28", "fc": "white", "ec": "#b8c7c2", "alpha": .94})
    set_geometry_extent(axes[1, 1], reference.polygons.values())
    axes[1, 1].set_title("(d) Spatial Structural Attributes", loc="left", fontweight="semibold")

    figure.suptitle("Hubei: Geographic Data to a Frozen Reference Structure", fontsize=15, fontweight="semibold")
    png = ROOT / "results/figures/Fig_reference_structure_Hubei.png"
    pdf = ROOT / "results/figures/Fig_reference_structure_Hubei.pdf"
    png.parent.mkdir(parents=True, exist_ok=True); figure.savefig(png, dpi=300, bbox_inches="tight")
    figure.savefig(pdf, bbox_inches="tight"); plt.close(figure)
    shutil.copy2(png, ROOT / "paper/figures" / png.name); shutil.copy2(pdf, ROOT / "paper/figures" / pdf.name)
    write_json({"producer": "E33_reference_structure_figure.py", "region": region,
                "inputs": [str((source / name).relative_to(ROOT)) for name in REQUIRED],
                "boundary_definitions": metadata.get("boundary_definitions"),
                "outputs": [str(png.relative_to(ROOT)), str(pdf.relative_to(ROOT))]},
               ROOT / "results/figures/reference_structure_manifest.json")
    print({"png": str(png), "pdf": str(pdf), "cells": len(reference.cells), "edges": len(reference.edges)})


if __name__ == "__main__":
    main()
