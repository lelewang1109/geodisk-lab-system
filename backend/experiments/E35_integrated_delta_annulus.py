from __future__ import annotations

import shutil
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import Normalize
from matplotlib.patches import Circle
import numpy as np
import pandas as pd

from common import ROOT, ensure_output_dirs, geometry_config
from geodisk_paper.geometry.serialization import load_geometry
from geodisk_paper.metrics.geometry import display_adjacency, edge_jaccard
from geodisk_paper.utils.io import read_json, write_csv, write_json
from paper_figure_utils import add_polygons, integrated_band_geometries, sha256


DATASETS = {
    "湖北": (ROOT / "results/spatial_refined/湖北/final_refined_annulus.geojson",
           "Fig_integrated_delta_annulus_Hubei.png", "Hubei"),
    "NCEP-AirTemp-Africa-2000": (ROOT / "results/external_refined/NCEP-AirTemp-Africa-2000/final_refined_annulus.geojson",
                                  "Fig_integrated_delta_annulus_NCEP.png", "NCEP Africa 2000"),
}


def band_ranges(count: int = 12) -> list[tuple[float, float]]:
    # D1 receives a slightly wider inner band. The remaining eleven transitions
    # occupy equal-width concentric bands with small separators.
    starts = np.linspace(.23, .985, count)
    ranges = [(.105, .205)]
    for index in range(1, count):
        left = float(starts[index - 1]); right = float(starts[index] - .008)
        ranges.append((left, right))
    return ranges


def build_integrated_layers(encoded: pd.DataFrame, geometry_path: Path, inner: float, outer: float):
    result = load_geometry(geometry_path, inner, outer)
    base = dict(zip(result.cell_ids, result.geometries)); layers = []
    for month, (band_inner, band_outer) in enumerate(band_ranges(), start=1):
        values = encoded[encoded.month == month].set_index(encoded[encoded.month == month].cell_id.astype(str))
        field = values.value.to_dict() if month == 1 else values.delta.to_dict()
        layers.append({
            "month": month, "label": "D1" if month == 1 else f"Δ{month-1},{month}",
            "band_inner": band_inner, "band_outer": band_outer,
            "polygons": integrated_band_geometries(base, inner, outer, band_inner, band_outer),
            "values": {str(key): float(value) for key, value in field.items()},
        })
    return result, base, layers


def render_integrated(dataset: str, encoded: pd.DataFrame, geometry_path: Path, output: Path,
                      display_title: str, inner: float, outer: float) -> list[dict]:
    result, base, layers = build_integrated_layers(encoded, geometry_path, inner, outer)
    value_low, value_high = [float(value) for value in np.quantile(encoded.value.to_numpy(float), [.02, .98])]
    delta_limit = max(float(np.quantile(np.abs(encoded.loc[encoded.month > 1, "delta"]), .95)), 1e-9)
    value_norm = Normalize(value_low, value_high); delta_norm = Normalize(-delta_limit, delta_limit)
    figure, axis = plt.subplots(figsize=(11.0, 10.5), constrained_layout=True)
    collections = []
    label_y = np.linspace(.72, -.72, len(layers))
    for layer, y_position in zip(layers, label_y):
        collection = add_polygons(
            axis, layer["polygons"], layer["values"],
            cmap="viridis" if layer["month"] == 1 else "RdBu_r",
            norm=value_norm if layer["month"] == 1 else delta_norm,
            edgecolor="#33443f", linewidth=.045 if len(base) > 250 else .085,
        )
        collections.append(collection)
        axis.add_patch(Circle((0, 0), layer["band_outer"], fill=False, edgecolor="white", linewidth=.45, alpha=.85))
        axis.annotate(layer["label"], xy=(layer["band_outer"], 0), xytext=(1.10, y_position),
                      fontsize=7.2, va="center", ha="left",
                      arrowprops={"arrowstyle": "-", "color": "#70807b", "lw": .45})
    axis.add_patch(Circle((0, 0), .09, facecolor="white", edgecolor="#b9c7c2", linewidth=.8))
    axis.text(0, 0, "fixed\nCell ID", ha="center", va="center", fontsize=7, color="#2c3e38")
    axis.set_xlim(-1.07, 1.32); axis.set_ylim(-1.07, 1.07); axis.set_aspect("equal"); axis.axis("off")
    axis.set_title(f"Integrated DeltaAnnulus · {display_title}\nD1 (inner) + 11 signed month-to-month changes (outward)",
                   fontsize=14, fontweight="semibold")
    value_bar = figure.colorbar(plt.cm.ScalarMappable(norm=value_norm, cmap="viridis"), ax=axis,
                                orientation="horizontal", fraction=.035, pad=.025, shrink=.42, anchor=(0, .5))
    value_bar.set_label("D1 absolute state (2–98% fixed normalization)", fontsize=8)
    delta_bar = figure.colorbar(plt.cm.ScalarMappable(norm=delta_norm, cmap="RdBu_r"), ax=axis,
                                orientation="horizontal", fraction=.035, pad=.09, shrink=.42, anchor=(1, .5))
    delta_bar.set_label("signed Δ (symmetric 95% fixed normalization)", fontsize=8)
    output.parent.mkdir(parents=True, exist_ok=True); figure.savefig(output, dpi=300, bbox_inches="tight"); plt.close(figure)

    source_edges = display_adjacency(result.cell_ids, result.geometries)
    source_ids = set(result.cell_ids); rows = []
    for layer in layers:
        ids = set(layer["polygons"])
        geometries = [layer["polygons"][cell_id] for cell_id in result.cell_ids]
        scaled_tolerance = 2e-5 * max((layer["band_outer"] - layer["band_inner"]) / max(outer - inner, 1e-12), .05)
        rendered_edges = display_adjacency(result.cell_ids, geometries, tolerance=scaled_tolerance)
        rows.append({
            "dataset": dataset, "layer": layer["label"], "month": layer["month"],
            "cell_count": len(ids), "cell_identity_accuracy": len(ids & source_ids) / len(source_ids),
            "deterministic_cell_tracking": ids == source_ids,
            "geometry_reoptimized_per_layer": False, "cell_reordering": False,
            "temporal_layer_mismatch_count": len(ids ^ source_ids),
            "logical_temporal_adjacency_jaccard": 1.0,
            "rendered_adjacency_jaccard": edge_jaccard(source_edges, rendered_edges),
            "source_final_geometry_sha256": sha256(geometry_path),
        })
    return rows


def main() -> None:
    ensure_output_dirs(); config = geometry_config(); inner = float(config["annulus_inner"]); outer = float(config["annulus_outer"])
    rows = []; entries = []
    for dataset, (geometry_path, figure_name, display_title) in DATASETS.items():
        encoded_path = ROOT / "results/temporal" / dataset / "monthly_delta_encoding.csv"
        manifest_path = ROOT / "results/temporal" / dataset / "encoding_manifest.json"
        if not geometry_path.exists():
            raise FileNotFoundError(f"Missing {geometry_path}; run E19 first")
        if not encoded_path.exists() or not manifest_path.exists():
            raise FileNotFoundError(f"Missing temporal encoding for {dataset}; run E5 first")
        encoded = pd.read_csv(encoded_path, encoding="utf-8-sig")
        encoding_manifest = read_json(manifest_path)
        output = ROOT / "results/figures" / figure_name
        dataset_rows = render_integrated(dataset, encoded, geometry_path, output, display_title, inner, outer)
        rows.extend(dataset_rows); shutil.copy2(output, ROOT / "paper/figures" / output.name)
        entries.append({"dataset": dataset, "encoding": str(encoded_path.relative_to(ROOT)),
                        "geometry": str(geometry_path.relative_to(ROOT)), "geometry_sha256": sha256(geometry_path),
                        "figure": str(output.relative_to(ROOT)), "normalization": encoding_manifest})
        print("[integrated DeltaAnnulus]", dataset, flush=True)
    table = pd.DataFrame(rows)
    write_csv(table, ROOT / "results/tables/Table_integrated_delta_annulus_consistency.csv")
    write_csv(table, ROOT / "paper/tables/Table_integrated_delta_annulus_consistency.csv")
    write_json({
        "producer": "E35_integrated_delta_annulus.py", "selected_design": "B",
        "design_reason": "Concentric remaps of one fixed Final GeoAnnulus retain a direct deterministic cell correspondence while placing D1 and all eleven deltas in one compact temporal order. Design A would visually privilege a separate center state and disconnect it from the canonical annulus topology.",
        "mapping": "Each layer is a deterministic radial homeomorphic remap of the same final GeoAnnulus polygons; theta order and cell IDs are unchanged; no monthly geometry optimization occurs.",
        "guardrail": "Identity, no-reoptimization and logical adjacency values are construction checks, not comparative performance advantages.",
        "entries": entries,
    }, ROOT / "results/temporal/integrated_delta_annulus_manifest.json")
    print(table.groupby("dataset")[["cell_identity_accuracy", "rendered_adjacency_jaccard",
                                     "temporal_layer_mismatch_count"]].agg(["min", "max"]).to_string())


if __name__ == "__main__":
    main()
