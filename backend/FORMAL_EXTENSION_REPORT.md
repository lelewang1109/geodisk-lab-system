# Formal Experiment Extension Report

## Completed extension

The first formal extension adds independent spatial models rather than merely recoloring the CEG grid:

- **NCEP-AirTemp-Africa-2000:** official NOAA PSL NCSS subset, 12 monthly 2.5° air-temperature grids, 401 cells and 741 reference edges after the fixed mainland-component policy.
- **NE-Admin0-Africa:** Natural Earth 5.1.1 irregular Admin-0 polygons, 50 cells and 109 shared-boundary edges after excluding Madagascar as the only cell outside the largest adjacency component.
- **Synthetic Topology Stress:** six deterministic masks testing circular, elongated, L-shaped, U-shaped, holed and disconnected domains.

Every downloaded file has a URL, byte count, retrieval timestamp and SHA-256 in `data/external/download_manifest.json`.

## Independent-data findings

On irregular African country polygons, GeoDisk reaches Adj. F1 0.609 and NP2 0.580; Direct Polar reaches F1 0.619 and NP2 0.543. GeoDisk therefore improves broader neighborhood preservation slightly while remaining geometrically valid, but it does not establish an adjacency advantage. GeoAnnulus reaches F1 0.577.

On the 401-cell NCEP grid, Harmonic is the strongest valid continuous baseline (Disk F1 0.700), while GeoDisk reaches 0.471 and GeoAnnulus 0.445. Direct Polar has near-complete recall but produces more than 2,300 new display edges and low precision, exposing severe collapse/overlap behavior on the coarse, concave continental mask.

## Synthetic stress findings

Direct Polar is topologically strong on the controlled grids but can be geometrically invalid. Proposed F1 ranges from approximately 0.546 to 0.722 for GeoDisk and 0.557 to 0.697 for GeoAnnulus. Elongated, L-shaped, U-shaped and holed cases produce high Proposed Area CV; U-shaped and holed cases also expose small but non-zero overlap. These are retained as declared limitations.

## Contact-tolerance sensitivity

Five display contact tolerances from `1e-6` to `5e-4` were evaluated over eight CEG provinces and two independent datasets. Proposed F1 is effectively invariant over the range. Direct Polar varies materially at very small tolerances, so its reported contact topology is less numerically stable.

## Statistical inference

Ten-thousand-repeat province bootstrap intervals confirm that the current CEG Proposed method is below Direct Polar:

- GeoDisk minus Direct Polar Disk F1: mean −0.209, 95% bootstrap CI [−0.233, −0.184].
- GeoAnnulus minus Direct Polar Annulus F1: mean −0.193, 95% bootstrap CI [−0.211, −0.176].

The difference is systematic and is not treated as province sampling noise.

## Method revision experiment

An explicitly separate revision adds six layers, NP2/local-direction objective terms, expanded within-layer swaps and constrained cross-layer candidates. It slightly changes GeoDisk F1 from 0.654 to 0.658 and GeoAnnulus from 0.631 to 0.633. This is not a meaningful solution to the main deficit; the old result is preserved and no table is overwritten.

## Next required work

1. Implement node-level and boundary/interior error decomposition.
2. Replace absolute contact tolerance with shared-boundary-length-normalized adjacency.
3. Add 4-neighbor/8-neighbor/clipped-reference sensitivity.
4. Optimize against the final power partition rather than only the regular slot graph.
5. Add a license-clear non-environmental scientific scalar field.
6. Complete DeltaAnnulus monthly/change correctness and the preregistered temporal-task benchmark.

