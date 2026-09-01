from __future__ import annotations

from itertools import product

import numpy as np
import pandas as pd

from common import ROOT, ensure_output_dirs, geometry_config, seed_everything
from geodisk_paper.utils.io import write_csv, write_json


COMPARISONS = {
    "disk": ("GeoDisk-Final", ["GeoDisk", "Direct Polar", "Harmonic", "Area-balanced", "Regular Topology"]),
    "annulus": ("GeoAnnulus-Final", ["GeoAnnulus", "Direct Polar", "Harmonic", "Area-balanced", "Regular Topology"]),
}


def _bootstrap(values: np.ndarray, rng, samples: int = 10000) -> tuple[float, float]:
    draws = values[rng.integers(0, len(values), size=(samples, len(values)))].mean(axis=1)
    return float(np.quantile(draws, .025)), float(np.quantile(draws, .975))


def _sign_flip(values: np.ndarray) -> float:
    observed = abs(float(values.mean()))
    signs = np.asarray(list(product((-1.0, 1.0), repeat=len(values))))
    return float(np.mean(np.abs(np.mean(signs * values, axis=1)) >= observed - 1e-15))


def _holm(series: pd.Series) -> pd.Series:
    order = np.argsort(series.to_numpy(float)); ranked = series.to_numpy(float)[order]
    corrected = np.maximum.accumulate((len(ranked) - np.arange(len(ranked))) * ranked)
    output = np.empty(len(ranked), dtype=float); output[order] = np.clip(corrected, 0.0, 1.0)
    return pd.Series(output, index=series.index)


def _compare(frame: pd.DataFrame, analysis: str, metric: str, node_group: str,
             regions: set[str], rng, rows: list[dict]) -> None:
    subset = frame[frame.dataset.astype(str).isin(regions)]
    for view, (refined, comparators) in COMPARISONS.items():
        left = subset[(subset.view == view) & (subset.method == refined) & (subset.node_group == node_group)]
        for comparator in comparators:
            right = subset[(subset.view == view) & (subset.method == comparator) & (subset.node_group == node_group)]
            merged = left.merge(right, on="dataset", suffixes=("_refined", "_comparator"))
            values = merged[f"{metric}_refined"].to_numpy(float) - merged[f"{metric}_comparator"].to_numpy(float)
            values = values[np.isfinite(values)]
            if not len(values):
                continue
            low, high = _bootstrap(values, rng)
            lower_is_better = "error" in metric
            rows.append({
                "analysis": analysis, "view": view, "node_group": node_group, "metric": metric,
                "refined_method": refined, "comparator": comparator, "region_count": len(values),
                "mean_difference": float(values.mean()), "ci95_low": low, "ci95_high": high,
                "paired_sign_flip_p": _sign_flip(values),
                "refined_better_count": int(np.sum(values < 0 if lower_is_better else values > 0)),
            })


def main() -> None:
    ensure_output_dirs(); rng = np.random.default_rng(seed_everything()); regions = set(geometry_config()["regions"])
    rows: list[dict] = []
    weighted = pd.read_csv(ROOT / "results/tables/Table_weighted_adjacency.csv", encoding="utf-8-sig")
    weighted["node_group"] = "all_edges"
    for metric in ("weighted_adj_f1", "weighted_edge_overlap"):
        _compare(weighted, "shared_boundary_weighted", metric, "all_edges", regions, rng, rows)
    node = pd.read_csv(ROOT / "results/tables/Table_boundary_interior_errors.csv", encoding="utf-8-sig")
    for group in ("boundary", "interior"):
        for metric in ("node_adj_f1", "node_neighbor_jaccard", "degree_absolute_error",
                       "node_direction_error_deg", "node_neighbor_order_accuracy"):
            _compare(node, "boundary_interior", metric, group, regions, rng, rows)
    result = pd.DataFrame(rows)
    result["paired_sign_flip_p_holm"] = result.groupby(
        ["analysis", "view", "node_group", "metric"], group_keys=False
    )["paired_sign_flip_p"].apply(_holm)
    result["holm_family_size"] = result.groupby(
        ["analysis", "view", "node_group", "metric"]
    )["comparator"].transform("size")
    write_csv(result, ROOT / "results/tables/Table_advanced_paired_statistics.csv")
    write_csv(result, ROOT / "paper/tables/Table_advanced_paired_statistics.csv")
    write_json({"resampling_unit": "province/region", "bootstrap_samples": 10000,
                "test": "exact paired sign-flip", "multiple_comparison": "Holm within each view/group/metric family"},
               ROOT / "results/spatial_refined/advanced_statistics_manifest.json")
    print(result[result.comparator.isin(["Harmonic", "Area-balanced"])].to_string(index=False))


if __name__ == "__main__":
    main()
