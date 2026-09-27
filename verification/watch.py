import time
import json
import sqlite3
import datetime
import hashlib
import urllib.parse
import xml.etree.ElementTree as ET
from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup
import httpx
from psycopg.types.json import Jsonb

from database.connection import get_connection


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
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                rows = conn.execute("SELECT DISTINCT url FROM query_page_map ORDER BY impressions DESC LIMIT ?", (limit,)).fetchall()
                for r in rows:
                    urls.append(r["url"])

                if not urls:
                    p_rows = conn.execute("SELECT url FROM pages ORDER BY in_links_count DESC LIMIT ?", (limit,)).fetchall()
                    for r in p_rows:
                        urls.append(r["url"])
        except Exception:
            pass

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


class WatchRunner:
    """
    Stage 9 Recurring Lightweight Watch Runner.
    Executes targeted lightweight health checks:
      1. robots.txt availability and disallow rules
      2. sitemap availability and URL drop detection
      3. top-page status codes (5xx/4xx), noindex leaks, and canonical changes
      4. template DOM structure drift
    Reuses existing SEOJEV critical regression classifications:
      - NOINDEX_LEAK (Critical)
      - CANONICAL_CHANGE (High)
      - STATUS_5XX_SPIKE (Critical)
      - SITEMAP_DROP (High)
      - ROBOTS_TXT_CHANGE / ROBOTS_TXT_BLOCKED (Critical/High)
      - TEMPLATE_DRIFT (Medium)
    """

    def __init__(self, db_url: Optional[str] = None, client: Optional[httpx.Client] = None):
        self.db_url = db_url
        self.client = client or httpx.Client(timeout=10.0, follow_redirects=True)

    def check_robots_txt(self, base_url: str) -> List[Dict[str, Any]]:
        """Probes robots.txt for accessibility and search-engine blocking directives."""
        alerts = []
        robots_url = urllib.parse.urljoin(base_url, "/robots.txt")
        try:
            resp = self.client.get(robots_url)
            if resp.status_code >= 500:
                alerts.append({
                    "alert_type": "STATUS_5XX_SPIKE",
                    "severity": "critical",
                    "title": "Robots.txt 5xx Server Error",
                    "message": f"Robots.txt returned HTTP {resp.status_code} at {robots_url}",
                    "affected_urls": [robots_url],
                    "current_value": f"HTTP {resp.status_code}",
                    "previous_value": "HTTP 200",
                    "details": {"status_code": resp.status_code, "url": robots_url}
                })
            elif resp.status_code == 404:
                alerts.append({
                    "alert_type": "ROBOTS_TXT_ERROR",
                    "severity": "medium",
                    "title": "Robots.txt Not Found (404)",
                    "message": f"Robots.txt returned HTTP 404 at {robots_url}",
                    "affected_urls": [robots_url],
                    "current_value": "HTTP 404",
                    "previous_value": "HTTP 200",
                    "details": {"status_code": 404, "url": robots_url}
                })
            elif resp.status_code == 200:
                content = resp.text
                lines = [line.strip() for line in content.splitlines()]
                current_agent = None
                disallow_all = False
                for line in lines:
                    if not line or line.startswith("#"):
                        continue
                    lower_line = line.lower()
                    if lower_line.startswith("user-agent:"):
                        current_agent = line.split(":", 1)[1].strip()
                    elif lower_line.startswith("disallow:") and current_agent in ("*", "googlebot"):
                        path = line.split(":", 1)[1].strip()
                        if path == "/":
                            disallow_all = True

                if disallow_all:
                    alerts.append({
                        "alert_type": "NOINDEX_LEAK",
                        "severity": "critical",
                        "title": "Robots.txt Blocking All Crawlers (Disallow: /)",
                        "message": f"Critical robots.txt rule 'Disallow: /' detected for '{current_agent or '*'}' at {robots_url}",
                        "affected_urls": [robots_url],
                        "current_value": "Disallow: /",
                        "previous_value": "Allow",
                        "details": {"rule": "Disallow: /", "user_agent": current_agent, "url": robots_url}
                    })
        except Exception as exc:
            alerts.append({
                "alert_type": "ROBOTS_TXT_ERROR",
                "severity": "high",
                "title": "Robots.txt Fetch Failed",
                "message": f"Connection error probing {robots_url}: {str(exc)}",
                "affected_urls": [robots_url],
                "current_value": str(exc),
                "previous_value": "reachable",
                "details": {"error": str(exc), "url": robots_url}
            })
        return alerts

    def check_sitemap(self, base_url: str, baseline_count: Optional[int] = None) -> List[Dict[str, Any]]:
        """Probes sitemap.xml for availability and URL drop regressions."""
        alerts = []
        sitemap_url = urllib.parse.urljoin(base_url, "/sitemap.xml")
        try:
            resp = self.client.get(sitemap_url)
            if resp.status_code >= 400:
                alerts.append({
                    "alert_type": "SITEMAP_DROP",
                    "severity": "high",
                    "title": "Sitemap Unreachable",
                    "message": f"Sitemap endpoint returned HTTP {resp.status_code} at {sitemap_url}",
                    "affected_urls": [sitemap_url],
                    "current_value": f"HTTP {resp.status_code}",
                    "previous_value": "HTTP 200",
                    "details": {"status_code": resp.status_code, "url": sitemap_url}
                })
            else:
                try:
                    # Count <loc> entries
                    root = ET.fromstring(resp.text)
                    locs = root.findall(".//{http://www.sitemaps.org/schemas/sitemap/0.9}loc")
                    if not locs:
                        locs = root.findall(".//loc")
                    url_count = len(locs)

                    if url_count == 0:
                        alerts.append({
                            "alert_type": "SITEMAP_DROP",
                            "severity": "high",
                            "title": "Sitemap URL Drop: 0 URLs",
                            "message": f"Sitemap XML at {sitemap_url} contains 0 URLs",
                            "affected_urls": [sitemap_url],
                            "current_value": "0 URLs",
                            "previous_value": f"{baseline_count or '>0'} URLs",
                            "details": {"url_count": 0, "url": sitemap_url}
                        })
                    elif baseline_count and baseline_count > 0 and url_count < (baseline_count * 0.8):
                        drop_pct = round(((baseline_count - url_count) / baseline_count) * 100, 1)
                        alerts.append({
                            "alert_type": "SITEMAP_DROP",
                            "severity": "high",
                            "title": f"Sitemap URL Count Dropped {drop_pct}%",
                            "message": f"Sitemap URL count dropped from {baseline_count} to {url_count} ({drop_pct}% drop)",
                            "affected_urls": [sitemap_url],
                            "current_value": f"{url_count} URLs",
                            "previous_value": f"{baseline_count} URLs",
                            "details": {"baseline_count": baseline_count, "current_count": url_count, "drop_pct": drop_pct}
                        })
                except ET.ParseError as pe:
                    alerts.append({
                        "alert_type": "SITEMAP_DROP",
                        "severity": "medium",
                        "title": "Sitemap XML Parse Error",
                        "message": f"Failed to parse XML sitemap at {sitemap_url}: {str(pe)}",
                        "affected_urls": [sitemap_url],
                        "current_value": "Malformed XML",
                        "previous_value": "Valid XML",
                        "details": {"error": str(pe), "url": sitemap_url}
                    })
        except Exception as exc:
            alerts.append({
                "alert_type": "SITEMAP_DROP",
                "severity": "high",
                "title": "Sitemap Connection Failed",
                "message": f"Connection error probing {sitemap_url}: {str(exc)}",
                "affected_urls": [sitemap_url],
                "current_value": str(exc),
                "previous_value": "reachable",
                "details": {"error": str(exc), "url": sitemap_url}
            })
        return alerts

    def check_top_pages(self, urls: List[str]) -> List[Dict[str, Any]]:
        """Probes high-value pages for 5xx/4xx errors, accidental noindex directives, and missing/changed canonicals."""
        alerts = []
        for url in urls:
            try:
                resp = self.client.get(url)
                status_code = resp.status_code
                if status_code >= 500:
                    alerts.append({
                        "alert_type": "STATUS_5XX_SPIKE",
                        "severity": "critical",
                        "title": f"5xx Server Error on {url}",
                        "message": f"Critical landing page returned HTTP {status_code}: {url}",
                        "affected_urls": [url],
                        "current_value": f"HTTP {status_code}",
                        "previous_value": "HTTP 200",
                        "details": {"status_code": status_code, "url": url}
                    })
                    continue
                elif status_code >= 400:
                    alerts.append({
                        "alert_type": "STATUS_4XX_ERROR",
                        "severity": "high",
                        "title": f"HTTP {status_code} Error on {url}",
                        "message": f"High-priority page returned HTTP {status_code}: {url}",
                        "affected_urls": [url],
                        "current_value": f"HTTP {status_code}",
                        "previous_value": "HTTP 200",
                        "details": {"status_code": status_code, "url": url}
                    })
                    continue

                # Check headers for X-Robots-Tag
                x_robots = resp.headers.get("x-robots-tag", "").lower()
                if "noindex" in x_robots:
                    alerts.append({
                        "alert_type": "NOINDEX_LEAK",
                        "severity": "critical",
                        "title": f"Noindex Directive Detected in HTTP Header on {url}",
                        "message": f"Page served with X-Robots-Tag containing noindex: {url}",
                        "affected_urls": [url],
                        "current_value": x_robots,
                        "previous_value": "index, follow",
                        "details": {"x_robots_tag": x_robots, "url": url}
                    })

                # Check HTML body
                soup = BeautifulSoup(resp.text, "html.parser")
                meta_robots = ""
                m = soup.find("meta", attrs={"name": "robots"})
                if m:
                    meta_robots = m.get("content", "")
                if "noindex" in meta_robots.lower() and "noindex" not in x_robots:
                    alerts.append({
                        "alert_type": "NOINDEX_LEAK",
                        "severity": "critical",
                        "title": f"Accidental noindex Meta Tag on {url}",
                        "message": f"HTML meta robots tag contains 'noindex' on critical page: {url}",
                        "affected_urls": [url],
                        "current_value": meta_robots,
                        "previous_value": "index, follow",
                        "details": {"meta_robots": meta_robots, "url": url}
                    })

                # Check canonical
                c_tag = soup.find("link", rel="canonical")
                canonical_href = (c_tag.get("href", "") if c_tag else "").strip()
                if not canonical_href:
                    alerts.append({
                        "alert_type": "CANONICAL_CHANGE",
                        "severity": "high",
                        "title": f"Canonical Tag Missing on {url}",
                        "message": f"Critical page is missing a self-referencing canonical tag: {url}",
                        "affected_urls": [url],
                        "current_value": "missing",
                        "previous_value": url,
                        "details": {"canonical": "", "url": url}
                    })

            except Exception as exc:
                alerts.append({
                    "alert_type": "STATUS_5XX_SPIKE",
                    "severity": "high",
                    "title": f"Connection Failure on {url}",
                    "message": f"Failed to fetch critical page {url}: {str(exc)}",
                    "affected_urls": [url],
                    "current_value": str(exc),
                    "previous_value": "accessible",
                    "details": {"error": str(exc), "url": url}
                })
        return alerts

    def check_template_drift(self, urls: List[str]) -> List[Dict[str, Any]]:
        """Detects structural DOM degradation or unexpected template collapse."""
        alerts = []
        for url in urls:
            try:
                resp = self.client.get(url)
                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.text, "html.parser")
                    tags = [tag.name for tag in soup.find_all()]
                    if len(tags) < 5:
                        alerts.append({
                            "alert_type": "TEMPLATE_DRIFT",
                            "severity": "medium",
                            "title": f"Template Structural Collapse on {url}",
                            "message": f"Page rendered only {len(tags)} DOM elements, indicating possible template failure: {url}",
                            "affected_urls": [url],
                            "current_value": f"{len(tags)} elements",
                            "previous_value": ">20 elements",
                            "details": {"element_count": len(tags), "url": url}
                        })
            except Exception:
                pass
        return alerts

    def persist_alerts(self, org_id: str, site_id: str, raw_alerts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Persists detected alerts into PostgreSQL alerts table idempotently using fingerprint deduplication."""
        persisted = []
        if not raw_alerts:
            return persisted

        now = datetime.datetime.now(datetime.timezone.utc)
        with get_connection(self.db_url) as conn:
            with conn.cursor() as cur:
                for a in raw_alerts:
                    alert_type = a.get("alert_type", "WATCH_ALERT")
                    severity = a.get("severity", "medium")
                    title = a.get("title", f"Alert: {alert_type}")
                    message = a.get("message", "")
                    affected = a.get("affected_urls", [])
                    details = a.get("details", {})
                    prev_val = a.get("previous_value")
                    curr_val = a.get("current_value")
                    source = a.get("source", "watch")

                    target_key = affected[0] if affected else "site"
                    fingerprint = hashlib.sha256(f"{site_id}:{alert_type}:{target_key}".encode("utf-8")).hexdigest()[:16]
                    alert_id = f"alert_{fingerprint}"

                    cur.execute(
                        """
                        INSERT INTO alerts (
                            id, org_id, site_id, alert_type, severity, title, message,
                            payload_json, source, fingerprint, affected_urls_json,
                            previous_value, current_value, status, detected_at
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'open', %s)
                        ON CONFLICT (id) DO UPDATE SET
                            message = EXCLUDED.message,
                            severity = EXCLUDED.severity,
                            title = EXCLUDED.title,
                            payload_json = EXCLUDED.payload_json,
                            affected_urls_json = EXCLUDED.affected_urls_json,
                            current_value = EXCLUDED.current_value,
                            previous_value = EXCLUDED.previous_value,
                            detected_at = EXCLUDED.detected_at,
                            status = 'open'
                        RETURNING id, org_id, site_id, alert_type, severity, title, message,
                                  payload_json, source, fingerprint, affected_urls_json,
                                  previous_value, current_value, status, detected_at;
                        """,
                        (
                            alert_id,
                            org_id,
                            site_id,
                            alert_type,
                            severity,
                            title,
                            message,
                            Jsonb(details),
                            source,
                            fingerprint,
                            Jsonb(affected),
                            prev_val,
                            curr_val,
                            now
                        )
                    )
                    row = cur.fetchone()
                    if row:
                        persisted.append(dict(row))
            conn.commit()
        return persisted

    def run_checks(
        self,
        site_id: str,
        org_id: str,
        checks: Optional[List[str]] = None,
        top_pages: Optional[List[str]] = None,
        base_url: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Runs configured lightweight checks and persists resulting alerts."""
        active_checks = set(checks or ["robots_txt", "sitemap", "top_pages", "template_drift"])
        target_base = base_url

        if not target_base or not top_pages:
            with get_connection(self.db_url) as conn:
                with conn.cursor() as cur:
                    if not target_base:
                        cur.execute("SELECT url FROM sites WHERE id = %s AND org_id = %s", (site_id, org_id))
                        s_row = cur.fetchone()
                        if s_row:
                            target_base = s_row["url"]
                    if not top_pages:
                        cur.execute(
                            "SELECT url FROM pages WHERE org_id = %s AND site_id = %s ORDER BY in_links_count DESC LIMIT 5",
                            (org_id, site_id)
                        )
                        p_rows = cur.fetchall()
                        if p_rows:
                            top_pages = [r["url"] for r in p_rows]

        target_base = target_base or "http://127.0.0.1:8000"
        pages_to_check = top_pages or [target_base]

        all_alerts = []
        if "robots_txt" in active_checks:
            all_alerts.extend(self.check_robots_txt(target_base))

        if "sitemap" in active_checks:
            all_alerts.extend(self.check_sitemap(target_base))

        if "top_pages" in active_checks:
            all_alerts.extend(self.check_top_pages(pages_to_check))

        if "template_drift" in active_checks:
            all_alerts.extend(self.check_template_drift(pages_to_check))

        persisted = self.persist_alerts(org_id=org_id, site_id=site_id, raw_alerts=all_alerts)
        return persisted
