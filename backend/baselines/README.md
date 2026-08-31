# Unified baseline registry

The executable baseline implementations live in `src/geodisk_paper/geometry/mappings.py` so they share the same `RegionReference`, geometry serializer, and final-polygon evaluator:

- `direct_polar`
- `harmonic_continuous`
- `geographic_area_balanced`

`experiments/E2_baseline_geometry.py` is the sole baseline entry point. Historical workflow directories and cached results are intentionally not copied here.

