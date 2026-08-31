from __future__ import annotations

from itertools import product

import numpy as np
import pandas as pd

from common import ROOT, ensure_output_dirs, seed_everything
from geodisk_paper.utils.io import write_csv, write_json


COMPARISONS = {
    "disk": {"refined": "GeoDisk-Final", "original": "GeoDisk"},
    "annulus": {"refined": "GeoAnnulus-Final", "original": "GeoAnnulus"},
}
METRICS = ["adj_f1", "np2", "local_direction_error_deg", "angular_error_deg", "radial_spearman"]


def _bootstrap(values: np.ndarray, rng, samples: int = 10000) -> tuple[float, float]:
    draws = values[rng.integers(0, len(values), size=(samples, len(values)))].mean(axis=1)
    return float(np.quantile(draws, .025)), float(np.quantile(draws, .975))


def _paired_sign_flip_p(values: np.ndarray, rng, samples: int = 10000) -> float:
    observed = abs(float(np.mean(values)))
    if len(values) <= 16:
        signs = np.asarray(list(product((-1.0, 1.0), repeat=len(values))))
        permuted = np.abs(np.mean(signs * values, axis=1))
        return float(np.mean(permuted >= observed - 1e-15))
    signs = rng.choice(np.asarray([-1.0, 1.0]), size=(samples, len(values)))
    permuted = np.abs(np.mean(signs * values, axis=1))
    return float((1 + np.sum(permuted >= observed)) / (samples + 1))


def _holm_adjust(values: pd.Series) -> pd.Series:
    order = np.argsort(values.to_numpy(float))
    ranked = values.to_numpy(float)[order]
    adjusted_ranked = np.maximum.accumulate((len(ranked) - np.arange(len(ranked))) * ranked)
    adjusted = np.empty(len(ranked), dtype=float)
    adjusted[order] = np.clip(adjusted_ranked, 0.0, 1.0)
    return pd.Series(adjusted, index=values.index)


def main() -> None:
    ensure_output_dirs(); rng = np.random.default_rng(seed_everything())
    baseline = pd.read_csv(ROOT / "results/tables/Table_spatial_fidelity.csv", encoding="utf-8-sig")
    baseline = baseline[~baseline.region.astype(str).str.startswith("OVERALL")]
    refined = pd.read_csv(ROOT / "results/tables/Table_final_power_refinement.csv", encoding="utf-8-sig")
    refined = refined[refined.dataset_family == "ceg"].rename(columns={"dataset": "region"})
    rows = []
    for view, names in COMPARISONS.items():
        refined_view = refined[(refined.view == view) & (refined.method == names["refined"])]
        comparators = [names["original"], "Direct Polar", "Harmonic", "Area-balanced", "Regular Topology"]
        for comparator in comparators:
            other = baseline[(baseline.view == view) & (baseline.method == comparator)]
            merged = refined_view.merge(other, on="region", suffixes=("_refined", "_comparator"))
            for metric in METRICS:
                difference = merged[f"{metric}_refined"].to_numpy(float) - merged[f"{metric}_comparator"].to_numpy(float)
                low, high = _bootstrap(difference, rng)
                permutation_p = _paired_sign_flip_p(difference, rng)
                rows.append({
                    "view": view, "refined_method": names["refined"], "comparator": comparator,
                    "metric": metric, "region_count": len(difference),
                    "refined_mean": float(merged[f"{metric}_refined"].mean()),
                    "comparator_mean": float(merged[f"{metric}_comparator"].mean()),
                    "mean_difference": float(np.mean(difference)), "ci95_low": low, "ci95_high": high,
                    "paired_permutation_p": permutation_p,
                    "refined_better_count": int(np.sum(difference < 0 if metric.endswith("error_deg") else difference > 0)),
                    "bootstrap_samples": 10000,
                })
    frame = pd.DataFrame(rows)
    frame["paired_permutation_p_holm"] = frame.groupby(
        ["view", "metric"], group_keys=False
    )["paired_permutation_p"].apply(_holm_adjust)
    frame["permutation_mode"] = np.where(frame.region_count <= 16, "exact", "monte_carlo")
    frame["holm_family_size"] = frame.groupby(["view", "metric"])["comparator"].transform("size")
    write_csv(frame, ROOT / "results/tables/Table_refined_paired_bootstrap.csv")
    write_csv(frame, ROOT / "paper/tables/Table_refined_paired_bootstrap.csv")
    key = frame[(frame.metric == "adj_f1") & frame.comparator.isin(["Direct Polar", "Harmonic", "Area-balanced"])]
    write_json({
        "resampling_unit": "province/region", "paired": True, "bootstrap_samples": 10000,
        "multiple_comparison_note": "Confidence intervals are descriptive and unadjusted. Exact paired sign-flip p-values are Holm-adjusted within each view-by-metric family across five comparators.",
        "primary_results": key.to_dict(orient="records"),
    }, ROOT / "results/spatial_refined/refined_statistics_manifest.json")
    print(key.to_string(index=False))


if __name__ == "__main__":
    main()
