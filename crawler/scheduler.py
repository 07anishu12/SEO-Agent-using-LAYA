import asyncio
import time
from typing import Set, Tuple, Optional, Dict
from collections import deque

class CrawlScheduler:
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

        # Queues by priority: 0=seed/sitemap, 1=canonical, 2=internal_link
        self._sitemap_queue = deque()
        self._canonical_queue = deque()
        self._link_queue = deque()

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
        return len(self._sitemap_queue) + len(self._canonical_queue) + len(self._link_queue)

    def total_discovered(self) -> int:
        return len(self.discovered_urls)

    def enqueue(self, url: str, discovery_source: str = "internal_link", depth: int = 0) -> bool:
        """
        Enqueues URL if not already discovered. Returns True if added.
        """
        if url in self.discovered_urls:
            return False

        self.discovered_urls.add(url)

        item = (url, discovery_source, depth)
        if discovery_source in ("seed", "sitemap"):
            self._sitemap_queue.append(item)
        elif discovery_source == "canonical":
            self._canonical_queue.append(item)
        else:
            self._link_queue.append(item)

        return True

    def dequeue(self) -> Optional[Tuple[str, str, int]]:
        """Dequeues highest priority URL."""
        if not self.has_capacity():
            return None

        if self._sitemap_queue:
            return self._sitemap_queue.popleft()
        if self._canonical_queue:
            return self._canonical_queue.popleft()
        if self._link_queue:
            return self._link_queue.popleft()
        return None

    async def throttle(self):
        """Cooperative rate limiter."""
        if self.delay_seconds <= 0:
            return
        async with self._rate_lock:
            now = time.monotonic()
            elapsed = now - self._last_request_time
            if elapsed < self.delay_seconds:
                await asyncio.sleep(self.delay_seconds - elapsed)
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
