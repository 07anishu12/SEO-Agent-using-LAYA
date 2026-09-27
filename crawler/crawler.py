import asyncio
import datetime
import time
import signal
import sys
import os
import urllib.parse
from typing import List, Dict, Any, Optional
from rich.console import Console
from rich.live import Live
from rich.table import Table
from rich.panel import Panel

from models.crawl import CrawlRun, CrawlStats
from models.page import PageData
from .normalizer import URLNormalizer
from .storage import CrawlStorage
from .robots import RobotsParser
from .sitemap import SitemapParser
from .fetcher import AsyncFetcher
from .renderer import PlaywrightRenderer
from .scheduler import CrawlScheduler
from .traps import TrapDetector
from .soft404 import Soft404Detector
from engine.content_store import ContentStore
from engine.memory_guard import MemoryGuard
from seo.engine import SEOEngine
from analysis.page_types import infer_page_type
from analysis.templates import derive_template_id

class SEOCrawler:
    def __init__(
        self,
        target_url: str,
        crawl_id: str,
        storage: CrawlStorage,
        config: Dict[str, Any],
        render_enabled: bool = False,
        resume: bool = False,
        max_pages: Optional[int] = None,
        concurrency: Optional[int] = None,
        cancel_check: Optional[Any] = None,
        url_progress_callback: Optional[Any] = None,
        show_live_display: Optional[bool] = None
    ):
        self.target_url = target_url
        self.crawl_id = crawl_id
        self.storage = storage
        self.config = config
        self.resume = resume
        self.cancel_check = cancel_check
        self.url_progress_callback = url_progress_callback
        self.show_live_display = show_live_display if show_live_display is not None else sys.stdout.isatty()

        crawl_cfg = config.get("crawler", {})
        self.crawl_cfg = crawl_cfg
        self.max_pages = max_pages or crawl_cfg.get("max_pages", 5000)
        self.concurrency = concurrency or crawl_cfg.get("concurrency", 10)
        self.delay = crawl_cfg.get("delay", 0.05)
        self.render_enabled = render_enabled or config.get("render", {}).get("enabled", False)

        self.normalizer = URLNormalizer(target_url)
        self.robots = RobotsParser(target_url, user_agent=crawl_cfg.get("user_agent", "SEOJEV-Bot"))
        self.sitemap_parser = SitemapParser(self.normalizer)
        conn_limit = max(self.concurrency * 2, crawl_cfg.get("max_connections", 100))
        keepalive_limit = max(int(self.concurrency * 1.5), crawl_cfg.get("max_keepalive_connections", 80))
        self.fetcher = AsyncFetcher(
            user_agent=crawl_cfg.get("user_agent", "SEOJEV-Bot/1.0"),
            timeout=crawl_cfg.get("timeout", 15.0),
            max_retries=crawl_cfg.get("max_retries", 3),
            verify_ssl=crawl_cfg.get("verify_ssl", True),
            max_connections=conn_limit,
            max_keepalive_connections=keepalive_limit
        )
        self.renderer = PlaywrightRenderer() if self.render_enabled else None
        self.scheduler = CrawlScheduler(
            max_pages=self.max_pages,
            concurrency=self.concurrency,
            delay_seconds=self.delay
        )
        self.seo_engine = SEOEngine(self.normalizer)
        self.content_store = ContentStore(base_dir=config.get("storage", {}).get("store_dir", "store"))
        self.trap_detector = TrapDetector()
        self.soft404_detector = Soft404Detector()
        self.memory_guard = MemoryGuard(limit_mb=crawl_cfg.get("rss_limit_mb", 2048.0))

        self.start_time = 0.0
        self.console = Console()
        self.stats = CrawlStats()
        self._shutdown_requested = False
        self._redirect_map: Dict[str, str] = {}

        # Live stats
        self.total_issues_found = 0
        self.total_4xx = 0
        self.total_5xx = 0

    def _setup_signal_handlers(self):
        def _handle_signal(sig, frame):
            self.console.print("\n[bold yellow]Graceful shutdown requested. Wrapping up active tasks...[/bold yellow]")
            self._shutdown_requested = True
            self.scheduler.stop()

        try:
            signal.signal(signal.SIGINT, _handle_signal)
            signal.signal(signal.SIGTERM, _handle_signal)
        except Exception:
            pass

    async def initialize(self):
        """Fetch robots.txt and sitemap seeds, prepare initial queue."""
        self._setup_signal_handlers()
        client = await self.fetcher.get_client()

        # 1. Fetch robots.txt
        self.console.print(f"[cyan]Inspecting robots.txt at {self.target_url}...[/cyan]")
        await self.robots.fetch_and_parse(client)
        if self.robots.exists:
            self.console.print(f"[green]✓ robots.txt loaded ({len(self.robots.disallow_rules)} disallow rules, {len(self.robots.sitemaps)} sitemaps)[/green]")
        else:
            self.console.print("[yellow]Notice: No robots.txt detected or non-200 status.[/yellow]")

        # 2. Sitemap discovery
        sitemap_seeds = list(self.robots.sitemaps)
        if not sitemap_seeds:
            # Fallback to standard /sitemap.xml
            base = self.normalizer.normalize(self.target_url)
            sitemap_seeds.append(f"{self.target_url.rstrip('/')}/sitemap.xml")

        self.console.print(f"[cyan]Discovering URLs from sitemaps...[/cyan]")
        sitemap_urls, records = await self.sitemap_parser.discover_all(client, sitemap_seeds)
        self.console.print(f"[green]✓ Discovered {len(sitemap_urls)} URLs across {len(records)} sitemap file(s).[/green]")

        # 2.5 Probe site for soft 404 template signature
        self.console.print("[cyan]Probing 404 template signature...[/cyan]")
        await self.soft404_detector.probe_site(self.fetcher, self.target_url)
        if self.soft404_detector.probed:
            self.console.print("[green]✓ Soft-404 detector initialized with site fingerprint.[/green]")

        # 3. Add seed & sitemap URLs to scheduler and storage
        scope_urls = self.crawl_cfg.get("scope_urls") or []
        if scope_urls:
            url_tuples = []
            for s_url in scope_urls:
                norm_s = self.normalizer.normalize(s_url)
                if norm_s and self.scheduler.enqueue(norm_s, discovery_source="scope", depth=0):
                    url_tuples.append((norm_s, "queued", "scope", 0))
            if url_tuples:
                self.storage.add_urls(self.crawl_id, url_tuples)
            return

        seed_norm = self.normalizer.normalize(self.target_url)
        url_tuples = []

        if seed_norm:
            self.scheduler.enqueue(seed_norm, discovery_source="seed", depth=0)
            url_tuples.append((seed_norm, "queued", "seed", 0))

        for sm_url in sitemap_urls:
            is_trap, trap_type, trap_reason = self.trap_detector.is_trap(sm_url)
            if is_trap:
                self.trap_detector.record_quarantine(sm_url, trap_type, trap_reason)
                continue

            if self.robots.is_allowed(sm_url):
                if self.scheduler.enqueue(sm_url, discovery_source="sitemap", depth=1):
                    url_tuples.append((sm_url, "queued", "sitemap", 1))
            else:
                self.scheduler.mark_blocked(sm_url)
                url_tuples.append((sm_url, "blocked", "sitemap", 1))

        self.storage.add_urls(self.crawl_id, url_tuples)

        # If resume mode, load previously queued URLs from database
        if self.resume:
            crawled_db = self.storage.get_crawled_urls(self.crawl_id)
            for u in crawled_db:
                self.scheduler.discovered_urls.add(u)
                self.scheduler.crawled_urls.add(u)
            queued_db = self.storage.get_queued_urls(self.crawl_id, limit=self.max_pages)
            for u, src, d in queued_db:
                self.scheduler.enqueue(u, discovery_source=src, depth=d)
            self.console.print(f"[cyan]Resuming crawl: loaded {len(queued_db)} queued URLs from database ({len(crawled_db)} already crawled).[/cyan]")

    def _render_progress_panel(self) -> Panel:
        elapsed = max(time.monotonic() - self.start_time, 0.1)
        completed = self.scheduler.total_completed()
        rate = round(completed / elapsed, 1)

        discovered = self.scheduler.total_discovered()
        queued = self.scheduler.total_queued()
        failed = len(self.scheduler.failed_urls)
        crawled = len(self.scheduler.crawled_urls)

        remaining = min(discovered - completed, self.max_pages - completed)
        eta_sec = int(remaining / rate) if rate > 0 and remaining > 0 else 0
        eta_str = f"{eta_sec // 60}m {eta_sec % 60}s" if eta_sec > 0 else "0s"

        table = Table.grid(padding=(0, 2))
        table.add_column(style="bold cyan", justify="right")
        table.add_column(style="bold white")
        table.add_column(style="bold cyan", justify="right")
        table.add_column(style="bold white")

        table.add_row("Discovered:", f"{discovered:,}", "Crawled:", f"{crawled:,}")
        table.add_row("Queued:", f"{queued:,}", "Failed:", f"{failed:,}")
        table.add_row("4xx Client:", f"{self.total_4xx}", "5xx Server:", f"{self.total_5xx}")
        table.add_row("Rate:", f"{rate} pages/sec", "ETA:", eta_str)
        table.add_row("SEO Findings:", f"{self.total_issues_found:,}", "Concurreny:", f"{self.concurrency}")

        return Panel(table, title="[bold green]SEOJEV Engine Live Crawl Monitor[/bold green]", border_style="cyan")

    async def crawl(self):
        """Main async crawl loop with batch persistence and redirect alias tracking."""
        self.start_time = time.monotonic()
        busy_workers = 0

        batch_buffer: List[Dict[str, Any]] = []
        batch_lock = asyncio.Lock()
        BATCH_SIZE = 200

        async def queue_status(url: str, status: str):
            async with batch_lock:
                batch_buffer.append({"url_status": (url, status)})
            if len(batch_buffer) >= BATCH_SIZE:
                await flush_batch(force=False)

        async def flush_batch(force: bool = False):
            async with batch_lock:
                if not batch_buffer:
                    return
                if not force and len(batch_buffer) < BATCH_SIZE:
                    return
                items = list(batch_buffer)
                batch_buffer.clear()
            await asyncio.to_thread(self.storage.save_crawl_batch, self.crawl_id, items)

        async def process_item(item):
            nonlocal busy_workers
            busy_workers += 1
            try:
                if self.cancel_check and self.cancel_check():
                    self._shutdown_requested = True
                    self.scheduler.stop()
                    return

                url, discovery_source, depth = item

                # Check robots.txt
                if not self.robots.is_allowed(url):
                    self.scheduler.mark_blocked(url)
                    await queue_status(url, "blocked")
                    return

                # Check memory guard periodically
                # Check memory guard periodically
                self.memory_guard.check_and_enforce()

                # Redirect learning
                if url in self._redirect_map:
                    url = self._redirect_map[url]

                # Check trap detector before fetch
                is_trap, trap_type, trap_reason = self.trap_detector.is_trap(url)
                if is_trap:
                    self.trap_detector.record_quarantine(url, trap_type, trap_reason)
                    self.scheduler.mark_skipped(url)
                    await queue_status(url, "trap_quarantine")
                    return

                await self.scheduler.throttle(self.fetcher.adaptive_delay_multiplier)

                host = urllib.parse.urlsplit(url).netloc
                self.scheduler.mark_host_active(host)
                try:
                    # Fetch page via HTTP
                    fetch_res = await self.fetcher.fetch(url)
                finally:
                    self.scheduler.mark_host_done(host)

                if fetch_res.status_code >= 400:
                    if 400 <= fetch_res.status_code < 500:
                        self.total_4xx += 1
                    elif fetch_res.status_code >= 500:
                        self.total_5xx += 1

                # Dynamic host alias registration for cross-subdomain/domain redirects
                if fetch_res.final_url and fetch_res.final_url != url:
                    self._redirect_map[url] = fetch_res.final_url
                    try:
                        p_final = urllib.parse.urlsplit(fetch_res.final_url)
                        p_orig = urllib.parse.urlsplit(url)
                        if p_final.netloc and p_orig.netloc and p_final.netloc.lower() != p_orig.netloc.lower():
                            self.normalizer.add_host_alias(p_orig.netloc, canonical_host=p_final.netloc)
                    except Exception:
                        pass

                html_content = fetch_res.text
                is_rendered = False

                # Selective rendering check
                if self.render_enabled and self.renderer and fetch_res.status_code == 200:
                    if len(html_content) < 800 or '<div id="root"></div>' in html_content or '<div id="__next"></div>' in html_content:
                        render_res = await self.renderer.render_page(url)
                        if render_res.get("html"):
                            html_content = render_res["html"]
                            is_rendered = True

                # Content-addressed compression
                content_hash, raw_ref = await asyncio.to_thread(self.content_store.put, html_content)
                rendered_ref = ""
                if is_rendered:
                    _, rendered_ref = await asyncio.to_thread(self.content_store.put, html_content)

                # Deduce page type and template ID
                page_type = infer_page_type(url)
                template_id = derive_template_id(url, page_type)

                # Process SEO rules
                page_data, links, images, schemas, issues = await asyncio.to_thread(
                    self.seo_engine.process_page,
                    url=url,
                    final_url=fetch_res.final_url,
                    status_code=fetch_res.status_code,
                    content_type=fetch_res.content_type,
                    response_time=fetch_res.response_time,
                    content_length=fetch_res.content_length,
                    redirect_chain=fetch_res.redirect_chain,
                    headers=fetch_res.headers,
                    html=html_content,
                    discovery_source=discovery_source,
                    page_type=page_type,
                    template_id=template_id,
                    crawl_depth=depth,
                    is_rendered=is_rendered,
                    error=fetch_res.error
                )
                page_data.crawl_id = self.crawl_id
                page_data.content_hash = content_hash

                # Check for soft 404
                is_soft_404, soft_reason = self.soft404_detector.is_soft_404(
                    status_code=fetch_res.status_code,
                    html=html_content,
                    title=page_data.title,
                    h1=page_data.h1_text
                )
                if is_soft_404:
                    from models.issue import SEOIssue
                    issues.append(SEOIssue(
                        url=url,
                        page_type=page_type,
                        template=template_id,
                        category="technical",
                        issue="soft_404_response",
                        severity="critical",
                        evidence=f"Status 200 returned but page matches 404 criteria: {soft_reason}",
                        recommendation="Configure web server to return true HTTP 404 / 410 status code."
                    ))

                self.total_issues_found += len(issues)

                # Discover new internal links (skip if scoped crawl)
                new_url_tuples = []
                if not (self.crawl_cfg.get("scope_urls")):
                    for link in links:
                        if link.is_internal and self.normalizer.is_crawlable_page(link.target_url):
                            is_link_trap, trap_t, trap_r = self.trap_detector.is_trap(link.target_url)
                            if is_link_trap:
                                self.trap_detector.record_quarantine(link.target_url, trap_t, trap_r)
                                continue

                            normalized_target = self.normalizer.normalize(link.target_url)
                            if normalized_target and self.scheduler.enqueue(normalized_target, discovery_source="internal_link", depth=depth + 1):
                                new_url_tuples.append((normalized_target, "queued", "internal_link", depth + 1))

                new_status = "crawled" if (fetch_res.is_success and not is_soft_404) else "failed"
                if new_status == "crawled":
                    self.scheduler.mark_crawled(url)
                else:
                    self.scheduler.mark_failed(url)

                batch_entry = {
                    "page": page_data,
                    "fetch": {
                        "url": url,
                        "status_code": fetch_res.status_code,
                        "headers": fetch_res.headers,
                        "response_time": fetch_res.response_time,
                        "content_hash": content_hash,
                        "raw_store_ref": raw_ref,
                        "rendered_store_ref": rendered_ref,
                        "is_rendered": is_rendered
                    },
                    "links": links,
                    "images": images,
                    "schemas": schemas,
                    "issues": issues,
                    "url_status": (url, new_status),
                    "discovered_urls": new_url_tuples
                }

                async with batch_lock:
                    batch_buffer.append(batch_entry)

                if len(batch_buffer) >= BATCH_SIZE:
                    await flush_batch(force=False)

                if self.url_progress_callback:
                    try:
                        self.url_progress_callback(
                            self.scheduler.crawled_count,
                            self.scheduler.discovered_count,
                            url
                        )
                    except Exception:
                        pass

            except Exception as e:
                import traceback
                self.console.print(f"[bold red]Error in process_item: {e}[/bold red]")
                traceback.print_exc()
                if 'url' in locals():
                    self.scheduler.mark_failed(url)
            finally:
                busy_workers -= 1

        async def worker():
            while not self._shutdown_requested and self.scheduler.has_capacity():
                if self.cancel_check and self.cancel_check():
                    self._shutdown_requested = True
                    self.scheduler.stop()
                    break
                item = self.scheduler.dequeue()
                if item is None:
                    if busy_workers > 0:
                        await asyncio.sleep(0.05)
                        continue
                    else:
                        break
                await process_item(item)

        # Launch worker pool
        try:
            if self.show_live_display:
                with Live(self._render_progress_panel(), refresh_per_second=2, console=self.console) as live:
                    workers = [asyncio.create_task(worker()) for _ in range(self.concurrency)]

                    async def monitor():
                        while any(not w.done() for w in workers):
                            live.update(self._render_progress_panel())
                            await asyncio.sleep(0.5)
                        live.update(self._render_progress_panel())

                    monitor_task = asyncio.create_task(monitor())
                    await asyncio.gather(*workers, return_exceptions=True)
                    await monitor_task
            else:
                workers = [asyncio.create_task(worker()) for _ in range(self.concurrency)]
                await asyncio.gather(*workers, return_exceptions=True)
        finally:
            # Always flush remaining batch items to SQLite
            await flush_batch(force=True)

        if self.cancel_check and self.cancel_check():
            self.storage.update_crawl_status(self.crawl_id, "cancelled", datetime.datetime.now().isoformat())

        # Cleanup
        await self.fetcher.close()
        if self.renderer:
            await self.renderer.close()
