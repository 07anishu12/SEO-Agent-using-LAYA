import time
import json
import sqlite3
import datetime
from typing import List, Dict, Any, Optional, Callable
from bs4 import BeautifulSoup
import httpx

class SiteWatcher:
    """
    Continuous site monitor for high-value pages.
    Detects critical regressions (accidental noindex, 404/500 spikes, title wipes, broken canonicals)
    against baseline snapshots.
    """
    def __init__(self, db_path: str = "data/seo.db", client: Optional[httpx.Client] = None):
        self.db_path = db_path
        self.client = client or httpx.Client(timeout=10.0, follow_redirects=True)

    def get_watch_targets(self, limit: int = 20) -> List[str]:
        """Loads critical URLs to monitor (top landing pages, homepage, high-inlink pages)."""
        urls = []
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            # Check query_page_map first
            rows = conn.execute("SELECT DISTINCT url FROM query_page_map ORDER BY impressions DESC LIMIT ?", (limit,)).fetchall()
            for r in rows:
                urls.append(r["url"])

            if not urls:
                # Fallback to pages table
                p_rows = conn.execute("SELECT url FROM pages ORDER BY in_links_count DESC LIMIT ?", (limit,)).fetchall()
                for r in p_rows:
                    urls.append(r["url"])

        return urls or ["https://example.com/"]

    def check_url(self, url: str) -> Dict[str, Any]:
        """Probes a single URL for live accessibility and SEO health."""
        start_t = time.perf_counter()
        issues = []
        try:
            resp = self.client.get(url)
            elapsed_ms = round((time.perf_counter() - start_t) * 1000, 1)
            status_code = resp.status_code
            html = resp.text
            soup = BeautifulSoup(html, "html.parser")

            if status_code >= 400:
                issues.append(f"HTTP error status {status_code}")

            meta_robots = ""
            m = soup.find("meta", attrs={"name": "robots"})
            if m:
                meta_robots = m.get("content", "")
            if "noindex" in meta_robots.lower():
                issues.append("Active noindex meta directive detected")

            title = soup.title.get_text(strip=True) if soup.title else ""
            if not title:
                issues.append("Title tag is missing or empty")

            c = soup.find("link", rel="canonical")
            canonical = c.get("href", "") if c else ""
            if not canonical:
                issues.append("Canonical tag missing")

            status = "HEALTHY" if not issues else "ALERT"

            return {
                "url": url,
                "status": status,
                "status_code": status_code,
                "response_time_ms": elapsed_ms,
                "title": title[:50],
                "canonical": canonical,
                "meta_robots": meta_robots,
                "issues": issues,
                "checked_at": datetime.datetime.now().isoformat()
            }
        except Exception as e:
            return {
                "url": url,
                "status": "ALERT",
                "status_code": 0,
                "response_time_ms": 0.0,
                "title": "",
                "canonical": "",
                "meta_robots": "",
                "issues": [f"Connection / fetch failure: {str(e)}"],
                "checked_at": datetime.datetime.now().isoformat()
            }

    def check_now(self, urls: Optional[List[str]] = None) -> Dict[str, Any]:
        """Runs an immediate verification sweep across target URLs."""
        target_urls = urls or self.get_watch_targets()
        results = []
        alerts_count = 0

        for u in target_urls:
            res = self.check_url(u)
            if res["status"] == "ALERT":
                alerts_count += 1
            results.append(res)

        return {
            "total_urls_checked": len(target_urls),
            "alerts_count": alerts_count,
            "overall_status": "HEALTHY" if alerts_count == 0 else "WARNING",
            "checked_at": datetime.datetime.now().isoformat(),
            "results": results
        }
