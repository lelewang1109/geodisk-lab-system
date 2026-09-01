# GeoDisk–DeltaAnnulus Paper Experiment Backend

This is the independent, reproducible first-round paper artifact for **Dataset 01 + Spatial Fidelity Benchmark**. It does not modify or import runtime code from the three historical repositories.

This directory is now the backend of the experiment system. The complete E0–E29 suite covers spatial fidelity, final-Power refinement, reference sensitivity, cross-domain generalization, temporal encoding, objective ablation, multi-seed stability, paired inference, failure analysis, repeated runtime and formal-readiness auditing. `geodisk_paper.api` exposes canonical result tables, figures, dataset metadata and a whitelist-based experiment runner to the sibling `frontend/` application.

## Research question

For a multi-temporal geographic scalar field, can a fixed circular abstraction preserve original adjacency, broader local neighborhoods, local directions, global bearings, and center-to-periphery order well enough to support compact comparison? The target pipeline is:

`Original Geographic Grid → topology-aware embedding → GeoDisk / GeoAnnulus → fixed DeltaAnnulus geometry`

This release evaluates spatial fidelity and fixed-geometry temporal change encoding. It does not claim that a circle is inherently better than a map, that a disk-to-annulus transform is a strict topological homeomorphism, or that the generated temporal ground truth substitutes for a human perceptual study. Circular space is used as a unified, fixed and compact comparison coordinate system.

The formal extension now also includes an independent NOAA regular grid, Natural Earth irregular country polygons, a NASA exoplanet sky grid, six controlled synthetic domains, reference/contact sensitivity, final-Power refinement, temporal encoding and bootstrap inference. See `FORMAL_EXTENSION_REPORT.md` and `PHASE2_METHOD_AND_EXPERIMENT_REPORT.md`.

## Verified dataset

**CEG-PM2.5-2000** means **China Environmental Grid PM2.5 2000**. This is an internal project name, not an official name published by a data provider.

E0 inspected all 366 daily NetCDF files from 2000-01-01 through 2000-12-31. The actual schema is `lat(353) × lon(613)`, both coordinates are ascending at 0.1° spacing, and the scalar variable is `PM2.5` with units `µg/m3`. All files share one grid and one schema. The 56.275% missing fraction is a stable outside-domain mask shared by all audited variables; retained regional macro-cells are required to have finite PM2.5 for all 366 dates.

Eight predeclared provinces are evaluated: Hubei, Hunan, Jiangxi, Guangdong, Fujian, Guangxi, Anhui and Zhejiang. The default 4×4 coarsening produces 65–142 stable cells per province. IDs such as `CEG2000_f4_r0123_c0456` persist across the original reference and every display.

## Methods

- **Direct Polar** maps all four cell vertices using boundary-ray radial normalization.
- **Harmonic** solves a uniform graph-Laplacian seed embedding and forms an unweighted domain partition. This replaces the historical Beijing-specific punctured mesh and is explicitly recorded as a methodological refactor.
- **Area-balanced** uses geographic polar seeds and a balanced power partition.
- **Regular Topology** uses radial layers, angular seats and configurable local swap optimization.
- **GeoDisk / GeoAnnulus** use the same original reference and topology logic, then create balanced power cells with an optional boundary-preserving warp.
- **GeoDisk-Final / GeoAnnulus-Final** use a fixed multi-start schedule and accept candidates only after adjacency has been recomputed from the final balanced Power polygons.

All methods receive exactly the same regional cells and PM2.5 values. All reported adjacency is recomputed from final polygons.

## Metrics

Core spatial fidelity is reported separately from geometry validity:

- Adjacency Precision, Recall and F1
- 2-hop Neighborhood Preservation (NP2), with NP3 in the detailed table
- Local Direction Error (LDE) on original adjacent pairs
- Angular Error relative to the regional reference center
- Radial Spearman correlation
- Display Area CV, Overlap Ratio, Gap Ratio and Invalid Polygon Count
- GeoDisk–GeoAnnulus edge Jaccard as cross-view consistency
- node-level and boundary/interior topology errors
- common-neighbor cyclic-order accuracy around each node
- shared-boundary-length-weighted precision, recall, F1 and normalized overlap
- 4/8-neighbor and reference-clipping sensitivity
- temporal change-sign, magnitude-rank, hotspot and event-detection fidelity

Area CV means display-area balance; it is not geographic-area preservation. Temporal change-sign, magnitude-rank, hotspot and event metrics use fixed geometry; perceptual-efficiency claims remain deferred until participant data are collected.

## Current result, without outcome polishing

The original Proposed implementation remains below the baselines reported in the first-round tables. Phase II improves mean CEG Adj. F1 to 0.780 for GeoDisk-Final and 0.748 for GeoAnnulus-Final, with zero invalid polygons. Paired bootstrap comparisons establish gains over Harmonic and Area-balanced, but Direct Polar remains higher at 0.862/0.824 and can produce invalid/overlapping geometry. The valid-layout topology advantage is now supported; a universal advantage over Direct Polar is not.

See `SPATIAL_EXPERIMENT_REPORT.md` for the first round and `PHASE2_METHOD_AND_EXPERIMENT_REPORT.md` for the refined method, astronomy, temporal and user-study-ready phases.

## Reproduction

Python 3.9 or newer is supported. From this project directory:

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
```

Run individual stages:

```bash
PYTHONPATH=src python3 experiments/E0_data_audit.py
PYTHONPATH=src python3 experiments/E1_prepare_regions.py
PYTHONPATH=src python3 experiments/E2_baseline_geometry.py
PYTHONPATH=src python3 experiments/E3_geodisk_geoannulus.py
PYTHONPATH=src python3 experiments/E4_spatial_fidelity.py
PYTHONPATH=src python3 experiments/E7_ablation.py
PYTHONPATH=src python3 experiments/E8_sensitivity.py
PYTHONPATH=src python3 experiments/E19_final_power_refinement.py
PYTHONPATH=src python3 experiments/E17_advanced_spatial_errors.py
PYTHONPATH=src python3 experiments/E18_reference_sensitivity.py
PYTHONPATH=src python3 experiments/E5_temporal_delta.py
PYTHONPATH=src python3 experiments/E6_change_metrics.py
python3 -m unittest discover -s tests -v
```

Or run the complete first-round experiment:

```bash
bash scripts/run_spatial_experiment.sh
```

Run the expanded formal suite, including verified external downloads:

```bash
bash scripts/run_formal_experiment.sh
```

For a submission-grade run, start from a clean frozen commit:

```bash
bash scripts/run_formal_experiment.sh --require-clean
```

The pipeline writes a resumable stage/duration/environment manifest under `results/run_manifests/`. See `FORMAL_EXPERIMENT_PROTOCOL_CN.md` and `paper/FORMAL_EXPERIMENT_READINESS.md` for the ordered protocol and remaining publication blockers.

`scripts/run_all.sh` now runs the complete formal suite. `run_temporal_experiment.sh` runs temporal encoding, change metrics and user-study material generation independently.

## Outputs

- Audit: `results/data_audit/`
- Original references: `data/processed/regions/<province>/`
- Final geometries and edge diagnostics: `results/spatial/<province>/`
- Canonical tables: `results/tables/`
- Ablation and sensitivity: `results/ablation/`, `results/sensitivity/`
- Manuscript-facing copies: `paper/tables/`, `paper/figures/`
- External download provenance: `data/external/download_manifest.json`
- Formal extension results: `results/tables/Table_external_*`, `Table_synthetic_*`, and `Table_contact_tolerance_sensitivity.csv`
- Phase II results: `Table_final_power_refinement.csv`, `Table_*weighted*`, `Table_*boundary*`, `Table_*neighbor*`, `Table_astronomy_generalization.csv`, `Table_temporal_*` and `Table_runtime_scalability.csv`
- Formal hardening: `Table_final_objective_ablation.csv`, `Table_seed_stability.csv`, `Table_advanced_paired_statistics.csv`, `Table_local_failure_cases.csv` and `results/formal_readiness/`

Raw NetCDF files remain outside the project and are never overwritten. Boundary provenance and redistribution licensing must be resolved before public release.
