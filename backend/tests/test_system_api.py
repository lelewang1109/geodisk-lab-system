import unittest

from geodisk_paper.api import (
    DATASETS,
    METHODS,
    legacy_insights,
    overview_payload,
    read_table,
    workbench,
)


class SystemApiTest(unittest.TestCase):
    def test_overview_uses_canonical_result_tables(self):
        overview = overview_payload()
        self.assertEqual(overview["dataset_count"], len(DATASETS))
        self.assertEqual(overview["method_count"], len(METHODS))
        self.assertGreater(overview["metrics"]["proposed_adj_f1"], 0)
        self.assertEqual(overview["metrics"]["proposed_invalid"], 0)

    def test_result_rows_are_typed(self):
        rows = read_table("external")
        self.assertTrue(rows)
        self.assertIsInstance(rows[0]["adj_f1"], float)
        self.assertIn("dataset", rows[0])

    def test_workbench_links_canonical_artifacts(self):
        payload = workbench(dataset="湖北", view="disk")
        self.assertEqual(len(payload["original"]["features"]), 130)
        self.assertEqual(len(payload["display"]["features"]), 130)
        self.assertEqual(len(payload["nodes"]), 130)
        self.assertEqual(len(payload["temporal"]), 130 * 12)
        self.assertEqual(payload["method"], "GeoDisk-Final")

    def test_legacy_insights_integrates_projects_two_and_three(self):
        payload = legacy_insights()
        states = payload["annual_states"]
        paths = payload["migration_paths"]
        self.assertEqual(len(states["annulus"]["features"]), 176)
        self.assertEqual(len(states["monthly_values"]), 176 * 12)
        self.assertEqual(len(states["state_intervals"]), 3)
        self.assertEqual(len(paths["provinces"]["features"]), 8)
        self.assertEqual(len(paths["case"]["gateway_sequence"]), 4)
        self.assertEqual(len(paths["path_table"]), 3)


if __name__ == "__main__":
    unittest.main()
