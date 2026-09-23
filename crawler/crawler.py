import asyncio
import time
import signal
import sys
import os
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
        concurrency: Optional[int] = None
    ):
        self.target_url = target_url
        self.crawl_id = crawl_id
        self.storage = storage
        self.config = config
        self.resume = resume

        crawl_cfg = config.get("crawler", {})
        self.max_pages = max_pages or crawl_cfg.get("max_pages", 5000)
        self.concurrency = concurrency or crawl_cfg.get("concurrency", 10)
        self.delay = crawl_cfg.get("delay", 0.05)
        self.render_enabled = render_enabled or config.get("render", {}).get("enabled", False)

        self.normalizer = URLNormalizer(target_url)
        self.robots = RobotsParser(target_url, user_agent=crawl_cfg.get("user_agent", "SEOJEV-Bot"))
        self.sitemap_parser = SitemapParser(self.normalizer)
        self.fetcher = AsyncFetcher(
            user_agent=crawl_cfg.get("user_agent", "SEOJEV-Bot/1.0"),
            timeout=crawl_cfg.get("timeout", 15.0),
            max_retries=crawl_cfg.get("max_retries", 3),
            verify_ssl=crawl_cfg.get("verify_ssl", True)
        )
        self.renderer = PlaywrightRenderer() if self.render_enabled else None
        self.scheduler = CrawlScheduler(
            max_pages=self.max_pages,
            concurrency=self.concurrency,
            delay_seconds=self.delay
        )
        self.seo_engine = SEOEngine(self.normalizer)

        self.start_time = 0.0
        self.console = Console()
        self.stats = CrawlStats()
        self._shutdown_requested = False

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

        # 3. Add seed & sitemap URLs to scheduler and storage
        seed_norm = self.normalizer.normalize(self.target_url)
        url_tuples = []

        if seed_norm:
            self.scheduler.enqueue(seed_norm, discovery_source="seed", depth=0)
            url_tuples.append((seed_norm, "queued", "seed", 0))

        for sm_url in sitemap_urls:
            if self.robots.is_allowed(sm_url):
                if self.scheduler.enqueue(sm_url, discovery_source="sitemap", depth=1):
                    url_tuples.append((sm_url, "queued", "sitemap", 1))
            else:
                self.scheduler.mark_blocked(sm_url)
                self.storage.update_url_status(self.crawl_id, sm_url, "blocked")

        self.storage.add_urls(self.crawl_id, url_tuples)

        # If resume mode, load previously queued URLs from database
        if self.resume:
            queued_db = self.storage.get_queued_urls(self.crawl_id, limit=self.max_pages)
            for u, src, d in queued_db:
                self.scheduler.enqueue(u, discovery_source=src, depth=d)
            self.console.print(f"[cyan]Resuming crawl: loaded {len(queued_db)} queued URLs from database.[/cyan]")

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
        """Main async crawl loop."""
        self.start_time = time.monotonic()
        active_workers = 0
        worker_tasks = set()

        async def worker():
            nonlocal active_workers
            while not self._shutdown_requested and self.scheduler.has_capacity():
                item = self.scheduler.dequeue()
                if item is None:
                    # Check if there are active workers still generating links
                    if active_workers > 1:
                        await asyncio.sleep(0.1)
                        continue
                    else:
                        break

                url, discovery_source, depth = item

                # Check robots.txt
                if not self.robots.is_allowed(url):
                    self.scheduler.mark_blocked(url)
                    self.storage.update_url_status(self.crawl_id, url, "blocked")
                    continue

                await self.scheduler.throttle()

                # Fetch page via HTTP
                fetch_res = await self.fetcher.fetch(url)

                if fetch_res.status_code >= 400:
                    if 400 <= fetch_res.status_code < 500:
                        self.total_4xx += 1
                    elif fetch_res.status_code >= 500:
                        self.total_5xx += 1

                html_content = fetch_res.text
                is_rendered = False

                # Selective rendering check
                if self.render_enabled and self.renderer and fetch_res.status_code == 200:
                    # If HTML is very thin or appears client-side rendered
                    if len(html_content) < 800 or '<div id="root"></div>' in html_content or '<div id="__next"></div>' in html_content:
                        render_res = await self.renderer.render_page(url)
                        if render_res.get("html"):
                            html_content = render_res["html"]
                            is_rendered = True

                # Deduce page type and template ID
                page_type = infer_page_type(url)
                template_id = derive_template_id(url, page_type)

                # Process SEO rules
                page_data, links, images, schemas, issues = self.seo_engine.process_page(
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

                self.total_issues_found += len(issues)

                # Persist results in SQLite
                self.storage.save_page(self.crawl_id, page_data)
                self.storage.save_links(self.crawl_id, links)
                self.storage.save_images(self.crawl_id, images)
                self.storage.save_schemas(self.crawl_id, schemas)
                self.storage.save_issues(self.crawl_id, issues)

                if fetch_res.is_success:
                    self.scheduler.mark_crawled(url)
                    self.storage.update_url_status(self.crawl_id, url, "crawled")
                else:
                    self.scheduler.mark_failed(url)
                    self.storage.update_url_status(self.crawl_id, url, "failed")

                # Discover new internal links
                new_url_tuples = []
                for link in links:
                    if link.is_internal and self.normalizer.is_crawlable_page(link.target_url):
                        if self.scheduler.enqueue(link.target_url, discovery_source="internal_link", depth=depth + 1):
                            new_url_tuples.append((link.target_url, "queued", "internal_link", depth + 1))

                if new_url_tuples:
                    self.storage.add_urls(self.crawl_id, new_url_tuples)

        # Launch worker pool
        with Live(self._render_progress_panel(), refresh_per_second=2, console=self.console) as live:
            workers = []
            for _ in range(self.concurrency):
                active_workers += 1
                w = asyncio.create_task(worker())
                workers.append(w)

            async def monitor():
                while any(not w.done() for w in workers):
                    live.update(self._render_progress_panel())
                    await asyncio.sleep(0.5)
                live.update(self._render_progress_panel())

            monitor_task = asyncio.create_task(monitor())
            await asyncio.gather(*workers, return_exceptions=True)
            await monitor_task

        # Cleanup
        await self.fetcher.close()
        if self.renderer:
            await self.renderer.close()
