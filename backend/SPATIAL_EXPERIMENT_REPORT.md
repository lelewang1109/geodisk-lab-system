# Spatial Experiment Report

## 1. Experiment status

The complete first-round **CEG-PM2.5-2000 + multi-region spatial benchmark** ran successfully on 2026-08-28. It produced audited data manifests, eight original references, six method families, final-polygon spatial metrics, geometry-validity metrics, cross-view consistency, ablation, sensitivity, figures and paper-facing tables. No province was removed after viewing outcomes.

## 2. Data audit

| Item | Verified result |
|---|---:|
| Daily files | 366 |
| Date range | 2000-01-01 – 2000-12-31 |
| Dimensions | 353 latitude × 613 longitude |
| Coordinate order | latitude ascending; longitude ascending |
| Resolution | 0.1° × 0.1° |
| PM2.5 variable | `PM2.5` |
| Units | µg/m3 |
| Distinct schemas | 1 |
| Same grid every day | yes |
| PM2.5 missing fraction | 0.56275 |

Missingness is the stable outside-domain mask; it was not filled or fabricated. Regional cells with any missing daily aggregate are rejected. The full daily and variable-level evidence is in `results/data_audit/`.

## 3. Original geographic references

| Province | Macro-cells | Original edges |
|---|---:|---:|
| Hubei | 130 | 225 |
| Hunan | 137 | 242 |
| Jiangxi | 107 | 188 |
| Guangdong | 108 | 181 |
| Fujian | 74 | 125 |
| Guangxi | 142 | 248 |
| Anhui | 96 | 160 |
| Zhejiang | 65 | 110 |

Each reference persists original polygons, centroids, approximate geographic area, theta, boundary-normalized rho, row/column identity, PM2.5 summaries, shared-edge adjacency, directed local angles, and cumulative 1/2/3-hop neighborhoods.

## 4. Parameters

Default geometry uses coarsening factor 4, five radial layers, eight optimization passes, annulus radii 0.48–1.0, six power-balancing iterations, disk warp 0.018 and annulus warp 0.022. The topology objective weights are adjacency 1.0, angular 0.08, local direction 0.04 and radial 0.04. Random seed is 20260827.

## 5. Mean spatial-fidelity results

| Method | View | Adj. F1 ↑ | NP2 ↑ | LDE ↓ | Angular Error ↓ | Radial Spearman ↑ |
|---|---|---:|---:|---:|---:|---:|
| Direct Polar | Disk | **0.862** | **0.761** | **13.50°** | 1.53° | 0.971 |
| Direct Polar | Annulus | **0.824** | **0.723** | **18.69°** | **1.06°** | 0.973 |
| Harmonic | Disk | 0.727 | 0.614 | 15.38° | 3.08° | 0.883 |
| Harmonic | Annulus | 0.691 | 0.594 | 19.91° | 1.50° | 0.895 |
| Area-balanced | Disk | 0.734 | 0.607 | 17.07° | 3.03° | **0.987** |
| Area-balanced | Annulus | 0.651 | 0.578 | 20.82° | 1.70° | **0.978** |
| Regular Topology | Disk | 0.555 | 0.442 | 32.53° | 3.98° | 0.962 |
| Regular Topology | Annulus | 0.582 | 0.471 | 31.76° | 3.98° | 0.957 |
| GeoDisk | Disk | 0.654 | 0.543 | 25.64° | 2.82° | 0.976 |
| GeoAnnulus | Annulus | 0.631 | 0.554 | 25.38° | 2.11° | 0.969 |

Mean/median/std and every province-level value are preserved in `Table_spatial_fidelity.csv`.

## 6. Geometry validity

Proposed GeoDisk/GeoAnnulus have zero invalid polygons and numerical-scale overlap/gap (GeoAnnulus mean gap ratio 4.7×10⁻⁸). Their Area CV is 0.669/0.721. Direct Polar has better spatial fidelity but a mean of 3.125/3.375 invalid polygons and gap ratios 0.098/0.080. Guangdong is its largest gap failure (0.274 disk, 0.263 annulus). This is the main observed fidelity–validity trade-off.

Mean GeoDisk–GeoAnnulus edge Jaccard is approximately 0.696 (range 0.609–0.748), so cross-view adjacency is similar but not identical and is not described as invariant.

## 7. Province-level failure cases

- Hubei is the lowest Proposed adjacency case: GeoDisk/GeoAnnulus F1 = 0.572/0.571.
- Guangdong combines relatively low Proposed F1 (0.613/0.596) with high display Area CV in the ablation subset; its elongated/coastal outline is difficult for the current seed partition.
- Zhejiang and Fujian perform best among Proposed cases, but they are retained alongside all poorer regions.
- Direct Polar's high recall (near 1) coexists with invalid polygons and uncovered domain area, showing why fidelity scores alone are insufficient.

## 8. Ablation

- Removing topology optimization changes GeoDisk F1 from 0.654 to 0.650 and GeoAnnulus from 0.631 to 0.616. The current optimizer helps slightly, especially for the annulus, but is not the source of a large gain.
- Removing the angular cost has negligible average effect; its present weight and swap neighborhood do not materially control the final partition.
- Removing radial-layer assignment is catastrophic: F1 drops to 0.318/0.363, LDE rises to 63.8°/55.8°, and Radial Spearman falls to 0.066/0.041.
- Removing area balancing slightly raises F1 to 0.659/0.629 but worsens Area CV from 0.669/0.721 to 0.739/0.826.
- Removing warp leaves adjacency unchanged. The warp is nearly neutral for structural fidelity at the tested strengths.

These results do not justify claiming every module contributes equally.

## 9. Sensitivity

Sensitivity was predeclared on Hubei and Guangdong for runtime control. Coarsening factors 3/4/5 show increasing F1 as cells become coarser, so factor 4 is a detail–fidelity compromise rather than a universal optimum. Six layers improve F1/NP2/LDE over four or five in this subset. Two, five and eight optimization passes produce identical recorded outcomes, indicating early convergence. Warp strengths 0–0.02 have essentially unchanged adjacency and NP2.

## 10. Answers to the first-round RQs

**RQ1 — adjacency.** No. The current GeoDisk/GeoAnnulus implementation does not beat Direct Polar on adjacency F1. It beats Regular Topology after irregular partitioning, but that is only an internal-stage improvement.

**RQ2 — neighborhood.** No. Direct Polar also has the best mean NP2. Proposed layouts preserve roughly 54–55% of 2-hop neighborhood Jaccard on average.

**RQ3 — local direction.** Not better than the direct/continuous baselines. Proposed LDE is about 25°, versus 13.5° for Direct Polar disk. Direction must be strengthened in the optimization if it is a central claim.

**RQ4 — global direction and radial order.** Mostly yes in an absolute sense: Proposed Angular Error is 2–3° and Radial Spearman is about 0.97. However, these are not uniquely better than all baselines.

**RQ5 — trade-off.** The current method purchases valid, domain-filling, more balanced irregular geometry at a measurable adjacency/neighborhood/direction cost. Radial layering is essential; area balancing improves fairness but slightly reduces topology; warp adds little at current strength.

## 11. Recommended next method iteration

Do not proceed to a superiority claim or user study yet. Improve the topology stage against the already fixed metrics: use a larger move set than within-layer adjacent swaps, evaluate final power-cell adjacency during optimization or add a differentiable surrogate for it, test six layers as a preregistered next setting, and reconsider whether organic warp is necessary. Preserve the present results as Version 1 failure evidence and rerun without altering metric definitions.

