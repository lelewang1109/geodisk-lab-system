from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from common import ROOT, dataset_config, ensure_output_dirs, experiment_config, geometry_config
from geodisk_paper.utils.io import read_json, write_json


def _record(rows: list[dict], check_id: str, area: str, severity: str, passed: bool,
            evidence: str, action: str, claim_scope: str = "algorithmic") -> None:
    rows.append({"check_id": check_id, "area": area, "severity": severity,
                 "status": "pass" if passed else "open", "claim_scope": claim_scope,
                 "evidence": evidence, "required_action": "none" if passed else action})


def main() -> None:
    ensure_output_dirs(); rows: list[dict] = []
    dataset = dataset_config(); geometry = geometry_config(); formal = experiment_config()["formal_evaluation"]
    provenance_fields = ["source_url", "license", "citation"]
    missing = [field for field in provenance_fields if not dataset.get(field)]
    _record(rows, "primary_data_provenance", "data", "blocker", not missing,
            f"missing fields: {missing}" if missing else "source, license and citation are declared",
            "Obtain and freeze the official CEG source URL, license/permission and citation before submission.")

    audit_path = ROOT / "results/data_audit/daily_file_manifest.csv"
    audit = pd.read_csv(audit_path) if audit_path.exists() else pd.DataFrame()
    has_hashes = "sha256" in audit.columns and len(audit) > 0 and audit.sha256.notna().all()
    _record(rows, "primary_file_hashes", "data", "major", has_hashes,
            f"{len(audit)} files; sha256 column={has_hashes}",
            "Rerun E0 after the hash-enabled audit code change to freeze all 366 source files.")

    tolerance_path = ROOT / "results/tables/Table_contact_tolerance_sensitivity.csv"
    tolerance = pd.read_csv(tolerance_path) if tolerance_path.exists() else pd.DataFrame()
    final_methods = {"GeoDisk-Final", "GeoAnnulus-Final"}
    tolerance_methods = set(tolerance.method) if "method" in tolerance else set()
    _record(rows, "final_contact_tolerance", "topology", "major", final_methods.issubset(tolerance_methods),
            f"methods={sorted(tolerance_methods)}", "Rerun E14 so the final methods are included in all five tolerances.")

    final_path = ROOT / "results/tables/Table_final_power_refinement.csv"
    final_frame = pd.read_csv(final_path) if final_path.exists() else pd.DataFrame()
    geometry_ok = (
        len(final_frame) > 0
        and {"invalid_polygon_count", "overlap_ratio", "gap_ratio"}.issubset(final_frame.columns)
        and int(final_frame.invalid_polygon_count.sum()) == 0
        and float(final_frame.overlap_ratio.max()) <= 1e-7
        and float(final_frame.gap_ratio.max()) <= 1e-7
    )
    _record(rows, "final_geometry_admissibility", "geometry", "blocker", geometry_ok,
            (f"rows={len(final_frame)}; invalid={int(final_frame.invalid_polygon_count.sum())}; "
             f"max_overlap={float(final_frame.overlap_ratio.max()):.3g}; max_gap={float(final_frame.gap_ratio.max()):.3g}")
            if len(final_frame) else "final refinement table missing",
            "Reject non-admissible candidates during final-Power selection and rerun E19 onward.")

    advanced_path = ROOT / "results/tables/Table_boundary_interior_errors.csv"
    advanced = pd.read_csv(advanced_path) if advanced_path.exists() else pd.DataFrame()
    datasets = set(advanced.dataset.astype(str)) if "dataset" in advanced else set()
    expected_advanced = {"NASA-Exoplanet-SkyGrid", "Synthetic-hole", "NCEP-AirTemp-Africa-2000"}
    _record(rows, "advanced_cross_domain_errors", "local_error", "major", expected_advanced.issubset(datasets),
            f"dataset_count={len(datasets)}", "Rerun E17 to include astronomy and all synthetic domains.")

    ablation_path = ROOT / "results/tables/Table_final_objective_ablation.csv"
    ablation = pd.read_csv(ablation_path) if ablation_path.exists() else pd.DataFrame()
    variant_count = int(ablation.variant.nunique()) if "variant" in ablation else 0
    _record(rows, "final_objective_ablation", "ablation", "major", variant_count >= 6,
            f"variant_count={variant_count}", "Run E25 and report the full objective plus five leave-one-term-out variants.")

    seed_path = ROOT / "results/tables/Table_seed_stability.csv"
    seed_frame = pd.read_csv(seed_path) if seed_path.exists() else pd.DataFrame()
    seed_count = int(seed_frame.seed.nunique()) if "seed" in seed_frame else 0
    seed_regions = int(seed_frame.region.nunique()) if "region" in seed_frame else 0
    expected_regions = len(formal["seed_stability_regions"])
    seed_ok = seed_count >= int(formal["minimum_seed_repetitions"]) and seed_regions == expected_regions
    _record(rows, "multi_seed_stability", "robustness", "major", seed_ok,
            f"seeds={seed_count}; regions={seed_regions}/{expected_regions}",
            "Run E26 with every declared seed and region; report mean, SD, minimum and maximum.")

    runtime_path = ROOT / "results/tables/Table_runtime_scalability.csv"
    runtime = pd.read_csv(runtime_path) if runtime_path.exists() else pd.DataFrame()
    minimum_repeat = int(runtime.repeat_count.min()) if "repeat_count" in runtime and len(runtime) else 0
    runtime_ok = minimum_repeat >= int(formal["minimum_runtime_repetitions"])
    _record(rows, "runtime_repetitions", "efficiency", "major", runtime_ok,
            f"minimum repeat_count={minimum_repeat}", "Run E23 with one warm-up and at least ten measured repetitions.")
    memory_ok = "process_high_water_rss_mb_median" in runtime and len(runtime) > 0
    _record(rows, "runtime_peak_memory", "efficiency", "minor", memory_ok,
            "suite-process high-water RSS recorded" if memory_ok else "peak RSS column missing",
            "Rerun E23 with native-allocation-aware process high-water RSS recording.")

    advanced_stats = ROOT / "results/tables/Table_advanced_paired_statistics.csv"
    _record(rows, "advanced_paired_inference", "statistics", "major", advanced_stats.exists(),
            "advanced paired table exists" if advanced_stats.exists() else "table missing",
            "Run E27 for weighted-adjacency and boundary/interior paired inference.")

    failures = ROOT / "results/tables/Table_local_failure_cases.csv"
    _record(rows, "failure_case_retention", "diagnostics", "minor", failures.exists(),
            "ranked failure table exists" if failures.exists() else "table missing",
            "Run E28 and retain local failures in the paper supplement.")

    response_path = ROOT / "user_study/response_schema.csv"
    responses = pd.read_csv(response_path) if response_path.exists() else pd.DataFrame()
    _record(rows, "human_participant_results", "user_study", "blocker", len(responses) > 0,
            f"response rows={len(responses)}", "Collect the preregistered participant study before making perceptual-efficiency claims.",
            claim_scope="perceptual_only")

    run_manifests = sorted((ROOT / "results/run_manifests").glob("run_*.json")) if (ROOT / "results/run_manifests").exists() else []
    successful = False
    if run_manifests:
        latest = read_json(run_manifests[-1])
        successful = latest.get("status") == "succeeded" and not latest.get("git_dirty_at_start")
        if latest.get("status") == "running" and not latest.get("git_dirty_at_start"):
            stages = latest.get("stages", [])
            current_is_audit = bool(stages) and stages[-1].get("name") == "E29" and stages[-1].get("status") == "running"
            prior_complete = all(stage.get("status") == "succeeded" for stage in stages[:-1])
            successful = current_is_audit and prior_complete and any(stage.get("name") == "TESTS" for stage in stages[:-1])
    _record(rows, "clean_full_pipeline_manifest", "reproducibility", "major", successful,
            f"successful clean manifests={int(successful)}; total manifests={len(run_manifests)}",
            "Run scripts/run_formal_experiment.sh from a clean frozen commit and preserve its manifest.")

    _record(rows, "published_baseline_implementation", "baselines", "major", False,
            "Current baselines are project-local implementations.",
            "Add or justify at least one independently published topology-preserving/cartogram baseline and verify parameter parity.")
    _record(rows, "confirmatory_holdout_dataset", "study_design", "major", False,
            "The eight CEG regions were available during method development.",
            "Freeze an untouched year or region before tuning, then run the declared primary comparison once.")
    analysis_plan = ROOT / "config/formal_hypotheses.yaml"
    _record(rows, "machine_readable_analysis_plan", "study_design", "major", analysis_plan.exists(),
            "post-hoc plan frozen for future reruns" if analysis_plan.exists() else "formal_hypotheses.yaml missing",
            "Freeze hypotheses, primary outcomes, units and multiplicity families before collecting a holdout dataset.")
    _record(rows, "backend_environment_lock", "reproducibility", "major", (ROOT / "requirements-lock.txt").exists(),
            "requirements-lock.txt present" if (ROOT / "requirements-lock.txt").exists() else "only lower-bound requirements are present",
            "Freeze an exact tested Python dependency lock for the submission artifact.")

    frame = pd.DataFrame(rows)
    output_dir = ROOT / "results/formal_readiness"; output_dir.mkdir(parents=True, exist_ok=True)
    write_json({"generated_at_utc": datetime.now(timezone.utc).isoformat(),
                "open_count": int((frame.status == "open").sum()),
                "checks": frame.to_dict(orient="records")}, output_dir / "formal_readiness.json")
    lines = ["# Formal Experiment Readiness Audit", "",
             "> `pass` means the artifact exists and satisfies the declared minimum; `open` is retained explicitly and must not be hidden in the paper.", "",
             "| Area | Check | Severity | Status | Evidence | Required action |", "| --- | --- | --- | --- | --- | --- |"]
    for row in frame.itertuples():
        lines.append(f"| {row.area} | `{row.check_id}` | {row.severity} | **{row.status}** | {row.evidence} | {row.required_action} |")
    lines.extend(["", "## Interpretation", "",
                  "Algorithmic claims and perceptual claims have separate gates. Missing participant responses block only perceptual-efficiency claims. Missing primary-data provenance blocks archival publication of the main CEG experiment even when numerical results are reproducible locally.", ""])
    (ROOT / "paper/FORMAL_EXPERIMENT_READINESS.md").write_text("\n".join(lines), encoding="utf-8")
    print(frame.to_string(index=False))


if __name__ == "__main__":
    main()
