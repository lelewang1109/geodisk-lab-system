from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import sys
import time


ROOT = Path(__file__).resolve().parents[1]
PYTHON = sys.executable
STAGES = [
    ("E31", "experiments/E31_final_spatial_figures.py"),
    ("E32", "experiments/E32_final_external_figures.py"),
    ("E33", "experiments/E33_reference_structure_figure.py"),
    ("E34", "experiments/E34_geodisk_method_figure.py"),
    ("E35", "experiments/E35_integrated_delta_annulus.py"),
    ("E36", "experiments/E36_user_study_v2_materials.py"),
    ("E37", "experiments/E37_failure_case_figures.py"),
    ("E38", "experiments/E38_case_study_hubei_temporal.py"),
]
EXPECTED = {
    "E31": ["results/tables/Table_final_spatial_comparison.csv", "results/figures/Fig_final_spatial_comparison_Hubei.png"],
    "E32": ["results/tables/Table_final_cross_domain_spatial.csv", "results/figures/Fig_final_external_NE-Admin0-Africa.png",
             "results/figures/Fig_final_external_NCEP-AirTemp-Africa-2000.png"],
    "E33": ["results/figures/Fig_reference_structure_Hubei.png", "results/figures/Fig_reference_structure_Hubei.pdf"],
    "E34": ["results/figures/Fig_geodisk_method_pipeline_Hubei.png"],
    "E35": ["results/figures/Fig_integrated_delta_annulus_Hubei.png", "results/figures/Fig_integrated_delta_annulus_NCEP.png",
             "results/tables/Table_integrated_delta_annulus_consistency.csv"],
    "E36": ["user_study_v2/task_manifest.csv", "user_study_v2/response_schema.csv", "user_study_v2/study_manifest.json"],
    "E37": ["results/figures/Fig_failure_cases_Hubei.png"],
    "E38": ["results/figures/Fig_case_hubei_temporal.png", "results/tables/Table_case_hubei_top_changes.csv",
             "results/temporal/case_hubei_manifest.json"],
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256(path.read_bytes()); return digest.hexdigest()


def _git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=ROOT, check=False, capture_output=True, text=True).stdout.strip()


def _write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp"); temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)


def _preflight() -> None:
    checks = [
        (ROOT / "results/spatial_refined/湖北/final_refined_disk.geojson", "Missing Hubei final geometry; run E19 first"),
        (ROOT / "results/external_refined/NE-Admin0-Africa/final_refined_disk.geojson", "Missing Natural Earth final geometry; run E19 first"),
        (ROOT / "results/external_refined/NCEP-AirTemp-Africa-2000/final_refined_annulus.geojson", "Missing NCEP final geometry; run E19 first"),
        (ROOT / "results/temporal/湖北/monthly_delta_encoding.csv", "Missing Hubei temporal encoding; run E5 first"),
        (ROOT / "results/tables/Table_node_level_errors.csv", "Missing node-level errors; run E17 first"),
    ]
    for path, message in checks:
        if not path.exists():
            raise SystemExit(message)
    header = (ROOT / "data/processed/regions/湖北/cells.csv").open(encoding="utf-8-sig").readline()
    if "is_topological_boundary" not in header or "is_geographic_boundary" not in header:
        raise SystemExit("Missing explicit boundary fields; run E1 first")


def main() -> None:
    _preflight()
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    manifest_path = ROOT / "results/run_manifests" / f"paper_completion_{timestamp}.json"
    config_files = sorted((ROOT / "config").glob("*.yaml"))
    payload = {
        "run_id": timestamp, "pipeline": "paper_completion", "status": "running",
        "timestamp": datetime.now(timezone.utc).isoformat(), "git_commit": _git("rev-parse", "HEAD"),
        "dirty_status": bool(_git("status", "--porcelain")), "python_version": platform.python_version(),
        "config_hash": {str(path.relative_to(ROOT)): _sha256(path) for path in config_files}, "stages": [],
    }
    _write(manifest_path, payload)
    try:
        for name, script in STAGES:
            started = time.perf_counter(); stage = {"name": name, "script": script, "status": "running"}
            payload["stages"].append(stage); _write(manifest_path, payload)
            completed = subprocess.run([PYTHON, script], cwd=ROOT, text=True, capture_output=True)
            outputs = [relative for relative in EXPECTED[name] if (ROOT / relative).exists()]
            stage.update({"status": "succeeded" if completed.returncode == 0 else "failed",
                          "return_code": completed.returncode, "duration_seconds": time.perf_counter() - started,
                          "outputs": outputs, "stdout_tail": completed.stdout[-4000:], "stderr_tail": completed.stderr[-4000:]})
            _write(manifest_path, payload)
            print(completed.stdout, end=""); print(completed.stderr, end="", file=sys.stderr)
            if completed.returncode:
                raise RuntimeError(f"{name} failed; see {manifest_path}")
            missing_outputs = sorted(set(EXPECTED[name]) - set(outputs))
            if missing_outputs:
                raise RuntimeError(f"{name} succeeded without required outputs: {missing_outputs}")
        payload["status"] = "succeeded"
    except Exception as error:
        payload["status"] = "failed"; payload["failure"] = str(error); raise
    finally:
        payload["finished_at"] = datetime.now(timezone.utc).isoformat()
        payload["dirty_status_at_end"] = bool(_git("status", "--porcelain")); _write(manifest_path, payload)
        print(f"paper completion manifest: {manifest_path}")


if __name__ == "__main__":
    main()
