from common import ROOT, ensure_output_dirs, geometry_config, project_boundaries
from geodisk_paper.data.regions import load_region_reference
from geodisk_paper.geometry.mappings import direct_polar, geographic_area_balanced, harmonic_continuous
from geodisk_paper.geometry.serialization import save_geometry


def main():
    ensure_output_dirs()
    config = geometry_config(); boundaries, _ = project_boundaries()
    inner, outer = float(config["annulus_inner"]), float(config["annulus_outer"])
    for region in config["regions"]:
        reference = load_region_reference(ROOT / "data/processed/regions", region)
        output = ROOT / "results/spatial" / region
        for view in ("disk", "annulus"):
            methods = [
                ("direct_polar", direct_polar(reference, boundaries[region], view, inner, outer)),
                ("harmonic", harmonic_continuous(reference, view, inner, outer)),
                ("area_balanced", geographic_area_balanced(reference, view, inner, outer, int(config["power_iterations"]))),
            ]
            for key, result in methods:
                save_geometry(result, output / f"{key}_{view}.geojson")
                print("[baseline]", region, key, view, flush=True)


if __name__ == "__main__":
    main()

