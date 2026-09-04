from __future__ import annotations

import shutil

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import Normalize
from matplotlib.patches import Circle
import numpy as np
import pandas as pd

from common import ROOT, ensure_output_dirs, geometry_config
from geodisk_paper.data.regions import load_region_reference
from geodisk_paper.geometry.serialization import load_geometry
from geodisk_paper.utils.io import write_csv, write_json
from E35_integrated_delta_annulus import build_integrated_layers
from paper_figure_utils import add_polygons, set_geometry_extent


def _panel(axis, polygons, values, norm, cmap, title):
    add_polygons(axis, polygons, values, norm=norm, cmap=cmap, linewidth=.1, edgecolor="#40534d")
    set_geometry_extent(axis, polygons.values(), margin=.025); axis.set_title(title, loc="left", fontsize=9.2, fontweight="semibold")


def _select_event(encoded: pd.DataFrame) -> tuple[int, pd.DataFrame, float]:
    transitions = encoded[encoded.month > 1].copy()
    threshold = float(transitions.delta.abs().quantile(.75))
    rows = []
    for month, group in transitions.groupby("month"):
        rows.append({"month": int(month), "transition": f"M{int(month)-1:02d}-M{int(month):02d}",
                     "mean_absolute_delta": float(group.delta.abs().mean()),
                     "p95_absolute_delta": float(group.delta.abs().quantile(.95)),
                     "high_change_cell_fraction": float((group.delta.abs() >= threshold).mean())})
    frame = pd.DataFrame(rows)
    for metric in ("mean_absolute_delta", "p95_absolute_delta", "high_change_cell_fraction"):
        spread = float(frame[metric].max() - frame[metric].min())
        frame[f"normalized_{metric}"] = (frame[metric] - frame[metric].min()) / max(spread, 1e-12)
    frame["event_score"] = frame[[column for column in frame if column.startswith("normalized_")]].mean(axis=1)
    selected = frame.sort_values(["event_score", "month"], ascending=[False, True]).iloc[0]
    return int(selected.month), frame, threshold


def main() -> None:
    ensure_output_dirs(); region = "湖北"; config = geometry_config()
    inner, outer = float(config["annulus_inner"]), float(config["annulus_outer"])
    encoded_path = ROOT / "results/temporal/湖北/monthly_delta_encoding.csv"
    geometry_path = ROOT / "results/spatial_refined/湖北/final_refined_annulus.geojson"
    if not geometry_path.exists():
        raise FileNotFoundError(f"Missing {geometry_path}; run E19 first")
    if not encoded_path.exists():
        raise FileNotFoundError(f"Missing {encoded_path}; run E5 first")
    reference = load_region_reference(ROOT / "data/processed/regions", region)
    annulus = load_geometry(geometry_path, inner, outer); annulus_polygons = dict(zip(annulus.cell_ids, annulus.geometries))
    encoded = pd.read_csv(encoded_path, dtype={"cell_id": str})
    month, transition_scores, high_threshold = _select_event(encoded)
    before = encoded[encoded.month == month - 1].set_index("cell_id")
    after = encoded[encoded.month == month].set_index("cell_id")
    current = encoded[encoded.month == month].copy().sort_values(["delta", "cell_id"], key=lambda col: col.abs() if col.name == "delta" else col,
                                                                  ascending=[False, True])
    ranked = current.assign(abs_delta=current.delta.abs()).sort_values(["abs_delta", "cell_id"], ascending=[False, True]).head(10).copy()
    graph = {cell_id: set() for cell_id in reference.cells.cell_id.astype(str)}
    for left, right in sorted(reference.edges):
        graph[left].add(right); graph[right].add(left)
    month_values = encoded[encoded.month == month].set_index("cell_id")
    rows = []
    for rank, row in enumerate(ranked.itertuples(), start=1):
        cell_id = str(row.cell_id); neighbors = sorted(graph[cell_id])
        neighbor_delta = month_values.loc[neighbors, "delta"].to_numpy(float) if neighbors else np.asarray([])
        rows.append({
            "rank": rank, "cell_id": cell_id, "transition": f"M{month-1:02d}-M{month:02d}",
            "before": float(before.loc[cell_id, "value"]), "after": float(after.loc[cell_id, "value"]),
            "delta": float(row.delta), "absolute_delta": float(abs(row.delta)),
            "theta": float(row.theta), "rho": float(row.rho),
            "reference_degree": len(neighbors), "neighbor_cell_ids": "|".join(neighbors),
            "neighbor_mean_delta": float(neighbor_delta.mean()) if len(neighbor_delta) else np.nan,
            "neighbor_same_sign_fraction": float(np.mean(np.sign(neighbor_delta) == np.sign(row.delta))) if len(neighbor_delta) else np.nan,
        })
    table = pd.DataFrame(rows)
    value_norm = Normalize(*np.quantile(encoded.value, [.02, .98]))
    delta_limit = max(float(np.quantile(np.abs(encoded.loc[encoded.month > 1, "delta"]), .95)), 1e-9)
    delta_norm = Normalize(-delta_limit, delta_limit)
    before_values = before.value.to_dict(); after_values = after.value.to_dict(); delta_values = after.delta.to_dict()
    figure, axes = plt.subplots(2, 3, figsize=(14.5, 9.3), constrained_layout=True)
    _panel(axes[0, 0], reference.polygons, before_values, value_norm, "viridis", f"(a) Geographic before: M{month-1:02d}")
    _panel(axes[0, 1], reference.polygons, after_values, value_norm, "viridis", f"(b) Geographic after: M{month:02d}")
    _panel(axes[0, 2], reference.polygons, delta_values, delta_norm, "RdBu_r", "(c) Geographic direct Δ")
    _panel(axes[1, 0], annulus_polygons, delta_values, delta_norm, "RdBu_r", "(d) GeoAnnulus-Final direct Δ")
    _, _, layers = build_integrated_layers(encoded, geometry_path, inner, outer)
    axis = axes[1, 1]
    for layer in layers:
        add_polygons(axis, layer["polygons"], layer["values"],
                     norm=value_norm if layer["month"] == 1 else delta_norm,
                     cmap="viridis" if layer["month"] == 1 else "RdBu_r",
                     linewidth=.025, edgecolor="#40534d")
        if layer["month"] == month:
            axis.add_patch(Circle((0, 0), layer["band_outer"], fill=False, edgecolor="#fdae61", linewidth=1.4))
    axis.set_xlim(-1.04, 1.08); axis.set_ylim(-1.04, 1.04); axis.set_aspect("equal"); axis.axis("off")
    axis.set_title("(e) Integrated DeltaAnnulus\nselected layer outlined", loc="left", fontsize=9.2, fontweight="semibold")
    colors = ["#b2182b" if value > 0 else "#2166ac" for value in table.delta]
    axes[1, 2].barh(np.arange(len(table))[::-1], table.absolute_delta, color=colors)
    axes[1, 2].set_yticks(np.arange(len(table))[::-1], [f"#{row.rank} {_short}" for row, _short in
                                                       zip(table.itertuples(), table.cell_id.str.split("_").str[-1])], fontsize=7)
    axes[1, 2].set_xlabel("absolute month-to-month change")
    axes[1, 2].set_title("(f) Automatically ranked top-changing cells", loc="left", fontsize=9.2, fontweight="semibold")
    axes[1, 2].grid(axis="x", alpha=.2)
    figure.colorbar(plt.cm.ScalarMappable(norm=value_norm, cmap="viridis"), ax=axes[0, :2].tolist(),
                    orientation="horizontal", shrink=.55, label="PM2.5 absolute state (µg/m³)")
    figure.colorbar(plt.cm.ScalarMappable(norm=delta_norm, cmap="RdBu_r"), ax=[axes[0, 2], axes[1, 0], axes[1, 1]],
                    orientation="horizontal", shrink=.55, label="signed PM2.5 change (µg/m³)")
    selected_score = float(transition_scores.loc[transition_scores.month == month, "event_score"].iloc[0])
    figure.suptitle(f"Hubei temporal case selected before rendering: M{month-1:02d}→M{month:02d} (score={selected_score:.3f})",
                    fontsize=14, fontweight="semibold")
    figure_path = ROOT / "results/figures/Fig_case_hubei_temporal.png"
    figure.savefig(figure_path, dpi=300, bbox_inches="tight"); plt.close(figure)
    shutil.copy2(figure_path, ROOT / "paper/figures" / figure_path.name)
    table_path = ROOT / "results/tables/Table_case_hubei_top_changes.csv"
    write_csv(table, table_path); write_csv(table, ROOT / "paper/tables" / table_path.name)
    manifest = {
        "producer": "E38_case_study_hubei_temporal.py", "region": region,
        "selection_rule": "Equal-weight mean of min-max normalized mean absolute delta, p95 absolute delta, and high-change cell fraction over all 11 transitions; earliest month breaks an exact tie.",
        "high_change_threshold": high_threshold, "selected_month": month,
        "selected_transition": f"M{month-1:02d}-M{month:02d}", "selected_event_score": selected_score,
        "all_transition_scores": transition_scores.to_dict(orient="records"),
        "inputs": [str(encoded_path.relative_to(ROOT)), str(geometry_path.relative_to(ROOT)),
                   "data/processed/regions/湖北/original_adjacency.csv"],
        "outputs": [str(figure_path.relative_to(ROOT)), str(table_path.relative_to(ROOT))],
        "interpretation_guardrail": "Supported language is observational: spatially coherent increase/decrease, center-periphery shift, localized/distributed change, persistent/reversed change. No meteorological or transport causality is inferred.",
    }
    manifest_path = ROOT / "results/temporal/case_hubei_manifest.json"; write_json(manifest, manifest_path)
    shutil.copy2(manifest_path, ROOT / "paper" / "case_hubei_manifest.json")
    print({"selected_transition": manifest["selected_transition"], "event_score": selected_score,
           "top_cell": table.iloc[0].cell_id, "top_delta": table.iloc[0].delta})


if __name__ == "__main__":
    main()
