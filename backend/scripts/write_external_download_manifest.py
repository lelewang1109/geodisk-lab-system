from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

import numpy as np
import xarray as xr

ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "data/external/download_manifest.json"
FILES = [
    ("NCEP-AirTemp-Africa-2000", ROOT / "data/external/noaa_ncep/air.mon.mean.africa.2000.nc",
     "https://psl.noaa.gov/thredds/ncss/grid/Datasets/ncep.reanalysis/Monthlies/surface/air.mon.mean.nc"),
    ("NE-Admin0-Africa", ROOT / "data/external/natural_earth/ne_110m_admin_0_countries.zip",
     "https://naturalearth.s3.amazonaws.com/110m_cultural/ne_110m_admin_0_countries.zip"),
    ("NASA-Exoplanet-SkyGrid", ROOT / "data/external/nasa_exoplanet/pscomppars_sky.csv",
     "https://exoplanetarchive.ipac.caltech.edu/TAP/sync?query=select%20pl_name%2Cra%2Cdec%2Cpl_rade%2Cdisc_year%2Cdiscoverymethod%20from%20pscomppars%20where%20ra%20is%20not%20null%20and%20dec%20is%20not%20null&format=csv"),
]

previous = {}
if MANIFEST_PATH.exists():
    previous = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))

records = []
for dataset_id, path, url in FILES:
    if not path.exists():
        raise FileNotFoundError(path)
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    record = {
        "dataset_id": dataset_id,
        "file": str(path.relative_to(ROOT)),
        "bytes": path.stat().st_size,
        "sha256": digest.hexdigest(),
        "source_url": url,
    }
    if path.suffix == ".nc":
        # NCSS rewrites the translation timestamp in global metadata on every
        # request. Hash variables only so identical scientific content remains
        # identifiable even when the container bytes change.
        content_digest = hashlib.sha256()
        with xr.open_dataset(path, decode_cf=False) as dataset:
            for name in sorted(dataset.variables):
                values = np.asarray(dataset[name].values)
                content_digest.update(name.encode("utf-8"))
                content_digest.update(str(values.dtype).encode("utf-8"))
                content_digest.update(str(values.shape).encode("utf-8"))
                content_digest.update(values.tobytes())
        record["scientific_content_sha256"] = content_digest.hexdigest()
        record["scientific_content_hash_scope"] = "sorted variable names, dtypes, shapes and array bytes; attributes excluded"
    records.append(record)

now = datetime.now(timezone.utc).isoformat()
previous_hashes = {item.get("dataset_id"): item.get("sha256") for item in previous.get("files", [])}
same_snapshot = bool(previous_hashes) and all(
    previous_hashes.get(item["dataset_id"]) == item["sha256"] for item in records
)
output = {
    "retrieved_at_utc": previous.get("retrieved_at_utc", now) if same_snapshot else now,
    "manifest_generated_at_utc": now,
    "files": records,
}
MANIFEST_PATH.write_text(
    json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8"
)
print(json.dumps(output, ensure_ascii=False, indent=2))
