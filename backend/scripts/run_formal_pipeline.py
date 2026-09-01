from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
from importlib.metadata import PackageNotFoundError, version
import json
from pathlib import Path
import platform
import subprocess
import sys
import time


ROOT = Path(__file__).resolve().parents[1]
PYTHON = sys.executable
STAGES = [
    ("E0", [PYTHON, "experiments/E0_data_audit.py"]),
    ("E1", [PYTHON, "experiments/E1_prepare_regions.py"]),
    ("E2", [PYTHON, "experiments/E2_baseline_geometry.py"]),
    ("E3", [PYTHON, "experiments/E3_geodisk_geoannulus.py"]),
    ("E4", [PYTHON, "experiments/E4_spatial_fidelity.py"]),
    ("E7", [PYTHON, "experiments/E7_ablation.py"]),
    ("E8", [PYTHON, "experiments/E8_sensitivity.py"]),
    ("E9", [PYTHON, "experiments/E9_case_study.py"]),
    ("DOWNLOAD_EXTERNAL", ["bash", "scripts/download_external_datasets.sh"]),
    ("E10", [PYTHON, "experiments/E10_prepare_external_datasets.py"]),
    ("E11", [PYTHON, "experiments/E11_external_spatial_geometry.py"]),
    ("E12", [PYTHON, "experiments/E12_external_spatial_fidelity.py"]),
    ("E13", [PYTHON, "experiments/E13_synthetic_stress.py"]),
    ("E15", [PYTHON, "experiments/E15_bootstrap_statistics.py"]),
    ("E16", [PYTHON, "experiments/E16_method_revision.py"]),
    ("E18", [PYTHON, "experiments/E18_reference_sensitivity.py"]),
    ("E19", [PYTHON, "experiments/E19_final_power_refinement.py"]),
    ("E22", [PYTHON, "experiments/E22_astronomy_generalization.py"]),
    ("E14", [PYTHON, "experiments/E14_contact_tolerance.py"]),
    ("E17", [PYTHON, "experiments/E17_advanced_spatial_errors.py"]),
    ("E20", [PYTHON, "experiments/E20_refined_statistics.py"]),
    ("E24", [PYTHON, "experiments/E24_refinement_ablation.py"]),
    ("E25", [PYTHON, "experiments/E25_final_objective_ablation.py"]),
    ("E26", [PYTHON, "experiments/E26_seed_stability.py"]),
    ("E27", [PYTHON, "experiments/E27_advanced_statistics.py"]),
    ("E28", [PYTHON, "experiments/E28_failure_cases.py"]),
    ("E23", [PYTHON, "experiments/E23_runtime_scalability.py"]),
    ("E5", [PYTHON, "experiments/E5_temporal_delta.py"]),
    ("E6", [PYTHON, "experiments/E6_change_metrics.py"]),
    ("E21", [PYTHON, "experiments/E21_user_study_materials.py"]),
    ("TESTS", [PYTHON, "-m", "unittest", "discover", "-s", "tests", "-v"]),
    ("E29", [PYTHON, "experiments/E29_formal_readiness_audit.py"]),
]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=ROOT, check=False, capture_output=True, text=True).stdout.strip()


def _environment() -> dict:
    packages = {}
    for name in ("fastapi", "matplotlib", "netCDF4", "numpy", "pandas", "PyYAML", "scipy", "shapely", "xarray"):
        try:
            packages[name] = version(name)
        except PackageNotFoundError:
            packages[name] = None
    return {"python": platform.python_version(), "platform": platform.platform(), "processor": platform.processor(),
            "packages": packages}


def _write_manifest(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the frozen GeoDisk formal experiment pipeline.")
    parser.add_argument("--from-stage", choices=[name for name, _ in STAGES])
    parser.add_argument("--through-stage", choices=[name for name, _ in STAGES])
    parser.add_argument("--skip-runtime", action="store_true")
    parser.add_argument("--skip-seed-stability", action="store_true")
    parser.add_argument("--require-clean", action="store_true")
    parser.add_argument("--list-stages", action="store_true")
    args = parser.parse_args()
    if args.list_stages:
        print("\n".join(name for name, _ in STAGES)); return
    dirty = bool(_git("status", "--porcelain"))
    if args.require_clean and dirty:
        raise SystemExit("Refusing a formal run from a dirty Git worktree.")
    stages = STAGES
    if args.from_stage:
        stages = stages[[name for name, _ in stages].index(args.from_stage):]
    if args.through_stage:
        stages = stages[:[name for name, _ in stages].index(args.through_stage) + 1]
    skipped = set()
    if args.skip_runtime: skipped.add("E23")
    if args.skip_seed_stability: skipped.add("E26")
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    manifest_path = ROOT / "results/run_manifests" / f"run_{timestamp}.json"
    config_files = sorted((ROOT / "config").glob("*.yaml"))
    payload = {
        "run_id": timestamp, "status": "running", "started_at_utc": datetime.now(timezone.utc).isoformat(),
        "git_commit": _git("rev-parse", "HEAD"), "git_dirty_at_start": dirty,
        "config_sha256": {str(path.relative_to(ROOT)): _sha256(path) for path in config_files},
        "environment": _environment(), "options": vars(args), "stages": [],
    }
    _write_manifest(manifest_path, payload)
    try:
        for name, command in stages:
            if name in skipped:
                payload["stages"].append({"name": name, "status": "skipped"}); _write_manifest(manifest_path, payload); continue
            print(f"\n[formal pipeline] {name}: {' '.join(command)}", flush=True)
            started = time.perf_counter(); stage = {"name": name, "command": command, "status": "running"}
            payload["stages"].append(stage); _write_manifest(manifest_path, payload)
            completed = subprocess.run(command, cwd=ROOT)
            stage.update({"duration_seconds": time.perf_counter() - started,
                          "return_code": completed.returncode,
                          "status": "succeeded" if completed.returncode == 0 else "failed"})
            _write_manifest(manifest_path, payload)
            if completed.returncode:
                raise RuntimeError(f"Stage {name} failed with exit code {completed.returncode}")
        payload["status"] = "succeeded"
    except Exception as error:
        payload["status"] = "failed"; payload["failure"] = str(error)
        raise
    finally:
        payload["finished_at_utc"] = datetime.now(timezone.utc).isoformat()
        payload["git_dirty_at_end"] = bool(_git("status", "--porcelain"))
        _write_manifest(manifest_path, payload)
        print(f"[formal pipeline] manifest: {manifest_path}", flush=True)


if __name__ == "__main__":
    main()
