import os
import tempfile
import json
import unittest
from search.serp_pipeline import SERPPipeline
from search.ai_observations import AIObservationsPipeline

class TestV3SERP(unittest.TestCase):
    def test_serp_pipeline_missing_data(self):
        pipe = SERPPipeline(serp_data_path=None)
        self.assertFalse(pipe.has_serp_data)
        opps = pipe.analyze_serp_feature_opportunities("bajaj pulsar price", {})
        self.assertEqual(opps[0]["status"], "SERP DATA REQUIRED")

    def test_serp_pipeline_with_data(self):
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
            json.dump({
                "bajaj pulsar 125 price": {
                    "features": ["faq", "product_snippets"],
                    "top_urls": ["https://bikewale.com/bajaj-pulsar-125"]
                }
            }, f)
            temp_path = f.name

        try:
            pipe = SERPPipeline(serp_data_path=temp_path)
            self.assertTrue(pipe.has_serp_data)
            opps = pipe.analyze_serp_feature_opportunities(
                "bajaj pulsar 125 price",
                {"schema_types": "WebPage"} # Missing FAQ and Product schema
            )
            self.assertEqual(len(opps), 2)
            features = [o["feature"] for o in opps]
            self.assertIn("FAQ Rich Snippet", features)
            self.assertIn("Product & Offer Snippet", features)
        finally:
            os.remove(temp_path)

    def test_attribute_presence_matrix(self):
        pipe = SERPPipeline()
        target_attrs = ["price", "mileage"]
        comp_attrs = {
            "bikewale.com": ["price", "mileage", "on_road_price", "variants"],
            "bikedekho.com": ["price", "mileage", "emi"]
        }
        matrix = pipe.build_attribute_presence_matrix("pulsar 125", target_attrs, comp_attrs)
        self.assertIn("on_road_price", matrix["attributes"])
        self.assertFalse(matrix["target_coverage"]["on_road_price"])
        self.assertTrue(matrix["competitors"]["bikewale.com"]["on_road_price"])

    def test_ai_observations_missing_and_template(self):
        ai_pipe = AIObservationsPipeline(observations_path=None)
        self.assertFalse(ai_pipe.has_observations)
        summary = ai_pipe.compute_summary()
        self.assertIn("AI OBSERVATIONS REQUIRED", summary["message"])

        queries = ai_pipe.generate_observation_query_template(["Bajaj Pulsar 125", "TVS Raider 125"])
        self.assertEqual(len(queries), 6)
        self.assertIn("What is the on-road price of Bajaj Pulsar 125 in Delhi?", queries)

if __name__ == "__main__":
    unittest.main()
