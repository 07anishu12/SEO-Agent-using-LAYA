import unittest
import asyncio
from crawler.scheduler import CrawlScheduler
from crawler.storage import CrawlStorage

class TestCrawlerScheduler(unittest.TestCase):
    def test_queue_and_deduplication(self):
        scheduler = CrawlScheduler(max_pages=10)
        self.assertTrue(scheduler.enqueue("https://www.drivio.in/", "seed", 0))
        # Duplicate enqueue should return False
        self.assertFalse(scheduler.enqueue("https://www.drivio.in/", "seed", 0))
        self.assertTrue(scheduler.enqueue("https://www.drivio.in/bikes", "internal_link", 1))

        item = scheduler.dequeue()
        self.assertIsNotNone(item)
        self.assertEqual(item[0], "https://www.drivio.in/")

if __name__ == "__main__":
    unittest.main()
