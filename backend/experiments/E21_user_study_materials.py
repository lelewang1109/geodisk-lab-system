from __future__ import annotations

import json
import math

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import PatchCollection
from matplotlib.colors import Normalize
from matplotlib.patches import Polygon as MplPolygon
import numpy as np
import pandas as pd
from scipy.stats import nct, t

from common import ROOT, ensure_output_dirs, experiment_config, seed_everything
from geodisk_paper.data.regions import load_region_reference
from geodisk_paper.geometry.power import polygon_parts
from geodisk_paper.geometry.serialization import load_geometry
from geodisk_paper.utils.io import write_csv, write_json


def paired_sample_size(effect: float = .5, alpha: float = .05, power: float = .8) -> int:
    for sample_size in range(8, 300):
        degrees = sample_size - 1
        critical = t.ppf(1 - alpha / 2, degrees)
        achieved = 1 - nct.cdf(critical, degrees, effect * math.sqrt(sample_size)) + nct.cdf(-critical, degrees, effect * math.sqrt(sample_size))
        if achieved >= power:
            return sample_size
    raise RuntimeError("Power target not reached")


def _render(polygons: dict, values: dict[str, float], candidates: list[str], output, limit: float, title: str) -> None:
    patches, colors, outlines = [], [], []
    for cell_id, geometry in polygons.items():
        for part in polygon_parts(geometry):
            patch = MplPolygon(np.asarray(part.exterior.coords), closed=True)
            patches.append(patch); colors.append(float(values.get(cell_id, 0.0)))
            if cell_id in candidates:
                outlines.append(MplPolygon(np.asarray(part.exterior.coords), closed=True, fill=False))
    figure, axis = plt.subplots(figsize=(5.2, 4.6), constrained_layout=True)
    collection = PatchCollection(patches, cmap="RdBu_r", norm=Normalize(-limit, limit), linewidth=.12, edgecolor="#31423d")
    collection.set_array(np.asarray(colors)); axis.add_collection(collection)
    if outlines:
        highlight = PatchCollection(outlines, facecolor="none", edgecolor="#f7c948", linewidth=1.3)
        axis.add_collection(highlight)
    bounds = np.asarray([geometry.bounds for geometry in polygons.values()])
    margin_x = max((bounds[:, 2].max() - bounds[:, 0].min()) * .04, .02)
    margin_y = max((bounds[:, 3].max() - bounds[:, 1].min()) * .04, .02)
    axis.set_xlim(bounds[:, 0].min() - margin_x, bounds[:, 2].max() + margin_x)
    axis.set_ylim(bounds[:, 1].min() - margin_y, bounds[:, 3].max() + margin_y)
    axis.set_aspect("equal"); axis.axis("off"); axis.set_title(title, fontsize=11)
    figure.colorbar(plt.cm.ScalarMappable(norm=Normalize(-limit, limit), cmap="RdBu_r"), ax=axis, shrink=.72, label="monthly change")
    output.parent.mkdir(parents=True, exist_ok=True); figure.savefig(output, dpi=160, bbox_inches="tight"); plt.close(figure)


def _candidate_ids(month: pd.DataFrame, rng) -> list[str]:
    ranked = month.assign(magnitude=month.delta.abs()).sort_values("magnitude", ascending=False)
    answer = str(ranked.iloc[0].cell_id)
    pool = ranked.iloc[max(1, len(ranked)//4):].cell_id.astype(str).tolist()
    distractors = list(rng.choice(pool, size=3, replace=False))
    candidates = [answer, *distractors]; rng.shuffle(candidates)
    return candidates


def main() -> None:
    ensure_output_dirs(); seed = seed_everything(); phase2 = experiment_config()["phase2"]; rng = np.random.default_rng(seed)
    study_root = ROOT / "user_study"; stimulus_root = study_root / "stimuli"
    definitions = [
        ("Hubei", "湖北", ROOT / "data/processed/regions", ROOT / "results/spatial_refined/湖北/final_refined_annulus.geojson"),
        ("NCEP", "NCEP-AirTemp-Africa-2000", ROOT / "data/processed/external_regions", ROOT / "results/external_refined/NCEP-AirTemp-Africa-2000/final_refined_annulus.geojson"),
    ]
    tasks = ["change_localization", "increase_decrease", "temporal_comparison", "radial_propagation"]
    transitions = [int(value) for value in phase2["user_study_transitions"]]; rows = []
    for short_name, dataset, reference_root, annulus_path in definitions:
        reference = load_region_reference(reference_root, dataset)
        encoded = pd.read_csv(ROOT / "results/temporal" / dataset / "monthly_delta_encoding.csv")
        annulus = load_geometry(annulus_path)
        geometries = {
            "geographic_map": reference.polygons,
            "delta_annulus": dict(zip(annulus.cell_ids, annulus.geometries)),
        }
        limit = max(float(encoded.delta.abs().quantile(.95)), 1e-9)
        for month_number in transitions:
            month = encoded[encoded.month == month_number].copy()
            values = dict(zip(month.cell_id.astype(str), month.delta.astype(float)))
            candidates = _candidate_ids(month, rng)
            ranked = month.assign(magnitude=month.delta.abs()).sort_values("magnitude", ascending=False)
            largest = str(ranked.iloc[0].cell_id); target = str(candidates[0])
            target_delta = float(month.set_index("cell_id").loc[target, "delta"])
            pair = [str(value) for value in ranked.iloc[:2].cell_id]; rng.shuffle(pair)
            pair_values = month.set_index("cell_id").delta.abs()
            comparison_answer = max(pair, key=lambda cell_id: float(pair_values.loc[cell_id]))
            inner_mean = float(month[month.rho <= month.rho.median()].delta.mean())
            outer_mean = float(month[month.rho > month.rho.median()].delta.mean())
            for condition, polygons in geometries.items():
                stimulus = stimulus_root / f"{short_name}_M{month_number:02d}_{condition}.png"
                _render(polygons, values, candidates, stimulus, limit, f"{short_name} · M{month_number-1:02d} → M{month_number:02d}")
                answers = {
                    "change_localization": largest,
                    "increase_decrease": "increase" if target_delta > 0 else "decrease" if target_delta < 0 else "stable",
                    "temporal_comparison": comparison_answer,
                    "radial_propagation": "outer" if outer_mean > inner_mean else "inner",
                }
                options = {
                    "change_localization": candidates,
                    "increase_decrease": ["increase", "decrease", "stable"],
                    "temporal_comparison": pair,
                    "radial_propagation": ["inner", "outer"],
                }
                for task in tasks:
                    rows.append({
                        "trial_id": f"{short_name}_M{month_number:02d}_{condition}_{task}",
                        "dataset": dataset, "transition": f"M{month_number-1:02d}-M{month_number:02d}",
                        "condition": condition, "task": task,
                        "stimulus_path": str(stimulus.relative_to(study_root)),
                        "candidate_cell_ids": json.dumps(options[task], ensure_ascii=False),
                        "target_cell_id": target if task == "increase_decrease" else "",
                        "ground_truth": answers[task], "color_limit": limit,
                        "counterbalance_block": "A" if condition == "geographic_map" else "B",
                    })
    manifest = pd.DataFrame(rows)
    write_csv(manifest, study_root / "task_manifest.csv")
    response_schema = pd.DataFrame(columns=[
        "participant_id", "trial_id", "condition", "task", "response", "correct",
        "completion_time_ms", "confidence_1_7", "device", "timestamp_utc",
    ])
    write_csv(response_schema, study_root / "response_schema.csv")
    required = paired_sample_size(); target = math.ceil(required / .85)
    write_json({
        "design": "within-subject 2-condition counterbalanced study", "conditions": ["geographic_map", "delta_annulus"],
        "tasks": tasks, "trial_count": len(manifest), "trials_per_participant_before_sampling": len(manifest),
        "power_analysis": {"test": "two-sided paired t approximation for the primary accuracy contrast",
                           "effect_size_dz": .5, "alpha": .05, "power": .8,
                           "complete_participants_required": required, "recruitment_target_15pct_attrition": target},
        "status": "materials generated; no participant data have been collected",
    }, study_root / "study_manifest.json")
    print({"trials": len(manifest), "required_complete": required, "recruitment_target": target})


if __name__ == "__main__":
    main()
