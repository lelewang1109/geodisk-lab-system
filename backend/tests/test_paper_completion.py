from __future__ import annotations

import json
from pathlib import Path
import unittest

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]


class PaperCompletionTests(unittest.TestCase):
    def test_boundary_definitions_are_frozen_in_reference(self):
        cells = pd.read_csv(ROOT / "data/processed/regions/湖北/cells.csv")
        self.assertTrue({"reference_degree", "is_topological_boundary", "is_geographic_boundary"}.issubset(cells.columns))
        self.assertTrue((cells.is_topological_boundary == (cells.reference_degree < 4)).all())
        sensitivity = pd.read_csv(ROOT / "results/tables/Table_boundary_definition_sensitivity.csv")
        self.assertEqual(set(sensitivity.boundary_definition), {"topological", "geographic"})
        self.assertEqual(set(sensitivity.node_group), {"boundary", "interior"})

    def test_final_figures_use_final_geojson(self):
        table = pd.read_csv(ROOT / "results/tables/Table_final_spatial_comparison.csv")
        final = table[table.method.isin(["GeoDisk-Final", "GeoAnnulus-Final"])]
        self.assertEqual(len(final), 16)
        self.assertTrue(final.source_geojson.str.contains("spatial_refined").all())
        for region in ("Hubei", "Hunan", "Jiangxi", "Guangdong", "Fujian", "Guangxi", "Anhui", "Zhejiang"):
            self.assertTrue((ROOT / f"results/figures/Fig_final_spatial_comparison_{region}.png").exists())

    def test_cross_domain_coverage(self):
        table = pd.read_csv(ROOT / "results/tables/Table_final_cross_domain_spatial.csv")
        self.assertEqual(set(table.dataset_family), {"CEG", "Natural Earth", "NCEP", "Synthetic", "NASA Exoplanet"})
        self.assertTrue({"GeoDisk-Final", "GeoAnnulus-Final"}.issubset(set(table.method)))

    def test_integrated_delta_is_fixed_identity_construction(self):
        table = pd.read_csv(ROOT / "results/tables/Table_integrated_delta_annulus_consistency.csv")
        self.assertEqual(set(table.layer), {"D1", "Δ1,2", "Δ2,3", "Δ3,4", "Δ4,5", "Δ5,6", "Δ6,7",
                                            "Δ7,8", "Δ8,9", "Δ9,10", "Δ10,11", "Δ11,12"})
        self.assertTrue((table.cell_identity_accuracy == 1).all())
        self.assertTrue((table.temporal_layer_mismatch_count == 0).all())
        self.assertFalse(table.geometry_reoptimized_per_layer.astype(bool).any())
        manifest = json.loads((ROOT / "results/temporal/integrated_delta_annulus_manifest.json").read_text())
        self.assertIn("construction checks, not comparative performance", manifest["guardrail"])

    def test_user_study_v2_has_no_fake_responses(self):
        tasks = pd.read_csv(ROOT / "user_study_v2/task_manifest.csv")
        responses = pd.read_csv(ROOT / "user_study_v2/response_schema.csv")
        manifest = json.loads((ROOT / "user_study_v2/study_manifest.json").read_text())
        self.assertEqual(tasks.condition.nunique(), 4)
        self.assertEqual(tasks.task.nunique(), 5)
        self.assertEqual(len(tasks), 240)
        self.assertEqual(len(responses), 0)
        self.assertEqual(manifest["status"], "NO PARTICIPANT DATA COLLECTED")

    def test_case_study_selection_and_outputs(self):
        manifest = json.loads((ROOT / "results/temporal/case_hubei_manifest.json").read_text())
        self.assertEqual(len(manifest["all_transition_scores"]), 11)
        selected = max(item["event_score"] for item in manifest["all_transition_scores"])
        self.assertAlmostEqual(manifest["selected_event_score"], selected)
        table = pd.read_csv(ROOT / "results/tables/Table_case_hubei_top_changes.csv")
        self.assertEqual(len(table), 10)
        self.assertTrue((table.absolute_delta.diff().dropna() <= 0).all())


if __name__ == "__main__":
    unittest.main()
