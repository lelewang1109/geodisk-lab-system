from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FILES = [
    ("NCEP-AirTemp-Africa-2000", ROOT / "data/external/noaa_ncep/air.mon.mean.africa.2000.nc",
     "https://psl.noaa.gov/thredds/ncss/grid/Datasets/ncep.reanalysis/Monthlies/surface/air.mon.mean.nc"),
    ("NE-Admin0-Africa", ROOT / "data/external/natural_earth/ne_110m_admin_0_countries.zip",
     "https://naturalearth.s3.amazonaws.com/110m_cultural/ne_110m_admin_0_countries.zip"),
    ("NASA-Exoplanet-SkyGrid", ROOT / "data/external/nasa_exoplanet/pscomppars_sky.csv",
     "https://exoplanetarchive.ipac.caltech.edu/TAP/sync?query=select%20pl_name%2Cra%2Cdec%2Cpl_rade%2Cdisc_year%2Cdiscoverymethod%20from%20pscomppars%20where%20ra%20is%20not%20null%20and%20dec%20is%20not%20null&format=csv"),
]

records = []
for dataset_id, path, url in FILES:
    if not path.exists():
        raise FileNotFoundError(path)
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    records.append({"dataset_id": dataset_id, "file": str(path.relative_to(ROOT)), "bytes": path.stat().st_size,
                    "sha256": digest.hexdigest(), "source_url": url})

output = {"retrieved_at_utc": datetime.now(timezone.utc).isoformat(), "files": records}
(ROOT / "data/external/download_manifest.json").write_text(
    json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8"
)
print(json.dumps(output, ensure_ascii=False, indent=2))
