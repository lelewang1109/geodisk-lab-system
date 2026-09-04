from __future__ import annotations

import shutil

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import numpy as np
import pandas as pd

from common import ROOT, ensure_output_dirs
from geodisk_paper.data.regions import load_region_reference
from geodisk_paper.geometry.serialization import load_geometry
from geodisk_paper.metrics.geometry import display_adjacency
from geodisk_paper.utils.io import write_json


def _incident(edges, cell_id):
    return {edge for edge in edges if cell_id in edge}


def _case_rows(reference, results, node):
    enriched = []
    for result in results:
        display = display_adjacency(result.cell_ids, result.geometries)
        for row in node[(node.method == result.method) & (node.view == result.view)].itertuples():
            expected, actual = _incident(reference.edges, row.cell_id), _incident(display, row.cell_id)
            enriched.append({"row": row, "result": result, "reference_edges": expected, "display_edges": actual,
                             "lost": expected - actual, "new": actual - expected, "preserved": expected & actual})
    boundary = [item for item in enriched if bool(item["row"].is_boundary)]
    interior = [item for item in enriched if not bool(item["row"].is_boundary)]
    pure_over = [item for item in enriched if item["new"] and not item["lost"]]
    direction = [item for item in enriched if not item["new"] and not item["lost"]
                 and np.isfinite(item["row"].node_direction_error_deg)]
    return [
        ("boundary failure", min(boundary, key=lambda item: (item["row"].node_adj_f1, -len(item["lost"]), -len(item["new"])))),
        ("interior failure", min(interior, key=lambda item: (item["row"].node_adj_f1, -len(item["lost"]), -len(item["new"])))),
        ("under-connected component", max(enriched, key=lambda item: (len(item["lost"]), -len(item["new"])))),
        ("over-connected", max(pure_over or enriched, key=lambda item: (len(item["new"]), -len(item["lost"])))),
        ("direction-only", max(direction, key=lambda item: item["row"].node_direction_error_deg)),
    ]


def _short(cell_id):
    parts = str(cell_id).split("_")
    return "_".join(parts[-2:])


def _plot_ego(axis, positions, focus, expected, actual, side, title):
    preserved, lost, new = expected & actual, expected - actual, actual - expected
    edges = expected if side == "reference" else actual
    nodes = {focus}
    for edge in expected | actual:
        nodes.update(edge)
    for edge in sorted(edges):
        other = edge[1] if edge[0] == focus else edge[0]
        if edge in preserved: color, style = "#1b9e77", "-"
        elif edge in lost: color, style = "#d73027", "--"
        else: color, style = "#e6ab02", "-"
        axis.plot([positions[focus][0], positions[other][0]], [positions[focus][1], positions[other][1]],
                  color=color, linestyle=style, linewidth=1.5, zorder=2)
    for cell_id in sorted(nodes):
        x, y = positions[cell_id]
        axis.scatter(x, y, s=48 if cell_id == focus else 22, c="#222222" if cell_id == focus else "#f7f7f7",
                     edgecolor="#333333", linewidth=.6, zorder=4)
        axis.text(x, y, _short(cell_id), fontsize=5.7, ha="center", va="bottom" if cell_id == focus else "top")
    xy = np.asarray([positions[cell_id] for cell_id in nodes]); dx = max(np.ptp(xy[:, 0]), 1e-6); dy = max(np.ptp(xy[:, 1]), 1e-6)
    axis.set_xlim(xy[:, 0].min() - .2 * dx, xy[:, 0].max() + .2 * dx)
    axis.set_ylim(xy[:, 1].min() - .2 * dy, xy[:, 1].max() + .2 * dy)
    axis.set_aspect("equal"); axis.axis("off"); axis.set_title(title, fontsize=8.3)


def main() -> None:
    ensure_output_dirs(); region = "湖北"
    table_path = ROOT / "results/tables/Table_node_level_errors.csv"
    if not table_path.exists():
        raise FileNotFoundError(f"Missing {table_path}; run E17 first")
    reference = load_region_reference(ROOT / "data/processed/regions", region)
    results = [load_geometry(ROOT / f"results/spatial_refined/{region}/final_refined_disk.geojson"),
               load_geometry(ROOT / f"results/spatial_refined/{region}/final_refined_annulus.geojson")]
    node = pd.read_csv(table_path, encoding="utf-8-sig")
    node = node[(node.dataset == region) & node.method.isin(["GeoDisk-Final", "GeoAnnulus-Final"])]
    cases = _case_rows(reference, results, node)
    source_positions = {str(row.cell_id): (float(row.longitude), float(row.latitude)) for row in reference.cells.itertuples()}
    figure, axes = plt.subplots(len(cases), 2, figsize=(9.2, 14.5), constrained_layout=True)
    manifest_cases = []
    for row_index, (label, case) in enumerate(cases):
        result = case["result"]; focus = str(case["row"].cell_id)
        display_positions = {cell_id: (float(geometry.centroid.x), float(geometry.centroid.y))
                             for cell_id, geometry in zip(result.cell_ids, result.geometries)}
        suffix = " (mixed: new edges also present)" if label.startswith("under") and case["new"] else ""
        _plot_ego(axes[row_index, 0], source_positions, focus, case["reference_edges"], case["display_edges"],
                  "reference", f"{label}{suffix}\nReference neighborhood")
        _plot_ego(axes[row_index, 1], display_positions, focus, case["reference_edges"], case["display_edges"],
                  "display", f"{result.method} neighborhood")
        manifest_cases.append({"case": label, "cell_id": focus, "method": result.method, "view": result.view,
                               "is_boundary": bool(case["row"].is_boundary),
                               "preserved_edges": sorted([list(edge) for edge in case["preserved"]]),
                               "lost_edges": sorted([list(edge) for edge in case["lost"]]),
                               "new_edges": sorted([list(edge) for edge in case["new"]]),
                               "selection_note": suffix.strip() or "exact requested category"})
    legend = [Line2D([0], [0], color="#1b9e77", lw=1.5, label="preserved edge"),
              Line2D([0], [0], color="#d73027", lw=1.5, ls="--", label="lost edge"),
              Line2D([0], [0], color="#e6ab02", lw=1.5, label="new edge")]
    figure.legend(handles=legend, loc="lower center", ncol=3, frameon=False)
    figure.suptitle("Hubei Final-method Local Failure Cases (computed from edge sets)", fontsize=14, fontweight="semibold")
    output = ROOT / "results/figures/Fig_failure_cases_Hubei.png"
    figure.savefig(output, dpi=300, bbox_inches="tight"); plt.close(figure)
    shutil.copy2(output, ROOT / "paper/figures" / output.name)
    write_json({"producer": "E37_failure_case_figures.py", "region": region,
                "selection": "deterministic extrema from E17 node rows; edge categories recomputed directly from reference.edges and display_adjacency",
                "guardrail": "Hubei has no pure under-connected final node; the panel uses the node with the largest real lost-edge count and labels its simultaneous new edges explicitly.",
                "cases": manifest_cases, "output": str(output.relative_to(ROOT))},
               ROOT / "results/figures/failure_cases_Hubei_manifest.json")
    print(pd.DataFrame([{**{k: v for k, v in item.items() if not k.endswith("edges")},
                             "preserved": len(item["preserved_edges"]), "lost": len(item["lost_edges"]), "new": len(item["new_edges"])}
                            for item in manifest_cases]).to_string(index=False))


if __name__ == "__main__":
    main()
