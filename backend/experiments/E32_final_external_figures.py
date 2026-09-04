from __future__ import annotations

import shutil

import pandas as pd
from shapely.ops import unary_union

from common import ROOT, ensure_output_dirs, geometry_config
from geodisk_paper.data.regions import load_region_reference
from geodisk_paper.geometry.serialization import load_geometry
from geodisk_paper.utils.io import write_csv, write_json
from geodisk_paper.visualization.figures import comparison_figure


DATASETS = {
    "NE-Admin0-Africa": ("Natural Earth Africa Admin-0", "log10 population estimate"),
    "NCEP-AirTemp-Africa-2000": ("NCEP Air Temperature Africa 2000", "annual mean air temperature (°C)"),
}
BASELINES = {
    "Direct Polar": "direct_polar_annulus.geojson",
    "Harmonic": "harmonic_annulus.geojson",
    "Area-balanced": "area_balanced_annulus.geojson",
    "Regular Topology": "regular_topology_annulus.geojson",
}
METHODS = {"Direct Polar", "Harmonic", "Area-balanced", "Regular Topology", "GeoDisk-Final", "GeoAnnulus-Final"}


def _read(path):
    if not path.exists():
        raise FileNotFoundError(f"Missing {path}; run its producer first")
    return pd.read_csv(path, encoding="utf-8-sig")


def _cross_domain_table() -> pd.DataFrame:
    blocks = []
    ceg = _read(ROOT / "results/tables/Table_spatial_fidelity.csv")
    ceg = ceg[~ceg.region.astype(str).str.startswith("OVERALL")]
    ceg_valid = _read(ROOT / "results/tables/Table_geometry_validity.csv")
    ceg_valid = ceg_valid[~ceg_valid.region.astype(str).str.startswith("OVERALL")]
    ceg = ceg.merge(ceg_valid, on=["region", "method", "view", "cell_count"], how="left")
    ceg = ceg.rename(columns={"region": "dataset"}); ceg["dataset_family"] = "CEG"
    blocks.append(ceg)

    external = _read(ROOT / "results/tables/Table_external_spatial_fidelity.csv")
    external_valid = _read(ROOT / "results/tables/Table_external_geometry_validity.csv")
    external = external.merge(external_valid, on=["dataset", "method", "view", "cell_count"], how="left")
    external["dataset_family"] = external.dataset.map({
        "NE-Admin0-Africa": "Natural Earth", "NCEP-AirTemp-Africa-2000": "NCEP",
    })
    blocks.append(external)

    synthetic = _read(ROOT / "results/tables/Table_synthetic_spatial_fidelity.csv")
    synthetic_valid = _read(ROOT / "results/tables/Table_synthetic_geometry_validity.csv")
    synthetic = synthetic.merge(synthetic_valid, on=["case", "method", "view", "cell_count"], how="left")
    synthetic["dataset"] = "Synthetic-" + synthetic.case.astype(str)
    synthetic["dataset_family"] = "Synthetic"; blocks.append(synthetic)

    final = _read(ROOT / "results/tables/Table_final_power_refinement.csv")
    final["dataset_family"] = final.dataset.map(
        lambda value: "CEG" if value in {"湖北", "湖南", "江西", "广东", "福建", "广西", "安徽", "浙江"}
        else "Natural Earth" if value == "NE-Admin0-Africa"
        else "NCEP" if value == "NCEP-AirTemp-Africa-2000" else "Synthetic"
    )
    blocks.append(final)

    astronomy = _read(ROOT / "results/tables/Table_astronomy_generalization.csv")
    astronomy["dataset_family"] = "NASA Exoplanet"; blocks.append(astronomy)

    frame = pd.concat(blocks, ignore_index=True, sort=False)
    frame = frame[frame.method.isin(METHODS)].copy()
    frame = frame.sort_values(["dataset_family", "dataset", "method", "view"])
    frame = frame.drop_duplicates(["dataset", "method", "view"], keep="last")
    first = ["dataset", "dataset_family", "method", "view", "cell_count"]
    metrics = [column for column in (
        "adj_precision", "adj_recall", "adj_f1", "np2", "np3", "local_direction_error_deg",
        "angular_error_deg", "radial_spearman", "area_cv", "overlap_ratio", "gap_ratio",
        "invalid_polygon_count",
    ) if column in frame.columns]
    return frame[first + metrics].reset_index(drop=True)


def main() -> None:
    ensure_output_dirs(); config = geometry_config()
    inner, outer = float(config["annulus_inner"]), float(config["annulus_outer"])
    manifest = []
    for dataset, (title, value_label) in DATASETS.items():
        reference = load_region_reference(ROOT / "data/processed/external_regions", dataset)
        boundary = unary_union(list(reference.polygons.values())); inputs = {}; paths = {}
        for label, filename in BASELINES.items():
            paths[label] = ROOT / "results/external_spatial" / dataset / filename
        paths.update({
            "GeoDisk-Final": ROOT / "results/external_refined" / dataset / "final_refined_disk.geojson",
            "GeoAnnulus-Final": ROOT / "results/external_refined" / dataset / "final_refined_annulus.geojson",
        })
        expected = set(reference.cells.cell_id.astype(str))
        for label, path in paths.items():
            if not path.exists():
                raise FileNotFoundError(f"Missing {path}; run {'E19' if label.endswith('Final') else 'E11'} first")
            result = load_geometry(path, inner, outer)
            if set(result.cell_ids) != expected:
                raise ValueError(f"Cell identity mismatch: {path}")
            inputs[label] = result
        output = ROOT / "results/figures" / f"Fig_final_external_{dataset}.png"
        comparison_figure(
            reference, boundary, inputs, output, title,
            value_column="scalar_value", value_label=value_label,
            labels=["Geographic Reference", *BASELINES, "GeoDisk-Final", "GeoAnnulus-Final"], dpi=300,
        )
        shutil.copy2(output, ROOT / "paper/figures" / output.name)
        manifest.append({"dataset": dataset, "figure": str(output.relative_to(ROOT)),
                         "inputs": [str(path.relative_to(ROOT)) for path in paths.values()]})
        print("[final external figure]", dataset, flush=True)
    table = _cross_domain_table()
    write_csv(table, ROOT / "results/tables/Table_final_cross_domain_spatial.csv")
    write_csv(table, ROOT / "paper/tables/Table_final_cross_domain_spatial.csv")
    write_json({"producer": "E32_final_external_figures.py", "figures": manifest,
                "table_sources": ["E4", "E12", "E13", "E19", "E22"]},
               ROOT / "results/figures/final_external_figures_manifest.json")
    print(table.groupby(["dataset_family", "method", "view"]).size().to_string())


if __name__ == "__main__":
    main()
