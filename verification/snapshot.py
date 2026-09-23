import os
import json
import hashlib
import sqlite3
import datetime
from typing import Dict, Any, List, Optional
from bs4 import BeautifulSoup

class SnapshotRecorder:
    """
    Captures complete state snapshots of URLs (title, canonical, robots, H1, schema, hashes)
    for pre/post deployment auditing and regression testing.
    """
    def __init__(self, db_path: str = "data/seo.db"):
        self.db_path = db_path

    def take_snapshot_for_url(
        self,
        run_id: str,
        url: str,
        page_data: Dict[str, Any],
        html_content: Optional[str] = None
    ) -> Dict[str, Any]:
        """Captures a snapshot for a single URL and persists it to SQLite."""
        norm_url = url.strip()
        soup = BeautifulSoup(html_content, "html.parser") if html_content else None

        title = page_data.get("title")
        if not title and soup and soup.title:
            title = soup.title.get_text(strip=True)

        canonical = page_data.get("canonical_url") or page_data.get("canonical")
        if not canonical and soup:
            c = soup.find("link", rel="canonical")
            if c:
                canonical = c.get("href")

        meta_robots = page_data.get("meta_robots")
        if not meta_robots and soup:
            m = soup.find("meta", attrs={"name": "robots"})
            if m:
                meta_robots = m.get("content")
        meta_robots = meta_robots or "index, follow"

        h1 = page_data.get("h1_text") or page_data.get("h1")
        if not h1 and soup:
            h1_tag = soup.find("h1")
            if h1_tag:
                h1 = h1_tag.get_text(strip=True)

        status_code = page_data.get("status_code", 200)

        # Compute content hash
        if html_content:
            content_hash = hashlib.sha256(html_content.encode("utf-8")).hexdigest()
        else:
            content_hash = page_data.get("content_hash", "")

        # Extract schema hash
        schema_types = []
        if soup:
            for s in soup.find_all("script", type="application/ld+json"):
                try:
                    data = json.loads(s.string or "{}")
                    items = data if isinstance(data, list) else [data]
                    for item in items:
                        if item.get("@type"):
                            schema_types.append(item.get("@type"))
                except Exception:
                    pass
        schema_str = ",".join(sorted(set(schema_types)))
        schema_hash = hashlib.sha256(schema_str.encode("utf-8")).hexdigest() if schema_str else ""

        metrics = {
            "word_count": page_data.get("word_count", 0),
            "in_links_count": page_data.get("in_links_count", 0),
            "out_links_count": page_data.get("out_links_count", 0),
            "load_time_ms": page_data.get("load_time", 0.0)
        }

        captured_at = datetime.datetime.now().isoformat()
        snapshot_id = f"SNAP-{hashlib.sha256(f'{run_id}|{norm_url}|{captured_at}'.encode()).hexdigest()[:12]}"

        record = {
            "snapshot_id": snapshot_id,
            "run_id": run_id,
            "url": norm_url,
            "title": title or "",
            "canonical": canonical or "",
            "meta_robots": meta_robots,
            "h1_text": h1 or "",
            "status_code": status_code,
            "schema_hash": schema_hash,
            "content_hash": content_hash,
            "metrics_json": json.dumps(metrics),
            "captured_at": captured_at
        }

        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
            INSERT OR REPLACE INTO snapshots (
                snapshot_id, run_id, url, title, canonical, meta_robots,
                h1_text, status_code, schema_hash, content_hash, metrics_json, captured_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                record["snapshot_id"], record["run_id"], record["url"], record["title"],
                record["canonical"], record["meta_robots"], record["h1_text"],
                record["status_code"], record["schema_hash"], record["content_hash"],
                record["metrics_json"], record["captured_at"]
            ))
            conn.commit()

        return record

    def take_snapshot_from_db(self, run_id: str, crawl_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Takes snapshots for all crawled pages currently in the pages table."""
        snapshots = []
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            query = "SELECT * FROM pages"
            params = []
            if crawl_id:
                query += " WHERE crawl_id = ?"
                params.append(crawl_id)
            rows = conn.execute(query, params).fetchall()

            for r in rows:
                p_data = dict(r)
                snap = self.take_snapshot_for_url(run_id, p_data["url"], p_data)
                snapshots.append(snap)

        return snapshots

    def get_snapshots_for_run(self, run_id: str) -> List[Dict[str, Any]]:
        """Retrieves all snapshots for a specific run ID."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("SELECT * FROM snapshots WHERE run_id = ?", (run_id,)).fetchall()
            return [dict(r) for r in rows]
