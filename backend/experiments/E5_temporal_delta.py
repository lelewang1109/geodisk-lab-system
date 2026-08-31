from __future__ import annotations

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import PatchCollection
from matplotlib.colors import Normalize
from matplotlib.patches import Polygon as MplPolygon
import numpy as np
import pandas as pd

from common import ROOT, ensure_output_dirs, experiment_config, geometry_config
from geodisk_paper.data.regions import load_region_reference
from geodisk_paper.geometry.power import polygon_parts
from geodisk_paper.geometry.serialization import load_geometry
from geodisk_paper.temporal.encoding import encode_temporal
from geodisk_paper.utils.io import write_csv, write_json


def _render_delta_small_multiples(dataset: str, encoded: pd.DataFrame, geometry_path, output) -> None:
    result = load_geometry(geometry_path)
    by_id = {cell_id: geometry for cell_id, geometry in zip(result.cell_ids, result.geometries)}
    limit = float(np.nanquantile(np.abs(encoded.delta), .95))
    norm = Normalize(-max(limit, 1e-9), max(limit, 1e-9)); cmap = plt.get_cmap("RdBu_r")
    figure, axes = plt.subplots(3, 4, figsize=(11, 8.5), constrained_layout=True)
    for month, axis in enumerate(axes.flat, start=1):
        values = encoded[encoded.month == month].set_index("cell_id").delta_reconstructed
        patches, colors = [], []
        for cell_id in result.cell_ids:
            for part in polygon_parts(by_id[cell_id]):
                patches.append(MplPolygon(np.asarray(part.exterior.coords), closed=True))
                colors.append(float(values.get(cell_id, 0.0)) if month > 1 else 0.0)
        collection = PatchCollection(patches, cmap=cmap, norm=norm, linewidth=.12, edgecolor="#263531")
        collection.set_array(np.asarray(colors)); axis.add_collection(collection)
        axis.set_xlim(-1.04, 1.04); axis.set_ylim(-1.04, 1.04); axis.set_aspect("equal"); axis.axis("off")
        axis.set_title(f"M{month:02d}" + (" · baseline" if month == 1 else ""), fontsize=9)
    display_name = "Hubei" if dataset == "湖北" else dataset
    figure.suptitle(f"Fixed-geometry DeltaAnnulus · {display_name}", fontsize=14, fontweight="semibold")
    colorbar = figure.colorbar(plt.cm.ScalarMappable(norm=norm, cmap=cmap), ax=axes, shrink=.72, pad=.02)
    colorbar.set_label("Reconstructed monthly change")
    output.parent.mkdir(parents=True, exist_ok=True); figure.savefig(output, dpi=190, bbox_inches="tight")
    plt.close(figure)


def main() -> None:
    ensure_output_dirs(); config = geometry_config(); phase2 = experiment_config()["phase2"]; rows = []; manifests = {}
    datasets = [(region, ROOT / "data/processed/regions", ROOT / "results/spatial_refined") for region in config["regions"]]
    datasets.append(("NCEP-AirTemp-Africa-2000", ROOT / "data/processed/external_regions", ROOT / "results/external_refined"))
    for dataset, reference_root, geometry_root in datasets:
        reference = load_region_reference(reference_root, dataset)
        encoded, manifest = encode_temporal(reference, dataset, bin_count=int(phase2["primary_temporal_bin_count"]))
        output = ROOT / "results/temporal" / dataset
        write_csv(encoded, output / "monthly_delta_encoding.csv")
        geometry_path = geometry_root / dataset / "final_refined_annulus.geojson"
        manifest["geometry_path"] = str(geometry_path.relative_to(ROOT))
        write_json(manifest, output / "encoding_manifest.json"); manifests[dataset] = manifest
        transition = encoded[encoded.month > 1]
        rows.append({
            "dataset": dataset, "variable": manifest["variable"], "units": manifest["units"],
            "cell_count": manifest["cell_count"], "month_count": 12, "transition_count": 11,
            "value_min": float(encoded.value.min()), "value_max": float(encoded.value.max()),
            "mean_absolute_delta": float(transition.delta.abs().mean()),
            "p95_absolute_delta": float(transition.delta.abs().quantile(.95)),
            "positive_change_fraction": float((transition.delta > 0).mean()),
            "negative_change_fraction": float((transition.delta < 0).mean()),
        })
        if dataset in {"湖北", "NCEP-AirTemp-Africa-2000"}:
            figure_name = "Fig_temporal_delta_Hubei.png" if dataset == "湖北" else "Fig_temporal_delta_NCEP.png"
            _render_delta_small_multiples(dataset, encoded, geometry_path, ROOT / "results/figures" / figure_name)
            (ROOT / "paper/figures" / figure_name).write_bytes((ROOT / "results/figures" / figure_name).read_bytes())
        print("[temporal encode]", dataset, flush=True)
    table = pd.DataFrame(rows)
    write_csv(table, ROOT / "results/tables/Table_temporal_encoding.csv")
    write_csv(table, ROOT / "paper/tables/Table_temporal_encoding.csv")
    write_json({"datasets": manifests, "encoding": "9-bin sequential value plus symmetric 9-bin direct delta"},
               ROOT / "results/temporal/temporal_encoding_manifest.json")
    print(table.to_string(index=False))


if __name__ == "__main__":
    main()
