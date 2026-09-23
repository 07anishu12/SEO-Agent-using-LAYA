import sqlite3
import json
import os
import threading
from typing import List, Dict, Any, Optional, Tuple
from models.page import PageData, LinkItem, ImageItem, SchemaItem
from models.issue import SEOIssue
from models.crawl import CrawlRun, CrawlStats

class CrawlStorage:
    def __init__(self, db_path: str = "data/seo.db"):
        self.db_path = db_path
        os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
        self._lock = threading.Lock()
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        return conn

    def _init_db(self):
        with self._lock, self._get_connection() as conn:
            conn.executescript("""
            CREATE TABLE IF NOT EXISTS crawl_runs (
                crawl_id TEXT PRIMARY KEY,
                target_url TEXT NOT NULL,
                start_time TEXT NOT NULL,
                end_time TEXT,
                status TEXT NOT NULL,
                max_pages INTEGER,
                concurrency INTEGER,
                config_json TEXT
            );

            CREATE TABLE IF NOT EXISTS urls (
                crawl_id TEXT NOT NULL,
                url TEXT NOT NULL,
                status TEXT NOT NULL, -- discovered, queued, crawled, failed, skipped, blocked
                discovery_source TEXT,
                depth INTEGER DEFAULT 0,
                discovered_at TEXT,
                visited_at TEXT,
                PRIMARY KEY (crawl_id, url)
            );
            CREATE INDEX IF NOT EXISTS idx_urls_status ON urls (crawl_id, status);

            CREATE TABLE IF NOT EXISTS pages (
                crawl_id TEXT NOT NULL,
                url TEXT NOT NULL,
                final_url TEXT,
                status_code INTEGER,
                content_type TEXT,
                response_time REAL,
                content_length INTEGER,
                redirect_chain TEXT,
                title TEXT,
                title_length INTEGER,
                title_word_count INTEGER,
                description TEXT,
                description_length INTEGER,
                h1_count INTEGER,
                h1_text TEXT,
                h2_count INTEGER,
                h3_count INTEGER,
                meta_robots TEXT,
                x_robots_tag TEXT,
                is_indexable INTEGER,
                is_follow INTEGER,
                canonical TEXT,
                canonical_status TEXT,
                is_self_canonical INTEGER,
                word_count INTEGER,
                paragraph_count INTEGER,
                text_html_ratio REAL,
                content_hash TEXT,
                internal_links_count INTEGER,
                unique_internal_links_count INTEGER,
                external_links_count INTEGER,
                unique_external_links_count INTEGER,
                images_count INTEGER,
                images_missing_alt INTEGER,
                schema_types TEXT,
                is_schema_valid INTEGER,
                hreflangs TEXT,
                page_type TEXT,
                template_id TEXT,
                crawl_depth INTEGER,
                is_rendered INTEGER,
                error TEXT,
                crawl_timestamp TEXT,
                PRIMARY KEY (crawl_id, url)
            );
            CREATE INDEX IF NOT EXISTS idx_pages_status ON pages (crawl_id, status_code);
            CREATE INDEX IF NOT EXISTS idx_pages_template ON pages (crawl_id, template_id);
            CREATE INDEX IF NOT EXISTS idx_pages_type ON pages (crawl_id, page_type);

            CREATE TABLE IF NOT EXISTS links (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                crawl_id TEXT NOT NULL,
                source_url TEXT NOT NULL,
                target_url TEXT NOT NULL,
                anchor_text TEXT,
                is_internal INTEGER,
                is_nofollow INTEGER,
                is_sponsored INTEGER,
                is_ugc INTEGER
            );
            CREATE INDEX IF NOT EXISTS idx_links_crawl ON links (crawl_id, source_url);
            CREATE INDEX IF NOT EXISTS idx_links_target ON links (crawl_id, target_url);

            CREATE TABLE IF NOT EXISTS images (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                crawl_id TEXT NOT NULL,
                page_url TEXT NOT NULL,
                image_url TEXT NOT NULL,
                alt_text TEXT,
                has_alt INTEGER,
                width INTEGER,
                height INTEGER,
                is_lazy INTEGER,
                image_format TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_images_page ON images (crawl_id, page_url);

            CREATE TABLE IF NOT EXISTS schemas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                crawl_id TEXT NOT NULL,
                page_url TEXT NOT NULL,
                schema_type TEXT NOT NULL,
                is_valid INTEGER,
                raw_json TEXT,
                error_message TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_schemas_page ON schemas (crawl_id, page_url);

            CREATE TABLE IF NOT EXISTS issues (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                crawl_id TEXT NOT NULL,
                url TEXT NOT NULL,
                page_type TEXT,
                template TEXT,
                category TEXT NOT NULL,
                issue TEXT NOT NULL,
                severity TEXT NOT NULL,
                evidence TEXT,
                recommendation TEXT,
                source TEXT DEFAULT 'deterministic_rule',
                laya_category TEXT,
                laya_severity TEXT,
                laya_action TEXT,
                laya_confidence REAL
            );
            CREATE INDEX IF NOT EXISTS idx_issues_crawl ON issues (crawl_id, category, severity);
            CREATE INDEX IF NOT EXISTS idx_issues_template ON issues (crawl_id, template);

            CREATE TABLE IF NOT EXISTS templates (
                crawl_id TEXT NOT NULL,
                template_id TEXT NOT NULL,
                page_count INTEGER,
                sample_urls TEXT,
                dominant_page_type TEXT,
                characteristics_json TEXT,
                PRIMARY KEY (crawl_id, template_id)
            );

            CREATE TABLE IF NOT EXISTS performance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                crawl_id TEXT NOT NULL,
                url TEXT NOT NULL,
                page_type TEXT,
                template_id TEXT,
                ttfb REAL,
                fcp REAL,
                lcp REAL,
                cls REAL,
                inp REAL,
                speed_index REAL,
                performance_score REAL,
                js_size INTEGER,
                css_size INTEGER,
                img_size INTEGER,
                total_size INTEGER,
                tested_at TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_perf_crawl ON performance (crawl_id, url);

            CREATE TABLE IF NOT EXISTS laya_decisions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                crawl_id TEXT NOT NULL,
                issue_key TEXT,
                prompt_summary TEXT,
                response_raw TEXT,
                latency_ms REAL,
                decision_category TEXT,
                decision_severity TEXT,
                decision_action TEXT,
                confidence REAL,
                created_at TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_laya_crawl ON laya_decisions (crawl_id);

            CREATE TABLE IF NOT EXISTS issue_clusters (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                crawl_id TEXT NOT NULL,
                cluster_id TEXT NOT NULL,
                issue TEXT NOT NULL,
                category TEXT NOT NULL,
                priority TEXT NOT NULL,
                severity TEXT,
                affected_urls_count INTEGER,
                affected_templates_count INTEGER,
                primary_affected_template TEXT,
                scope TEXT,
                evidence_summary TEXT,
                recommended_action TEXT,
                engineering_fix_location TEXT,
                sample_urls TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_clusters_crawl ON issue_clusters (crawl_id, priority);

            CREATE TABLE IF NOT EXISTS ranking_opportunities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                crawl_id TEXT NOT NULL,
                url TEXT NOT NULL,
                page_type TEXT,
                template TEXT,
                target_query TEXT,
                current_position REAL,
                impressions INTEGER,
                clicks INTEGER,
                ctr REAL,
                position_bracket TEXT,
                technical_status TEXT,
                content_status TEXT,
                internal_link_status TEXT,
                structured_data_status TEXT,
                performance_status TEXT,
                serp_coverage TEXT,
                aeo_status TEXT,
                geo_status TEXT,
                competitor_gap TEXT,
                primary_gap_type TEXT,
                priority TEXT,
                priority_score REAL,
                evidence TEXT,
                recommended_actions TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_opps_crawl ON ranking_opportunities (crawl_id, priority);

            CREATE TABLE IF NOT EXISTS product_pages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                crawl_id TEXT NOT NULL,
                url TEXT NOT NULL,
                brand TEXT,
                model TEXT,
                variant TEXT,
                price_str TEXT,
                ex_showroom_price TEXT,
                on_road_price TEXT,
                emi_str TEXT,
                specs_json TEXT,
                variants_json TEXT,
                colors_json TEXT,
                coverage_score_pct REAL,
                present_sections_json TEXT,
                missing_sections_json TEXT,
                primary_intent TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_prod_crawl ON product_pages (crawl_id, brand, model);

            CREATE TABLE IF NOT EXISTS internal_link_opportunities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                crawl_id TEXT NOT NULL,
                target_url TEXT NOT NULL,
                source_url TEXT NOT NULL,
                recommended_anchor_text TEXT,
                reason TEXT,
                priority TEXT,
                opportunity_score REAL
            );
            CREATE INDEX IF NOT EXISTS idx_link_opps_crawl ON internal_link_opportunities (crawl_id);
            """)

    def save_crawl_run(self, run: CrawlRun):
        with self._lock, self._get_connection() as conn:
            conn.execute("""
            INSERT OR REPLACE INTO crawl_runs 
            (crawl_id, target_url, start_time, end_time, status, max_pages, concurrency, config_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (run.crawl_id, run.target_url, run.start_time, run.end_time, run.status, run.max_pages, run.concurrency, run.config_json))
            conn.commit()

    def update_crawl_status(self, crawl_id: str, status: str, end_time: Optional[str] = None):
        with self._lock, self._get_connection() as conn:
            conn.execute("UPDATE crawl_runs SET status = ?, end_time = ? WHERE crawl_id = ?", (status, end_time, crawl_id))
            conn.commit()

    def get_latest_crawl_run(self, target_url: str) -> Optional[Dict[str, Any]]:
        with self._lock, self._get_connection() as conn:
            row = conn.execute("SELECT * FROM crawl_runs WHERE target_url = ? ORDER BY start_time DESC LIMIT 1", (target_url,)).fetchone()
            return dict(row) if row else None

    def add_urls(self, crawl_id: str, url_tuples: List[Tuple[str, str, str, int]]):
        """Batch insert discovered URLs: (url, status, discovery_source, depth). Ignores duplicates."""
        if not url_tuples:
            return
        with self._lock, self._get_connection() as conn:
            conn.executemany("""
            INSERT OR IGNORE INTO urls (crawl_id, url, status, discovery_source, depth, discovered_at)
            VALUES (?, ?, ?, ?, ?, datetime('now'))
            """, [(crawl_id, u, s, src, d) for u, s, src, d in url_tuples])
            conn.commit()

    def update_url_status(self, crawl_id: str, url: str, status: str):
        with self._lock, self._get_connection() as conn:
            conn.execute("UPDATE urls SET status = ?, visited_at = datetime('now') WHERE crawl_id = ? AND url = ?", (status, crawl_id, url))
            conn.commit()

    def get_queued_urls(self, crawl_id: str, limit: int = 1000) -> List[Tuple[str, str, int]]:
        """Returns list of (url, discovery_source, depth) for queued/discovered URLs."""
        with self._lock, self._get_connection() as conn:
            rows = conn.execute("""
            SELECT url, discovery_source, depth FROM urls 
            WHERE crawl_id = ? AND status IN ('discovered', 'queued') 
            ORDER BY depth ASC, rowid ASC LIMIT ?
            """, (crawl_id, limit)).fetchall()
    def save_fetch(
        self,
        run_id: str,
        url: str,
        status_code: int,
        headers: Dict[str, str],
        response_time: float,
        content_hash: str,
        raw_store_ref: str,
        rendered_store_ref: str = "",
        is_rendered: bool = False
    ):
        with self._lock, self._get_connection() as conn:
            conn.execute("""
            INSERT INTO fetches 
            (run_id, url, status_code, headers_json, response_time, content_hash, raw_store_ref, rendered_store_ref, is_rendered, fetched_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
            """, (run_id, url, status_code, json.dumps(headers) if headers else "{}", response_time, content_hash, raw_store_ref, rendered_store_ref, 1 if is_rendered else 0))
            conn.commit()

    def save_page(self, crawl_id: str, page: PageData):
        with self._lock, self._get_connection() as conn:
            conn.execute("""
            INSERT OR REPLACE INTO pages (
                crawl_id, url, final_url, status_code, content_type, response_time, content_length,
                redirect_chain, title, title_length, title_word_count, description, description_length,
                h1_count, h1_text, h2_count, h3_count, meta_robots, x_robots_tag, is_indexable, is_follow,
                canonical, canonical_status, is_self_canonical, word_count, paragraph_count,
                text_html_ratio, content_hash, internal_links_count, unique_internal_links_count,
                external_links_count, unique_external_links_count, images_count, images_missing_alt,
                schema_types, is_schema_valid, hreflangs, page_type, template_id, crawl_depth,
                is_rendered, error, crawl_timestamp
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                crawl_id, page.url, page.final_url, page.status_code, page.content_type, page.response_time,
                page.content_length, json.dumps(page.redirect_chain), page.title, page.title_length,
                page.title_word_count, page.description, page.description_length, page.h1_count,
                page.h1_text, page.h2_count, page.h3_count, page.meta_robots, page.x_robots_tag,
                1 if page.is_indexable else 0, 1 if page.is_follow else 0, page.canonical,
                page.canonical_status, 1 if page.is_self_canonical else 0, page.word_count,
                page.paragraph_count, page.text_html_ratio, page.content_hash,
                page.internal_links_count, page.unique_internal_links_count,
                page.external_links_count, page.unique_external_links_count,
                page.images_count, page.images_missing_alt,
                json.dumps(page.schema_types), 1 if page.is_schema_valid else 0,
                json.dumps(page.hreflangs), page.page_type, page.template_id,
                page.crawl_depth, 1 if page.is_rendered else 0, page.error, page.crawl_timestamp
            ))
            conn.commit()

    def save_links(self, crawl_id: str, links: List[LinkItem]):
        if not links:
            return
        with self._lock, self._get_connection() as conn:
            conn.executemany("""
            INSERT INTO links (crawl_id, source_url, target_url, anchor_text, is_internal, is_nofollow, is_sponsored, is_ugc)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, [(crawl_id, l.source_url, l.target_url, l.anchor_text, 1 if l.is_internal else 0, 1 if l.is_nofollow else 0, 1 if l.is_sponsored else 0, 1 if l.is_ugc else 0) for l in links])
            conn.commit()

    def save_images(self, crawl_id: str, images: List[ImageItem]):
        if not images:
            return
        with self._lock, self._get_connection() as conn:
            conn.executemany("""
            INSERT INTO images (crawl_id, page_url, image_url, alt_text, has_alt, width, height, is_lazy, image_format)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, [(crawl_id, img.page_url, img.image_url, img.alt_text, 1 if img.has_alt else 0, img.width, img.height, 1 if img.is_lazy else 0, img.image_format) for img in images])
            conn.commit()

    def save_schemas(self, crawl_id: str, schemas: List[SchemaItem]):
        if not schemas:
            return
        with self._lock, self._get_connection() as conn:
            conn.executemany("""
            INSERT INTO schemas (crawl_id, page_url, schema_type, is_valid, raw_json, error_message)
            VALUES (?, ?, ?, ?, ?, ?)
            """, [(crawl_id, s.page_url, s.schema_type, 1 if s.is_valid else 0, s.raw_json, s.error_message) for s in schemas])
            conn.commit()

    def save_issues(self, crawl_id: str, issues: List[SEOIssue]):
        if not issues:
            return
        with self._lock, self._get_connection() as conn:
            conn.executemany("""
            INSERT INTO issues (crawl_id, url, page_type, template, category, issue, severity, evidence, recommendation, source, laya_category, laya_severity, laya_action, laya_confidence)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, [(crawl_id, i.url, i.page_type, i.template, i.category, i.issue, i.severity, i.evidence, i.recommendation, i.source, i.laya_category, i.laya_severity, i.laya_action, i.laya_confidence) for i in issues])
            conn.commit()

    def update_issue_laya(self, issue_id: int, laya_category: str, laya_severity: str, laya_action: str, confidence: float):
        with self._lock, self._get_connection() as conn:
            conn.execute("""
            UPDATE issues SET laya_category = ?, laya_severity = ?, laya_action = ?, laya_confidence = ?
            WHERE id = ?
            """, (laya_category, laya_severity, laya_action, confidence, issue_id))
            conn.commit()

    def save_laya_decision(self, crawl_id: str, issue_key: str, prompt_summary: str, response_raw: str, latency_ms: float, decision_category: str, decision_severity: str, decision_action: str, confidence: float):
        with self._lock, self._get_connection() as conn:
            conn.execute("""
            INSERT INTO laya_decisions (crawl_id, issue_key, prompt_summary, response_raw, latency_ms, decision_category, decision_severity, decision_action, confidence, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
            """, (crawl_id, issue_key, prompt_summary, response_raw, latency_ms, decision_category, decision_severity, decision_action, confidence))
            conn.commit()

    def save_performance(self, crawl_id: str, perf_data: Dict[str, Any]):
        with self._lock, self._get_connection() as conn:
            conn.execute("""
            INSERT INTO performance (crawl_id, url, page_type, template_id, ttfb, fcp, lcp, cls, inp, speed_index, performance_score, js_size, css_size, img_size, total_size, tested_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
            """, (
                crawl_id, perf_data.get("url"), perf_data.get("page_type"), perf_data.get("template_id"),
                perf_data.get("ttfb"), perf_data.get("fcp"), perf_data.get("lcp"), perf_data.get("cls"),
                perf_data.get("inp"), perf_data.get("speed_index"), perf_data.get("performance_score"),
                perf_data.get("js_size"), perf_data.get("css_size"), perf_data.get("img_size"),
                perf_data.get("total_size")
            ))
            conn.commit()

    def save_templates(self, crawl_id: str, templates: List[Dict[str, Any]]):
        if not templates:
            return
        with self._lock, self._get_connection() as conn:
            conn.executemany("""
            INSERT OR REPLACE INTO templates (crawl_id, template_id, page_count, sample_urls, dominant_page_type, characteristics_json)
            VALUES (?, ?, ?, ?, ?, ?)
            """, [(crawl_id, t["template_id"], t["page_count"], json.dumps(t.get("sample_urls", [])), t.get("dominant_page_type", ""), json.dumps(t.get("characteristics", {}))) for t in templates])
            conn.commit()

    def get_stats(self, crawl_id: str) -> CrawlStats:
        stats = CrawlStats()
        with self._lock, self._get_connection() as conn:
            row = conn.execute("""
            SELECT 
                COUNT(*) as discovered,
                SUM(CASE WHEN status = 'crawled' THEN 1 ELSE 0 END) as crawled,
                SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed,
                SUM(CASE WHEN status = 'skipped' THEN 1 ELSE 0 END) as skipped,
                SUM(CASE WHEN status = 'blocked' THEN 1 ELSE 0 END) as blocked
            FROM urls WHERE crawl_id = ?
            """, (crawl_id,)).fetchone()
            if row:
                stats.urls_discovered = row["discovered"] or 0
                stats.urls_crawled = row["crawled"] or 0
                stats.urls_failed = row["failed"] or 0
                stats.urls_skipped = row["skipped"] or 0
                stats.urls_blocked_robots = row["blocked"] or 0

            # Pages stats
            p_row = conn.execute("""
            SELECT 
                AVG(response_time) as avg_resp,
                SUM(CASE WHEN status_code >= 400 AND status_code < 500 THEN 1 ELSE 0 END) as err_4xx,
                SUM(CASE WHEN status_code >= 500 THEN 1 ELSE 0 END) as err_5xx,
                SUM(CASE WHEN is_indexable = 1 THEN 1 ELSE 0 END) as indexable,
                SUM(CASE WHEN is_indexable = 0 THEN 1 ELSE 0 END) as non_indexable
            FROM pages WHERE crawl_id = ?
            """, (crawl_id,)).fetchone()
            if p_row:
                stats.average_response_time = round(p_row["avg_resp"] or 0.0, 3)
                stats.urls_error_4xx = p_row["err_4xx"] or 0
                stats.urls_error_5xx = p_row["err_5xx"] or 0
                stats.indexable_urls = p_row["indexable"] or 0
                stats.non_indexable_urls = p_row["non_indexable"] or 0

            # Issues stats
            i_row = conn.execute("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN severity = 'critical' THEN 1 ELSE 0 END) as crit,
                SUM(CASE WHEN severity = 'high' THEN 1 ELSE 0 END) as hi,
                SUM(CASE WHEN severity = 'medium' THEN 1 ELSE 0 END) as med,
                SUM(CASE WHEN severity = 'low' THEN 1 ELSE 0 END) as lo
            FROM issues WHERE crawl_id = ?
            """, (crawl_id,)).fetchone()
            if i_row:
                stats.total_issues = i_row["total"] or 0
                stats.critical_issues = i_row["crit"] or 0
                stats.high_issues = i_row["hi"] or 0
                stats.medium_issues = i_row["med"] or 0
                stats.low_issues = i_row["lo"] or 0

            # Templates count
            t_row = conn.execute("SELECT COUNT(*) as cnt FROM templates WHERE crawl_id = ?", (crawl_id,)).fetchone()
            stats.templates_count = t_row["cnt"] if t_row else 0

            # Performance samples count
            perf_row = conn.execute("SELECT COUNT(*) as cnt FROM performance WHERE crawl_id = ?", (crawl_id,)).fetchone()
            stats.performance_sample_count = perf_row["cnt"] if perf_row else 0

            # Laya decisions count
            laya_row = conn.execute("SELECT COUNT(*) as cnt FROM laya_decisions WHERE crawl_id = ?", (crawl_id,)).fetchone()
            stats.laya_decisions_count = laya_row["cnt"] if laya_row else 0

        stats.urls_eligible = stats.urls_discovered - stats.urls_blocked_robots
        return stats

    def get_all_pages(self, crawl_id: str) -> List[Dict[str, Any]]:
        with self._lock, self._get_connection() as conn:
            rows = conn.execute("SELECT * FROM pages WHERE crawl_id = ?", (crawl_id,)).fetchall()
            return [dict(r) for r in rows]

    def get_all_issues(self, crawl_id: str) -> List[Dict[str, Any]]:
        with self._lock, self._get_connection() as conn:
            rows = conn.execute("SELECT * FROM issues WHERE crawl_id = ?", (crawl_id,)).fetchall()
            return [dict(r) for r in rows]

    def get_all_links(self, crawl_id: str) -> List[Dict[str, Any]]:
        with self._lock, self._get_connection() as conn:
            rows = conn.execute("SELECT * FROM links WHERE crawl_id = ?", (crawl_id,)).fetchall()
            return [dict(r) for r in rows]

    def get_all_templates(self, crawl_id: str) -> List[Dict[str, Any]]:
        with self._lock, self._get_connection() as conn:
            rows = conn.execute("SELECT * FROM templates WHERE crawl_id = ?", (crawl_id,)).fetchall()
            return [dict(r) for r in rows]

    def get_all_performance(self, crawl_id: str) -> List[Dict[str, Any]]:
        with self._lock, self._get_connection() as conn:
            rows = conn.execute("SELECT * FROM performance WHERE crawl_id = ?", (crawl_id,)).fetchall()
            return [dict(r) for r in rows]

    def get_all_laya_decisions(self, crawl_id: str) -> List[Dict[str, Any]]:
        with self._lock, self._get_connection() as conn:
            rows = conn.execute("SELECT * FROM laya_decisions WHERE crawl_id = ?", (crawl_id,)).fetchall()
            return [dict(r) for r in rows]

    def save_issue_clusters(self, crawl_id: str, clusters: List[Dict[str, Any]]):
        if not clusters:
            return
        with self._lock, self._get_connection() as conn:
            conn.executemany("""
            INSERT INTO issue_clusters (
                crawl_id, cluster_id, issue, category, priority, severity, affected_urls_count,
                affected_templates_count, primary_affected_template, scope, evidence_summary,
                recommended_action, engineering_fix_location, sample_urls
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, [(
                crawl_id, c["cluster_id"], c["issue"], c["category"], c["priority"], c.get("severity", ""),
                c.get("affected_urls_count", 0), c.get("affected_templates_count", 0),
                c.get("primary_affected_template", ""), c.get("scope", "template"),
                c.get("evidence_summary", ""), c.get("recommended_action", ""),
                c.get("engineering_fix_location", ""), json.dumps(c.get("sample_urls", []))
            ) for c in clusters])
            conn.commit()

    def get_all_issue_clusters(self, crawl_id: str) -> List[Dict[str, Any]]:
        with self._lock, self._get_connection() as conn:
            rows = conn.execute("SELECT * FROM issue_clusters WHERE crawl_id = ? ORDER BY id ASC", (crawl_id,)).fetchall()
            return [dict(r) for r in rows]

    def save_ranking_opportunities(self, crawl_id: str, opps: List[Any]):
        if not opps:
            return
        dict_opps = [o.to_dict() if hasattr(o, "to_dict") else dict(o) for o in opps]
        with self._lock, self._get_connection() as conn:
            conn.executemany("""
            INSERT INTO ranking_opportunities (
                crawl_id, url, page_type, template, target_query, current_position, impressions,
                clicks, ctr, position_bracket, technical_status, content_status, internal_link_status,
                structured_data_status, performance_status, serp_coverage, aeo_status, geo_status,
                competitor_gap, primary_gap_type, priority, priority_score, evidence, recommended_actions
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, [(
                crawl_id,
                d.get("url", ""),
                d.get("page_type", ""),
                d.get("template", ""),
                d.get("target_query"),
                d.get("current_position"),
                d.get("impressions"),
                d.get("clicks"),
                d.get("ctr"),
                d.get("position_bracket", ""),
                d.get("technical_status", ""),
                d.get("content_status", ""),
                d.get("internal_link_status", ""),
                d.get("structured_data_status", ""),
                d.get("performance_status", ""),
                d.get("serp_coverage", ""),
                d.get("aeo_status", ""),
                d.get("geo_status", ""),
                d.get("competitor_gap", ""),
                d.get("primary_gap_type", ""),
                d.get("priority", "P1"),
                d.get("priority_score", 50.0),
                d.get("evidence", ""),
                json.dumps(d.get("recommended_actions", []))
            ) for d in dict_opps])
            conn.commit()

    def get_all_ranking_opportunities(self, crawl_id: str) -> List[Dict[str, Any]]:
        with self._lock, self._get_connection() as conn:
            rows = conn.execute("SELECT * FROM ranking_opportunities WHERE crawl_id = ? ORDER BY priority_score DESC", (crawl_id,)).fetchall()
            return [dict(r) for r in rows]

    def save_product_pages(self, crawl_id: str, prod_pages: List[Any]):
        if not prod_pages:
            return
        with self._lock, self._get_connection() as conn:
            conn.executemany("""
            INSERT INTO product_pages (
                crawl_id, url, brand, model, variant, price_str, ex_showroom_price, on_road_price,
                emi_str, specs_json, variants_json, colors_json, coverage_score_pct,
                present_sections_json, missing_sections_json, primary_intent
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, [(
                crawl_id, p.url, p.brand, p.model, p.variant, p.price_str, p.ex_showroom_price,
                p.on_road_price, p.emi_str, json.dumps(p.specs.__dict__ if hasattr(p.specs, "__dict__") else p.specs),
                json.dumps(p.variants_list), json.dumps(p.colors_list), p.coverage_score_pct,
                json.dumps(p.present_content_sections), json.dumps(p.missing_content_sections),
                p.primary_intent
            ) for p in prod_pages])
            conn.commit()

    def get_all_product_pages(self, crawl_id: str) -> List[Dict[str, Any]]:
        with self._lock, self._get_connection() as conn:
            rows = conn.execute("SELECT * FROM product_pages WHERE crawl_id = ?", (crawl_id,)).fetchall()
            return [dict(r) for r in rows]

    def save_internal_link_opportunities(self, crawl_id: str, link_opps: List[Dict[str, Any]]):
        if not link_opps:
            return
        with self._lock, self._get_connection() as conn:
            conn.executemany("""
            INSERT INTO internal_link_opportunities (
                crawl_id, target_url, source_url, recommended_anchor_text, reason, priority, opportunity_score
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, [(
                crawl_id, lo["target_url"], lo["source_url"], lo["recommended_anchor_text"],
                lo["reason"], lo["priority"], lo["opportunity_score"]
            ) for lo in link_opps])
            conn.commit()

    def get_all_internal_link_opportunities(self, crawl_id: str) -> List[Dict[str, Any]]:
        with self._lock, self._get_connection() as conn:
            rows = conn.execute("SELECT * FROM internal_link_opportunities WHERE crawl_id = ? ORDER BY opportunity_score DESC", (crawl_id,)).fetchall()
            return [dict(r) for r in rows]
