import unittest
from crawler.normalizer import URLNormalizer
from crawler.sitemap import SitemapParser

class TestSitemapParser(unittest.TestCase):
    def test_sitemap_url_extraction(self):
        normalizer = URLNormalizer("https://www.drivio.in/")
        parser = SitemapParser(normalizer)
        
        sample_xml = """<?xml version="1.0" encoding="UTF-8"?>
        <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
            <url>
                <loc>https://www.drivio.in/</loc>
                <lastmod>2026-09-01</lastmod>
            </url>
            <url>
                <loc>https://www.drivio.in/bikes/honda</loc>
            </url>
        </urlset>
        """
        discovered, _ = parser.parse_sitemap_content(sample_xml)
        self.assertEqual(len(discovered), 2)
        self.assertEqual(discovered[0], "https://www.drivio.in/")
        self.assertEqual(discovered[1], "https://www.drivio.in/bikes/honda")

if __name__ == "__main__":
    unittest.main()
