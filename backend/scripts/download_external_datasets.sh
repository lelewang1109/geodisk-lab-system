#!/usr/bin/env bash
set -euo pipefail
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
NOAA_DIR="$PROJECT_DIR/data/external/noaa_ncep"
NE_DIR="$PROJECT_DIR/data/external/natural_earth"
NASA_DIR="$PROJECT_DIR/data/external/nasa_exoplanet"
mkdir -p "$NOAA_DIR" "$NE_DIR" "$NASA_DIR"

REFRESH=false
if [[ "${1:-}" == "--refresh" ]]; then
  REFRESH=true
elif [[ $# -gt 0 ]]; then
  echo "Usage: $0 [--refresh]" >&2
  exit 2
fi

download_file() {
  local target="$1"
  local url="$2"
  if [[ "$REFRESH" == false && -s "$target" ]]; then
    echo "[external data] reuse frozen file: ${target#$PROJECT_DIR/}"
    return
  fi
  curl --fail --location --retry 3 --output "$target.part" "$url"
  mv "$target.part" "$target"
}

download_file "$NOAA_DIR/air.mon.mean.africa.2000.nc" \
  "https://psl.noaa.gov/thredds/ncss/grid/Datasets/ncep.reanalysis/Monthlies/surface/air.mon.mean.nc?var=air&north=40&west=-20&east=55&south=-40&disableProjSubset=on&horizStride=1&time_start=2000-01-01T00%3A00%3A00Z&time_end=2000-12-01T00%3A00%3A00Z&timeStride=1&accept=netcdf4"

download_file "$NE_DIR/ne_110m_admin_0_countries.zip" \
  "https://naturalearth.s3.amazonaws.com/110m_cultural/ne_110m_admin_0_countries.zip"

NASA_URL="https://exoplanetarchive.ipac.caltech.edu/TAP/sync?query=select%20pl_name%2Cra%2Cdec%2Cpl_rade%2Cdisc_year%2Cdiscoverymethod%20from%20pscomppars%20where%20ra%20is%20not%20null%20and%20dec%20is%20not%20null&format=csv"
download_file "$NASA_DIR/pscomppars_sky.csv" "$NASA_URL"

python3 "$PROJECT_DIR/scripts/write_external_download_manifest.py"
