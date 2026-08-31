#!/usr/bin/env python3
"""Export all whitelisted workbench datasets for the hosted D3 interface."""

from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
OUTPUT = ROOT / "frontend" / "public" / "data"
sys.path.insert(0, str(BACKEND / "src"))

from geodisk_paper.api import WORKBENCH_DATASETS, workbench  # noqa: E402


SLUGS = {
    "湖北": "hubei", "湖南": "hunan", "江西": "jiangxi", "广东": "guangdong",
    "福建": "fujian", "广西": "guangxi", "安徽": "anhui", "浙江": "zhejiang",
    "NCEP-AirTemp-Africa-2000": "ncep-africa",
    "NE-Admin0-Africa": "natural-earth-africa",
    "NASA-Exoplanet-SkyGrid": "nasa-exoplanet",
}


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    for dataset in WORKBENCH_DATASETS:
        slug = SLUGS.get(dataset)
        if slug is None:
            continue
        for view in ("disk", "annulus"):
            payload = workbench(dataset=dataset, view=view)
            path = OUTPUT / f"workbench-{slug}-{view}.json"
            path.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
            print(f"[snapshot] {dataset} {view}: {path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
