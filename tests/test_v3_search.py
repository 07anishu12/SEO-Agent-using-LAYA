import unittest
from search.gsc_pipeline import GSCPipeline
from search.ctr_model import SiteCTRModel
from search.query_miner import QueryMiner
from search.fit_analyzer import QueryFitAnalyzer
from verticals.automotive import AutomotiveVertical

class TestV3Search(unittest.TestCase):
    def test_gsc_pipeline(self):
        pipeline = GSCPipeline()
        # Normalization
        norm = pipeline.normalize_gsc_url("https://www.drivio.in/bikes/bajaj/pulsar-125/")
        self.assertEqual(norm, "https://www.drivio.in/bikes/bajaj/pulsar-125")

        # Brackets
        self.assertEqual(pipeline.get_position_bracket(2.5), "1-3")
        self.assertEqual(pipeline.get_position_bracket(8.0), "4-10")
        self.assertEqual(pipeline.get_position_bracket(14.5), "11-20")
        self.assertEqual(pipeline.get_position_bracket(25.0), "21-30")

    def test_site_ctr_model(self):
        ctr_model = SiteCTRModel()
        exp_ctr, source = ctr_model.get_expected_ctr(1.0)
        self.assertEqual(exp_ctr, 0.280)
        self.assertEqual(source, "ASSUMED")

        # Click headroom
        headroom = ctr_model.calculate_click_headroom(position=1.0, actual_ctr=0.10, impressions=1000)
        self.assertEqual(headroom["click_gap_vs_baseline"], 180.0) # (0.28 - 0.10) * 1000 = 180
        self.assertIn("Scenario, not a forecast", headroom["interpretation"])

    def test_query_miner_intents(self):
        v = AutomotiveVertical()
        miner = QueryMiner(v)
        res = miner.parse_query("bajaj pulsar 125 price in delhi")
        self.assertEqual(res["primary_intent"], "pricing")
        self.assertEqual(res["location"], "delhi")

    def test_query_fit_and_cannibalization(self):
        fit_analyzer = QueryFitAnalyzer()
        verdict, _ = fit_analyzer.evaluate_fit(
            query_info={"primary_intent": "pricing"},
            landing_page={"url": "https://drivio.in/bikes/bajaj/pulsar-125", "page_type": "model"},
            ranking_position=3.0
        )
        self.assertEqual(verdict, "CORRECT_LANDING")

        # Test cannibalization
        rows = [
            {"query": "pulsar 125 emi", "page": "https://drivio.in/p1", "impressions": 1000, "position": 4.0},
            {"query": "pulsar 125 emi", "page": "https://drivio.in/p2", "impressions": 800, "position": 12.0}
        ]
        cannibals = fit_analyzer.detect_cannibalization(rows)
        self.assertEqual(len(cannibals), 1)
        self.assertEqual(cannibals[0]["query"], "pulsar 125 emi")

if __name__ == "__main__":
    unittest.main()
