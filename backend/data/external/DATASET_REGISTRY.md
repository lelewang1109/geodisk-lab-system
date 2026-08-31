# External Dataset Registry

## NCEP-AirTemp-Africa-2000

- Internal experiment name; not an official NOAA dataset title.
- Source: NOAA Physical Sciences Laboratory, NCEP/NCAR Reanalysis monthly mean surface air temperature.
- Official dataset endpoint: `https://psl.noaa.gov/thredds/fileServer/Datasets/ncep.reanalysis/Monthlies/surface/air.mon.mean.nc`
- Downloaded artifact: an official NCSS server-side subset (`-20°–55°E`, `40°S–40°N`, calendar year 2000), avoiding unrelated years and grid cells.
- Official subset-service description: `https://psl.noaa.gov/thredds/ncss/grid/Datasets/ncep.reanalysis/Monthlies/surface/air.mon.mean.nc/dataset.html`
- Processing scope: year 2000, Africa land-mask reference, 12 monthly fields.
- The source file remains unchanged; processed subsets are generated separately.

## NE-Admin0-Africa

- Internal experiment name; not an official Natural Earth dataset title.
- Source: Natural Earth 1:110m Admin-0 Countries, version 5.1.1 as listed by the project.
- Official archive endpoint: `https://naturalearth.s3.amazonaws.com/110m_cultural/ne_110m_admin_0_countries.zip`
- Terms: Natural Earth states that its data are public domain; the project terms page must be cited in the paper.
- Processing scope: African mainland country polygons; any component filtering is recorded, not performed silently.

Checksums, sizes and retrieval timestamps are generated in `download_manifest.json`.

## NASA-Exoplanet-SkyGrid

- Internal experiment name derived from the NASA Exoplanet Archive Planetary Systems Composite Parameters (`pscomppars`) table.
- Official TAP documentation: `https://exoplanetarchive.ipac.caltech.edu/docs/TAP/usingTAP.html`.
- Retrieved fields: planet name, right ascension, declination, planet radius, discovery year and discovery method for rows with finite sky coordinates.
- Processing scope: 18 right-ascension bins by 9 equal-area declination bands; scalar value is `log1p` of the confirmed-planet count in each sky cell.
- The right-ascension seam is explicitly represented as a wrap-around reference edge.
- Publication acknowledgment and archive citation must follow `https://exoplanetarchive.ipac.caltech.edu/docs/acknowledge.html`.
- This is the predeclared non-environmental scientific generalization dataset; it is not another variable placed on the CEG geography.
