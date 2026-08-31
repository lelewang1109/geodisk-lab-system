# Project Refactor Plan

## Scope and research logic

This project evaluates whether a fixed circular abstraction can preserve original-grid adjacency, multi-hop neighborhoods, local directions, global bearings, and center-to-periphery order. The first release is restricted to the internally named **CEG-PM2.5-2000** dataset and the spatial-fidelity benchmark. Delta time rings, change metrics, and the user study remain explicitly out of scope for this round.

## Evidence from the three historical stages

### Stage 1 — method and baseline source

- Retain the four-vertex/boundary-ray idea from workflow v3, stable layer assignment, angular ordering, and the distinction between geometry-driven baselines and topology-aware assignment.
- Retain three representative baseline families: direct polar, harmonic/continuous, and area-balanced.
- Refactor rather than copy the old Beijing-specific mesh code. It hard-codes the Beijing input contract and center-hole construction, and its old metrics mostly describe area/overlap rather than original-vs-display spatial fidelity.
- Discard workflow-v1/v2/v3 directory duplication and historical result snapshots from the new project.

### Stage 2 — selective visual-geometry source

- Retain the balanced power-cell construction and the boundary-preserving organic warp as optional, configurable geometry stages.
- Retain the important warning that area balance is display-area balance, not preservation of geographic area.
- Do not import annual pollution-state clustering, envelopes, bridge cells, hotspots, or final visual styling into the spatial benchmark.

### Stage 3 — principal method prototype

- Retain the coupled GeoDisk/GeoAnnulus design, topology-aware radial layers and angular seats, balanced irregular partition, fixed cell identity, adjacency evaluation, Angular Error, Radial Spearman, area CV, ablation, sensitivity, and the same eight provinces.
- Refactor the precipitation CSV adapter into a generic `DatasetAdapter` and a real daily-NetCDF adapter.
- Replace positional integer identity with stable string `cell_id` values persisted in CSV/GeoJSON.
- Recompute all geometry from Dataset 01 and the copied boundary asset; no Stage-3 geometry cache is read.
- Do not carry Stage-3 path recovery or precipitation conclusions into this PM2.5 benchmark.

## Metric audit

Existing Stage-3 code implements adjacency precision/recall/F1, Angular Error, Radial Spearman, area CV, raw gap/overlap areas, and Disk–Annulus edge Jaccard. It does **not** implement the requested NP2/NP3, Local Direction Error, normalized overlap/gap ratios, invalid-polygon count, or per-region/mean/median/std paper tables. The new `src/geodisk_paper/metrics/` layer adds these metrics and evaluates final polygons, not an intermediate slot graph.

## Unified input and identity contract

`DailyNetCDFAdapter` audits actual schemas before resolving the PM2.5 variable. `E1_prepare_regions.py` groups the common 0.1-degree grid into configured macro-cells and assigns IDs of the form `CEG2000_f4_r####_c####`. The same ID indexes source polygons, PM2.5 summaries, every display geometry, edge sets, neighborhoods, tables, and figures.

## Formal methods retained in the benchmark

1. Direct Polar (four vertices; disk and annulus)
2. Harmonic / Continuous (graph-harmonic seed embedding with domain partition)
3. Area-balanced (balanced power partition initialized by geographic polar coordinates)
4. Regular Topology-aware (layer/seat geometry before irregularization)
5. GeoDisk (topology-aware seeds, balanced power partition, optional warp)
6. GeoAnnulus (same reference and optimization logic in an annular domain)

The harmonic baseline is implemented at the stable cell graph/seed level because the historical punctured shared-vertex mesh is Beijing-specific and is not valid for arbitrary masks without a separately justified hole construction. This methodological difference is recorded in outputs rather than hidden.

## Ablation and sensitivity design

Ablations independently disable topology optimization, angular cost, radial-layer constraint, area balancing, and warp. Sensitivity varies coarsening, layer count, optimization passes, and warp strength. The default sensitivity subset is Hubei and Guangdong to bound runtime; it is declared before results are generated and is not chosen from performance.

## Execution order and completion checks

1. E0 audits all daily files and writes schema/date/missingness manifests.
2. E1 writes regional original references, original edges/directions, and 1–3 hop neighborhoods.
3. E2 builds the three geometry baselines.
4. E3 builds Regular Topology, GeoDisk, and GeoAnnulus.
5. E4 evaluates final polygons, exports tables, and renders like-for-like figures.
6. E7 and E8 produce ablation and sensitivity tables/curves.
7. Tests check identity, grid adjacency, metric bounds, geometry validity, and numerical delta reconstruction.

No historical repository or raw NetCDF file is modified. Failures are raised with explicit context; no province or method is silently dropped.

