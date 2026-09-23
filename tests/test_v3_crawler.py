import unittest
from crawler.traps import TrapDetector
from crawler.soft404 import Soft404Detector
from crawler.scheduler import CrawlScheduler
from crawler.logs import ServerLogAnalyzer
from engine.memory_guard import MemoryGuard

class TestV3Crawler(unittest.TestCase):
    def test_trap_detector(self):
        detector = TrapDetector(max_facet_params=3, max_pagination_depth=50)

        # 1. Normal URL
        is_t, _, _ = detector.is_trap("https://drivio.in/bikes/bajaj/pulsar-125")
        self.assertFalse(is_t)

        # 2. Session ID
        is_t, ttype, _ = detector.is_trap("https://drivio.in/bikes/bajaj?jsessionid=abc12345")
        self.assertTrue(is_t)
        self.assertEqual(ttype, "session_id")

        # 3. Calendar trap
        is_t, ttype, _ = detector.is_trap("https://drivio.in/events/2026/09/24/daily-rides")
        self.assertTrue(is_t)
        self.assertEqual(ttype, "calendar_trap")

        # 4. Faceted parameter explosion (>3 facet params)
        is_t, ttype, _ = detector.is_trap("https://drivio.in/bikes?color=red&sort=price&filter=abs&facet=commuter")
        self.assertTrue(is_t)
        self.assertEqual(ttype, "parameter_explosion")

        # 5. Excessive pagination
        is_t, ttype, _ = detector.is_trap("https://drivio.in/bikes?page=150")
        self.assertTrue(is_t)
        self.assertEqual(ttype, "infinite_pagination")

        # 6. Repeating path loop
        is_t, ttype, _ = detector.is_trap("https://drivio.in/bikes/pulsar/bikes/pulsar/bikes/pulsar")
        self.assertTrue(is_t)
        self.assertEqual(ttype, "repeating_path")

    def test_soft404_detector(self):
        detector = Soft404Detector()

        # Thin HTML shell
        is_s, reason = detector.is_soft_404(200, "<html><body>Hello</body></html>")
        self.assertTrue(is_s)
        self.assertIn("Thin HTML shell", reason)

        # Substantive page with explicit 404 title
        html = "<html><body>" + ("<p>Automotive vehicle specifications content</p>" * 20) + "</body></html>"
        is_s, reason = detector.is_soft_404(200, html, title="404 Not Found - Drivio")
        self.assertTrue(is_s)
        self.assertIn("Explicit 404 indicator", reason)

        # Valid normal page
        is_s, _ = detector.is_soft_404(200, html, title="Bajaj Pulsar 125 Specs & Price")
        self.assertFalse(is_s)

    def test_scheduler_priority_scoring(self):
        scheduler = CrawlScheduler(max_pages=10)

        # Enqueue in reverse priority order
        scheduler.enqueue("https://drivio.in/deep-link", discovery_source="internal_link", depth=5)
        scheduler.enqueue("https://drivio.in/shallow-link", discovery_source="internal_link", depth=1)
        scheduler.enqueue("https://drivio.in/sitemap-page", discovery_source="sitemap", depth=1)
        scheduler.enqueue("https://drivio.in/seed-home", discovery_source="seed", depth=0)

        # Dequeue should return sitemap/seed first (highest priority)
        first = scheduler.dequeue()
        self.assertIn(first[0], ("https://drivio.in/seed-home", "https://drivio.in/sitemap-page"))

        second = scheduler.dequeue()
        self.assertIn(second[0], ("https://drivio.in/seed-home", "https://drivio.in/sitemap-page"))

        # Then shallow link before deep link
        third = scheduler.dequeue()
        self.assertEqual(third[0], "https://drivio.in/shallow-link")

        fourth = scheduler.dequeue()
        self.assertEqual(fourth[0], "https://drivio.in/deep-link")

    def test_memory_guard(self):
        guard = MemoryGuard(limit_mb=2048.0)
        current = guard.get_current_rss_mb()
        self.assertGreater(current, 0.0)
        self.assertTrue(guard.check_and_enforce())

if __name__ == "__main__":
    unittest.main()
