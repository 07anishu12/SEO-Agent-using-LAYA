import unittest
from verticals.registry import VerticalRegistry
from verticals.automotive import AutomotiveVertical
from verticals.generic import GenericVertical
from verticals.ymyl_finance import YMYLFinanceOverlay
from extraction.provenance_extractor import ProvenanceExtractor

class DummyProfile:
    def __init__(self, domain: str, page_types: dict = None):
        self.domain = domain
        self.page_types = page_types or {}

class TestV3Verticals(unittest.TestCase):
    def test_vertical_registry_automotive_detection(self):
        reg = VerticalRegistry()
        prof = DummyProfile("www.drivio.in", {"model": 1500})
        v, score, overlays = reg.select_vertical(prof)
        self.assertEqual(v.name, "automotive")
        self.assertGreaterEqual(score, 0.90)

    def test_vertical_registry_generic_fallback(self):
        reg = VerticalRegistry()
        prof = DummyProfile("example-accounting-firm.org", {"article": 20})
        v, score, _ = reg.select_vertical(prof)
        self.assertEqual(v.name, "generic")

    def test_ymyl_finance_overlay(self):
        overlay = YMYLFinanceOverlay()
        prof = DummyProfile("loan.drivio.in", {"finance": 50})
        score = overlay.detect(prof)
        self.assertGreaterEqual(score, 0.85)

    def test_provenance_extractor_golden_fixture(self):
        with open("lab/fixtures/product_page_complete.html", "r", encoding="utf-8") as f:
            html = f.read()

        v = AutomotiveVertical()
        extractor = ProvenanceExtractor(v)
        attrs, profile = extractor.extract_with_provenance(html, "https://drivio.in/bajaj/pulsar-125")

        # Verify extracted attributes with provenance
        self.assertIsNotNone(attrs["price"]["value"])
        self.assertEqual(attrs["price"]["source_type"], "visible")
        self.assertIn("₹92,990", attrs["price"]["text_span"])

        self.assertIsNotNone(attrs["mileage"]["value"])
        self.assertEqual(attrs["mileage"]["value"], "51.4 kmpl")

        self.assertIsNotNone(attrs["engine_cc"]["value"])
        self.assertEqual(attrs["engine_cc"]["value"], "124.4 cc")

        # Verify 12-class ProductCoverageProfile
        self.assertEqual(profile["total_classes"], 12)
        self.assertGreater(profile["coverage_percentage"], 50.0)
        self.assertTrue(profile["classes"]["PRICE"]["present"])
        self.assertTrue(profile["classes"]["SPECIFICATIONS"]["present"])
        self.assertTrue(profile["classes"]["MILEAGE"]["present"])
        self.assertTrue(profile["classes"]["FAQ"]["present"])

if __name__ == "__main__":
    unittest.main()
