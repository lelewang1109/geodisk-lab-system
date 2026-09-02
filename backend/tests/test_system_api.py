import json
from pathlib import Path
import unittest

from geodisk_paper.api import (
    DATASETS,
    METHODS,
    evidence_payload,
    legacy_insights,
    overview_payload,
    read_table,
    workbench,
)


class SystemApiTest(unittest.TestCase):
    ROOT = Path(__file__).resolve().parents[1]
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
        self.assertTrue(payload["reference_edges"])
        self.assertTrue(payload["display_edges"])
        cell_ids = {
            str(feature["properties"]["cell_id"])
            for feature in payload["display"]["features"]
        }
        self.assertTrue(all(source in cell_ids and target in cell_ids
                            for source, target in payload["display_edges"]))

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

    def test_evidence_payload_is_frozen_and_traceable(self):
        payload = evidence_payload()
        self.assertEqual(payload["evidence_mode"], "frozen_canonical_tables")
        self.assertFalse(payload["mutates_geometry"])
        self.assertEqual(payload["final_geometry"]["invalid_polygon_count"], 0)
        self.assertLessEqual(payload["final_geometry"]["max_overlap_ratio"], 1e-7)
        self.assertTrue(payload["neighbor_models"])
        self.assertTrue(payload["contact_tolerances"])
        self.assertGreaterEqual(payload["readiness"]["pass"], 10)

    def test_tvcg_claim_evidence_audit_is_machine_readable(self):
        path = self.ROOT / "results/formal_readiness/tvcg_submission_audit.json"
        payload = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(payload["verdict"], "algorithmic_artifact_ready_but_full_submission_not_ready")
        self.assertGreaterEqual(payload["pass_count"], 10)
        self.assertTrue(payload["research_questions"])
        self.assertTrue(payload["contributions"])
        self.assertIn("human_system_evaluation", {row["check_id"] for row in payload["checks"]})


if __name__ == "__main__":
    unittest.main()
