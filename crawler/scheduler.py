import asyncio
import time
import heapq
from typing import Set, Tuple, Optional, Dict, List
from collections import deque
import urllib.parse

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
        self._host_queues: Dict[str, deque] = {}
        self._host_active: Dict[str, int] = {}
        self._host_max_concurrency: Dict[str, int] = {}
        self._dispatched: Set[str] = set()

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

    @property
    def crawled_count(self) -> int:
        return len(self.crawled_urls)

    @property
    def discovered_count(self) -> int:
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
        item = (url, discovery_source, depth)
        
        host = urllib.parse.urlsplit(url).netloc
        if host not in self._host_queues:
            self._host_queues[host] = deque()
        self._host_queues[host].append(item)
        
        # Store negative score so heapq behaves as max-heap
        heapq.heappush(self._priority_heap, (-score, self._seq, item))
        return True

    def requeue(self, item: Tuple[str, str, int]):
        """Re-enqueues an in-flight item when processing is interrupted or paused."""
        url, discovery_source, depth = item
        self._dispatched.discard(url)
        score = self.calculate_priority(discovery_source, depth)
        self._seq += 1
        heapq.heappush(self._priority_heap, (-score, self._seq, item))

    def mark_host_active(self, host: str):
        self._host_active[host] = self._host_active.get(host, 0) + 1

    def mark_host_done(self, host: str):
        if self._host_active.get(host, 0) > 0:
            self._host_active[host] -= 1

    def dequeue(self) -> Optional[Tuple[str, str, int]]:
        """Dequeues highest priority URL while respecting per-host active concurrency."""
        if not self.has_capacity():
            return None

        deferred = []
        try:
            # Check up to a bounded number of candidates to avoid thrashing the heap on busy hosts
            max_checks = min(len(self._priority_heap), max(self.concurrency, 20))
            for _ in range(max_checks):
                if not self._priority_heap:
                    break
                score, seq, item = heapq.heappop(self._priority_heap)
                url = item[0]
                if url in self._dispatched:
                    continue
                host = urllib.parse.urlsplit(url).netloc
                max_host_c = self._host_max_concurrency.get(host, min(self.concurrency, 40))
                if host and self._host_active.get(host, 0) >= max_host_c:
                    deferred.append((score, seq, item))
                    continue
                self._dispatched.add(url)
                return item
            return None
        finally:
            for d in deferred:
                heapq.heappush(self._priority_heap, d)

    async def throttle(self, multiplier: float = 1.0):
        """Cooperative non-blocking rate limiter respecting adaptive multiplier and concurrency."""
        actual_delay = self.delay_seconds * max(multiplier, 1.0)
        if actual_delay <= 0.001:
            return
        async with self._rate_lock:
            now = time.monotonic()
            target_time = max(now, self._last_request_time + (actual_delay / max(self.concurrency, 1)))
            wait_time = target_time - now
            self._last_request_time = target_time

        if wait_time > 0:
            await asyncio.sleep(wait_time)

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
