from __future__ import annotations

from dataclasses import replace
import math
import shutil

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import Normalize
from matplotlib.lines import Line2D
from matplotlib.patches import Circle
import numpy as np

from common import ROOT, ensure_output_dirs, geometry_config, project_boundaries, seed_everything
from geodisk_paper.data.regions import load_region_reference
from geodisk_paper.geometry.mappings import proposed_irregular
from geodisk_paper.geometry.serialization import load_geometry
from geodisk_paper.metrics.geometry import display_adjacency
from geodisk_paper.topology.embedding import build_topology_embedding, regular_polygons
from geodisk_paper.utils.io import write_json
from paper_figure_utils import add_polygons, centroid_map, draw_edges, set_geometry_extent


def _plot_canonical(axis, polygons, values, norm, title):
    add_polygons(axis, polygons, values, norm=norm, linewidth=.2)
    set_geometry_extent(axis, polygons.values(), margin=.025); axis.set_title(title, loc="left", fontsize=10, fontweight="semibold")


def main() -> None:
    ensure_output_dirs(); region = "湖北"; config = geometry_config(); seed = seed_everything()
    reference = load_region_reference(ROOT / "data/processed/regions", region)
    boundaries, _ = project_boundaries(); boundary = boundaries[region]
    revision, refinement = config["method_revision"], config["final_power_refinement"]
    embedding = build_topology_embedding(
        reference, layer_count=int(revision["layer_count"]),
        optimize_passes=int(refinement["embedding_optimize_passes"]["ceg"]), seed=seed,
        weights=dict(revision["topology_weights"]), radial_constraint=True,
        search_mode="expanded_cross", candidate_budget=int(refinement["embedding_candidate_budget"]["ceg"]),
    )
    inner, outer = float(config["annulus_inner"]), float(config["annulus_outer"])
    initial_embedding = replace(embedding, assignment=embedding.initial_assignment.copy())
    initial_regular = regular_polygons(initial_embedding, "disk", inner, outer)
    optimized_regular = regular_polygons(embedding, "disk", inner, outer)
    pre_final_result = proposed_irregular(reference, embedding, "disk", inner=inner, outer=outer,
                                          iterations=int(refinement["power_iterations_small"]), warp_strength=0.0)
    pre_final = dict(zip(pre_final_result.cell_ids, pre_final_result.geometries))
    final_disk_path = ROOT / "results/spatial_refined" / region / "final_refined_disk.geojson"
    final_annulus_path = ROOT / "results/spatial_refined" / region / "final_refined_annulus.geojson"
    if not final_disk_path.exists() or not final_annulus_path.exists():
        raise FileNotFoundError("Missing Hubei final_refined geometry; run E19 first")
    final_disk_result = load_geometry(final_disk_path, inner, outer)
    final_annulus_result = load_geometry(final_annulus_path, inner, outer)
    final_disk = dict(zip(final_disk_result.cell_ids, final_disk_result.geometries))
    final_annulus = dict(zip(final_annulus_result.cell_ids, final_annulus_result.geometries))
    values = dict(zip(reference.cells.cell_id.astype(str), reference.cells.annual_mean_pm25.astype(float)))
    norm = Normalize(*np.quantile(np.asarray(list(values.values())), [.02, .98]))

    figure, axes = plt.subplots(2, 3, figsize=(15.4, 9.5), constrained_layout=True)
    geographic_positions = {str(row.cell_id): (float(row.longitude), float(row.latitude)) for row in reference.cells.itertuples()}
    add_polygons(axes[0, 0], reference.polygons, values, norm=norm, linewidth=.2)
    draw_edges(axes[0, 0], geographic_positions, reference.edges, color="#173f37", linewidth=.35, alpha=.55)
    axes[0, 0].plot(*boundary.exterior.xy, color="black", linewidth=.9)
    set_geometry_extent(axes[0, 0], reference.polygons.values())
    axes[0, 0].set_title("(a) Geographic Reference", loc="left", fontsize=10, fontweight="semibold")

    axis = axes[0, 1]
    for layer in range(1, embedding.layer_count + 1):
        radius = math.sqrt(layer / embedding.layer_count)
        axis.add_patch(Circle((0, 0), radius, fill=False, edgecolor="#9db2ac", linewidth=.6))
    for slot in embedding.slots:
        for angle in (slot.theta_left, slot.theta_right):
            axis.plot([slot.r_inner * math.cos(angle), slot.r_outer * math.cos(angle)],
                      [slot.r_inner * math.sin(angle), slot.r_outer * math.sin(angle)],
                      color="#b8c6c2", linewidth=.28)
    seam = min(slot.theta_left for slot in embedding.slots)
    axis.plot([0, math.cos(seam)], [0, math.sin(seam)], color="#c51b7d", linewidth=1.3, label="seam")
    axis.scatter([0], [0], marker="*", s=90, c="#ef8a17", edgecolor="white", zorder=5, label="anchor")
    axis.text(-.98, -.98, "ρ quantile layers\nθ order within each layer", fontsize=8,
              bbox={"boxstyle": "round,pad=.25", "fc": "white", "ec": "#ccd7d3"})
    axis.set_xlim(-1.04, 1.04); axis.set_ylim(-1.04, 1.04); axis.set_aspect("equal"); axis.axis("off")
    axis.set_title("(b) Radial / Angular Initialization", loc="left", fontsize=10, fontweight="semibold")

    _plot_canonical(axes[0, 2], initial_regular, values, norm, "(c) Initial Canonical Slot Assignment")
    example_ids = reference.cells.sort_values("rho").iloc[[15, 60, 110]].cell_id.astype(str)
    for number, cell_id in enumerate(example_ids, start=1):
        point = initial_regular[cell_id].centroid
        axes[0, 2].text(point.x, point.y, str(number), ha="center", va="center", fontsize=7,
                        bbox={"boxstyle": "circle,pad=.12", "fc": "white", "ec": "#333333"})
    axes[0, 2].text(.02, .02, f"slot objective = {embedding.initial_objective:.4f}",
                    transform=axes[0, 2].transAxes, fontsize=8)

    _plot_canonical(axes[1, 0], optimized_regular, values, norm, "(d) Optimized Slot Assignment")
    axes[1, 0].text(.02, .02, f"topology objective\n{embedding.initial_objective:.4f} → {embedding.final_objective:.4f}",
                    transform=axes[1, 0].transAxes, fontsize=8,
                    bbox={"boxstyle": "round,pad=.25", "fc": "white", "ec": "#c5d0cc"})

    _plot_canonical(axes[1, 1], pre_final, values, norm, "(e) Balanced Power Partition (pre-final)")
    axes[1, 1].text(.02, .02, "topology seed positions → equal-area Power cells",
                    transform=axes[1, 1].transAxes, fontsize=8)

    _plot_canonical(axes[1, 2], final_disk, values, norm, "(f) Final Polygon-level Refinement")
    final_positions = centroid_map(final_disk)
    display = display_adjacency(final_disk_result.cell_ids, final_disk_result.geometries,
                                tolerance=float(refinement["contact_tolerance"]))
    preserved, lost, new = reference.edges & display, reference.edges - display, display - reference.edges
    draw_edges(axes[1, 2], final_positions, preserved, color="#1b9e77", linewidth=.42, alpha=.55, zorder=5)
    draw_edges(axes[1, 2], final_positions, lost, color="#d73027", linewidth=.65, alpha=.75, zorder=6)
    draw_edges(axes[1, 2], final_positions, new, color="#e6ab02", linewidth=.55, alpha=.7, zorder=6)
    legend = [Line2D([0], [0], color="#1b9e77", label=f"preserved ({len(preserved)})"),
              Line2D([0], [0], color="#d73027", label=f"lost ({len(lost)})"),
              Line2D([0], [0], color="#e6ab02", label=f"new ({len(new)})")]
    axes[1, 2].legend(handles=legend, loc="lower left", frameon=False, fontsize=7)
    inset = axes[1, 2].inset_axes([.68, .02, .29, .29])
    add_polygons(inset, final_annulus, values, norm=norm, linewidth=.08)
    inset.set_xlim(-1.02, 1.02); inset.set_ylim(-1.02, 1.02); inset.set_aspect("equal"); inset.axis("off")
    inset.set_title("GeoAnnulus-Final", fontsize=6.5)
    axes[1, 2].text(.02, .96, f"final objective: {final_disk_result.metadata['initial_final_power_objective']:.4f} → "
                                  f"{final_disk_result.metadata['optimized_final_power_objective']:.4f}",
                    transform=axes[1, 2].transAxes, fontsize=7.5, va="top")

    figure.suptitle("GeoDisk: Reference-guided Canonicalization on Real Hubei Data", fontsize=15, fontweight="semibold")
    png = ROOT / "results/figures/Fig_geodisk_method_pipeline_Hubei.png"
    pdf = ROOT / "results/figures/Fig_geodisk_method_pipeline_Hubei.pdf"
    figure.savefig(png, dpi=300, bbox_inches="tight"); figure.savefig(pdf, bbox_inches="tight"); plt.close(figure)
    shutil.copy2(png, ROOT / "paper/figures" / png.name); shutil.copy2(pdf, ROOT / "paper/figures" / pdf.name)
    write_json({"producer": "E34_geodisk_method_figure.py", "region": region, "seed": seed,
                "inputs": ["data/processed/regions/湖北/*", str(final_disk_path.relative_to(ROOT)),
                           str(final_annulus_path.relative_to(ROOT))],
                "topology_objective": {"initial": embedding.initial_objective, "final": embedding.final_objective},
                "final_edges": {"preserved": len(preserved), "lost": len(lost), "new": len(new)},
                "outputs": [str(png.relative_to(ROOT)), str(pdf.relative_to(ROOT))]},
               ROOT / "results/figures/geodisk_method_pipeline_manifest.json")
    print({"topology_objective": [embedding.initial_objective, embedding.final_objective],
           "final_edges": [len(preserved), len(lost), len(new)]})


if __name__ == "__main__":
    main()
