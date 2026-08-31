# GeoDisk Lab

GeoDisk Lab is a reproducible research system for topology-aware circular spatial mapping, fixed-geometry temporal encoding, annual pollution-state analysis, and province-level migration-path exploration.

The repository combines the complete Python experiment suite with a single-screen React + D3 visual analytics interface.

- Interactive system: <https://geodisk-lab.lelewang1012.chatgpt.site>
- Local frontend: <http://localhost:3000>
- Local API documentation: <http://127.0.0.1:8000/docs>

## Current research status

The completed experiments support two claims:

1. The generated Disk and Annulus layouts are geometrically valid.
2. The encoding and evaluation pipeline is stable across the included spatial, climate, administrative, astronomy, and synthetic datasets.

The current evidence does **not** establish a universal topology-adjacency advantage over every baseline. Boundary/interior error decomposition, shared-boundary weighting, 4/8-neighborhood sensitivity, and final Power Diagram adjacency are therefore retained as explicit evaluation targets rather than hidden limitations.

## Repository structure

```text
geodisk-lab-system/
├── backend/
│   ├── src/geodisk_paper/       # geometry, topology, temporal and API modules
│   ├── experiments/             # E0–E24 reproducible experiments
│   ├── data/                    # processed and external research datasets
│   ├── results/                 # canonical tables, figures and geometries
│   ├── tests/                   # scientific invariants and API integration tests
│   └── user_study/              # preregistration and study materials
├── frontend/
│   ├── app/                     # React/Vinext application and D3 views
│   └── public/data/             # portable read-only experiment snapshots
├── docs/                         # system architecture and reproducibility notes
└── scripts/                      # setup, start and verification entry points
```

The repository is self-contained. The integrated annual-state and migration-path views read the bundled snapshot in `frontend/public/data/legacy-insights.json`; they do not require the original sibling project folders.

## Quick start

Requirements:

- Python 3.9+
- Node.js 22+
- npm

```bash
git clone https://github.com/lelewang1109/geodisk-lab-system.git
cd geodisk-lab-system
bash scripts/setup_system.sh
bash scripts/start_system.sh
```

The start script launches the FastAPI backend on port `8000` and the visual analytics frontend on port `3000`.

## Development

Run the services separately:

```bash
# Terminal 1: backend
cd backend
PYTHONPATH=src python3 -m uvicorn geodisk_paper.api:app --host 127.0.0.1 --port 8000

# Terminal 2: frontend
cd frontend
npm install
npm run dev
```

The hosted frontend automatically falls back to bundled Hubei Disk/Annulus and cross-stage snapshots when the local API is unavailable.

## Reproduce and verify

Run the complete scientific and integration test suite:

```bash
bash scripts/verify_system.sh
```

Run the formal experiment sequence:

```bash
cd backend
bash scripts/run_formal_experiment.sh
```

Individual experiment stages are available in `backend/experiments/E0_*.py` through `E24_*.py`. Canonical paper-ready tables are written to `backend/results/tables/` and figures to `backend/results/figures/`.

## Integrated visual analytics interface

The single-screen system presents three coordinated lenses:

- **Spatial mapping:** geographic reference, GeoDisk/GeoAnnulus Power partition, cell selection, pan and zoom.
- **Annual states:** fixed S1/S2/S3 intervals, 176-cell membership, monthly evidence and overlap categories.
- **Migration paths:** projected province geometry, regional transitions and four-step temporal context.

D3 v7.9 drives geometry projection, path rendering, zoom/pan interaction, flow edges, scales, axes and monthly profile interaction. React manages application state and cross-view coordination.

## Safety boundary

The local API exposes only canonical artifacts and a whitelist of experiment commands. It does not accept arbitrary filesystem paths or shell commands. Keep the service bound to `127.0.0.1` unless authentication and deployment hardening are added.

## Documentation

- [System architecture](docs/ARCHITECTURE.md)
- [Evaluation metrics and experiment protocol (Chinese)](docs/EVALUATION_METRICS_CN.md)
- [Experiment roadmap](backend/FORMAL_EXPERIMENT_ROADMAP.md)
- [Phase 2 method and experiment report](backend/PHASE2_METHOD_AND_EXPERIMENT_REPORT.md)
- [User-study protocol](backend/user_study/USER_STUDY_PROTOCOL.md)
