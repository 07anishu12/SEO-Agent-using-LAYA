import unittest
from simulation.link_graph import EnrichedLinkGraph
from simulation.recommender import GroundedLinkRecommender
from simulation.graph_simulator import GraphSimulator
from analysis.content_gaps_v3 import ContentGapEngineV3
from verticals.automotive import AutomotiveVertical

class TestV3Simulation(unittest.TestCase):
    def test_enriched_link_graph(self):
        graph = EnrichedLinkGraph(target_url="https://drivio.in")
        pages = [
            {"url": "https://drivio.in", "page_type": "homepage"},
            {"url": "https://drivio.in/bikes", "page_type": "listing"},
            {"url": "https://drivio.in/bikes/pulsar", "page_type": "model"}
        ]
        links = [
            {"source_url": "https://drivio.in", "target_url": "https://drivio.in/bikes", "is_internal": 1, "dom_region": "nav"},
            {"source_url": "https://drivio.in/bikes", "target_url": "https://drivio.in/bikes/pulsar", "is_internal": 1, "dom_region": "body"}
        ]
        graph.build_graph(pages, links)
        metrics = graph.compute_metrics()

        self.assertIn("https://drivio.in/bikes/pulsar", metrics)
        self.assertEqual(metrics["https://drivio.in/bikes/pulsar"]["inbound_links_total"], 1)
        self.assertEqual(metrics["https://drivio.in/bikes/pulsar"]["inbound_contextual"], 1)
        self.assertEqual(metrics["https://drivio.in/bikes/pulsar"]["click_depth"], 2)

    def test_grounded_recommender(self):
        recommender = GroundedLinkRecommender(max_links_per_source=2)
        pages = [
            {"url": "https://drivio.in/bikes/bajaj", "page_type": "brand", "title": "Bajaj Bikes Catalog Pulsar and Avenger", "h1_text": "Bajaj Motorcycles"},
            {"url": "https://drivio.in/bikes/bajaj/pulsar-125", "page_type": "model"}
        ]
        graph_metrics = {
            "https://drivio.in/bikes/bajaj/pulsar-125": {"inbound_links_total": 1, "click_depth": 3, "pagerank": 0.001}
        }
        product_pages = [
            {"url": "https://drivio.in/bikes/bajaj/pulsar-125", "brand": "Bajaj", "model": "Pulsar 125"}
        ]
        recs = recommender.recommend_links(pages, graph_metrics, product_pages)
        self.assertEqual(len(recs), 1)
        self.assertEqual(recs[0]["source_url"], "https://drivio.in/bikes/bajaj")
        self.assertEqual(recs[0]["target_url"], "https://drivio.in/bikes/bajaj/pulsar-125")
        self.assertEqual(recs[0]["recommended_anchor"], "Bajaj Pulsar 125")

    def test_graph_simulator(self):
        graph = EnrichedLinkGraph(target_url="https://drivio.in")
        pages = [
            {"url": "https://drivio.in", "page_type": "homepage"},
            {"url": "https://drivio.in/bikes", "page_type": "listing"},
            {"url": "https://drivio.in/orphan-bike", "page_type": "model"}
        ]
        links = [
            {"source_url": "https://drivio.in", "target_url": "https://drivio.in/bikes", "is_internal": 1, "dom_region": "nav"}
        ]
        graph.build_graph(pages, links)
        simulator = GraphSimulator()

        recs = [{
            "source_url": "https://drivio.in/bikes",
            "target_url": "https://drivio.in/orphan-bike"
        }]
        res = simulator.simulate_impact(graph.graph, recs, root_url="https://drivio.in")

        self.assertEqual(res["simulation_label"], "Internal Site Graph Impact")
        self.assertEqual(res["orphans_resolved"], 1)
        self.assertEqual(res["edges_added"], 1)

    def test_content_gaps_v3(self):
        v = AutomotiveVertical()
        engine = ContentGapEngineV3(v)
        prod = {"brand": "Bajaj", "model": "Pulsar 125"}
        coverage = {
            "classes": {
                "PRICE": {"present": False},
                "VARIANTS": {"present": False},
                "SPECIFICATIONS": {"present": True},
                "FAQ": {"present": False}
            }
        }
        gaps = engine.analyze_gaps(prod, coverage)
        self.assertGreaterEqual(len(gaps), 3)
        self.assertEqual(gaps[0]["section_name"], "On-Road Price Breakdown")
        self.assertEqual(gaps[0]["format"], "table")

if __name__ == "__main__":
    unittest.main()
