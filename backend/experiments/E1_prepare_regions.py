from common import ROOT, adapter_from_audit, ensure_output_dirs, geometry_config, project_boundaries
from geodisk_paper.data.regions import prepare_region_references


def main():
    ensure_output_dirs()
    config = geometry_config()
    adapter = adapter_from_audit()
    schema = adapter.inspect_schema()
    boundaries, _ = project_boundaries()
    references = prepare_region_references(
        adapter, schema, boundaries, list(config["regions"]), ROOT / "data/processed/regions",
        coarsen_factor=int(config["coarsen_factor"]), min_valid_fraction=float(config["min_valid_fraction"]),
    )
    print({name: {"cells": len(ref.cells), "edges": len(ref.edges)} for name, ref in references.items()})


if __name__ == "__main__":
    main()

