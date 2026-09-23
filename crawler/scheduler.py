import asyncio
import time
import heapq
from typing import Set, Tuple, Optional, Dict, List
from collections import deque

class CrawlScheduler:
    """Priority frontier scheduler with politeness rate limiting and adaptive throttling."""
    def __init__(
        self,
        max_pages: int = 5000,
        concurrency: int = 10,
        delay_seconds: float = 0.05
    ):
        self.max_pages = max_pages
        self.concurrency = concurrency
        self.delay_seconds = delay_seconds
        self.semaphore = asyncio.Semaphore(concurrency)

        # Priority min-heap storing (-priority_score, sequence_id, (url, discovery_source, depth))
        self._priority_heap: List[Tuple[float, int, Tuple[str, str, int]]] = []
        self._seq = 0

        self.discovered_urls: Set[str] = set()
        self.crawled_urls: Set[str] = set()
        self.failed_urls: Set[str] = set()
        self.skipped_urls: Set[str] = set()
        self.blocked_urls: Set[str] = set()

        self._last_request_time = 0.0
        self._rate_lock = asyncio.Lock()
        self._stop_event = asyncio.Event()

    def has_capacity(self) -> bool:
        return len(self.crawled_urls) + len(self.failed_urls) < self.max_pages

    def total_completed(self) -> int:
        return len(self.crawled_urls) + len(self.failed_urls)

    def total_queued(self) -> int:
        return len(self._priority_heap)

    def total_discovered(self) -> int:
        return len(self.discovered_urls)

    def calculate_priority(self, discovery_source: str, depth: int) -> float:
        """Calculates crawl priority score (higher is fetched sooner)."""
        base = 50.0
        if discovery_source in ("seed", "sitemap"):
            base = 100.0
        elif discovery_source == "canonical":
            base = 80.0
        
        # Prefer shallower pages
        depth_bonus = max(0, 10 - depth) * 2.0
        return base + depth_bonus

    def enqueue(self, url: str, discovery_source: str = "internal_link", depth: int = 0) -> bool:
        """Enqueues URL if not already discovered. Returns True if added."""
        if url in self.discovered_urls:
            return False

        self.discovered_urls.add(url)
        score = self.calculate_priority(discovery_source, depth)
        
        self._seq += 1
        # Store negative score so heapq behaves as max-heap
        heapq.heappush(self._priority_heap, (-score, self._seq, (url, discovery_source, depth)))
        return True

    def dequeue(self) -> Optional[Tuple[str, str, int]]:
        """Dequeues highest priority URL."""
        if not self.has_capacity():
            return None

        if self._priority_heap:
            _, _, item = heapq.heappop(self._priority_heap)
            return item
        return None

    async def throttle(self, multiplier: float = 1.0):
        """Cooperative rate limiter respecting adaptive multiplier."""
        actual_delay = self.delay_seconds * max(multiplier, 1.0)
        if actual_delay <= 0:
            return
        async with self._rate_lock:
            now = time.monotonic()
            elapsed = now - self._last_request_time
            if elapsed < actual_delay:
                await asyncio.sleep(actual_delay - elapsed)
            self._last_request_time = time.monotonic()

    def mark_crawled(self, url: str):
        self.crawled_urls.add(url)

    def mark_failed(self, url: str):
        self.failed_urls.add(url)

    def mark_skipped(self, url: str):
        self.skipped_urls.add(url)

    def mark_blocked(self, url: str):
        self.blocked_urls.add(url)

    def stop(self):
        self._stop_event.set()

    def is_stopped(self) -> bool:
        return self._stop_event.is_set()
