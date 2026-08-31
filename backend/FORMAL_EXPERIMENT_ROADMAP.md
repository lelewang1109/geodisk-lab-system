# Formal Experiment Roadmap

## Paper-level acceptance criteria

The project is not considered ready for a superiority claim until it satisfies all of the following:

1. Every metric definition is frozen before method retuning.
2. Final-polygon adjacency is stable over a declared contact-tolerance range.
3. Proposed geometry remains valid while closing most of the F1/NP2 gap to Direct Polar.
4. Results include macro, cell-weighted, edge-weighted and bootstrap confidence summaries.
5. Failure cases are retained and analyzed by boundary/interior status and shape complexity.
6. Generalization is tested on a different regular-grid source, irregular areal polygons and controlled synthetic domains.
7. Temporal claims are supported by fixed-layout correctness, change metrics and a preregistered time-selection rule.
8. Perceptual-efficiency claims are made only after a real user study.

## Dataset matrix

| ID | Spatial model | Scalar/time role | Scientific purpose |
|---|---|---|---|
| CEG-PM2.5-2000 | 0.1° regular environmental grid | 366 daily PM2.5 fields | Primary China experiment |
| NCEP-AirTemp-Africa-2000 | 2.5° global reanalysis grid subset to Africa | 12 monthly air-temperature fields | Independent provider, resolution and scalar |
| NE-Admin0-Africa | Irregular country polygons | Natural Earth attributes; scalar is secondary | Generalization beyond row/column grids |
| Synthetic Shape Suite | Controlled quad grids | Deterministic analytic scalar fields | Stress tests for concavity, aspect ratio, holes and components |
| NASA-Exoplanet-SkyGrid | 18×9 equal-solid-angle astronomical grid | Confirmed-planet count and archive attributes | Non-environmental scientific generalization |

Adding another variable on the CEG grid is reserved for temporal/change evaluation because it does not change the spatial-reference geometry.

## Ordered work packages

### WP1 — Data and provenance

- Download through versioned, official project endpoints.
- Preserve original archives read-only.
- Record SHA-256, byte count, URL, retrieval date, license/terms link and schema.
- Generate processed artifacts only through scripts.

### WP2 — Reference validation

- Support regular grid, clipped grid and arbitrary polygon references.
- Compare 4-neighbor, 8-neighbor and shared-boundary adjacency.
- Sweep boundary inclusion fraction and shared-boundary threshold.
- Label boundary and interior cells.

### WP3 — Metric hardening

- Add shared-boundary-length weighted adjacency.
- Add node-level fidelity tables and error maps.
- Add rotation-aligned LDE and neighbor-angle-order error.
- Add macro/cell/edge weighted summaries, bootstrap CIs and paired permutation tests.
- Add display-contact tolerance sensitivity.

### WP4 — Method revision

- Add arbitrary within-layer swaps, cross-layer moves and block moves.
- Use NP2/local-direction terms or validated surrogates.
- Add a final-partition adjacency refinement stage.
- Treat area balance as a constraint/Pareto objective.
- Re-evaluate six layers and remove warp if it remains neutral.

### WP5 — Full evaluation

- Re-run all baselines, Proposed, ablations and sensitivity on every dataset.
- Report failures without outcome-based filtering.
- Complete fixed-geometry DeltaAnnulus time encoding and change metrics.
- Freeze a user-study protocol before collecting participants.

## Phase II completion status

- WP1: complete for NOAA, Natural Earth and NASA external artifacts; checksums and retrieval timestamps recorded.
- WP2: complete for 4/8-neighbor and full/clipped CEG references with four inclusion thresholds.
- WP3: complete for node, boundary/interior, shared-boundary-weighted, bootstrap and contact-tolerance metrics. Rotation-aligned LDE remains an optional secondary metric; the primary LDE definition is unchanged to preserve comparability.
- WP4: complete for deterministic multi-start and final-Power polygon-force refinement. Block moves were not retained because final-polygon forces provide the accepted local refinement mechanism.
- WP5: algorithmic, temporal and user-study-material generation are complete. Human participant collection is intentionally not complete and is the only prerequisite for perceptual-efficiency claims.
