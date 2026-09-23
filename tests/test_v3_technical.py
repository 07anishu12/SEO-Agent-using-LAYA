import unittest
from technical.js_seo import JSSEOAnalyzer
from technical.root_causes import RootCauseClusterer
from analysis.aeo_v3 import AEOAnalyzerV3
from analysis.geo_v3 import GEOAnalyzerV3
from analysis.freshness_trust import FreshnessTrustAnalyzer
from verticals.automotive import AutomotiveVertical

class TestV3Technical(unittest.TestCase):
    def test_js_seo_analyzer(self):
        analyzer = JSSEOAnalyzer()
        raw = "<html><body><div id='root'></div></body></html>"
        rendered = "<html><head><link rel='canonical' href='https://drivio.in/p1' /></head><body><div id='root'><h1>Bajaj Pulsar</h1><p>Full specs content here...</p><a href='/p2'>Next</a></div></body></html>"

        res = analyzer.compare_raw_vs_rendered(raw, rendered, "https://drivio.in/p1")
        self.assertTrue(res["has_js_seo_risk"])
        self.assertEqual(res["verdict"], "JS SEO RISK")
        self.assertLess(res["content_visible_in_raw_ratio"], 0.35)

    def test_root_cause_clustering(self):
        clusterer = RootCauseClusterer()
        issues = [
            {"url": "https://drivio.in/dead", "issue": "http_404_error", "template": "tpl_news", "severity": "critical"},
            {"url": "https://drivio.in/dead", "issue": "missing_canonical", "template": "tpl_news", "severity": "medium"}, # downstream symptom
            {"url": "https://drivio.in/p2", "issue": "missing_meta_description", "template": "tpl_bikes", "severity": "low"}
        ]
        res = clusterer.cluster_root_causes(issues)
        self.assertEqual(res["suppressed_symptoms_count"], 1) # missing_canonical on 404 page suppressed
        self.assertEqual(res["root_cause_clusters_count"], 2)

    def test_aeo_analyzer_v3(self):
        v = AutomotiveVertical()
        analyzer = AEOAnalyzerV3(v)
        html = """
        <html><body>
        <h2>Frequently Asked Questions</h2>
        <h3>What is the on-road price of Bajaj Pulsar 125 in Delhi?</h3>
        <p>The Bajaj Pulsar 125 on-road price in Delhi is ₹1,08,500 including RTO and insurance.</p>
        <h3>What is the real-world mileage of Bajaj Pulsar 125?</h3>
        <p>The real-world mileage is 51.4 kmpl in city traffic conditions.</p>
        <h3>What are the available variants and prices of Bajaj Pulsar 125?</h3>
        <p>Available in Neon Single Seat (₹92,990) and Carbon Split Seat (₹98,400).</p>
        </body></html>
        """
        page_data = {"model": "Bajaj Pulsar 125", "schema_types": "Product, FAQPage"}
        res = analyzer.evaluate_aeo(html, page_data)
        self.assertGreater(res["aeo_readiness_score"], 40.0)
        self.assertGreaterEqual(res["extractable_answer_blocks_count"], 2)

    def test_geo_analyzer_v3(self):
        analyzer = GEOAnalyzerV3()
        page_data = {
            "title": "Bajaj Pulsar 125 Specifications and Price",
            "h1_text": "Bajaj Pulsar 125",
            "brand": "Bajaj",
            "model": "Pulsar 125",
            "schema_types": "Product, Organization"
        }
        res = analyzer.evaluate_geo(page_data, html="<table><tr><td>Engine</td><td>124.4 cc</td></tr></table>")
        self.assertEqual(res["label"], "STRUCTURAL GEO ANALYSIS")
        self.assertEqual(res["geo_readiness_score"], 100.0)
        self.assertEqual(res["readiness_level"], "High")

    def test_freshness_trust_analyzer(self):
        analyzer = FreshnessTrustAnalyzer()
        # Page with loan offer but no disclaimer
        page_data = {"title": "Apply for Two Wheeler Loan Online", "url": "https://drivio.in/loan"}
        html = "<p>Get your bike loan with low EMI starting ₹2,000/month. Instant approval.</p>"
        res = analyzer.evaluate(page_data, html)
        self.assertTrue(res["has_trust_findings"])
        types = [f["type"] for f in res["findings"]]
        self.assertIn("ymyl_missing_disclaimer", types)

if __name__ == "__main__":
    unittest.main()
