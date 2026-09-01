from __future__ import annotations

import math
from pathlib import Path
import sys
import unittest

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from geodisk_paper.data.regions import grid_edges, load_region_reference
from geodisk_paper.geometry.serialization import load_geometry
from geodisk_paper.metrics.geometry import geometry_validity
from geodisk_paper.metrics.spatial import adjacency_scores, neighborhood_preservation


class SpatialProjectTests(unittest.TestCase):
    def test_cell_identity(self):
        for region in ("湖北", "广东"):
            reference = load_region_reference(ROOT / "data/processed/regions", region)
            expected = set(reference.cells.cell_id.astype(str))
            for name in ("proposed_disk.geojson", "proposed_annulus.geojson"):
                result = load_geometry(ROOT / "results/spatial" / region / name)
                self.assertEqual(expected, set(result.cell_ids))
                self.assertEqual(len(expected), len(result.cell_ids))

    def test_original_adjacency(self):
        frame = pd.DataFrame([
            {"cell_id": "a", "block_row": 0, "block_col": 0},
            {"cell_id": "b", "block_row": 0, "block_col": 1},
            {"cell_id": "c", "block_row": 1, "block_col": 0},
            {"cell_id": "d", "block_row": 2, "block_col": 2},
        ])
        self.assertEqual(grid_edges(frame), {("a", "b"), ("a", "c")})
        reference = load_region_reference(ROOT / "data/processed/regions", "湖北")
        positions = {str(r.cell_id): (int(r.block_row), int(r.block_col)) for r in reference.cells.itertuples()}
        for left, right in reference.edges:
            dr = abs(positions[left][0] - positions[right][0])
            dc = abs(positions[left][1] - positions[right][1])
            self.assertEqual(dr + dc, 1)

    def test_metric_bounds(self):
        reference = {("a", "b"), ("b", "c")}
        display = {("a", "b"), ("a", "c")}
        values = adjacency_scores(reference, display)
        self.assertTrue(0 <= values["adj_precision"] <= 1)
        self.assertTrue(0 <= values["adj_recall"] <= 1)
        self.assertTrue(0 <= values["adj_f1"] <= 1)
        np2 = neighborhood_preservation(["a", "b", "c"], reference, display, 2)
        self.assertTrue(0 <= np2 <= 1)
        table = pd.read_csv(ROOT / "results/tables/Table_spatial_fidelity.csv")
        actual = table[~table.region.str.startswith("OVERALL")]
        for column in ("adj_precision", "adj_recall", "adj_f1", "np2", "np3"):
            self.assertTrue(actual[column].between(0, 1).all())
        self.assertTrue(actual.local_direction_error_deg.between(0, 180).all())
        self.assertTrue(actual.angular_error_deg.between(0, 180).all())
        self.assertTrue(actual.radial_spearman.between(-1, 1).all())

    def test_geometry_validity(self):
        for region in ("湖北", "广东"):
            for name in ("proposed_disk.geojson", "proposed_annulus.geojson"):
                result = load_geometry(ROOT / "results/spatial" / region / name)
                values = geometry_validity(result.geometries, result.domain)
                self.assertEqual(values["invalid_polygon_count"], 0)
                self.assertLess(values["overlap_ratio"], 1e-6)
                self.assertLess(values["gap_ratio"], 1e-5)

    def test_temporal_reconstruction(self):
        d1 = np.asarray([1.0, 2.0, 4.0])
        d2 = np.asarray([2.5, 1.5, 8.0])
        delta = d2 - d1
        self.assertLess(float(np.max(np.abs((d1 + delta) - d2))), 1e-12)

    def test_external_dataset_identity(self):
        for dataset in ("NE-Admin0-Africa", "NCEP-AirTemp-Africa-2000"):
            reference = load_region_reference(ROOT / "data/processed/external_regions", dataset)
            expected = set(reference.cells.cell_id.astype(str))
            for name in ("proposed_disk.geojson", "proposed_annulus.geojson"):
                result = load_geometry(ROOT / "results/external_spatial" / dataset / name)
                self.assertEqual(expected, set(result.cell_ids))

    def test_synthetic_suite_declared_cases(self):
        expected = {"disk_like", "elongated", "l_shape", "concave_u", "hole", "disconnected"}
        actual = {path.name.replace("Synthetic-", "") for path in (ROOT / "data/processed/synthetic_regions").glob("Synthetic-*")}
        self.assertEqual(expected, actual)

    def test_proposed_contact_tolerance_stability(self):
        frame = pd.read_csv(ROOT / "results/tables/Table_contact_tolerance_sensitivity.csv")
        proposed = frame[frame.method.isin(["GeoDisk", "GeoAnnulus", "GeoDisk-Final", "GeoAnnulus-Final"])]
        self.assertIn("GeoDisk-Final", set(proposed.method))
        spread = proposed.groupby(["dataset", "method", "view"]).adj_f1.agg(lambda values: values.max() - values.min())
        self.assertTrue((spread < .01).all())


if __name__ == "__main__":
    unittest.main()
