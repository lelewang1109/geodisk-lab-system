from __future__ import annotations

import numpy as np
import pandas as pd

from common import ROOT, ensure_output_dirs
from geodisk_paper.utils.io import write_csv, write_json


def _category(row) -> str:
    preserved = min(int(round(row.reference_degree * row.node_adj_recall)),
                    int(round(row.display_degree * row.node_adj_precision)))
    lost = max(int(row.reference_degree) - preserved, 0)
    new = max(int(row.display_degree) - preserved, 0)
    if lost and new:
        return "mixed_lost_and_new"
    if lost:
        return "under_connected"
    if new:
        return "over_connected"
    if np.isfinite(row.node_direction_error_deg) and row.node_direction_error_deg > 30:
        return "direction_only"
    return "low_order_or_secondary"


def main() -> None:
    ensure_output_dirs()
    node = pd.read_csv(ROOT / "results/tables/Table_node_level_errors.csv", encoding="utf-8-sig")
    node = node[node.method.isin(["GeoDisk-Final", "GeoAnnulus-Final"])].copy()
    node["failure_category"] = [_category(row) for row in node.itertuples()]
    ranked = node.sort_values(
        ["dataset", "method", "view", "is_boundary", "node_adj_f1", "degree_absolute_error", "node_direction_error_deg"],
        ascending=[True, True, True, True, True, False, False], na_position="last",
    ).groupby(["dataset", "method", "view", "is_boundary"], as_index=False, group_keys=False).head(10)
    ranked["failure_rank"] = ranked.groupby(["dataset", "method", "view", "is_boundary"]).cumcount() + 1
    write_csv(ranked, ROOT / "results/tables/Table_local_failure_cases.csv")
    summary = node.groupby(["method", "view", "is_boundary", "failure_category"], as_index=False).agg(
        node_count=("cell_id", "count"), mean_node_f1=("node_adj_f1", "mean"),
        mean_degree_error=("degree_absolute_error", "mean"), mean_direction_error=("node_direction_error_deg", "mean"))
    write_csv(summary, ROOT / "paper/tables/Table_failure_taxonomy.csv")
    write_json({"selection": "ten lowest node adjacency F1 cases per dataset/method/view/boundary group",
                "tie_breakers": ["higher degree error", "higher direction error"],
                "guardrail": "failure cases are retained rather than excluded from aggregate statistics"},
               ROOT / "results/spatial_refined/failure_case_manifest.json")
    print(summary.to_string(index=False))


if __name__ == "__main__":
    main()
