import unittest
from analysis.gsc import GSCAnalyzer
from analysis.product_intelligence import ProductIntelligenceEngine
from analysis.aeo import AEOAnalyzer
from analysis.geo import GEOAnalyzer
from analysis.aggregation import build_issue_clusters

class TestV2Intelligence(unittest.TestCase):
    def test_gsc_analyzer_without_file(self):
        gsc = GSCAnalyzer()
        self.assertFalse(gsc.has_data)
        self.assertIsNone(gsc.get_page_ranking_data("https://www.drivio.in/bikes/tvs/raider-125"))

    def test_product_intelligence_extraction(self):
        engine = ProductIntelligenceEngine()
        page_data = {
            "url": "https://www.drivio.in/bikes/tvs/raider-125",
            "title": "TVS Raider 125 Price, Mileage, Specs & Features | Drivio",
            "h1_text": "TVS Raider 125 Price & Specifications",
            "page_type": "model",
            "template_id": "tpl_model_3seg",
            "images_count": 4,
            "schema_types": ["Product", "Offer"]
        }
        mock_html = """
        <html><body>
            <p>The TVS Raider 125 is powered by a 124.8 cc engine producing 11.38 bhp and 11.2 Nm of torque.</p>
            <p>Certified mileage is 67 kmpl with a 5-speed manual gearbox.</p>
            <p>Ex-showroom price starts from ₹95,219 with on-road price around ₹1.12 Lakh. EMI starts from ₹2,850/mo.</p>
            <div class="variant">Drum Brake</div>
            <div class="variant">Disc Brake</div>
            <details><summary>What is the mileage of TVS Raider?</summary>67 kmpl under test conditions.</details>
        </body></html>
        """
        prod = engine.extract_product_intelligence(page_data, mock_html)
        self.assertEqual(prod.brand, "Tvs")
        self.assertIn("Raider", prod.model)
        self.assertEqual(prod.specs.engine_cc, "124.8 cc")
        self.assertIn("67 kmpl", prod.specs.mileage)
        self.assertIn("₹", prod.price_str)
        self.assertTrue(prod.coverage_score_pct > 30.0)

    def test_aeo_and_geo(self):
        engine = ProductIntelligenceEngine()
        page_data = {
            "url": "https://www.drivio.in/bikes/tvs/raider-125",
            "title": "TVS Raider 125 Price, Mileage & Specs",
            "h1_text": "TVS Raider 125",
            "page_type": "model",
            "template_id": "tpl_model_3seg",
            "schema_types": ["Product"]
        }
        prod = engine.extract_product_intelligence(page_data, "<p>124 cc engine with 67 kmpl mileage and ₹95,000 price.</p>")
        
        aeo = AEOAnalyzer().evaluate_page(page_data, prod)
        geo = GEOAnalyzer().evaluate_page(page_data, prod)

        self.assertIn("aeo_readiness_score", aeo)
        self.assertIn("geo_readiness_score", geo)
        self.assertTrue(aeo["aeo_readiness_score"] > 0)
        self.assertTrue(geo["geo_readiness_score"] > 0)

    def test_issue_clustering_stops_explosion(self):
        # 100 separate issues for the same missing description
        issues = [
            {"issue": "missing_meta_description", "category": "metadata", "severity": "medium", "template": "tpl_model", "url": f"https://www.drivio.in/bikes/model-{i}"}
            for i in range(100)
        ]
        # plus 50 duplicate titles
        issues.extend([
            {"issue": "duplicate_title_tag", "category": "duplicates", "severity": "medium", "template": "tpl_listing", "url": f"https://www.drivio.in/listing-{i}"}
            for i in range(50)
        ])
        
        clusters = build_issue_clusters(issues)
        # Should consolidate into exactly 2 clusters instead of 150 independent issues!
        self.assertEqual(len(clusters), 2)
        desc_cluster = next(c for c in clusters if c["issue"] == "missing_meta_description")
        self.assertEqual(desc_cluster["affected_urls_count"], 100)
        self.assertEqual(desc_cluster["primary_affected_template"], "tpl_model")
        self.assertLessEqual(len(desc_cluster["sample_urls"]), 8)

if __name__ == "__main__":
    unittest.main()
