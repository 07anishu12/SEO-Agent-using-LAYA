import asyncio
import time
from typing import Optional, Dict, Any
from playwright.async_api import async_playwright, Browser, Playwright

class PlaywrightRenderer:
    def __init__(self, max_concurrent: int = 2, wait_timeout_ms: int = 12000):
        self.max_concurrent = max_concurrent
        self.wait_timeout_ms = wait_timeout_ms
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self._pw: Optional[Playwright] = None
        self._browser: Optional[Browser] = None
        self._lock = asyncio.Lock()

    async def _init_browser(self):
        async with self._lock:
            if self._browser is None:
                self._pw = await async_playwright().start()
                self._browser = await self._pw.chromium.launch(
                    headless=True,
                    args=["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"]
                )

    async def render_page(self, url: str) -> Dict[str, Any]:
        """
        Renders page using headless Chromium in a controlled pool.
        Returns rendered HTML, load duration, and performance timings.
        """
        await self._init_browser()
        async with self.semaphore:
            start_time = time.monotonic()
            context = None
            page = None
            try:
                context = await self._browser.new_context(
                    user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36 (SEOJEV/1.0)",
                    viewport={"width": 1280, "height": 800}
                )
                page = await context.new_page()

                # Navigate and wait for domcontentloaded
                resp = await page.goto(url, wait_until="domcontentloaded", timeout=self.wait_timeout_ms)
                status_code = resp.status if resp else 200

                # Brief idle wait for client-side hydration
                try:
                    await page.wait_for_load_state("networkidle", timeout=3000)
                except Exception:
                    pass

                rendered_html = await page.content()
                duration = time.monotonic() - start_time

                return {
                    "url": url,
                    "status_code": status_code,
                    "html": rendered_html,
                    "duration": round(duration, 3),
                    "error": None
                }
            except Exception as e:
                duration = time.monotonic() - start_time
                return {
                    "url": url,
                    "status_code": 0,
                    "html": "",
                    "duration": round(duration, 3),
                    "error": str(e)[:150]
                }
            finally:
                if page:
                    try:
                        await page.close()
                    except Exception:
                        pass
                if context:
                    try:
                        await context.close()
                    except Exception:
                        pass

    async def close(self):
        async with self._lock:
            if self._browser:
                try:
                    await self._browser.close()
                except Exception:
                    pass
                self._browser = None
            if self._pw:
                try:
                    await self._pw.stop()
                except Exception:
                    pass
                self._pw = None
