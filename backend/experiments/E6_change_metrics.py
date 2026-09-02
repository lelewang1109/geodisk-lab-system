from __future__ import annotations

import math

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

from common import ROOT, ensure_output_dirs, experiment_config, geometry_config, seed_everything
from geodisk_paper.utils.io import write_csv, write_json


def _reconstruct(values: np.ndarray, low: float, high: float, bins: int) -> np.ndarray:
    edges = np.linspace(low, high, bins + 1); centers = .5 * (edges[:-1] + edges[1:])
    indexes = np.clip(np.searchsorted(edges, np.clip(values, low, high), side="right") - 1, 0, bins - 1)
    return centers[indexes]


def _top_fraction(values: np.ndarray, fraction: float) -> set[int]:
    count = max(1, int(math.ceil(len(values) * fraction)))
    return set(np.argsort(np.abs(values))[-count:])


def _metrics(true: np.ndarray, predicted: np.ndarray, scale: float) -> dict[str, float]:
    epsilon = max(scale * 1e-8, 1e-12)
    active = np.abs(true) > epsilon
    sign = float(np.mean(np.sign(true[active]) == np.sign(predicted[active]))) if np.any(active) else 1.0
    absolute_true = np.abs(true)
    absolute_predicted = np.abs(predicted)
    if np.ptp(absolute_true) <= epsilon or np.ptp(absolute_predicted) <= epsilon:
        rank = 0.0
    else:
        rank = float(spearmanr(absolute_true, absolute_predicted).statistic)
        if not np.isfinite(rank):
            rank = 0.0
    true_top, predicted_top = _top_fraction(true, .10), _top_fraction(predicted, .10)
    top_jaccard = len(true_top & predicted_top) / len(true_top | predicted_top)
    threshold = float(np.quantile(np.abs(true), .75))
    truth_event = set(np.flatnonzero(np.abs(true) >= threshold))
    predicted_event = set(np.flatnonzero(np.abs(predicted) >= threshold))
    common = truth_event & predicted_event
    precision = len(common) / len(predicted_event) if predicted_event else 0.0
    recall = len(common) / len(truth_event) if truth_event else 1.0
    event_f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {
        "delta_sign_accuracy": sign,
        "delta_mae": float(np.mean(np.abs(predicted - true))),
        "normalized_delta_mae": float(np.mean(np.abs(predicted - true)) / max(scale, 1e-12)),
        "delta_bias": float(np.mean(predicted - true)),
        "magnitude_spearman": rank,
        "top10_change_jaccard": float(top_jaccard),
        "high_change_event_f1": float(event_f1),
    }


def _evaluate_dataset(dataset: str, encoded: pd.DataFrame, bin_counts: list[int], rows: list[dict]) -> None:
    matrix = encoded.pivot(index="cell_id", columns="month", values="value").sort_index(axis=1).to_numpy(float)
    low, high = np.quantile(matrix, [.02, .98]); true_delta = np.diff(matrix, axis=1)
    delta_limit = max(float(np.quantile(np.abs(true_delta), .95)), 1e-12)
    for bin_count in bin_counts:
        reconstructed_values = _reconstruct(matrix, float(low), float(high), bin_count)
        derived = np.diff(reconstructed_values, axis=1)
        direct = _reconstruct(true_delta, -delta_limit, delta_limit, bin_count)
        for transition in range(11):
            for mode, predicted in (("derived_from_value_bins", derived[:, transition]),
                                    ("direct_diverging_delta", direct[:, transition])):
                rows.append({
                    "dataset": dataset, "transition": f"M{transition + 1:02d}-M{transition + 2:02d}",
                    "bin_count": bin_count, "encoding_mode": mode, "cell_count": matrix.shape[0],
                    "cell_identity_accuracy": 1.0, "geometry_centroid_drift": 0.0,
                    "temporal_adjacency_jaccard": 1.0,
                    **_metrics(true_delta[:, transition], predicted, delta_limit),
                })


def _bootstrap_difference(frame: pd.DataFrame, seed: int, samples: int = 5000) -> pd.DataFrame:
    selected = frame[frame.bin_count == 9]
    index_columns = ["dataset", "transition"]
    metrics = ["delta_sign_accuracy", "normalized_delta_mae", "magnitude_spearman",
               "top10_change_jaccard", "high_change_event_f1"]
    pivot = selected.pivot(index=index_columns, columns="encoding_mode", values=metrics).dropna()
    rng = np.random.default_rng(seed); rows = []
    for metric in metrics:
        direct = pivot[(metric, "direct_diverging_delta")].to_numpy(float)
        derived = pivot[(metric, "derived_from_value_bins")].to_numpy(float)
        difference = direct - derived
        draws = np.mean(difference[rng.integers(0, len(difference), size=(samples, len(difference)))], axis=1)
        rows.append({
            "metric": metric, "comparison": "direct_diverging_delta - derived_from_value_bins",
            "pair_count": len(difference), "mean_difference": float(np.mean(difference)),
            "ci95_low": float(np.quantile(draws, .025)), "ci95_high": float(np.quantile(draws, .975)),
            "bootstrap_samples": samples,
        })
    return pd.DataFrame(rows)


def main() -> None:
    ensure_output_dirs(); config = geometry_config(); phase2 = experiment_config()["phase2"]
    seed = seed_everything(); rows: list[dict] = []
    datasets = list(config["regions"]) + ["NCEP-AirTemp-Africa-2000"]
    for dataset in datasets:
        path = ROOT / "results/temporal" / dataset / "monthly_delta_encoding.csv"
        if not path.exists():
            raise FileNotFoundError(f"Run E5 first: {path}")
        _evaluate_dataset(dataset, pd.read_csv(path), [int(value) for value in phase2["temporal_bin_counts"]], rows)
        print("[change fidelity]", dataset, flush=True)
    frame = pd.DataFrame(rows)
    write_csv(frame, ROOT / "results/tables/Table_temporal_change_fidelity_detailed.csv")
    summary = frame.groupby(["encoding_mode", "bin_count"], as_index=False).agg(
        dataset_transition_count=("transition", "count"),
        delta_sign_accuracy=("delta_sign_accuracy", "mean"),
        normalized_delta_mae=("normalized_delta_mae", "mean"),
        magnitude_spearman=("magnitude_spearman", "mean"),
        top10_change_jaccard=("top10_change_jaccard", "mean"),
        high_change_event_f1=("high_change_event_f1", "mean"),
        cell_identity_accuracy=("cell_identity_accuracy", "mean"),
        geometry_centroid_drift=("geometry_centroid_drift", "mean"),
        temporal_adjacency_jaccard=("temporal_adjacency_jaccard", "mean"),
    )
    bootstrap = _bootstrap_difference(frame, seed)
    write_csv(summary, ROOT / "results/tables/Table_temporal_change_fidelity.csv")
    write_csv(summary, ROOT / "paper/tables/Table_temporal_change_fidelity.csv")
    write_csv(bootstrap, ROOT / "paper/tables/Table_temporal_encoding_bootstrap.csv")
    write_json({
        "bin_counts": phase2["temporal_bin_counts"], "transition_count_per_dataset": 11,
        "evaluation_modes": ["difference between reconstructed monthly values", "direct symmetric diverging delta"],
        "fixed_geometry_metrics": {"cell_identity_accuracy": 1.0, "geometry_centroid_drift": 0.0,
                                   "temporal_adjacency_jaccard": 1.0},
        "interpretation_guardrail": "Fixed-geometry stability is a construction property, not evidence of perceptual accuracy.",
    }, ROOT / "results/temporal/change_metric_manifest.json")
    print(summary.to_string(index=False)); print(bootstrap.to_string(index=False))


if __name__ == "__main__":
    main()
