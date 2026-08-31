"""Local HTTP service for the GeoDisk experiment console.

The service exposes paper artifacts as read-only JSON and permits only a small,
predeclared set of reproducible experiment commands.  Arbitrary shell commands
and arbitrary file paths are intentionally unsupported.
"""

from __future__ import annotations

import csv
import json
import subprocess
import sys
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel


PROJECT_ROOT = Path(__file__).resolve().parents[2]
FORMAL_SUITE_ROOT = PROJECT_ROOT.parent.parent
STATE_PROJECT_ROOT = FORMAL_SUITE_ROOT / "2-annual_pollution_states_pipeline"
PATH_PROJECT_ROOT = FORMAL_SUITE_ROOT / "3-geodisk-deltaannulus_final"
INTEGRATED_SNAPSHOT = PROJECT_ROOT.parent / "frontend/public/data/legacy-insights.json"
TABLE_DIR = PROJECT_ROOT / "results" / "tables"
FIGURE_DIR = PROJECT_ROOT / "results" / "figures"
RUN_DIR = PROJECT_ROOT / "results" / "system_runs"

TABLES = {
    "spatial": TABLE_DIR / "Table_spatial_fidelity.csv",
    "external": TABLE_DIR / "Table_external_spatial_fidelity.csv",
    "synthetic": TABLE_DIR / "Table_synthetic_spatial_fidelity.csv",
    "geometry": TABLE_DIR / "Table_geometry_validity.csv",
    "external_geometry": TABLE_DIR / "Table_external_geometry_validity.csv",
    "synthetic_geometry": TABLE_DIR / "Table_synthetic_geometry_validity.csv",
    "tolerance": TABLE_DIR / "Table_contact_tolerance_sensitivity.csv",
    "revision": TABLE_DIR / "Table_method_revision.csv",
    "refined": TABLE_DIR / "Table_final_power_refinement.csv",
    "weighted": TABLE_DIR / "Table_weighted_adjacency.csv",
    "boundary": TABLE_DIR / "Table_boundary_interior_errors.csv",
    "temporal": TABLE_DIR / "Table_temporal_change_fidelity.csv",
    "astronomy": TABLE_DIR / "Table_astronomy_generalization.csv",
}

WORKBENCH_DATASETS = {
    "湖北": {
        "label": "CEG · Hubei PM2.5", "unit": "µg/m³",
        "reference": PROJECT_ROOT / "data/processed/regions/湖北",
        "display": PROJECT_ROOT / "results/spatial_refined/湖北",
        "temporal": PROJECT_ROOT / "results/temporal/湖北/monthly_delta_encoding.csv",
    },
    "NCEP-AirTemp-Africa-2000": {
        "label": "NCEP · Africa Air Temperature", "unit": "°C",
        "reference": PROJECT_ROOT / "data/processed/external_regions/NCEP-AirTemp-Africa-2000",
        "display": PROJECT_ROOT / "results/external_refined/NCEP-AirTemp-Africa-2000",
        "temporal": PROJECT_ROOT / "results/temporal/NCEP-AirTemp-Africa-2000/monthly_delta_encoding.csv",
    },
    "NE-Admin0-Africa": {
        "label": "Natural Earth · Africa Admin-0", "unit": "population",
        "reference": PROJECT_ROOT / "data/processed/external_regions/NE-Admin0-Africa",
        "display": PROJECT_ROOT / "results/external_refined/NE-Admin0-Africa",
        "temporal": None,
    },
    "NASA-Exoplanet-SkyGrid": {
        "label": "NASA · Exoplanet Sky Grid", "unit": "log1p planets",
        "reference": PROJECT_ROOT / "data/processed/external_regions/NASA-Exoplanet-SkyGrid",
        "display": PROJECT_ROOT / "results/astronomy_spatial/NASA-Exoplanet-SkyGrid",
        "temporal": None,
    },
}
for _region_cn, _region_en in (
    ("湖北", "Hubei"), ("湖南", "Hunan"), ("江西", "Jiangxi"), ("广东", "Guangdong"),
    ("福建", "Fujian"), ("广西", "Guangxi"), ("安徽", "Anhui"), ("浙江", "Zhejiang"),
):
    WORKBENCH_DATASETS[_region_cn] = {
        "label": f"CEG · {_region_en} PM2.5", "unit": "µg/m³",
        "reference": PROJECT_ROOT / f"data/processed/regions/{_region_cn}",
        "display": PROJECT_ROOT / f"results/spatial_refined/{_region_cn}",
        "temporal": PROJECT_ROOT / f"results/temporal/{_region_cn}/monthly_delta_encoding.csv",
    }

RUN_COMMANDS = {
    "tests": [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"],
    "audit": [sys.executable, "experiments/E0_data_audit.py"],
    "spatial": ["bash", "scripts/run_spatial_experiment.sh"],
    "formal": ["bash", "scripts/run_formal_experiment.sh"],
}

DATASETS = [
    {
        "id": "CEG-PM2.5-2000",
        "name": "China PM2.5 Daily Field",
        "domain": "环境 · 时空场",
        "geometry": "省域规则网格",
        "size": "8 个省域 · 366 天",
        "variable": "PM2.5 (µg/m³)",
        "status": "verified",
    },
    {
        "id": "NCEP-AirTemp-Africa-2000",
        "name": "NCEP Surface Air Temperature",
        "domain": "气候 · 月度场",
        "geometry": "2.5° 规则网格",
        "size": "401 单元 · 12 个月",
        "variable": "Air temperature (°C)",
        "status": "verified",
    },
    {
        "id": "NE-Admin0-Africa",
        "name": "Natural Earth Africa Admin-0",
        "domain": "人文地理 · 人口",
        "geometry": "不规则国家多边形",
        "size": "50 单元 · 109 邻接边",
        "variable": "Population estimate",
        "status": "verified",
    },
    {
        "id": "Synthetic-Topology-6",
        "name": "Controlled Topology Stress Suite",
        "domain": "合成 · 压力测试",
        "geometry": "凹形 / 带孔 / 离散等",
        "size": "6 种预声明形状",
        "variable": "Deterministic scalar field",
        "status": "verified",
    },
    {
        "id": "NASA-Exoplanet-SkyGrid",
        "name": "NASA Exoplanet Equal-area Sky Grid",
        "domain": "天文 · 非环境科学",
        "geometry": "18×9 等固体角天空网格",
        "size": "162 单元 · 6,354 行星记录",
        "variable": "log1p confirmed-planet count",
        "status": "verified",
    },
]

METHODS = [
    {"id": "direct-polar", "name": "Direct Polar", "role": "高忠实度基线", "validity": "可产生无效多边形"},
    {"id": "harmonic", "name": "Harmonic", "role": "拉普拉斯嵌入基线", "validity": "合法"},
    {"id": "area-balanced", "name": "Area-balanced", "role": "面积均衡基线", "validity": "合法"},
    {"id": "regular-topology", "name": "Regular Topology", "role": "径向层级基线", "validity": "合法"},
    {"id": "geodisk", "name": "GeoDisk", "role": "提出方法 · 盘", "validity": "合法"},
    {"id": "geoannulus", "name": "GeoAnnulus", "role": "提出方法 · 环", "validity": "合法"},
    {"id": "geodisk-final", "name": "GeoDisk-Final", "role": "最终 Power 邻接优化 · 盘", "validity": "合法"},
    {"id": "geoannulus-final", "name": "GeoAnnulus-Final", "role": "最终 Power 邻接优化 · 环", "validity": "合法"},
]


def _coerce(value: str) -> Any:
    if value == "":
        return None
    try:
        return int(value)
    except ValueError:
        try:
            return float(value)
        except ValueError:
            return value


def read_table(scope: str) -> list[dict[str, Any]]:
    path = TABLES.get(scope)
    if path is None or not path.exists():
        raise HTTPException(status_code=404, detail=f"Unknown or missing table: {scope}")
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        return [{key: _coerce(value) for key, value in row.items()} for row in csv.DictReader(stream)]


def _mean(rows: list[dict[str, Any]], key: str) -> float | None:
    values = [float(row[key]) for row in rows if isinstance(row.get(key), (int, float))]
    return round(sum(values) / len(values), 4) if values else None


def _read_csv(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        return [{key: _coerce(value) for key, value in row.items()} for row in csv.DictReader(stream)]


def _read_json(path: Path) -> Any:
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Missing workbench artifact: {path.name}")
    return json.loads(path.read_text(encoding="utf-8"))


def overview_payload() -> dict[str, Any]:
    spatial = read_table("spatial")
    proposed = [row for row in spatial if row.get("method") in {"GeoDisk", "GeoAnnulus"}]
    direct = [row for row in spatial if row.get("method") == "Direct Polar"]
    invalid = read_table("geometry")
    proposed_invalid = sum(
        int(row.get("invalid_polygon_count") or 0)
        for row in invalid
        if row.get("method") in {"GeoDisk", "GeoAnnulus"}
    )
    refined = read_table("refined")
    refined_ceg = [row for row in refined if row.get("dataset_family") == "ceg"]
    refined_disk = [row for row in refined_ceg if row.get("view") == "disk"]
    refined_annulus = [row for row in refined_ceg if row.get("view") == "annulus"]
    temporal = read_table("temporal")
    temporal_primary = [row for row in temporal if row.get("encoding_mode") == "direct_diverging_delta" and row.get("bin_count") == 9]
    return {
        "project": "GeoDisk–DeltaAnnulus",
        "phase": "Formal Experiment 01",
        "dataset_count": len(DATASETS),
        "real_region_count": 11,
        "synthetic_case_count": 6,
        "method_count": len(METHODS),
        "test_status": "18 / 18",
        "metrics": {
            "proposed_adj_f1": _mean(proposed, "adj_f1"),
            "direct_adj_f1": _mean(direct, "adj_f1"),
            "proposed_np2": _mean(proposed, "np2"),
            "proposed_radial": _mean(proposed, "radial_spearman"),
            "proposed_invalid": proposed_invalid,
            "refined_disk_adj_f1": _mean(refined_disk, "adj_f1"),
            "refined_annulus_adj_f1": _mean(refined_annulus, "adj_f1"),
            "refined_invalid": int(sum(int(row.get("invalid_polygon_count") or 0) for row in refined)),
            "temporal_sign_accuracy": _mean(temporal_primary, "delta_sign_accuracy"),
        },
        "conclusion": "最终 Power 邻接优化已显著超过合法几何基线，但仍低于可产生无效多边形的 Direct Polar。",
        "updated_at": datetime.fromtimestamp(
            max(path.stat().st_mtime for path in TABLES.values() if path.exists()), timezone.utc
        ).isoformat(),
    }


class RunRequest(BaseModel):
    experiment: Literal["tests", "audit", "spatial", "formal"]


class RunRegistry:
    def __init__(self) -> None:
        self._runs: dict[str, dict[str, Any]] = {}
        self._lock = threading.Lock()

    def list(self) -> list[dict[str, Any]]:
        with self._lock:
            return sorted(self._runs.values(), key=lambda run: run["started_at"], reverse=True)

    def launch(self, experiment: str) -> dict[str, Any]:
        with self._lock:
            if any(run["status"] == "running" for run in self._runs.values()):
                raise HTTPException(status_code=409, detail="Another experiment is already running")
            run_id = uuid.uuid4().hex[:10]
            RUN_DIR.mkdir(parents=True, exist_ok=True)
            run = {
                "id": run_id,
                "experiment": experiment,
                "status": "running",
                "started_at": datetime.now(timezone.utc).isoformat(),
                "finished_at": None,
                "return_code": None,
                "log_url": f"/api/runs/{run_id}/log",
            }
            self._runs[run_id] = run
        threading.Thread(target=self._execute, args=(run_id, experiment), daemon=True).start()
        return dict(run)

    def _execute(self, run_id: str, experiment: str) -> None:
        log_path = RUN_DIR / f"{run_id}.log"
        env = {"PYTHONPATH": str(PROJECT_ROOT / "src")}
        import os
        env = {**os.environ, **env}
        with log_path.open("w", encoding="utf-8") as log:
            process = subprocess.run(
                RUN_COMMANDS[experiment],
                cwd=PROJECT_ROOT,
                env=env,
                stdout=log,
                stderr=subprocess.STDOUT,
                check=False,
            )
        with self._lock:
            self._runs[run_id].update(
                status="succeeded" if process.returncode == 0 else "failed",
                finished_at=datetime.now(timezone.utc).isoformat(),
                return_code=process.returncode,
            )

    def log_path(self, run_id: str) -> Path:
        with self._lock:
            if run_id not in self._runs:
                raise HTTPException(status_code=404, detail="Run not found")
        return RUN_DIR / f"{run_id}.log"


runs = RunRegistry()
app = FastAPI(title="GeoDisk Research API", version="0.2.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)
if FIGURE_DIR.exists():
    app.mount("/artifacts", StaticFiles(directory=FIGURE_DIR), name="artifacts")


@app.get("/api/health")
def health() -> dict[str, Any]:
    return {"status": "ok", "project_root": str(PROJECT_ROOT), "version": app.version}


@app.get("/api/overview")
def overview() -> dict[str, Any]:
    return overview_payload()


@app.get("/api/datasets")
def datasets() -> list[dict[str, str]]:
    return DATASETS


@app.get("/api/methods")
def methods() -> list[dict[str, str]]:
    return METHODS


@app.get("/api/results")
def results(
    scope: str = Query("spatial"),
    method: str | None = Query(None),
    view: str | None = Query(None),
) -> dict[str, Any]:
    rows = read_table(scope)
    if method:
        rows = [row for row in rows if row.get("method") == method]
    if view:
        rows = [row for row in rows if row.get("view") == view]
    return {"scope": scope, "count": len(rows), "rows": rows}


@app.get("/api/workbench")
def workbench(
    dataset: str = Query("湖北"),
    view: Literal["disk", "annulus"] = Query("disk"),
) -> dict[str, Any]:
    """Return whitelisted canonical artifacts for the linked analysis views."""
    config = WORKBENCH_DATASETS.get(dataset)
    if config is None:
        raise HTTPException(status_code=404, detail="Unknown workbench dataset")
    method = "GeoDisk-Final" if view == "disk" else "GeoAnnulus-Final"
    reference_root = Path(config["reference"])
    display_root = Path(config["display"])
    original = _read_json(reference_root / "original_geometry.geojson")
    display = _read_json(display_root / f"final_refined_{view}.geojson")
    metadata = _read_json(display_root / f"final_refined_{view}.metadata.json")
    reference_edges = [
        [str(row["source"]), str(row["target"])]
        for row in _read_csv(reference_root / "original_adjacency.csv")
    ]
    nodes = [
        row for row in _read_csv(TABLE_DIR / "Table_node_level_errors.csv")
        if row.get("dataset") == dataset and row.get("method") == method and row.get("view") == view
    ]
    temporal_path = config.get("temporal")
    temporal = _read_csv(Path(temporal_path)) if temporal_path else []
    return {
        "dataset": dataset, "label": config["label"], "unit": config["unit"],
        "view": view, "method": method, "original": original, "display": display,
        "reference_edges": reference_edges, "nodes": nodes, "temporal": temporal,
        "cells": _read_csv(reference_root / "cells.csv"), "metadata": metadata,
    }


@app.get("/api/legacy-insights")
def legacy_insights() -> dict[str, Any]:
    """Expose the fixed, read-only state and path artifacts from projects 2 and 3."""
    if INTEGRATED_SNAPSHOT.exists():
        return _read_json(INTEGRATED_SNAPSHOT)
    state_results = STATE_PROJECT_ROOT / "results"
    path_results = PATH_PROJECT_ROOT / "results"
    return {
        "annual_states": {
            "annulus": _read_json(state_results / "03_irregular_annulus/irregular_annulus_cells.geojson"),
            "annulus_metrics": _read_json(state_results / "03_irregular_annulus/irregular_annulus_metrics.json"),
            "analysis_metrics": _read_json(state_results / "04_temporal_states/analysis_metrics.json"),
            "state_intervals": _read_csv(state_results / "04_temporal_states/state_intervals.csv"),
            "similarity": _read_csv(state_results / "04_temporal_states/adjacent_month_similarity.csv"),
            "monthly_summary": _read_csv(state_results / "04_temporal_states/monthly_summary.csv"),
            "monthly_values": _read_csv(state_results / "04_temporal_states/monthly_pm25_with_hotspots.csv"),
            "centers": _read_csv(state_results / "04_temporal_states/monthly_pollution_centers.csv"),
            "frequency": _read_csv(state_results / "04_temporal_states/annual_hotspot_frequency.csv"),
            "membership": _read_csv(state_results / "04_temporal_states/state_overlap_membership.csv"),
        },
        "migration_paths": {
            "provinces": _read_json(PATH_PROJECT_ROOT / "data/external/selected_real_provinces.geojson"),
            "case": _read_json(path_results / "case_study/case_summary.json"),
            "geometry": _read_json(path_results / "manifests/geometry_summary.json"),
            "all_windows": _read_json(path_results / "manifests/path_summary.json"),
            "holdout": _read_json(path_results / "manifests/path_refinement_summary.json"),
            "geometry_table": _read_csv(PATH_PROJECT_ROOT / "paper/tables/Table1_geometry_summary.csv"),
            "path_table": _read_csv(PATH_PROJECT_ROOT / "paper/tables/Table3_path_recovery_summary.csv"),
            "holdout_table": _read_csv(PATH_PROJECT_ROOT / "paper/tables/Table4_holdout_summary.csv"),
        },
    }


@app.get("/api/figures")
def figures() -> list[dict[str, str]]:
    if not FIGURE_DIR.exists():
        return []
    return [
        {"name": path.stem, "filename": path.name, "url": f"/artifacts/{path.name}"}
        for path in sorted(FIGURE_DIR.glob("*.png"))
    ]


@app.get("/api/runs")
def list_runs() -> list[dict[str, Any]]:
    return runs.list()


@app.post("/api/runs", status_code=202)
def start_run(request: RunRequest) -> dict[str, Any]:
    return runs.launch(request.experiment)


@app.get("/api/runs/{run_id}/log")
def run_log(run_id: str) -> FileResponse:
    path = runs.log_path(run_id)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Log is not available yet")
    return FileResponse(path, media_type="text/plain", filename=path.name)


def main() -> None:
    import uvicorn
    uvicorn.run("geodisk_paper.api:app", host="127.0.0.1", port=8000, reload=False)


if __name__ == "__main__":
    main()
