import os
import sqlite3
import tempfile
import unittest
import httpx
from unittest.mock import MagicMock
from crawler.storage import CrawlStorage
from verification.snapshot import SnapshotRecorder
from verification.differ import SnapshotDiffer
from verification.experiment import ExperimentEvaluator
from verification.watch import SiteWatcher

class TestV3Verification(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.test_db_path = os.path.join(self.temp_dir.name, "test_seo.db")
        CrawlStorage(self.test_db_path)
        with sqlite3.connect(self.test_db_path) as conn:
            with open("crawler/migrations/001_v3_core_tables.sql", "r") as f:
                conn.executescript(f.read())

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_snapshot_recorder(self):
        rec = SnapshotRecorder(db_path=self.test_db_path)
        html = """
        <html>
          <head>
            <title>Test Page Title</title>
            <meta name="robots" content="index, follow">
            <link rel="canonical" href="https://example.com/test-page">
            <script type="application/ld+json">{"@type": "Product", "name": "Item"}</script>
          </head>
          <body><h1>Heading One</h1></body>
        </html>
        """
        page_data = {"status_code": 200, "word_count": 150}
        snap = rec.take_snapshot_for_url("run_before", "https://example.com/test-page", page_data, html)

        self.assertTrue(snap["snapshot_id"].startswith("SNAP-"))
        self.assertEqual(snap["title"], "Test Page Title")
        self.assertEqual(snap["h1_text"], "Heading One")
        self.assertEqual(snap["status_code"], 200)
        self.assertTrue(len(snap["schema_hash"]) > 0)
        self.assertTrue(len(snap["content_hash"]) > 0)

        with sqlite3.connect(self.test_db_path) as conn:
            row = conn.execute("SELECT title, status_code FROM snapshots WHERE url = ?", ("https://example.com/test-page",)).fetchone()
            self.assertEqual(row[0], "Test Page Title")
            self.assertEqual(row[1], 200)

    def test_snapshot_differ(self):
        rec = SnapshotRecorder(db_path=self.test_db_path)
        differ = SnapshotDiffer(db_path=self.test_db_path)

        # Before run:
        # url1: 404 error
        # url2: 200 index
        # url3: 200 index
        rec.take_snapshot_for_url("run_pre", "https://example.com/page-1", {"status_code": 404, "title": "Not Found"})
        rec.take_snapshot_for_url("run_pre", "https://example.com/page-2", {"status_code": 200, "meta_robots": "index, follow", "title": "Good Page"})
        rec.take_snapshot_for_url("run_pre", "https://example.com/page-3", {"status_code": 200, "meta_robots": "index, follow", "title": "Constant Page"})

        # After run:
        # url1: fixed -> 200
        # url2: regressed -> noindex
        # url3: unchanged -> 200 index
        rec.take_snapshot_for_url("run_post", "https://example.com/page-1", {"status_code": 200, "title": "Restored Page"})
        rec.take_snapshot_for_url("run_post", "https://example.com/page-2", {"status_code": 200, "meta_robots": "noindex, follow", "title": "Good Page"})
        rec.take_snapshot_for_url("run_post", "https://example.com/page-3", {"status_code": 200, "meta_robots": "index, follow", "title": "Constant Page"})

        diff_file = os.path.join(self.temp_dir.name, "test-diff.json")
        res = differ.diff_runs("run_pre", "run_post", export_path=diff_file)

        self.assertEqual(res["summary"]["FIXED"], 1)
        self.assertEqual(res["summary"]["REGRESSED"], 1)
        self.assertEqual(res["summary"]["UNCHANGED"], 1)
        self.assertTrue(os.path.exists(diff_file))

        with sqlite3.connect(self.test_db_path) as conn:
            diff_count = conn.execute("SELECT COUNT(*) FROM snapshot_diffs").fetchone()[0]
            self.assertEqual(diff_count, 3)

    def test_experiment_evaluator(self):
        evaluator = ExperimentEvaluator(db_path=self.test_db_path)
        test_urls = ["https://example.com/bike-a", "https://example.com/bike-b"]
        control_urls = ["https://example.com/bike-c", "https://example.com/bike-d"]

        # Test cohort grew by 50 clicks; Control cohort grew by 10 clicks (seasonal)
        # Net DiD lift = 40 clicks
        res = evaluator.evaluate_cohorts(
            experiment_id="EXP-001",
            annotation="Inject specifications table and Vehicle schema",
            template="tpl_bike_detail",
            deploy_date="2026-09-01",
            test_urls=test_urls,
            control_urls=control_urls,
            pre_metrics={"test": 100.0, "control": 100.0},
            post_metrics={"test": 150.0, "control": 110.0},
            metric_name="clicks"
        )

        summary = res["result_summary"]
        self.assertEqual(summary["test_delta"], 50.0)
        self.assertEqual(summary["control_delta"], 10.0)
        self.assertEqual(summary["did_net_lift"], 40.0)
        self.assertEqual(summary["lift_pct"], 40.0)
        self.assertEqual(summary["claim_type"], "OBSERVED")
        self.assertIn("not an assurance of causal effect", summary["observational_note"])

        with sqlite3.connect(self.test_db_path) as conn:
            row = conn.execute("SELECT experiment_id, annotation FROM experiments WHERE experiment_id = ?", ("EXP-001",)).fetchone()
            self.assertEqual(row[0], "EXP-001")

    def test_site_watcher(self):
        # Mock httpx client
        mock_client = MagicMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = """
        <html>
          <head>
            <title>Healthy Homepage</title>
            <link rel="canonical" href="https://example.com/">
            <meta name="robots" content="index, follow">
          </head>
          <body>Hello</body>
        </html>
        """
        mock_client.get.return_value = mock_resp

        watcher = SiteWatcher(db_path=self.test_db_path, client=mock_client)
        res = watcher.check_url("https://example.com/")
        self.assertEqual(res["status"], "HEALTHY")
        self.assertEqual(len(res["issues"]), 0)

        # Test alert on 404
        mock_resp_404 = MagicMock()
        mock_resp_404.status_code = 404
        mock_resp_404.text = "Not found"
        mock_client.get.return_value = mock_resp_404

        res_alert = watcher.check_url("https://example.com/broken")
        self.assertEqual(res_alert["status"], "ALERT")
        self.assertTrue(any("404" in i for i in res_alert["issues"]))

if __name__ == "__main__":
    unittest.main()
