from __future__ import annotations

from collections import Counter

import pandas as pd

from common import ROOT, ensure_output_dirs
from geodisk_paper.utils.io import read_json, write_csv, write_json


ROOTS = {
    "ceg": ROOT / "results/spatial_refined",
    "external": ROOT / "results/external_refined",
    "synthetic": ROOT / "results/synthetic_refined",
    "astronomy": ROOT / "results/astronomy_spatial",
}


def main() -> None:
    ensure_output_dirs(); rows = []
    for family, root in ROOTS.items():
        if not root.exists():
            continue
        for path in sorted(root.glob("*/final_refined_*.metadata.json")):
            metadata = read_json(path); history = metadata["candidate_history"]
            starts = [item for item in history if not str(item["candidate"]).startswith("force_")]
            forces = [item for item in history if str(item["candidate"]).startswith("force_")]
            topology = next(item for item in starts if item["candidate"] == "topology")
            multistart = max(starts, key=lambda item: item["objective"])
            final = max(history, key=lambda item: item["objective"])
            rows.append({
                "dataset_family": family, "dataset": path.parent.name, "view": metadata["view"],
                "selected_candidate": metadata["selected_candidate"],
                "topology_only_objective": topology["objective"], "topology_only_adj_f1": topology["adj_f1"],
                "best_multistart_candidate": multistart["candidate"],
                "best_multistart_objective": multistart["objective"], "best_multistart_adj_f1": multistart["adj_f1"],
                "final_objective": final["objective"], "final_adj_f1": final["adj_f1"],
                "multistart_objective_gain": multistart["objective"] - topology["objective"],
                "force_objective_gain": final["objective"] - multistart["objective"],
                "multistart_adj_f1_gain": multistart["adj_f1"] - topology["adj_f1"],
                "force_adj_f1_gain": final["adj_f1"] - multistart["adj_f1"],
                "force_candidate_count": len(forces),
            })
    frame = pd.DataFrame(rows)
    write_csv(frame, ROOT / "results/tables/Table_refinement_component_ablation.csv")
    write_csv(frame, ROOT / "paper/tables/Table_refinement_component_ablation.csv")
    summary = frame.groupby(["dataset_family", "view"], as_index=False).agg(
        dataset_count=("dataset", "count"), multistart_adj_f1_gain=("multistart_adj_f1_gain", "mean"),
        force_adj_f1_gain=("force_adj_f1_gain", "mean"),
        multistart_objective_gain=("multistart_objective_gain", "mean"),
        force_objective_gain=("force_objective_gain", "mean"))
    write_csv(summary, ROOT / "paper/tables/Table_refinement_component_ablation_summary.csv")
    write_json({"selected_candidate_counts": dict(Counter(frame.selected_candidate)),
                "interpretation": "multi-start and force gains are measured against the same final-Power objective, not slot adjacency"},
               ROOT / "results/spatial_refined/refinement_component_manifest.json")
    print(summary.to_string(index=False))


if __name__ == "__main__":
    main()
