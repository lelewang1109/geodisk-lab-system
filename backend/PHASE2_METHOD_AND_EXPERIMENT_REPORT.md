# Phase II Method and Experiment Report

## 1. What changed

Phase II replaces the earlier slot-graph-only search with a deterministic multi-start refinement whose acceptance test is computed from the **final balanced Power polygons**. Every candidate is fully reconstructed, polygon adjacency is re-extracted, and only then is the objective evaluated. The resulting methods are named `GeoDisk-Final` and `GeoAnnulus-Final`; the original `GeoDisk` and `GeoAnnulus` outputs remain unchanged for an honest before/after comparison.

The final objective combines adjacency F1, NP@2, local-direction error, angular error, radial order and an area-CV penalty. Its fixed candidate schedule contains the topology, harmonic and geographic seeds, two 50/50 blends, followed by deterministic attraction on lost reference edges and repulsion on new display edges. The same schedule and weights are used for every dataset.

Important scope statement: the reference adjacency graph is used during optimization. This is a supervised layout optimization, not an unsupervised topology discovery algorithm.

## 2. Expanded evaluation matrix

- 8 CEG PM2.5 province domains, 65–142 cells each.
- Natural Earth Africa Admin-0, 50 irregular polygons.
- NCEP Africa air temperature, 401 regular grid cells and 12 months.
- NASA Exoplanet Archive sky grid, 162 equal-solid-angle cells derived from 6,354 current `pscomppars` records.
- 6 deterministic topology stress cases: disk-like, elongated, L-shaped, concave U, hole and disconnected.
- 4/8-neighbor reference definitions.
- Full macro-cell versus province-clipped reference geometry.
- Cell inclusion thresholds 0, 0.25, 0.50 and 0.75.
- 5/7/9/13-bin temporal encoding sensitivity over 99 dataset-transition pairs.

## 3. New metrics

### Node and boundary/interior decomposition

Each cell now reports incident-edge precision/recall/F1, neighbor Jaccard, degree error, angular error, radial-rank error, incident local-direction error and common-neighbor cyclic-order accuracy. The last metric tests whether neighbor pairs retain clockwise/counter-clockwise order around the focal node. Results are aggregated separately for boundary and interior nodes.

Across the 10 original real datasets, `GeoDisk-Final` node F1 is 0.724 on boundary cells and 0.791 on interior cells. Its direction error is 22.06°/13.01° and cyclic-order accuracy is 0.927/0.947 for boundary/interior cells. `GeoAnnulus-Final` is more balanced: node F1 is 0.727/0.718 and cyclic-order accuracy is 0.909/0.929.

### Shared-boundary-weighted adjacency

Weighted precision uses displayed shared-boundary length; weighted recall uses reference shared-boundary length. A normalized boundary-distribution overlap is reported separately. `GeoDisk-Final` reaches mean weighted F1 0.879 and `GeoAnnulus-Final` 0.800 on the 10 original real datasets.

### Reference sensitivity

With the 4-neighbor definition, `GeoDisk-Final` averages F1 0.772 across the 8 CEG regions plus NCEP; with the 8-neighbor definition it reaches 0.849. `GeoAnnulus-Final` changes from 0.738 to 0.801. The ordering against valid baselines is not reversed.

Changing from full retained macro-cells to province-clipped reference polygons materially lowers every method's adjacency scores because clipping removes or fragments several nominal grid contacts. Therefore the paper must report the reference policy explicitly; the full-cell and clipped results must not be pooled.

## 4. Final-Power refinement results

| Family | Method | View | Before F1 | Refined F1 | NP@2 | Invalid |
|---|---|---:|---:|---:|---:|---:|
| CEG (8) | GeoDisk-Final | Disk | 0.660 | 0.780 | 0.644 | 0 |
| CEG (8) | GeoAnnulus-Final | Annulus | 0.630 | 0.748 | 0.640 | 0 |
| External (2) | GeoDisk-Final | Disk | 0.560 | 0.738 | 0.636 | 0 |
| External (2) | GeoAnnulus-Final | Annulus | 0.510 | 0.650 | 0.545 | 0 |
| Synthetic (6) | GeoDisk-Final | Disk | 0.618 | 0.771 | 0.636 | 0 |
| Synthetic (6) | GeoAnnulus-Final | Annulus | 0.605 | 0.715 | 0.605 | 0 |

On the 8 CEG regions, paired bootstrap differences and exact paired sign-flip tests show (raw p followed by Holm-adjusted p across the five comparators in the same view/metric family):

- GeoDisk-Final versus Harmonic: `+0.053` F1, 95% CI `[+0.017, +0.103]`, `p=0.0156`, Holm `p=0.0391`.
- GeoDisk-Final versus Area-balanced: `+0.046`, CI `[+0.031, +0.061]`, `p=0.0078`, Holm `p=0.0391`.
- GeoDisk-Final versus Direct Polar: `-0.082`, CI `[-0.095, -0.070]`, `p=0.0078`, Holm `p=0.0391`.
- GeoAnnulus-Final versus Harmonic: `+0.057`, CI `[+0.032, +0.083]`, `p=0.0156`, Holm `p=0.0391`.
- GeoAnnulus-Final versus Area-balanced: `+0.097`, CI `[+0.077, +0.113]`, `p=0.0078`, Holm `p=0.0391`.
- GeoAnnulus-Final versus Direct Polar: `-0.076`, CI `[-0.098, -0.057]`, `p=0.0078`, Holm `p=0.0391`.

The defensible conclusion is now stronger but still bounded: final-Power refinement establishes a topology advantage over the valid-geometry baselines, while Direct Polar retains higher CEG adjacency at the cost of invalid and overlapping geometries.

## 5. Component ablation

For CEG, deterministic multi-start selection contributes mean F1 gains of +0.097 (Disk) and +0.065 (Annulus) over the topology-only final partition. Final polygon-force iterations add another +0.024/+0.054. Both components therefore contribute; the result is not just a renamed baseline initialization.

## 6. Astronomy generalization

The NASA Exoplanet Archive dataset closes the non-environmental-science gap. The current downloaded snapshot is recorded by URL, byte count and SHA-256. It is aggregated into 18 right-ascension bins and 9 equal-solid-angle declination bands, with an explicit wrap edge across the right-ascension seam.

- GeoDisk-Final: F1 0.764, NP@2 0.642, zero invalid polygons.
- Best valid disk baseline, Area-balanced: F1 0.741.
- GeoAnnulus-Final: F1 0.705, NP@2 0.624, zero invalid polygons.
- Direct Polar: F1 0.324 and 128 invalid polygons because the cylindrical sky seam is not compatible with its direct planar polar warp.

Archive data remain dynamic; the checksum and retrieval timestamp define the evaluated snapshot.

## 7. Temporal DeltaAnnulus

The same final annulus geometry and cell IDs are reused for all 12 months. Two encodings are compared:

1. reconstruct two sequential monthly bins and subtract them;
2. directly encode the signed monthly delta with a symmetric diverging scale.

At 9 bins over 99 dataset-transition pairs:

- Direct delta sign accuracy: 0.839 versus 0.702 for derived differences.
- Normalized delta MAE: 0.0646 versus 0.1127.
- Change-magnitude Spearman: 0.865 versus 0.681.
- Bootstrap direct-minus-derived sign-accuracy difference: +0.136, 95% CI `[+0.110, +0.166]`.

Fixed identity accuracy 1.0, centroid drift 0 and temporal adjacency Jaccard 1.0 are construction properties of the fixed geometry. They are not perceptual-study evidence.

## 8. Runtime

Single-process wall-clock measurements on the recorded local environment show:

- 50 cells: 1.69 s final refinement.
- 130 cells: 12.13 s.
- 162 cells: 18.27 s.
- 401 cells: 61.60 s, plus 42.54 s for the slot embedding.

The final refinement is roughly 10–17 times slower than one original Power-partition generation in these cases. These are single-run engineering measurements, not runtime confidence intervals.

## 9. User study readiness

The repository now contains 96 counterbalanced trial definitions across two conditions, four tasks, two datasets and six transitions. Power planning requires 34 complete participants for `dz=0.5`, two-sided alpha 0.05 and power 0.80; the recruitment target is 40 with attrition. The protocol, preregistration draft, stimuli, ground truth and empty response schema are present. No participant result is claimed.

## 10. Primary outputs

- `Table_final_power_refinement.csv`
- `Table_refined_paired_bootstrap.csv`
- `Table_refinement_component_ablation.csv`
- `Table_node_level_errors.csv`
- `Table_boundary_interior_errors.csv`
- `Table_weighted_adjacency.csv`
- `Table_neighbor_model_sensitivity.csv`
- `Table_reference_clipping_sensitivity.csv`
- `Table_astronomy_generalization.csv`
- `Table_temporal_change_fidelity.csv`
- `Table_runtime_scalability.csv`

All canonical tables are under `results/tables/`; paper-facing copies are under `paper/tables/`.

## 11. Remaining claims that still require external work

- Human perceptual superiority requires the preregistered user study; generated ground truth cannot answer it.
- Public redistribution of the original CEG raw files and provincial boundary artifact still requires source/license resolution.
- Direct Polar's high topology score cannot be treated as a valid-layout win where its invalid/overlap counts are nonzero.
- The final method is computationally more expensive and still does not exceed Direct Polar's CEG adjacency score.
