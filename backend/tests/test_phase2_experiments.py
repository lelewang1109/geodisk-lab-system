from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

import pandas as pd

from geodisk_paper.data.regions import load_region_reference
from geodisk_paper.data.external_datasets import prepare_exoplanet_sky_reference
from geodisk_paper.geometry.serialization import load_geometry
from geodisk_paper.metrics.geometry import geometry_validity
from geodisk_paper.metrics.spatial import weighted_adjacency_scores


ROOT = Path(__file__).resolve().parents[1]


class Phase2ExperimentTests(unittest.TestCase):
    def test_weighted_adjacency_definition(self):
        values = weighted_adjacency_scores({("a", "b"): 2.0, ("b", "c"): 1.0},
                                           {("a", "b"): 3.0, ("a", "c"): 1.0})
        self.assertAlmostEqual(values["weighted_adj_precision"], .75)
        self.assertAlmostEqual(values["weighted_adj_recall"], 2 / 3)
        self.assertTrue(0 <= values["weighted_edge_overlap"] <= 1)

    def test_advanced_error_groups_declared(self):
        table = pd.read_csv(ROOT / "results/tables/Table_boundary_interior_errors.csv")
        self.assertTrue({"boundary", "interior", "all"}.issubset(set(table.node_group)))
        self.assertTrue(table.node_adj_f1.between(0, 1).all())
        self.assertIn("GeoDisk-Final", set(table.method))
        finite_order = table.node_neighbor_order_accuracy.dropna()
        self.assertTrue(finite_order.between(0, 1).all())

    def test_reference_sensitivity_variants(self):
        neighbors = pd.read_csv(ROOT / "results/tables/Table_neighbor_model_sensitivity.csv")
        clipping = pd.read_csv(ROOT / "results/tables/Table_reference_clipping_sensitivity.csv")
        self.assertEqual(set(neighbors.neighbor_model), {"4-neighbor", "8-neighbor"})
        self.assertEqual(set(clipping.reference_policy), {"full_macro_cell", "province_clipped"})
        self.assertEqual(set(clipping.inclusion_threshold), {0.0, .25, .5, .75})

    def test_refined_geometry_identity_and_validity(self):
        for region in ("湖北", "广东"):
            reference = load_region_reference(ROOT / "data/processed/regions", region)
            expected = set(reference.cells.cell_id.astype(str))
            for view in ("disk", "annulus"):
                result = load_geometry(ROOT / "results/spatial_refined" / region / f"final_refined_{view}.geojson")
                self.assertEqual(expected, set(result.cell_ids))
                validity = geometry_validity(result.geometries, result.domain)
                self.assertEqual(validity["invalid_polygon_count"], 0)
                self.assertLess(validity["overlap_ratio"], 1e-7)

    def test_refinement_improves_its_final_power_start(self):
        table = pd.read_csv(ROOT / "results/tables/Table_final_power_refinement.csv")
        self.assertTrue((table.adj_f1 + 1e-12 >= table.final_power_f1_before_refinement).all())
        self.assertEqual(int(table.invalid_polygon_count.sum()), 0)
        inference = pd.read_csv(ROOT / "results/tables/Table_refined_paired_bootstrap.csv")
        self.assertIn("paired_permutation_p_holm", inference.columns)
        self.assertTrue(inference.paired_permutation_p_holm.between(0, 1).all())
        self.assertEqual(set(inference.permutation_mode), {"exact"})

    def test_temporal_encoding_and_study_materials(self):
        encoded = pd.read_csv(ROOT / "results/temporal/湖北/monthly_delta_encoding.csv")
        self.assertEqual(set(encoded.month), set(range(1, 13)))
        self.assertEqual(encoded.groupby("cell_id").month.nunique().min(), 12)
        summary = pd.read_csv(ROOT / "results/tables/Table_temporal_change_fidelity.csv")
        self.assertTrue(summary.delta_sign_accuracy.between(0, 1).all())
        self.assertTrue((summary.temporal_adjacency_jaccard == 1).all())
        tasks = pd.read_csv(ROOT / "user_study/task_manifest.csv")
        responses = pd.read_csv(ROOT / "user_study/response_schema.csv")
        self.assertEqual(len(tasks), 96)
        self.assertEqual(len(responses), 0)

    def test_astronomy_reference_wrap_and_results(self):
        source = ROOT / "data/external/nasa_exoplanet/pscomppars_sky.csv"
        with TemporaryDirectory() as temporary:
            reference, _, metadata = prepare_exoplanet_sky_reference(source, temporary)
        self.assertEqual(len(reference.cells), 162)
        self.assertEqual(len(reference.edges), 306)
        self.assertTrue(metadata["right_ascension_wrap"])
        self.assertIn(tuple(sorted(("NASA_EXO_r00_c00", "NASA_EXO_r00_c17"))), reference.edges)
        table = pd.read_csv(ROOT / "results/tables/Table_astronomy_generalization.csv")
        final = table[table.method.isin(["GeoDisk-Final", "GeoAnnulus-Final"])]
        self.assertEqual(len(final), 2)
        self.assertEqual(int(final.invalid_polygon_count.sum()), 0)

    def test_final_objective_ablation_matches_frozen_full_result(self):
        ablation = pd.read_csv(ROOT / "results/tables/Table_final_objective_ablation.csv")
        self.assertEqual(ablation.variant.nunique(), 6)
        full = ablation[ablation.variant == "Full objective"]
        frozen = pd.read_csv(ROOT / "results/tables/Table_final_power_refinement.csv")
        frozen = frozen[frozen.dataset.isin(full.region)].rename(columns={"dataset": "region"})
        merged = full.merge(frozen, on=["region", "view"], suffixes=("_ablation", "_frozen"))
        self.assertEqual(len(merged), len(full))
        self.assertTrue((merged.adj_f1_ablation - merged.adj_f1_frozen).abs().max() < 1e-12)

    def test_seed_stability_declared_repetitions(self):
        table = pd.read_csv(ROOT / "results/tables/Table_seed_stability.csv")
        self.assertGreaterEqual(table.seed.nunique(), 5)
        self.assertEqual(table.region.nunique(), 8)
        self.assertEqual(int(table.invalid_polygon_count.sum()), 0)

    def test_advanced_statistics_and_failure_cases(self):
        inference = pd.read_csv(ROOT / "results/tables/Table_advanced_paired_statistics.csv")
        self.assertEqual(set(inference.analysis), {"shared_boundary_weighted", "boundary_interior"})
        self.assertTrue(inference.paired_sign_flip_p_holm.between(0, 1).all())
        failures = pd.read_csv(ROOT / "results/tables/Table_local_failure_cases.csv")
        self.assertTrue({"GeoDisk-Final", "GeoAnnulus-Final"}.issubset(set(failures.method)))
        self.assertTrue(failures.failure_rank.between(1, 10).all())


if __name__ == "__main__":
    unittest.main()
