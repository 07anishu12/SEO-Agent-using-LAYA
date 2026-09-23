import unittest
from crawler.normalizer import URLNormalizer

class TestURLNormalizer(unittest.TestCase):
    def setUp(self):
        self.normalizer = URLNormalizer("https://www.drivio.in/")

    def test_domain_matching(self):
        self.assertTrue(self.normalizer.is_same_domain("https://www.drivio.in/bikes"))
        self.assertTrue(self.normalizer.is_same_domain("https://drivio.in/bikes"))
        self.assertTrue(self.normalizer.is_same_domain("/bikes/honda"))
        self.assertFalse(self.normalizer.is_same_domain("https://google.com"))
        self.assertFalse(self.normalizer.is_same_domain("https://example.com"))

    def test_strip_tracking_params(self):
        url = "https://www.drivio.in/bikes?utm_source=facebook&utm_medium=cpc&page=2"
        normalized = self.normalizer.normalize(url)
        self.assertEqual(normalized, "https://www.drivio.in/bikes?page=2")

    def test_strip_fragment(self):
        url = "https://www.drivio.in/bikes#specs"
        normalized = self.normalizer.normalize(url)
        self.assertEqual(normalized, "https://www.drivio.in/bikes")

    def test_duplicate_slashes(self):
        url = "https://www.drivio.in//bikes///honda/"
        normalized = self.normalizer.normalize(url)
        self.assertEqual(normalized, "https://www.drivio.in/bikes/honda")

    def test_media_extensions(self):
        self.assertFalse(self.normalizer.is_crawlable_page("https://www.drivio.in/image.jpg"))
        self.assertFalse(self.normalizer.is_crawlable_page("https://www.drivio.in/document.pdf"))
        self.assertTrue(self.normalizer.is_crawlable_page("https://www.drivio.in/bikes/activa"))

if __name__ == "__main__":
    unittest.main()
