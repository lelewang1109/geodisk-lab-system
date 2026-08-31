#!/usr/bin/env bash
set -euo pipefail
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
NOAA_DIR="$PROJECT_DIR/data/external/noaa_ncep"
NE_DIR="$PROJECT_DIR/data/external/natural_earth"
NASA_DIR="$PROJECT_DIR/data/external/nasa_exoplanet"
mkdir -p "$NOAA_DIR" "$NE_DIR" "$NASA_DIR"

curl --fail --location --retry 3 --output "$NOAA_DIR/air.mon.mean.africa.2000.nc.part" \
  "https://psl.noaa.gov/thredds/ncss/grid/Datasets/ncep.reanalysis/Monthlies/surface/air.mon.mean.nc?var=air&north=40&west=-20&east=55&south=-40&disableProjSubset=on&horizStride=1&time_start=2000-01-01T00%3A00%3A00Z&time_end=2000-12-01T00%3A00%3A00Z&timeStride=1&accept=netcdf4"
mv "$NOAA_DIR/air.mon.mean.africa.2000.nc.part" "$NOAA_DIR/air.mon.mean.africa.2000.nc"

curl --fail --location --retry 3 --output "$NE_DIR/ne_110m_admin_0_countries.zip.part" \
  "https://naturalearth.s3.amazonaws.com/110m_cultural/ne_110m_admin_0_countries.zip"
mv "$NE_DIR/ne_110m_admin_0_countries.zip.part" "$NE_DIR/ne_110m_admin_0_countries.zip"

curl --fail --location --retry 3 --get \
  "https://exoplanetarchive.ipac.caltech.edu/TAP/sync" \
  --data-urlencode "query=select pl_name,ra,dec,pl_rade,disc_year,discoverymethod from pscomppars where ra is not null and dec is not null" \
  --data "format=csv" \
  --output "$NASA_DIR/pscomppars_sky.csv.part"
mv "$NASA_DIR/pscomppars_sky.csv.part" "$NASA_DIR/pscomppars_sky.csv"

python3 "$PROJECT_DIR/scripts/write_external_download_manifest.py"
