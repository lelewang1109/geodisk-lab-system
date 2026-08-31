from __future__ import annotations

import pandas as pd

from common import (ROOT, adapter_from_audit, ensure_output_dirs, experiment_config,
                    geometry_config, project_boundaries, seed_everything)
from evaluation_helpers import evaluate_result
from geodisk_paper.data.regions import load_region_reference, prepare_region_references
from geodisk_paper.geometry.mappings import proposed_irregular
from geodisk_paper.topology.embedding import build_topology_embedding
from geodisk_paper.utils.io import write_csv, write_json
from geodisk_paper.visualization.figures import sensitivity_figure


def _run(reference, geometry, seed, *, layer_count, optimize_passes, warp_strength):
    embedding = build_topology_embedding(reference, layer_count=layer_count, optimize_passes=optimize_passes,
                                         seed=seed, weights=dict(geometry["topology_weights"]), radial_constraint=True)
    rows = []
    for view in ("disk", "annulus"):
        result = proposed_irregular(reference, embedding, view, inner=float(geometry["annulus_inner"]),
                                    outer=float(geometry["annulus_outer"]), iterations=int(geometry["power_iterations"]),
                                    warp_strength=warp_strength, balance=True)
        rows.append({"view": view, **evaluate_result(reference, result)})
    return rows


def main():
    ensure_output_dirs(); geometry = geometry_config(); experiment = experiment_config(); seed = seed_everything()
    sweep = experiment["sensitivity"]; regions = list(experiment["sensitivity_regions"])
    boundaries, _ = project_boundaries()
    reference_roots = {int(geometry["coarsen_factor"]): ROOT / "data/processed/regions"}
    for factor in sweep["coarsen_factors"]:
        factor = int(factor)
        if factor == int(geometry["coarsen_factor"]): continue
        root = ROOT / "results/cache" / f"sensitivity_reference_f{factor}"
        marker = root / regions[0] / "cells.csv"
        if not marker.exists():
            adapter = adapter_from_audit(); schema = adapter.inspect_schema()
            prepare_region_references(adapter, schema, boundaries, regions, root,
                                      coarsen_factor=factor, min_valid_fraction=float(geometry["min_valid_fraction"]))
        reference_roots[factor] = root

    rows = []
    defaults = {"coarsen_factor": int(geometry["coarsen_factor"]), "layer_count": int(geometry["layer_count"]),
                "optimize_passes": int(geometry["optimize_passes"]), "warp_strength": 0.5*(float(geometry["disk_warp_strength"])+float(geometry["annulus_warp_strength"]))}
    parameters = {
        "coarsen_factor": sweep["coarsen_factors"], "layer_count": sweep["layer_counts"],
        "optimize_passes": sweep["optimize_passes"], "warp_strength": sweep["warp_strengths"],
    }
    for parameter, values in parameters.items():
        for value in values:
            settings = dict(defaults); settings[parameter] = value
            for region in regions:
                reference = load_region_reference(reference_roots[int(settings["coarsen_factor"])], region)
                evaluated = _run(reference, geometry, seed, layer_count=int(settings["layer_count"]),
                                 optimize_passes=int(settings["optimize_passes"]), warp_strength=float(settings["warp_strength"]))
                for item in evaluated:
                    rows.append({"region": region, "parameter": parameter, "value": value,
                                 "cell_count": len(reference.cells), **item})
            print("[sensitivity]", parameter, value, flush=True)
    frame = pd.DataFrame(rows)
    write_csv(frame, ROOT / "results/sensitivity/Table_sensitivity.csv")
    sensitivity_figure(frame, ROOT / "results/sensitivity/Fig_sensitivity.png")
    summary = frame.groupby(["parameter", "value", "view"], as_index=False).agg(
        adj_f1=("adj_f1", "mean"), np2=("np2", "mean"),
        local_direction_error_deg=("local_direction_error_deg", "mean"),
        angular_error_deg=("angular_error_deg", "mean"), radial_spearman=("radial_spearman", "mean"), area_cv=("area_cv", "mean"))
    write_csv(summary, ROOT / "paper/tables/Table_sensitivity.csv")
    write_json({"declared_regions": regions, "selection_basis": "predeclared runtime-bounded shape contrast; not outcome-selected",
                "recommended_default": defaults}, ROOT / "results/sensitivity/sensitivity_manifest.json")
    (ROOT / "paper/figures/Fig_sensitivity.png").write_bytes((ROOT / "results/sensitivity/Fig_sensitivity.png").read_bytes())


if __name__ == "__main__":
    main()

