from common import ROOT, ensure_output_dirs
from geodisk_paper.data.external_datasets import (prepare_natural_earth_reference, prepare_ncep_africa_reference,
                                                  prepare_synthetic_references)
from geodisk_paper.utils.io import write_json


def main():
    ensure_output_dirs()
    output = ROOT / "data/processed/external_regions"
    ne_reference, africa_domain, ne_meta = prepare_natural_earth_reference(
        ROOT / "data/external/natural_earth/ne_110m_admin_0_countries.zip", output)
    ncep_reference, _, ncep_meta = prepare_ncep_africa_reference(
        ROOT / "data/external/noaa_ncep/air.mon.mean.africa.2000.nc", africa_domain, output)
    synthetic = prepare_synthetic_references(ROOT / "data/processed/synthetic_regions")
    summary = {
        "NE-Admin0-Africa": {"cells": len(ne_reference.cells), "edges": len(ne_reference.edges), **ne_meta},
        "NCEP-AirTemp-Africa-2000": {"cells": len(ncep_reference.cells), "edges": len(ncep_reference.edges), **ncep_meta},
        "Synthetic-Topology-Stress": {case: {"cells": len(reference.cells), "edges": len(reference.edges)}
                                      for case, reference in synthetic.items()},
    }
    write_json(summary, ROOT / "results/data_audit/external_dataset_summary.json")
    print(summary)


if __name__ == "__main__":
    main()
