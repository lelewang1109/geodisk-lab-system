from __future__ import annotations

import json
import math
import shutil

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import Normalize
from matplotlib.patches import Circle
import numpy as np
import pandas as pd

from common import ROOT, ensure_output_dirs, experiment_config, geometry_config, seed_everything
from geodisk_paper.data.regions import load_region_reference
from geodisk_paper.geometry.serialization import load_geometry
from geodisk_paper.utils.io import write_csv, write_json
from E35_integrated_delta_annulus import build_integrated_layers
from paper_figure_utils import add_polygons, set_geometry_extent


CONDITIONS = {
    "C1_geographic_state_comparison": "Geographic State Comparison",
    "C2_geographic_direct_delta": "Geographic Direct Delta",
    "C3_canonical_geoannulus_direct_delta": "Canonical GeoAnnulus Direct Delta",
    "C4_integrated_deltaannulus": "Integrated DeltaAnnulus",
}
TASKS = ["change_localization", "increase_decrease", "magnitude_comparison",
         "temporal_comparison", "radial_center_periphery_pattern"]


def _highlight(axis, polygons, candidates):
    for number, cell_id in enumerate(candidates, start=1):
        if cell_id not in polygons:
            continue
        point = polygons[cell_id].representative_point()
        axis.text(point.x, point.y, str(number), ha="center", va="center", fontsize=6.5,
                  bbox={"boxstyle": "circle,pad=.1", "fc": "#fff7bc", "ec": "#d95f0e", "lw": .6}, zorder=8)


def _panel(axis, polygons, values, norm, cmap, title, candidates=()):
    add_polygons(axis, polygons, values, norm=norm, cmap=cmap, linewidth=.08, edgecolor="#40534d")
    _highlight(axis, polygons, candidates); set_geometry_extent(axis, polygons.values(), margin=.025)
    axis.set_title(title, fontsize=8.5)


def _render_stimulus(condition, reference, annulus, encoded, target_month, candidates,
                     value_norm, delta_norm, output, inner, outer):
    comparison_month = max(2, target_month - 1)
    by_month = {month: encoded[encoded.month == month].set_index("cell_id") for month in range(1, 13)}
    annulus_polygons = dict(zip(annulus.cell_ids, annulus.geometries))
    if condition == "C1_geographic_state_comparison":
        figure, axes = plt.subplots(2, 2, figsize=(7.4, 6.6), constrained_layout=True)
        for row, month in enumerate((comparison_month, target_month)):
            before = by_month[month - 1].value.to_dict(); after = by_month[month].value.to_dict()
            _panel(axes[row, 0], reference.polygons, before, value_norm, "viridis", f"M{month-1:02d}")
            _panel(axes[row, 1], reference.polygons, after, value_norm, "viridis", f"M{month:02d}", candidates)
            axes[row, 0].set_ylabel("comparison" if row == 0 else "target", fontsize=8)
        scalar = plt.cm.ScalarMappable(norm=value_norm, cmap="viridis")
    elif condition in {"C2_geographic_direct_delta", "C3_canonical_geoannulus_direct_delta"}:
        figure, axes = plt.subplots(1, 2, figsize=(7.6, 3.8), constrained_layout=True)
        polygons = reference.polygons if condition.startswith("C2") else annulus_polygons
        for axis, month, label in zip(axes, (comparison_month, target_month), ("comparison", "target")):
            values = by_month[month].delta.to_dict()
            _panel(axis, polygons, values, delta_norm, "RdBu_r", f"{label}: M{month-1:02d}→M{month:02d}", candidates if label == "target" else ())
        scalar = plt.cm.ScalarMappable(norm=delta_norm, cmap="RdBu_r")
    else:
        _, _, layers = build_integrated_layers(encoded, annulus.metadata.get("_path", output), inner, outer)
        figure, axis = plt.subplots(figsize=(6.6, 6.2), constrained_layout=True); axes = [axis]
        for layer in layers:
            norm = value_norm if layer["month"] == 1 else delta_norm
            cmap = "viridis" if layer["month"] == 1 else "RdBu_r"
            add_polygons(axis, layer["polygons"], layer["values"], norm=norm, cmap=cmap,
                         linewidth=.04, edgecolor="#40534d")
            if layer["month"] in {comparison_month, target_month}:
                color = "#4d4d4d" if layer["month"] == comparison_month else "#fdae61"
                axis.add_patch(Circle((0, 0), layer["band_outer"], fill=False, edgecolor=color,
                                      linewidth=1.1 if layer["month"] == target_month else .7))
                axis.text(layer["band_outer"] + .01, 0, "target" if layer["month"] == target_month else "comparison",
                          fontsize=6.5, color=color)
                if layer["month"] == target_month:
                    _highlight(axis, layer["polygons"], candidates)
        axis.set_xlim(-1.05, 1.13); axis.set_ylim(-1.05, 1.05); axis.set_aspect("equal"); axis.axis("off")
        axis.set_title("D1 + eleven fixed-identity delta layers", fontsize=9)
        scalar = plt.cm.ScalarMappable(norm=delta_norm, cmap="RdBu_r")
    figure.suptitle(CONDITIONS[condition], fontsize=11, fontweight="semibold")
    figure.colorbar(scalar, ax=np.asarray(axes).ravel().tolist(), orientation="horizontal", shrink=.55, pad=.025,
                    label="absolute state" if condition.startswith("C1") else "signed month-to-month change")
    output.parent.mkdir(parents=True, exist_ok=True); figure.savefig(output, dpi=300, bbox_inches="tight"); plt.close(figure)


def _candidates(month: pd.DataFrame, rng) -> list[str]:
    ranked = month.assign(magnitude=month.delta.abs()).sort_values(["magnitude", "cell_id"], ascending=[False, True])
    answer = str(ranked.iloc[0].cell_id)
    pool = ranked.iloc[max(1, len(ranked) // 4):].cell_id.astype(str).tolist()
    distractors = list(rng.choice(pool, size=3, replace=False))
    result = [answer, *distractors]; rng.shuffle(result); return result


def main() -> None:
    ensure_output_dirs(); seed = seed_everything(); rng = np.random.default_rng(seed)
    geometry = geometry_config(); inner = float(geometry["annulus_inner"]); outer = float(geometry["annulus_outer"])
    transitions = [int(value) for value in experiment_config()["phase2"]["user_study_transitions"]]
    study_root = ROOT / "user_study_v2"; stimulus_root = study_root / "stimuli"; rows = []
    definitions = [
        ("Hubei", "湖北", ROOT / "data/processed/regions", ROOT / "results/spatial_refined/湖北/final_refined_annulus.geojson"),
        ("NCEP", "NCEP-AirTemp-Africa-2000", ROOT / "data/processed/external_regions",
         ROOT / "results/external_refined/NCEP-AirTemp-Africa-2000/final_refined_annulus.geojson"),
    ]
    for short, dataset, reference_root, geometry_path in definitions:
        encoded_path = ROOT / "results/temporal" / dataset / "monthly_delta_encoding.csv"
        if not geometry_path.exists():
            raise FileNotFoundError(f"Missing {geometry_path}; run E19 first")
        if not encoded_path.exists():
            raise FileNotFoundError(f"Missing {encoded_path}; run E5 first")
        reference = load_region_reference(reference_root, dataset); annulus = load_geometry(geometry_path, inner, outer)
        annulus.metadata["_path"] = geometry_path
        encoded = pd.read_csv(encoded_path, dtype={"cell_id": str})
        value_norm = Normalize(*np.quantile(encoded.value, [.02, .98]))
        limit = max(float(np.quantile(np.abs(encoded.loc[encoded.month > 1, "delta"]), .95)), 1e-9)
        delta_norm = Normalize(-limit, limit)
        for month in transitions:
            current = encoded[encoded.month == month].copy(); candidates = _candidates(current, rng)
            ranked = current.assign(magnitude=current.delta.abs()).sort_values(["magnitude", "cell_id"], ascending=[False, True])
            largest = str(ranked.iloc[0].cell_id); target = str(ranked.iloc[len(ranked) // 3].cell_id)
            pair = [str(ranked.iloc[0].cell_id), str(ranked.iloc[1].cell_id)]; rng.shuffle(pair)
            comparison_month = max(2, month - 1)
            comparison = encoded[encoded.month == comparison_month]
            current_score = float(current.delta.abs().mean()); comparison_score = float(comparison.delta.abs().mean())
            median_rho = float(current.rho.median())
            inner_score = float(current[current.rho <= median_rho].delta.abs().mean())
            outer_score = float(current[current.rho > median_rho].delta.abs().mean())
            relative_difference = abs(inner_score - outer_score) / max(inner_score, outer_score, 1e-12)
            radial_answer = "balanced" if relative_difference <= .05 else "inner_dominant" if inner_score > outer_score else "outer_dominant"
            truths = {
                "change_localization": largest,
                "increase_decrease": "increase" if float(current.set_index("cell_id").loc[target, "delta"]) > 0 else "decrease",
                "magnitude_comparison": max(pair, key=lambda cell: abs(float(current.set_index("cell_id").loc[cell, "delta"]))),
                "temporal_comparison": "target_transition" if current_score > comparison_score else "comparison_transition",
                "radial_center_periphery_pattern": radial_answer,
            }
            options = {
                "change_localization": candidates, "increase_decrease": ["increase", "decrease"],
                "magnitude_comparison": pair, "temporal_comparison": ["comparison_transition", "target_transition"],
                "radial_center_periphery_pattern": ["inner_dominant", "outer_dominant", "balanced"],
            }
            for block, condition in enumerate(CONDITIONS):
                stimulus = stimulus_root / f"{short}_M{month:02d}_{condition}.png"
                _render_stimulus(condition, reference, annulus, encoded, month, candidates,
                                 value_norm, delta_norm, stimulus, inner, outer)
                for task in TASKS:
                    rows.append({
                        "trial_id": f"{short}_M{month:02d}_{condition}_{task}", "dataset": dataset,
                        "target_transition": f"M{month-1:02d}-M{month:02d}",
                        "comparison_transition": f"M{comparison_month-1:02d}-M{comparison_month:02d}",
                        "condition": condition, "condition_label": CONDITIONS[condition], "task": task,
                        "stimulus_path": str(stimulus.relative_to(study_root)),
                        "candidate_cell_ids": json.dumps(options[task], ensure_ascii=False),
                        "target_cell_id": target if task == "increase_decrease" else "",
                        "ground_truth": truths[task], "delta_color_limit": limit,
                        "counterbalance_block": chr(65 + block),
                    })
    manifest = pd.DataFrame(rows); write_csv(manifest, study_root / "task_manifest.csv")
    schema = pd.DataFrame(columns=["participant_id", "trial_id", "condition", "task", "response", "correct",
                                         "completion_time_ms", "confidence_1_7", "device", "timestamp_utc"])
    write_csv(schema, study_root / "response_schema.csv")
    write_json({
        "design": "within-subject four-condition decomposition",
        "conditions": CONDITIONS, "contrasts": {
            "C1_vs_C2": "direct delta encoding", "C2_vs_C3": "canonicalization",
            "C3_vs_C4": "integrated temporal organization",
        },
        "tasks": TASKS, "trial_count": len(manifest), "seed": seed,
        "radial_ground_truth": "Compare mean absolute delta for cells at/below versus above the dataset median rho; balanced if relative difference <= 5%.",
        "causal_guardrail": "The radial task measures an objective center/periphery pattern and is not described as propagation.",
        "status": "NO PARTICIPANT DATA COLLECTED",
    }, study_root / "study_manifest.json")
    print({"stimuli": manifest.stimulus_path.nunique(), "trials": len(manifest), "responses": len(schema),
           "status": "NO PARTICIPANT DATA COLLECTED"})


if __name__ == "__main__":
    main()
