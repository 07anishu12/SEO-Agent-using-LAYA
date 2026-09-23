import os
import shutil
import tempfile
import unittest

from lab.site_generator import SyntheticSiteGenerator
from lab.gsc_generator import SyntheticGSCGenerator
from lab.scorecard import DetectorScorecard
from lab.feedback import FeedbackEngine
from crawler.migrations import MigrationRunner

class TestV3Lab(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.test_dir, "test_seo.db")
        # Initialize schema
        runner = MigrationRunner(db_path=self.db_path)
        runner.run_migrations()

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_synthetic_site_generator(self):
        gen = SyntheticSiteGenerator(base_url="https://test-moto.local")
        self.assertGreater(len(gen.pages), 5)
        self.assertIn("https://test-moto.local/", gen.pages)
        self.assertIn("https://test-moto.local/bikes/thunder-250", gen.pages)
        self.assertGreater(len(gen.ground_truth_manifest), 3)

    def test_synthetic_gsc_generator(self):
        gsc_gen = SyntheticGSCGenerator(base_url="https://test-moto.local")
        rows = gsc_gen.generate_rows()
        self.assertGreater(len(rows), 4)

        # Verify striking distance presence
        pos_11_20 = [r for r in rows if 11.0 <= r["position"] <= 20.0]
        self.assertGreater(len(pos_11_20), 0)

        # Verify cannibalization flip-flop presence (same query on 2 dates across 2 URLs)
        cannibal_rows = [r for r in rows if r["query"] == "blaze 125 scooter price"]
        self.assertEqual(len(cannibal_rows), 4)

    def test_detector_scorecard_gates(self):
        gen = SyntheticSiteGenerator(base_url="https://test-moto.local")
        scorecard = DetectorScorecard(db_path=self.db_path)
        results = scorecard.evaluate(gen)

        # Check precision and recall metrics
        prec = results["overall_precision"]
        rec = results["overall_recall"]

        self.assertGreaterEqual(prec, 0.95, f"Detector precision {prec} failed quality gate (>= 0.95)")
        self.assertGreaterEqual(rec, 0.85, f"Detector recall {rec} failed quality gate (>= 0.85)")
        self.assertTrue(results["passed_gate"])

    def test_feedback_engine_suppression(self):
        fb = FeedbackEngine(db_path=self.db_path)
        fp = "fp_abc12345"

        self.assertFalse(fb.is_suppressed(fp))

        # Record false positive
        fb.record_feedback(fp, "rule_canonical", "https://test.local/p1", "false_positive", "Benign redirect")
        self.assertTrue(fb.is_suppressed(fp))

if __name__ == "__main__":
    unittest.main()
