import unittest
from understanding.template_miner import TemplateMiner
from understanding.programmatic import ProgrammaticFamilyAnalyzer
from understanding.entity_graph import EntityGraphEngine
from understanding.index_funnel import IndexFunnelReconciler
from understanding.profile import ProfileGenerator

class TestV3Understanding(unittest.TestCase):
    def test_template_miner(self):
        miner = TemplateMiner()
        sig1 = miner.extract_url_signature("https://drivio.in/bikes/bajaj/pulsar-125")
        sig2 = miner.extract_url_signature("https://drivio.in/bikes/tvs/raider-125")
        self.assertEqual(sig1, sig2)

        pages = [
            {"url": "https://drivio.in/bikes/bajaj/pulsar-125", "page_type": "model"},
            {"url": "https://drivio.in/bikes/tvs/raider-125", "page_type": "model"},
            {"url": "https://drivio.in/about", "page_type": "legal"}
        ]
        clusters = miner.cluster_pages(pages)
        self.assertGreaterEqual(len(clusters), 2)

    def test_programmatic_family_analyzer(self):
        analyzer = ProgrammaticFamilyAnalyzer()
        pages = [
            {"url": f"https://drivio.in/bikes/pulsar-125/{city}", "word_count": 250}
            for city in ["delhi", "mumbai", "bangalore", "chennai", "hyderabad", "pune"]
        ]
        families = analyzer.detect_families(pages)
        self.assertEqual(len(families), 1)
        self.assertEqual(families[0]["verdict"], "consolidate") # Thin token swap
        self.assertEqual(families[0]["cells_present"], 6)

    def test_entity_graph_engine_aliases_and_contradictions(self):
        graph = EntityGraphEngine()
        graph.register_entity("ent_pulsar_125", "Bajaj Pulsar 125", "model", ["Pulsar 125", "pulsar-125-neon"])

        # 1. Alias equivalence: brand prefix absent/present should be recognized as alias
        self.assertTrue(graph.are_aliases("Bajaj Pulsar 125", "Pulsar 125"))
        self.assertTrue(graph.are_aliases("pulsar 125", "bajaj pulsar 125"))

        # 2. Contradiction between Title and H1
        issues = graph.evaluate_page_consistency(
            url="https://drivio.in/test",
            title="Thunder 250 Price and Specs",
            h1="Blaze 125 Scooter"
        )
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0]["issue_type"], "entity_conflict_title_h1")

        # 3. Price fact contradiction
        issues_price = graph.evaluate_page_consistency(
            url="https://drivio.in/test",
            title="Bajaj Pulsar 125 Price",
            h1="Bajaj Pulsar 125",
            visible_price="₹92,990",
            schema_price="150000"
        )
        self.assertEqual(len(issues_price), 1)
        self.assertEqual(issues_price[0]["issue_type"], "cross_source_price_mismatch")

    def test_index_funnel_reconciler(self):
        reconciler = IndexFunnelReconciler()
        sitemaps = {"https://drivio.in/p1", "https://drivio.in/p2", "https://drivio.in/p3"}
        pages = [
            {"url": "https://drivio.in/p1", "status_code": 200, "is_indexable": 1},
            {"url": "https://drivio.in/p2", "status_code": 200, "is_indexable": 0},
            {"url": "https://drivio.in/p4", "status_code": 200, "is_indexable": 1} # Linked but not in sitemap
        ]
        gsc = {
            "https://drivio.in/p1": {"impressions": 100, "clicks": 5}
        }
        res = reconciler.build_funnel(sitemaps, pages, gsc)
        self.assertEqual(len(res["funnel_stages"]), 6)
        self.assertEqual(res["mismatches"]["in_sitemap_non_indexable_count"], 1)
        self.assertEqual(res["mismatches"]["linked_not_in_sitemap_count"], 1)

    def test_profile_generator(self):
        gen = ProfileGenerator()
        pages = [
            {"url": "https://drivio.in/", "page_type": "homepage", "is_indexable": 1},
            {"url": "https://drivio.in/bikes", "page_type": "listing", "is_indexable": 1}
        ]
        profile = gen.generate_profile("https://drivio.in/", pages, sitemap_urls_count=10)
        self.assertEqual(profile.domain, "drivio.in")
        self.assertEqual(profile.indexability_ratio_pct, 100.0)

if __name__ == "__main__":
    unittest.main()
