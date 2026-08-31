from __future__ import annotations

import numpy as np
import pandas as pd

from common import ROOT, seed_everything
from geodisk_paper.utils.io import write_csv


METRICS = ["adj_precision", "adj_recall", "adj_f1", "np2", "local_direction_error_deg",
           "angular_error_deg", "radial_spearman"]


def bootstrap_ci(values: np.ndarray, rng, repetitions: int = 10000):
    draws = rng.choice(values, size=(repetitions, len(values)), replace=True).mean(axis=1)
    return float(values.mean()), float(np.quantile(draws, .025)), float(np.quantile(draws, .975))


def main():
    seed = seed_everything(); rng = np.random.default_rng(seed)
    frame = pd.read_csv(ROOT / "results/tables/Table_spatial_fidelity.csv")
    frame = frame[~frame.region.str.startswith("OVERALL")].copy()
    rows = []
    for (method, view), group in frame.groupby(["method", "view"], sort=False):
        for metric in METRICS:
            mean, low, high = bootstrap_ci(group[metric].to_numpy(float), rng)
            rows.append({"method": method, "view": view, "metric": metric, "province_count": len(group),
                         "mean": mean, "bootstrap_ci_2.5": low, "bootstrap_ci_97.5": high,
                         "bootstrap_repetitions": 10000, "seed": seed})
    write_csv(pd.DataFrame(rows), ROOT / "paper/tables/Table_spatial_bootstrap_ci.csv")

    comparisons = []
    pairs = [("GeoDisk", "Direct Polar", "disk"), ("GeoAnnulus", "Direct Polar", "annulus")]
    for proposed, baseline, view in pairs:
        left = frame[(frame.method == proposed) & (frame.view == view)].set_index("region")
        right = frame[(frame.method == baseline) & (frame.view == view)].set_index("region")
        common = sorted(set(left.index) & set(right.index))
        for metric in METRICS:
            differences = left.loc[common, metric].to_numpy(float) - right.loc[common, metric].to_numpy(float)
            draws = rng.choice(differences, size=(10000, len(differences)), replace=True).mean(axis=1)
            comparisons.append({"proposed": proposed, "baseline": baseline, "view": view, "metric": metric,
                                "paired_count": len(common), "mean_difference_proposed_minus_baseline": float(differences.mean()),
                                "bootstrap_ci_2.5": float(np.quantile(draws, .025)),
                                "bootstrap_ci_97.5": float(np.quantile(draws, .975))})
    write_csv(pd.DataFrame(comparisons), ROOT / "paper/tables/Table_paired_bootstrap_differences.csv")
    print(pd.DataFrame(comparisons).to_string(index=False))


if __name__ == "__main__":
    main()

