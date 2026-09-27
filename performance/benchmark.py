"""
SEOJEV Performance Benchmark Suite — measures crawler, signal, and Laya throughput.

Provides before/after comparison infrastructure for the architecture optimization.
Supports synthetic scale tests from 1K to 500K URLs.
"""
import asyncio
import json
import os
import psutil
import sqlite3
import time
from dataclasses import dataclass, field, asdict
from typing import Dict, Any, List, Optional


@dataclass
class BenchmarkResult:
    """Single benchmark measurement."""
    name: str = ""
    url_count: int = 0

    # Crawl metrics
    crawl_urls_per_sec: float = 0.0
    crawl_duration_sec: float = 0.0
    crawl_active_workers: int = 0
    crawl_http_latency_avg_ms: float = 0.0
    crawl_error_rate: float = 0.0
    crawl_429_count: int = 0
    crawl_5xx_count: int = 0
    crawl_redirect_count: int = 0

    # Signal metrics
    signal_urls_per_sec: float = 0.0
    signal_duration_sec: float = 0.0
    template_count: int = 0
    candidate_count: int = 0

    # Laya metrics
    laya_candidates: int = 0
    laya_decisions: int = 0
    laya_decisions_per_sec: float = 0.0
    laya_cache_hits: int = 0
    laya_cache_hit_rate: float = 0.0
    laya_queue_depth: int = 0
    laya_queue_wait_ms: float = 0.0
    laya_p50_ms: float = 0.0
    laya_p95_ms: float = 0.0
    laya_p99_ms: float = 0.0

    # Opportunity/Work order metrics
    opportunity_count: int = 0
    work_order_count: int = 0

    # System metrics
    cpu_percent: float = 0.0
    memory_mb: float = 0.0
    memory_peak_mb: float = 0.0
    sqlite_write_rate: float = 0.0

    # Timing
    total_duration_sec: float = 0.0
    timestamp: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, default=str)


class PerformanceObserver:
    """Lightweight performance observer that tracks system metrics during a run.

    Non-blocking, does not interfere with the crawl.
    """

    def __init__(self):
        self._start_time: float = 0.0
        self._samples: List[Dict[str, float]] = []
        self._peak_memory_mb: float = 0.0
        self._monitoring = False
        self._monitor_task: Optional[asyncio.Task] = None

    async def start(self):
        """Begin periodic system metric sampling."""
        self._start_time = time.monotonic()
        self._monitoring = True
        self._monitor_task = asyncio.create_task(self._sample_loop())

    async def stop(self) -> Dict[str, Any]:
        """Stop sampling and return summary."""
        self._monitoring = False
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass

        elapsed = time.monotonic() - self._start_time
        process = psutil.Process()
        current_mem = process.memory_info().rss / (1024 * 1024)

        return {
            "elapsed_sec": round(elapsed, 2),
            "cpu_percent": psutil.cpu_percent(interval=0.1),
            "memory_mb": round(current_mem, 1),
            "memory_peak_mb": round(self._peak_memory_mb, 1),
            "sample_count": len(self._samples)
        }

    async def _sample_loop(self):
        """Sample system metrics every 2 seconds."""
        process = psutil.Process()
        while self._monitoring:
            try:
                mem_mb = process.memory_info().rss / (1024 * 1024)
                cpu = process.cpu_percent()
                self._peak_memory_mb = max(self._peak_memory_mb, mem_mb)
                self._samples.append({
                    "time": round(time.monotonic() - self._start_time, 2),
                    "memory_mb": round(mem_mb, 1),
                    "cpu_percent": round(cpu, 1)
                })
            except Exception:
                pass
            await asyncio.sleep(2.0)


class BenchmarkRunner:
    """Runs SEOJEV benchmarks at multiple scale points and records results."""

    def __init__(self, output_dir: str = "data/benchmarks"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        self.results: List[BenchmarkResult] = []

    def record_result(self, result: BenchmarkResult):
        """Record and persist a benchmark result."""
        result.timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        self.results.append(result)

        # Append to results file
        results_file = os.path.join(self.output_dir, "benchmark_results.jsonl")
        with open(results_file, "a") as f:
            f.write(result.to_json() + "\n")

    def create_result_from_pipeline(
        self,
        name: str,
        url_count: int,
        pass_timings: Dict[str, float],
        stats: Any,
        laya_summary: Dict[str, Any],
        observer_data: Dict[str, Any]
    ) -> BenchmarkResult:
        """Create a BenchmarkResult from pipeline execution data."""
        crawl_time = pass_timings.get("P1_CRAWL", 0.0)
        signal_time = pass_timings.get("P2_SIGNALS", 0.0)
        total_time = sum(pass_timings.values())

        pages_crawled = getattr(stats, "urls_crawled", url_count) or url_count

        return BenchmarkResult(
            name=name,
            url_count=url_count,
            crawl_urls_per_sec=round(pages_crawled / max(crawl_time, 0.001), 2),
            crawl_duration_sec=crawl_time,
            signal_duration_sec=signal_time,
            signal_urls_per_sec=round(pages_crawled / max(signal_time, 0.001), 2),
            laya_candidates=laya_summary.get("total_candidates", 0),
            laya_decisions=laya_summary.get("total_decisions", 0),
            laya_decisions_per_sec=round(
                laya_summary.get("total_decisions", 0) / max(pass_timings.get("P4_CALIBRATION", 0.001), 0.001), 2
            ),
            laya_cache_hits=laya_summary.get("total_cache_hits", 0),
            laya_cache_hit_rate=round(
                laya_summary.get("total_cache_hits", 0) / max(laya_summary.get("total_decisions", 1), 1) * 100, 1
            ),
            laya_p50_ms=laya_summary.get("p50_ms", 0),
            laya_p95_ms=laya_summary.get("p95_ms", 0),
            laya_p99_ms=laya_summary.get("p99_ms", 0),
            cpu_percent=observer_data.get("cpu_percent", 0),
            memory_mb=observer_data.get("memory_mb", 0),
            memory_peak_mb=observer_data.get("memory_peak_mb", 0),
            total_duration_sec=total_time,
        )

    def print_comparison(self, before: BenchmarkResult, after: BenchmarkResult):
        """Print before/after comparison."""
        speedup_crawl = round(after.crawl_urls_per_sec / max(before.crawl_urls_per_sec, 0.001), 1)
        speedup_signal = round(after.signal_urls_per_sec / max(before.signal_urls_per_sec, 0.001), 1)
        speedup_total = round(before.total_duration_sec / max(after.total_duration_sec, 0.001), 1)

        print(f"""
╔══════════════════════════════════════════════════════════════╗
║                 SEOJEV BENCHMARK COMPARISON                  ║
╠══════════════════════════════════════════════════════════════╣
║                      BEFORE          AFTER       SPEEDUP     ║
╠══════════════════════════════════════════════════════════════╣
║ Crawler URLs/sec:   {before.crawl_urls_per_sec:>8.1f}      {after.crawl_urls_per_sec:>8.1f}      {speedup_crawl:>6.1f}x     ║
║ Signal URLs/sec:    {before.signal_urls_per_sec:>8.1f}      {after.signal_urls_per_sec:>8.1f}      {speedup_signal:>6.1f}x     ║
║ Total Duration:     {before.total_duration_sec:>8.1f}s     {after.total_duration_sec:>8.1f}s     {speedup_total:>6.1f}x     ║
║ Memory (peak MB):   {before.memory_peak_mb:>8.1f}      {after.memory_peak_mb:>8.1f}               ║
║ Laya Decisions/sec: {before.laya_decisions_per_sec:>8.1f}      {after.laya_decisions_per_sec:>8.1f}               ║
║ Laya Cache Hit %:   {before.laya_cache_hit_rate:>8.1f}      {after.laya_cache_hit_rate:>8.1f}               ║
╚══════════════════════════════════════════════════════════════╝
""")

    def print_summary(self):
        """Print summary of all recorded benchmarks."""
        print("\n" + "=" * 70)
        print("SEOJEV BENCHMARK RESULTS")
        print("=" * 70)
        for r in self.results:
            print(f"\n  {r.name} ({r.url_count:,} URLs)")
            print(f"    Crawler:  {r.crawl_urls_per_sec:.1f} URLs/sec  ({r.crawl_duration_sec:.1f}s)")
            print(f"    Signals:  {r.signal_urls_per_sec:.1f} URLs/sec  ({r.signal_duration_sec:.1f}s)")
            print(f"    Laya:     {r.laya_decisions} decisions  ({r.laya_decisions_per_sec:.1f}/sec)")
            print(f"    Memory:   {r.memory_mb:.0f} MB  (peak {r.memory_peak_mb:.0f} MB)")
            print(f"    Total:    {r.total_duration_sec:.1f}s")
        print("=" * 70)
