# System architecture

## Data flow

```text
processed datasets
       |
       v
E0–E24 experiment scripts
       |
       +--> canonical CSV tables and JSON metadata
       +--> GeoJSON reference and Power geometries
       +--> publication figures
       |
       v
FastAPI read-only artifact layer
       |
       v
React state coordination + D3 rendering
```

## Backend boundaries

`backend/src/geodisk_paper/` is divided by research responsibility:

- `data/`: dataset adapters, region preparation and audits.
- `geometry/`: disk/annulus mappings, Power construction and serialization.
- `topology/`: embeddings and final-Power refinement.
- `metrics/`: geometry and spatial-fidelity metrics.
- `temporal/`: fixed-geometry temporal change encoding.
- `visualization/`: paper-oriented static figure generation.
- `api.py`: typed, read-only system endpoints and whitelisted experiment runs.

The API never accepts arbitrary experiment commands. `/api/runs` maps only to the predefined `tests`, `audit`, `spatial`, and `formal` workflows.

## Frontend boundaries

The production route is intentionally small:

- `integrated-workbench.tsx`: data loading, controls and coordinated selection state.
- `d3-views.tsx`: D3 projections, partition paths, province flows, zoom/pan, axes and monthly curves.
- `integrated-workbench.css`: single-screen conference-style layout.
- `public/data/`: immutable deployment snapshots used when the local API is unavailable.

The frontend first requests live local artifacts. If the request fails, it loads the bundled snapshots without changing the interaction model.

## Reproducibility layers

1. **Scientific invariants:** geometry validity, cell identity, topology definitions and temporal reconstruction tests.
2. **Canonical outputs:** fixed table and figure paths consumed by both the paper and system.
3. **API integration:** tests verify that the interface receives the same canonical artifacts.
4. **Deployment snapshot:** published interaction remains available without exposing the local experiment runner.

## Extension points

- Add a dataset adapter under `geodisk_paper/data/`.
- Register only validated datasets in the backend workbench whitelist.
- Add metrics through the canonical table pipeline before exposing them in the interface.
- Preserve cell identity across reference, display and temporal artifacts.
- Evaluate topology against the final Power Diagram, not an intermediate slot graph.
