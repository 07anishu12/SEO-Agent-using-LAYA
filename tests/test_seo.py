import unittest
from crawler.normalizer import URLNormalizer
from seo.engine import SEOEngine

class TestSEOEngine(unittest.TestCase):
    def setUp(self):
        self.normalizer = URLNormalizer("https://www.drivio.in/")
        self.engine = SEOEngine(self.normalizer)

    def test_missing_title_and_h1(self):
        html = "<html><head></head><body><p>Hello world without headings or title tags.</p></body></html>"
        page, links, images, schemas, issues = self.engine.process_page(
            url="https://www.drivio.in/test",
            final_url="https://www.drivio.in/test",
            status_code=200,
            content_type="text/html",
            response_time=0.2,
            content_length=len(html),
            redirect_chain=[],
            headers={},
            html=html
        )
        issue_names = [i.issue for i in issues]
        self.assertIn("missing_title", issue_names)
        self.assertIn("missing_h1", issue_names)
        self.assertIn("missing_canonical_tag", issue_names)

    def test_valid_page(self):
        html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Honda Activa 6G On Road Price, Specs & Features | Drivio</title>
            <meta name="description" content="Check Honda Activa 6G on road price in India, mileage, specs, color options, variants and EMI offers only on Drivio.">
            <link rel="canonical" href="https://www.drivio.in/bikes/honda/activa-6g">
        </head>
        <body>
            <h1>Honda Activa 6G Price & Specs</h1>
            <h2>Key Specifications</h2>
            <p>The Honda Activa 6G is one of the highest selling scooters in India featuring a reliable 110cc engine.</p>
            <a href="/bikes/tvs/jupiter">Compare with TVS Jupiter</a>
            <img src="/img/activa.webp" alt="Honda Activa 6G Scooter" width="600" height="400">
        </body>
        </html>
        """
        page, links, images, schemas, issues = self.engine.process_page(
            url="https://www.drivio.in/bikes/honda/activa-6g",
            final_url="https://www.drivio.in/bikes/honda/activa-6g",
            status_code=200,
            content_type="text/html",
            response_time=0.3,
            content_length=len(html),
            redirect_chain=[],
            headers={},
            html=html
        )
        self.assertEqual(page.h1_count, 1)
        self.assertTrue(page.is_self_canonical)
        self.assertEqual(len(links), 1)
        self.assertEqual(len(images), 1)
        self.assertTrue(images[0].has_alt)

if __name__ == "__main__":
    unittest.main()
