"""
SEOJEV Pipeline — Library Wrapper for V3 Engine Execution.
Allows the 6-layer audit engine to be invoked directly from Python (e.g. CLI, Celery, FastAPI)
with progress callbacks and cooperative cancellation.
"""

import asyncio
import datetime
import json
import logging
import os
import sqlite3
import sys
import time
import types
import urllib.parse
import yaml
from collections import Counter
from typing import Dict, Any, List, Optional, Callable, Set

logger = logging.getLogger("seojev.pipeline")

from models.crawl import CrawlRun, CrawlStats
from crawler.storage import CrawlStorage
from crawler.migrations import MigrationRunner
from crawler.crawler import SEOCrawler
from analysis.internal_links import build_and_analyze_link_graph
from analysis.templates import analyze_templates
from analysis.duplicates import analyze_duplicates
from analysis.aggregation import build_issue_clusters
from analysis.gsc import GSCAnalyzer
from analysis.product_intelligence import ProductIntelligenceEngine
from analysis.aeo import AEOAnalyzer
from analysis.geo import GEOAnalyzer
from analysis.serp import SERPAnalyzer
from analysis.opportunities import OpportunitySynthesizer
from performance.sampler import select_performance_sample
from performance.lighthouse import PerformanceAuditor
from laya.analyzer import LayaSEOAnalyzer
from laya.decision import LayaDecision, LayaCandidateInput, DecisionType, ConfidenceGate
from laya.worker_pool import LayaWorkerPool
from laya.candidates import build_candidates, opportunity_candidate_key
from laya.persistence import OPPORTUNITY_COLUMNS, insert_decision
from laya.decision import LAYA_PROMPT_VERSION, load_settings
from reporting.csv_report import CSVReportGenerator
from reporting.json_report import JSONReportGenerator
from reporting.docx_report import DocxReportGenerator
from reporting.executive_docx import ExecutiveSummaryGenerator
from reporting.docx_master import MasterDocxReportGenerator
from reporting.executive_master import MasterExecutiveSummaryGenerator
from reporting.csv_suite import CSVSuiteExporter
from reporting.html_explorer import HTMLExplorerGenerator
from engine.opportunity_engine_v3 import OpportunityEngineV3
from engine.work_orders import WorkOrderManager
from engine.priority_model import PriorityModel
from engine.claims_linter import ClaimsLinter
from engine.evidence import EvidenceLedger
from engine.content_store import ContentStore
from verticals.registry import VerticalRegistry
from extraction.provenance_extractor import ProvenanceExtractor
from technical.root_causes import RootCauseClusterer
from search.gsc_pipeline import GSCPipeline
from understanding.index_funnel import IndexFunnelReconciler
from understanding.entity_graph import EntityGraphEngine
from verification.snapshot import SnapshotRecorder
from verification.runner import VerificationRunner


class PipelineCancelledException(Exception):
    """Raised when cooperative cancellation is requested during pipeline execution."""
    pass


class SEOJEVPipeline:
    """
    Unified 6-Pass Search Intelligence Operating System Pipeline.
    Passes:
      - P1_CRAWL: Asynchronous crawl, discovery, sitemaps, selective rendering, storage.
      - P2_DETERMINISTIC_EVIDENCE: Link graph, templates, duplicates, and deterministic detectors.
      - P3_CANDIDATE_REDUCTION: Search context and reduced candidate/opportunity clusters.
      - P4_LAYA_DECISION_ENGINE: Laya primary semantic SEO decisions.
      - P5_VALIDATED_OPPORTUNITIES: Validated opportunities, priority, work orders, and claims linting.
      - P6_REPORTS: Word master reports, CSV suite, HTML explorer, JSON summaries.
    """

    def __init__(
        self,
        target_url: str,
        crawl_id: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None,
        output_dir: Optional[str] = None,
        db_path: Optional[str] = None,
        progress_callback: Optional[Callable[[str, float, str, Optional[Dict[str, Any]]], None]] = None,
        cancel_check: Optional[Callable[[], bool]] = None,
        options: Optional[Dict[str, Any]] = None
    ):
        target = target_url.strip()
        if not target.startswith(("http://", "https://")):
            target = "https://" + target
        self.target_url = target
        from engine.profiles import resolve_profile
        self.config = resolve_profile(config, (options or {}).get("profile", "dev"))
        self.options = options or {}
        self.progress_callback = progress_callback
        self.cancel_check = cancel_check

        # Configure paths
        self.output_dir = output_dir or self.options.get("output") or self.config.get("reports", {}).get("output_dir", "reports/")
        os.makedirs(self.output_dir, exist_ok=True)
        self.db_path = db_path or self.config.get("storage", {}).get("db_path", "data/seo.db")
        os.makedirs(os.path.dirname(self.db_path) or ".", exist_ok=True)
        if self.config['profile'] == 'dev':
            from engine.dev_sample import build_sample
            source = self.db_path
            sample_path = os.path.join(self.output_dir, 'dev-sample-' + str(time.time_ns()) + '.db')
            crawl_id, selected = build_sample(source, sample_path,
                crawl_id or self.options.get('crawl_id'), self.config['runtime']['max_urls'],
                self.config['runtime']['seed'], self.target_url)
            self.db_path = sample_path
            self.options.update(analyze_only=True, crawl_id=crawl_id, max_pages=len(selected),
                                concurrency=2, performance_sample=0)
            crawl_id = None  # Preserve the copied source run instead of replacing it.
        self.storage = CrawlStorage(db_path=self.db_path)
        self.content_store = ContentStore(base_dir=self.config.get("storage", {}).get("store_dir", "store"))
        self.migration_runner = MigrationRunner(db_path=self.db_path)
        self.migration_runner.run_migrations()

        # Crawl ID resolution
        self._last_pct: float = 0.0
        self.crawl_id = self._resolve_crawl_id(crawl_id)
        self.stats = CrawlStats()
        self.pass_timings: Dict[str, float] = {}

    def _resolve_crawl_id(self, explicit_id: Optional[str]) -> str:
        if explicit_id:
            max_p = self.options.get("max_pages", 5000)
            conc = self.options.get("concurrency", 10)
            run_record = CrawlRun(
                crawl_id=explicit_id,
                target_url=self.target_url,
                start_time=datetime.datetime.now().isoformat(),
                max_pages=max_p,
                concurrency=conc
            )
            self.storage.save_crawl_run(run_record)
            return explicit_id
        if self.options.get("crawl_id"):
            return self.options["crawl_id"]
        if self.options.get("analyze_only"):
            latest = self.storage.get_latest_crawl_run(self.target_url)
            return latest["crawl_id"] if latest else "crawl_20260923_234236"
        if self.options.get("resume"):
            latest = self.storage.get_latest_crawl_run(self.target_url)
            if latest and latest.get("status") != "completed":
                return latest["crawl_id"]

        # Default: fresh run
        fresh_id = f"crawl_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
        max_p = self.options.get("max_pages", 5000)
        conc = self.options.get("concurrency", 10)
        run_record = CrawlRun(
            crawl_id=fresh_id,
            target_url=self.target_url,
            start_time=datetime.datetime.now().isoformat(),
            max_pages=max_p,
            concurrency=conc
        )
        self.storage.save_crawl_run(run_record)
        return fresh_id

    def emit_progress(self, pass_name: str, pct: float, message: str, meta: Optional[Dict[str, Any]] = None):
        """Invoke external progress callback if registered with guaranteed monotonic pct."""
        if pct < getattr(self, "_last_pct", 0.0):
            pct = self._last_pct
        self._last_pct = pct
        if self.progress_callback:
            try:
                import inspect
                sig = inspect.signature(self.progress_callback)
                # Keep old event consumers readable during rolling upgrades; the
                # stored/current stage remains the new semantic stage below.
                legacy_pass = {
                    "P2_DETERMINISTIC_EVIDENCE": "P2_SIGNALS",
                    "P3_CANDIDATE_REDUCTION": "P3_SEARCH_OPPORTUNITIES",
                    "P4_LAYA_DECISION_ENGINE": "P4_CALIBRATION",
                    "P5_VALIDATED_OPPORTUNITIES": "P5_WORK_ORDERS",
                    "P6_REPORTS": "P6_DELIVERABLES",
                }.get(pass_name)
                if legacy_pass:
                    if len(sig.parameters) >= 4:
                        self.progress_callback(legacy_pass, pct, message, meta or {})
                    else:
                        self.progress_callback(legacy_pass, pct, message)
                if len(sig.parameters) >= 4:
                    self.progress_callback(pass_name, pct, message, meta or {})
                else:
                    self.progress_callback(pass_name, pct, message)
            except Exception:
                try:
                    self.progress_callback(pass_name, pct, message, meta or {})
                except Exception:
                    try:
                        self.progress_callback(pass_name, pct, message)
                    except Exception:
                        pass

    def check_cancelled(self):
        """Raises PipelineCancelledException if cancel_check triggers."""
        if getattr(self, "memory_guard", None):
            self.memory_guard.checkpoint()
        if self.cancel_check and self.cancel_check():
            raise PipelineCancelledException(f"Pipeline execution cancelled by caller for run '{self.crawl_id}'.")

    def checkpoint_contract(self):
        analyzer = LayaSEOAnalyzer.get_singleton(self.config.get("laya", {}).get("model_id", "aac6fef/laya-mlx"))
        settings = {**load_settings(), **self.config.get("laya", {})}
        return {"prompt_version": LAYA_PROMPT_VERSION, "checkpoint_id": analyzer.preflight()["checkpoint_id"],
                "confidence": settings["confidence"], "pipeline_version": "strict-laya-v3"}

    def is_stage_complete(self, stage: str) -> bool:
        """Legacy aliases are safe only upstream; decisions require current provenance."""
        aliases = {"P2_DETERMINISTIC_EVIDENCE": "P2_SIGNALS", "P3_CANDIDATE_REDUCTION": "P3_SEARCH_OPPORTUNITIES"}
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute("SELECT status, metadata_json FROM stage_checkpoints WHERE crawl_id=? AND stage IN (?, ?) ORDER BY stage=? DESC LIMIT 1",
                               (self.crawl_id, stage, aliases.get(stage, stage), stage)).fetchone()
            if not row or row[0] != "completed":
                return False
            if stage.startswith(("P4_", "P5_", "P6_")):
                if self.options.get("rerun_laya"):
                    return False
                metadata = json.loads(row[1] or "{}")
                if metadata.get("contract") != self.checkpoint_contract():
                    return False
                if stage == "P4_LAYA_DECISION_ENGINE":
                    expected = metadata.get("laya_summary", {}).get("total_decisions", 0)
                    complete = conn.execute("""SELECT COUNT(*) FROM laya_decisions WHERE crawl_id=?
                        AND cluster_id IS NOT NULL AND choice IS NOT NULL AND gate IS NOT NULL
                        AND prompt_version=? AND head_confidences IS NOT NULL AND checkpoint_id=?""",
                        (self.crawl_id, LAYA_PROMPT_VERSION, metadata["contract"]["checkpoint_id"])).fetchone()[0]
                    return expected > 0 and complete == expected
                if not self.is_stage_complete("P4_LAYA_DECISION_ENGINE"):
                    return False
                if stage == "P6_REPORTS":
                    return self.is_stage_complete("P5_VALIDATED_OPPORTUNITIES") and all(
                        os.path.isfile(os.path.join(self.output_dir, name)) for name in
                        ("SEOJEV_V3_AUDIT_REPORT.docx", "SEOJEV_EXECUTIVE_SUMMARY.docx", "explorer.html", "summary.json"))
            return True

    def mark_stage_complete(self, stage: str, metadata: Optional[Dict[str, Any]] = None):
        metadata = dict(metadata or {})
        if stage.startswith(("P4_", "P5_", "P6_")):
            metadata["contract"] = self.checkpoint_contract()
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""INSERT OR REPLACE INTO stage_checkpoints
                (crawl_id,stage,status,metadata_json,completed_at) VALUES (?,?,'completed',?,?)""",
                (self.crawl_id, stage, json.dumps(metadata, default=str), datetime.datetime.now().isoformat()))
            order = ["P1_CRAWL", "P2_DETERMINISTIC_EVIDENCE", "P3_CANDIDATE_REDUCTION", "P4_LAYA_DECISION_ENGINE", "P5_VALIDATED_OPPORTUNITIES", "P6_REPORTS"]
            for downstream in order[order.index(stage)+1:]:
                conn.execute("UPDATE stage_checkpoints SET status='stale' WHERE crawl_id=? AND stage=?", (self.crawl_id, downstream))

    # -------------------------------------------------------------------------
    # PASS 1: CRAWL & DISCOVERY
    # -------------------------------------------------------------------------
    async def run_pass_1_crawl(self) -> Dict[str, Any]:
        """P1: Execute async crawling, selective rendering, sitemap & robots parsing."""
        self.check_cancelled()
        t0 = time.monotonic()
        self.emit_progress("P1_CRAWL", 0.0, f"Initializing crawl engine for {self.target_url}...")

        is_analyze_only = bool(self.options.get("analyze_only") or self.options.get("crawl_id"))
        crawl_duration = 0.0

        if not is_analyze_only:
            def url_cb(crawled: int, discovered: int, current_url: str):
                max_pages = self.options.get("max_pages", 5000)
                sub_pct = min(25.0, (crawled / max(max_pages, 1)) * 25.0)
                self.emit_progress("P1_CRAWL", round(sub_pct, 1), f"Crawling ({crawled}/{discovered}): {current_url[:60]}", {
                    "crawled": crawled,
                    "discovered": discovered,
                    "current_url": current_url
                })

            crawler_config = dict(self.config or {})
            c_cfg = dict(crawler_config.get("crawler", {}))
            if self.options.get("scope_urls"):
                c_cfg["scope_urls"] = self.options["scope_urls"]
                c_cfg["max_pages"] = len(self.options["scope_urls"])
            crawler_config["crawler"] = c_cfg

            crawler = SEOCrawler(
                target_url=self.target_url,
                crawl_id=self.crawl_id,
                storage=self.storage,
                config=crawler_config,
                render_enabled=bool(self.options.get("render")),
                resume=bool(self.options.get("resume")),
                max_pages=len(self.options["scope_urls"]) if self.options.get("scope_urls") else self.options.get("max_pages", 5000),
                concurrency=self.options.get("concurrency", 10),
                cancel_check=self.cancel_check,
                url_progress_callback=url_cb,
                show_live_display=self.options.get("show_live_display")
            )

            await crawler.initialize()
            self.emit_progress("P1_CRAWL", 5.0, "Crawler initialized. Fetching URLs...")
            await crawler.crawl()
            self.check_cancelled()
            crawl_duration = round(time.monotonic() - t0, 2)
            self.emit_progress("P1_CRAWL", 25.0, f"Crawl phase complete ({crawl_duration}s).")
        else:
            self.emit_progress("P1_CRAWL", 25.0, f"Skipped HTTP fetch (analyzing existing dataset '{self.crawl_id}').")

        # Record complete state snapshots for all crawled pages
        try:
            rec = SnapshotRecorder(db_path=self.db_path, content_store=self.content_store)
            rec.take_snapshot_from_db(self.crawl_id, self.crawl_id)
        except Exception:
            pass

        self.pass_timings["P1_CRAWL"] = round(time.monotonic() - t0, 2)
        return {"crawl_id": self.crawl_id, "crawl_duration": crawl_duration}

    # -------------------------------------------------------------------------
    # PASS 2: DETERMINISTIC EVIDENCE
    # -------------------------------------------------------------------------
    async def run_pass_2_signals(self, p1_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """P2: Generate deterministic evidence and detector candidates."""
        self.check_cancelled()
        t0 = time.monotonic()
        self.emit_progress("P2_DETERMINISTIC_EVIDENCE", 26.0, "Retrieving deterministic crawl evidence...")

        with sqlite3.connect(self.db_path) as conn:
            n = conn.execute('SELECT COUNT(*) FROM pages WHERE crawl_id=?',(self.crawl_id,)).fetchone()[0]
        if n > 500:
            raise RuntimeError('Legacy evidence adapter is limited to 500 URLs; use chunk/global reducers before scaling')
        pages = self.storage.get_all_pages(self.crawl_id)
        links = self.storage.get_all_links(self.crawl_id)
        issues = self.storage.get_all_issues(self.crawl_id)

        # 2a. NetworkX Link Graph
        self.check_cancelled()
        self.emit_progress("P2_DETERMINISTIC_EVIDENCE", 29.0, f"Analyzing link graph across {len(pages):,} pages...")
        node_metrics, link_issues, link_opportunities = build_and_analyze_link_graph(pages, links, self.target_url)
        if link_issues:
            self.storage.save_issues(self.crawl_id, link_issues)
            issues.extend([iss.to_dict() for iss in link_issues])
        self.storage.save_internal_link_opportunities(self.crawl_id, link_opportunities)

        # 2b. Templates & Duplicates
        self.check_cancelled()
        self.emit_progress("P2_DETERMINISTIC_EVIDENCE", 33.0, "Clustering templates and collecting duplicate evidence...")
        templates, template_issues = analyze_templates(pages, issues)
        self.storage.save_templates(self.crawl_id, templates)
        if template_issues:
            self.storage.save_issues(self.crawl_id, template_issues)
            issues.extend([iss.to_dict() for iss in template_issues])

        dup_issues = analyze_duplicates(pages)
        if dup_issues:
            self.storage.save_issues(self.crawl_id, dup_issues)
            issues.extend([iss.to_dict() for iss in dup_issues])

        all_issues = self.storage.get_all_issues(self.crawl_id)

        # 2c. Issue Clusters & Root Causes
        self.emit_progress("P2_DETERMINISTIC_EVIDENCE", 37.0, f"Reducing {len(all_issues):,} detector candidates into evidence clusters...")
        issue_clusters = build_issue_clusters(all_issues)
        self.storage.save_issue_clusters(self.crawl_id, issue_clusters)

        root_cause_clusterer = RootCauseClusterer()
        rc_result = root_cause_clusterer.cluster_root_causes(all_issues)

        # 2d. Index Funnel Reconciliation
        self.emit_progress("P2_DETERMINISTIC_EVIDENCE", 40.0, "Reconciling index funnel across sitemaps and crawled links...")
        index_reconciler = IndexFunnelReconciler()
        with self.storage._get_connection() as _uconn:
            sitemap_rows = _uconn.execute("SELECT url FROM urls WHERE crawl_id = ? AND discovery_source = 'sitemap'", (self.crawl_id,)).fetchall()
            if not sitemap_rows:
                sitemap_rows = _uconn.execute("SELECT url FROM urls WHERE discovery_source = 'sitemap'").fetchall()
            sitemap_url_set = {r["url"] for r in sitemap_rows}

        funnel_data = index_reconciler.build_funnel(sitemap_url_set, pages)
        funnel_csv_path = os.path.join(self.output_dir, "index-funnel.csv")
        index_reconciler.export_csv(funnel_data, funnel_csv_path)

        # 2e. Core Web Vitals Performance Audit
        self.check_cancelled()
        perf_db_records = self.storage.get_all_performance(self.crawl_id)
        if not perf_db_records:
            perf_sample_size = min(self.options.get("performance_sample", 100), len(pages))
            if perf_sample_size > 0:
                self.emit_progress("P2_DETERMINISTIC_EVIDENCE", 43.0, f"Running Core Web Vitals audit on {perf_sample_size} sample pages...")
                sample_pages = select_performance_sample(pages, sample_size=perf_sample_size, homepage_url=self.target_url)
                perf_auditor = PerformanceAuditor(timeout_ms=12000)
                perf_results = await perf_auditor.audit_pages(sample_pages, max_concurrency=2)
                for p_res in perf_results:
                    self.storage.save_performance(self.crawl_id, p_res)
                perf_db_records = self.storage.get_all_performance(self.crawl_id)

        # 2f. Vertical Knowledge & Product Intelligence
        self.check_cancelled()
        self.emit_progress("P2_DETERMINISTIC_EVIDENCE", 46.0, "Extracting product intelligence and vertical domain attributes...")
        prod_engine = ProductIntelligenceEngine()
        product_pages_data = []
        product_data_map = {}
        for p in pages:
            if prod_engine.is_product_page(p):
                prod_info = prod_engine.extract_product_intelligence(p)
                product_pages_data.append(prod_info)
                product_data_map[p["url"]] = prod_info
        self.storage.save_product_pages(self.crawl_id, product_pages_data)

        _domain = urllib.parse.urlsplit(self.target_url).netloc.lower()
        site_profile_hint = types.SimpleNamespace(
            domain=_domain,
            url=self.target_url,
            page_count=len(pages),
            product_page_count=len(product_pages_data),
            page_types={p.get("page_type", ""): True for p in pages}
        )
        v_registry = VerticalRegistry()
        active_vertical, v_confidence, v_overlays = v_registry.select_vertical(site_profile_hint)
        prov_extractor = ProvenanceExtractor(active_vertical)

        # Attribute extraction
        with sqlite3.connect(self.db_path) as _conn:
            _conn.execute("PRAGMA journal_mode=WAL")
            for p in pages:
                if p.get("page_type") not in ("model", "product", "vehicle", "bike"):
                    continue
                content_hash = p.get("content_hash", "")
                if not content_hash:
                    continue
                html = self.content_store.get(content_hash) or ""
                if not html:
                    continue
                try:
                    attrs, _ = prov_extractor.extract_with_provenance(html, p["url"])
                    for attr_name, attr_data in attrs.items():
                        val = attr_data.get("value")
                        if val is None:
                            continue
                        _conn.execute("""
                            INSERT OR REPLACE INTO attributes
                            (run_id, url, attribute_name, attribute_value, source_type, selector, text_span, confidence)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            self.crawl_id, p["url"], attr_name, str(val),
                            attr_data.get("source_type", "visible"),
                            attr_data.get("selector", ""),
                            attr_data.get("text_span", ""),
                            attr_data.get("confidence", 0.9)
                        ))
                except Exception:
                    pass
            _conn.commit()

        # 2g. Entity Consistency Validation
        self.check_cancelled()
        entity_engine = EntityGraphEngine()
        entity_conflict_issues = []
        for p in pages:
            if p.get("page_type") not in ("model", "product", "vehicle", "bike"):
                continue
            try:
                contradictions = entity_engine.evaluate_page_consistency(
                    url=p.get("url", ""),
                    title=p.get("title", "") or "",
                    h1=p.get("h1_text", "") or "",
                    schema_entities=[],
                    visible_price=None,
                    schema_price=None
                )
                for c in contradictions:
                    entity_conflict_issues.append({
                        "url": p["url"],
                        "issue": c.get("issue_type", "entity_conflict"),
                        "message": c.get("message", "Entity inconsistency detected"),
                        "severity": c.get("severity", "high"),
                        "category": "entity",
                        "recommendation": "Fix entity naming/price consistency across title, H1, schema, and visible content."
                    })
            except Exception:
                pass

        if entity_conflict_issues:
            with sqlite3.connect(self.db_path) as _ec_conn:
                _ec_conn.execute("PRAGMA journal_mode=WAL")
                for _ec in entity_conflict_issues:
                    _ec_conn.execute(
                        "INSERT INTO issues (crawl_id, url, category, issue, severity, evidence, recommendation) VALUES (?, ?, ?, ?, ?, ?, ?)",
                        (self.crawl_id, _ec["url"], _ec["category"], _ec["issue"], _ec["severity"], _ec["message"], _ec["recommendation"])
                    )
                _ec_conn.commit()

        self.emit_progress("P2_DETERMINISTIC_EVIDENCE", 50.0, "Deterministic evidence collection complete.")
        self.pass_timings["P2_DETERMINISTIC_EVIDENCE"] = round(time.monotonic() - t0, 2)

        return {
            "pages": pages,
            "links": links,
            "all_issues": self.storage.get_all_issues(self.crawl_id),
            "issue_clusters": issue_clusters,
            "node_metrics": node_metrics,
            "link_opportunities": link_opportunities,
            "templates": templates,
            "product_pages_data": product_pages_data,
            "product_data_map": product_data_map,
            "perf_db_records": perf_db_records,
            "active_vertical": active_vertical.name
        }

    # -------------------------------------------------------------------------
    # PASS 3: CANDIDATE/TEMPLATE REDUCTION
    # -------------------------------------------------------------------------
    async def run_pass_3_search_opportunities(self, p2_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """P3: Add search context and reduce deterministic candidates into opportunities."""
        self.check_cancelled()
        t0 = time.monotonic()
        self.emit_progress("P3_CANDIDATE_REDUCTION", 51.0, "Ingesting search context for candidate reduction...")

        pages = (p2_data or {}).get("pages") or self.storage.get_all_pages(self.crawl_id)
        product_data_map = p2_data.get("product_data_map", {}) if p2_data else {}
        issue_clusters = (p2_data or {}).get("issue_clusters") or self.storage.get_all_issue_clusters(self.crawl_id)
        node_metrics = p2_data.get("node_metrics", {}) if p2_data else {}
        link_opportunities = p2_data.get("link_opportunities", []) if p2_data else self.storage.get_all_internal_link_opportunities(self.crawl_id)
        product_pages_data = p2_data.get("product_pages_data", []) if p2_data else []

        # 3a. GSC & Search Pipelines
        gsc_file = self.options.get("gsc") or ("data/gsc/gsc.csv" if os.path.exists("data/gsc/gsc.csv") else None)
        gsc_analyzer = GSCAnalyzer(gsc_csv_path=gsc_file)
        gsc_v3 = GSCPipeline(
            gsc_csv_path=gsc_file,
            brand_terms=[self.target_url.replace("https://", "").replace("http://", "").split(".")[0]]
        )

        gsc_v3_query_page_map = []
        if gsc_v3.has_data:
            crawled_url_set = {p["url"].rstrip("/") for p in pages}
            with sqlite3.connect(self.db_path) as _conn:
                _conn.execute("PRAGMA journal_mode=WAL")
                for r in gsc_v3.rows:
                    norm_page = r["page"].rstrip("/")
                    in_crawl = norm_page in crawled_url_set
                    _conn.execute("""
                        INSERT OR REPLACE INTO gsc_rows
                        (run_id, query, page, clicks, impressions, ctr, position, date_recorded, is_brand, position_bracket, matched_crawl_url)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        self.crawl_id, r["query"], r["page"], r["clicks"], r["impressions"],
                        r["ctr"], r["position"], r.get("date", ""), 1 if r["is_brand"] else 0,
                        r["bracket"], norm_page if in_crawl else None
                    ))
                    if in_crawl:
                        gsc_v3_query_page_map.append({
                            "query": r["query"], "url": norm_page,
                            "clicks": r["clicks"], "impressions": r["impressions"],
                            "ctr": r["ctr"], "position": r["position"],
                            "bracket": r["bracket"], "verdict": "CORRECT_LANDING",
                            "click_gap": 0.0
                        })
                _conn.commit()

        # 3b. AEO, GEO, and SERP
        self.check_cancelled()
        self.emit_progress("P3_CANDIDATE_REDUCTION", 58.0, "Evaluating deterministic content and search signals...")
        aeo_analyzer = AEOAnalyzer()
        geo_analyzer = GEOAnalyzer()
        serp_analyzer = SERPAnalyzer(serp_data_path=self.options.get("serp_data"))

        aeo_evals = {}
        geo_evals = {}
        serp_evals = {}
        for p in pages:
            u = p["url"]
            prod_info = product_data_map.get(u)
            aeo_evals[u] = aeo_analyzer.evaluate_page(p, prod_info)
            geo_evals[u] = geo_analyzer.evaluate_page(p, prod_info)
            if prod_info:
                serp_evals[u] = serp_analyzer.analyze_product_serp_gaps(prod_info)

        avg_aeo = round(sum(e["aeo_readiness_score"] for e in aeo_evals.values()) / max(len(aeo_evals), 1), 1)
        avg_geo = round(sum(e["geo_readiness_score"] for e in geo_evals.values()) / max(len(geo_evals), 1), 1)

        opp_synthesizer = OpportunitySynthesizer(gsc_analyzer=gsc_analyzer if gsc_analyzer.has_data else None)
        ranking_opportunities, product_actions = opp_synthesizer.synthesize_opportunities(
            pages=pages,
            product_data_map=product_data_map,
            node_metrics=node_metrics,
            link_opportunities=link_opportunities,
            aeo_evals=aeo_evals,
            geo_evals=geo_evals,
            serp_evals=serp_evals
        )
        self.storage.save_ranking_opportunities(self.crawl_id, ranking_opportunities)

        # 3c. OpportunityEngineV3 Multi-Factor Synthesis
        self.check_cancelled()
        self.emit_progress("P3_CANDIDATE_REDUCTION", 65.0, "Reducing candidates into structured opportunity groups...")
        v3_findings = []
        for cluster in issue_clusters:
            sample_urls_raw = cluster.get('sample_urls', '')
            if isinstance(sample_urls_raw, str):
                try:
                    sample_url_list = json.loads(sample_urls_raw) if sample_urls_raw.startswith('[') else [u.strip() for u in sample_urls_raw.split(',') if u.strip()]
                except Exception:
                    sample_url_list = [u.strip() for u in sample_urls_raw.split(',') if u.strip()]
            else:
                sample_url_list = list(sample_urls_raw) if sample_urls_raw else []

            tpl = cluster.get('primary_affected_template', 'default')
            scope = cluster.get('scope', 'template')

            if scope == 'site' or not sample_url_list:
                v3_findings.append({
                    'rule_id': cluster.get('cluster_id', cluster.get('issue', 'GENERIC')),
                    'url': None,
                    'scope_key': 'site',
                    'severity': (cluster.get('severity') or cluster.get('priority', 'medium')).upper(),
                    'message': cluster.get('evidence_summary', cluster.get('issue', '')),
                    'template_id': tpl,
                    'recommended_action': cluster.get('recommended_action', '')
                })
            else:
                for url in sample_url_list[:5]:
                    v3_findings.append({
                        'rule_id': cluster.get('cluster_id', cluster.get('issue', 'GENERIC')),
                        'url': url,
                        'scope_key': 'template' if tpl != 'default' else 'page',
                        'severity': (cluster.get('severity') or cluster.get('priority', 'medium')).upper(),
                        'message': cluster.get('evidence_summary', cluster.get('issue', '')),
                        'template_id': tpl,
                        'recommended_action': cluster.get('recommended_action', '')
                    })

        v3_content_gaps = []
        for p in product_pages_data:
            if hasattr(p, "missing_content_sections") and p.missing_content_sections:
                v3_content_gaps.append({
                    'url': p.url,
                    'missing_sections': p.missing_content_sections,
                    'missing_attributes': []
                })

        all_templates = self.storage.get_all_templates(self.crawl_id)
        opp_engine_v3 = OpportunityEngineV3(db_path=self.db_path)
        v3_opps = opp_engine_v3.synthesize_opportunities(
            run_id=self.crawl_id,
            pages=pages,
            findings=v3_findings,
            templates={t["template_id"]: t for t in all_templates},
            query_page_map=gsc_v3_query_page_map,
            link_recommendations=link_opportunities,
            content_gaps=v3_content_gaps,
            aeo_evals=aeo_evals,
            geo_evals=geo_evals
        )
        opp_engine_v3.persist_opportunities(v3_opps)

        self.emit_progress("P3_CANDIDATE_REDUCTION", 70.0, f"Reduced candidates to {len(v3_opps):,} opportunity groups.")
        self.pass_timings["P3_CANDIDATE_REDUCTION"] = round(time.monotonic() - t0, 2)

        return {
            "v3_opps": v3_opps,
            "ranking_opportunities": ranking_opportunities,
            "product_actions": product_actions,
            "gsc_analyzer": gsc_analyzer,
            "gsc_v3_query_page_map": gsc_v3_query_page_map,
            "aeo_evals": aeo_evals,
            "geo_evals": geo_evals,
            "avg_aeo": avg_aeo,
            "avg_geo": avg_geo
        }

    # -------------------------------------------------------------------------
    # PASS 4: LAYA PRIMARY SEO DECISION
    # -------------------------------------------------------------------------
    async def run_pass_4_laya_decision(self, p3_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Run every reduced candidate through Laya and verify persisted provenance."""
        self.check_cancelled()
        t0 = time.monotonic()
        self.emit_progress("P4_LAYA_DECISION_ENGINE", 71.0, "Running strict MLX preflight...")
        from engine.chunks import SQLiteStageStore
        from engine.memory_guard import MemoryGuard
        from laya.streaming import LocalMLXService, iter_candidates, decide_classes
        limits = self.config['runtime']
        guard = getattr(self, 'memory_guard', None) or MemoryGuard(limits['memory_budget_mb'],
            batch_size=limits['batch_size'], min_available_mb=limits['min_available_mb'], pause_seconds=limits['pause_seconds'])
        store = SQLiteStageStore(self.db_path)
        service = LocalMLXService(self.config, guard, self.db_path)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('DELETE FROM laya_decisions WHERE crawl_id=?', (self.crawl_id,))
            resets = ','.join(f'"{col}"=NULL' for col in OPPORTUNITY_COLUMNS if col != 'laya_validated')
            conn.execute(f'UPDATE opportunities SET {resets},laya_validated=0 WHERE run_id=?', (self.crawl_id,))
        gates = Counter()
        count = real = cache_hits = 0
        with guard.stage('laya_and_fan_out'):
            for decision in decide_classes(iter_candidates(self.db_path, self.crawl_id), service, store, guard, self.crawl_id):
                self.check_cancelled()
                validated = int(decision.is_real_issue and decision.gate in ('AUTO_ACCEPT', 'HUMAN_REVIEW'))
                with sqlite3.connect(self.db_path) as conn:
                    insert_decision(conn, 'laya_decisions', decision)
                    updated = conn.execute("""UPDATE opportunities SET laya_action=?,laya_confidence=?,laya_decision_id=?,
                        laya_validated=?,laya_verdict=?,laya_scope=?,laya_root_cause=?,laya_canonical_indexability=?,
                        laya_content_assessment=?,laya_cannibalization=?,laya_internal_linking=?,laya_candidate_id=?,
                        laya_gate=?,laya_head_confidences=?,laya_checkpoint_id=?
                        WHERE run_id=? AND opportunity_id IN (SELECT opportunity_id FROM candidate_membership WHERE run_id=? AND candidate_id=?)""",
                        (decision.choice,decision.confidence,decision.decision_id,validated,decision.verdict,decision.scope,
                         decision.root_cause,json.dumps(decision.canonical_indexability),json.dumps(decision.content_assessment),
                         json.dumps(decision.cannibalization),json.dumps(decision.internal_linking),decision.cluster_id,
                         decision.gate,json.dumps(decision.head_confidences),decision.checkpoint_id,
                         self.crawl_id,self.crawl_id,decision.cluster_id)).rowcount
                gates[decision.gate] += updated
                count += 1
                real += decision.is_real_issue
                cache_hits += decision.from_cache
        if not count:
            raise RuntimeError('Pass 4 has zero candidates')
        with sqlite3.connect(self.db_path) as conn:
            unmatched = conn.execute('SELECT COUNT(*) FROM opportunities WHERE run_id=? AND laya_candidate_id IS NULL',(self.crawl_id,)).fetchone()[0]
            stored = conn.execute('SELECT COUNT(*) FROM laya_decisions WHERE crawl_id=?',(self.crawl_id,)).fetchone()[0]
        if unmatched or stored != count:
            raise RuntimeError(f'Incomplete candidate fan-out: unmatched={unmatched}, decisions={stored}/{count}')
        summary = {**(store.get('metrics',self.crawl_id) or {}), 'total_decisions':count,
                   'total_cache_hits':cache_hits,'inference_count':count-cache_hits,'real_issues':real,
                   'validated':gates['AUTO_ACCEPT']+gates['HUMAN_REVIEW'], 'human_review':gates['HUMAN_REVIEW'],
                   'suppressed':gates['SUPPRESS'],'opportunity_gates':dict(gates),'unmatched_opportunities':unmatched,
                   'peak_rss_mb':guard.peak_rss_mb,'preflight':service.analyzer.preflight()}
        self.pass_timings['P4_LAYA_DECISION_ENGINE'] = round(time.monotonic()-t0,2)
        self._laya_summary=summary
        return {'laya_summary':summary}

    # -------------------------------------------------------------------------
    # PASS 5: VALIDATED OPPORTUNITIES, PRIORITY & WORK ORDERS
    # -------------------------------------------------------------------------
    async def run_pass_5_work_orders(self, p4_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """P5: Generate work orders only from Laya validated opportunities."""
        self.check_cancelled()
        t0 = time.monotonic()
        self.emit_progress("P5_VALIDATED_OPPORTUNITIES", 81.0, "Generating priority-ranked work orders from validated opportunities...")

        wo_mgr = WorkOrderManager(db_path=self.db_path)
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            decision_stats = conn.execute("SELECT COUNT(*), COALESCE(SUM(is_real_issue),0) FROM laya_decisions WHERE crawl_id=? AND prompt_version=? AND head_confidences IS NOT NULL", (self.crawl_id, LAYA_PROMPT_VERSION)).fetchone()
            if decision_stats[0] == 0:
                raise RuntimeError("Pass 5 refused: Pass 4 has no persisted current Laya decisions")
            rows = conn.execute("SELECT * FROM opportunities WHERE run_id = ? AND COALESCE(laya_validated, 0) = 1", (self.crawl_id,)).fetchall()
            v3_opps = [dict(r) for r in rows]
            if not v3_opps and decision_stats[1]:
                raise RuntimeError(f"Pass 5 found zero validated opportunities despite {decision_stats[1]} real-issue decisions; inspect gates and candidate membership")
            if any(o["laya_gate"] not in ("AUTO_ACCEPT", "HUMAN_REVIEW") or not o["laya_candidate_id"] or not o["laya_decision_id"] for o in v3_opps):
                raise RuntimeError("Pass 5 found validated opportunities with invalid Laya provenance")

        work_orders = wo_mgr.create_work_orders_from_opportunities(self.crawl_id, v3_opps)
        wo_mgr.persist_work_orders(work_orders, run_id=self.crawl_id)

        # Baseline verification measures stored evidence; no deployment is implied.
        verifier = VerificationRunner(db_path=self.db_path)
        page_map = {p["url"]: p for p in self.storage.get_all_pages(self.crawl_id)}
        verification_results = []
        for order in work_orders:
            urls = json.loads(order["evidence_json"]).get("sample_urls", [])
            url = urls[0] if urls else self.target_url
            page = page_map.get(url)
            html = self.content_store.get(page["content_hash"]) if page and page.get("content_hash") else None
            verification_results.append(verifier.verify_work_order(order, target_url=url, html_content=html, page_data=page))
        with open(os.path.join(self.output_dir, "verification-results.json"), "w") as output:
            json.dump({"phase": "baseline_before_remediation", "results": verification_results}, output, indent=2)

        tickets_dir = os.path.join(self.output_dir, "tickets")
        ticket_stats = wo_mgr.export_all_tickets(self.crawl_id, tickets_dir)

        # Claims Linter Quality Gate
        self.check_cancelled()
        self.emit_progress("P5_VALIDATED_OPPORTUNITIES", 86.0, "Executing Claims Linter quality gate against forbidden claims...")
        claims_linter = ClaimsLinter()
        lint_violations = []
        for wo in work_orders:
            lint_violations.extend(claims_linter.lint_work_order(wo))

        lint_report_path = os.path.join(self.output_dir, 'lint-report.json')
        claims_linter.export_report(lint_violations, lint_report_path)

        self.emit_progress("P5_VALIDATED_OPPORTUNITIES", 90.0, f"Validated opportunities prioritized; {len(work_orders)} work orders generated.")
        self.pass_timings["P5_VALIDATED_OPPORTUNITIES"] = round(time.monotonic() - t0, 2)
        return {
            "work_orders": work_orders,
            "verification_count": len(verification_results),
            "ticket_stats": ticket_stats,
            "lint_violations_count": len(lint_violations),
            "lint_report_path": lint_report_path
        }

    # -------------------------------------------------------------------------
    # PASS 6: REPORTS
    # -------------------------------------------------------------------------
    async def run_pass_6_deliverables(self, p5_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """P6: Render reports and deliverables."""
        self.check_cancelled()
        t0 = time.monotonic()
        self.emit_progress("P6_REPORTS", 91.0, "Rendering reports and CSV suites...")

        stats = self.storage.get_stats(self.crawl_id)
        audit_date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # 6a. Master 28-Section Audit Word Report
        master_docx_path = os.path.join(self.output_dir, "SEOJEV_V3_AUDIT_REPORT.docx")
        master_docx_gen = MasterDocxReportGenerator(output_path=master_docx_path, db_path=self.db_path)
        master_docx_gen.generate_master_report(self.crawl_id, self.target_url)

        # 6b. Master Executive Summary Word Report
        exec_master_path = os.path.join(self.output_dir, "SEOJEV_EXECUTIVE_SUMMARY.docx")
        exec_master_gen = MasterExecutiveSummaryGenerator(output_path=exec_master_path, db_path=self.db_path)
        exec_master_gen.generate(self.crawl_id, self.target_url)

        # 6c. 25+ Stable CSV Dataset Suite
        self.check_cancelled()
        csv_suite_dir = os.path.join(self.output_dir, "csv")
        csv_suite_exporter = CSVSuiteExporter(output_dir=csv_suite_dir, db_path=self.db_path)
        csv_exported = csv_suite_exporter.export_all(self.crawl_id)

        # 6d. Offline Interactive HTML Explorer
        self.check_cancelled()
        self.emit_progress("P6_REPORTS", 96.0, "Generating offline interactive HTML Explorer dashboard...")
        html_explorer_path = os.path.join(self.output_dir, "explorer.html")
        html_explorer_gen = HTMLExplorerGenerator(output_path=html_explorer_path, db_path=self.db_path)
        domain_clean = self.target_url.replace("https://", "").replace("http://", "").strip("/")
        html_explorer_gen.generate(domain=domain_clean, run_id=self.crawl_id)

        # 6e. Summary JSON & Readme
        json_gen = JSONReportGenerator(output_dir=self.output_dir)
        pages = self.storage.get_all_pages(self.crawl_id)
        all_templates = self.storage.get_all_templates(self.crawl_id)
        all_issues = self.storage.get_all_issues(self.crawl_id)
        page_types_dist = dict(Counter(p.get("page_type", "other") for p in pages))
        status_dist = dict(Counter(p.get("status_code", 0) for p in pages))
        issue_cat_dist = dict(Counter(i.get("category", "other") for i in all_issues))

        json_gen.generate_crawl_summary_json(self.target_url, self.crawl_id, stats, page_types_dist, status_dist, issue_cat_dist)
        json_gen.generate_site_profile(self.target_url, stats.urls_discovered, page_types_dist, len(all_templates), out_path=os.path.join(self.output_dir, "site-profile.json"))
        summary = json_gen.generate_summary_json(self.target_url, self.crawl_id, audit_date, stats, getattr(self, "_laya_summary", {}))
        summary["laya"] = getattr(self, "_laya_summary", {})
        with open(os.path.join(self.output_dir, "summary.json"), "w") as output:
            json.dump(summary, output, indent=2)
        json_gen.generate_readme(self.target_url, self.crawl_id, stats)

        self.storage.update_crawl_status(self.crawl_id, "completed", datetime.datetime.now().isoformat())

        self.emit_progress("P6_REPORTS", 100.0, "Audit completed successfully. Reports compiled.")
        self.pass_timings["P6_REPORTS"] = round(time.monotonic() - t0, 2)

        return {
            "master_docx": master_docx_path,
            "executive_docx": exec_master_path,
            "html_explorer": html_explorer_path,
            "csv_suite_dir": csv_suite_dir,
            "csv_exported_count": len(csv_exported) if isinstance(csv_exported, dict) else 25,
            "status": "completed"
        }

    # -------------------------------------------------------------------------
    # RUN ALL PASSES
    # -------------------------------------------------------------------------
    async def run_all(self) -> Dict[str, Any]:
        """Runs Crawl → Evidence → Reduction → Laya → Validation → Reports."""
        start_wall_time = time.monotonic()
        try:
            self.check_cancelled()
            LayaSEOAnalyzer.get_singleton(self.config.get("laya", {}).get("model_id", "aac6fef/laya-mlx")).preflight()
            # P1: Crawl
            if self.is_stage_complete("P1_CRAWL"):
                self.emit_progress("P1_CRAWL", 25.0, f"Stage P1_CRAWL already completed for {self.crawl_id}. Resuming from checkpoint.")
                p1_res = {"crawl_id": self.crawl_id, "resumed": True}
            else:
                p1_res = await self.run_pass_1_crawl()
                self.mark_stage_complete("P1_CRAWL", p1_res)
            self.check_cancelled()

            # P2: Deterministic evidence
            if self.is_stage_complete("P2_DETERMINISTIC_EVIDENCE"):
                self.emit_progress("P2_DETERMINISTIC_EVIDENCE", 50.0, f"Deterministic evidence already completed for {self.crawl_id}.")
                p2_res = {"crawl_id": self.crawl_id, "resumed": True}
            else:
                p2_res = await self.run_pass_2_signals(p1_res)
                self.mark_stage_complete("P2_DETERMINISTIC_EVIDENCE", {"status": "completed"})
            self.check_cancelled()

            # P3: Candidate/template reduction
            if self.is_stage_complete("P3_CANDIDATE_REDUCTION"):
                self.emit_progress("P3_CANDIDATE_REDUCTION", 70.0, f"Candidate reduction already completed for {self.crawl_id}.")
                p3_res = {"crawl_id": self.crawl_id, "resumed": True}
            else:
                p3_res = await self.run_pass_3_search_opportunities(p2_res)
                self.mark_stage_complete("P3_CANDIDATE_REDUCTION", {"status": "completed"})
            self.check_cancelled()

            # P4: Laya primary SEO decision
            if self.is_stage_complete("P4_LAYA_DECISION_ENGINE"):
                self.emit_progress("P4_LAYA_DECISION_ENGINE", 80.0, f"Laya SEO decisions already completed for {self.crawl_id}.")
                with sqlite3.connect(self.db_path) as conn:
                    p4_res = json.loads(conn.execute("SELECT metadata_json FROM stage_checkpoints WHERE crawl_id=? AND stage='P4_LAYA_DECISION_ENGINE'", (self.crawl_id,)).fetchone()[0])
                self._laya_summary = p4_res["laya_summary"]
            else:
                p4_res = await self.run_pass_4_laya_decision(p3_res)
                self.mark_stage_complete("P4_LAYA_DECISION_ENGINE", p4_res)
            self.check_cancelled()

            # P5: Validated opportunities, priority, and work orders
            if self.is_stage_complete("P5_VALIDATED_OPPORTUNITIES"):
                self.emit_progress("P5_VALIDATED_OPPORTUNITIES", 90.0, f"Validated opportunities already completed for {self.crawl_id}.")
                p5_res = {"crawl_id": self.crawl_id, "resumed": True}
            else:
                p5_res = await self.run_pass_5_work_orders(p4_res)
                self.mark_stage_complete("P5_VALIDATED_OPPORTUNITIES", {"status": "completed"})
            self.check_cancelled()

            # P6: Reports
            if self.is_stage_complete("P6_REPORTS"):
                self.emit_progress("P6_REPORTS", 100.0, f"Reports already completed for {self.crawl_id}.")
                p6_res = {"crawl_id": self.crawl_id, "resumed": True}
            else:
                p6_res = await self.run_pass_6_deliverables(p5_res)
                self.mark_stage_complete("P6_REPORTS", {"status": "completed"})

            total_duration = round(time.monotonic() - start_wall_time, 2)
            stats = self.storage.get_stats(self.crawl_id)
            laya_analyzer = LayaSEOAnalyzer.get_singleton()

            pages_crawled = stats.urls_crawled or len(self.storage.get_all_pages(self.crawl_id))
            pages_per_sec = round(pages_crawled / max(total_duration, 0.001), 2)
            db_time = getattr(self.storage, "total_db_write_time", 0.0)

            # Section 21 exact RUN SUMMARY
            summary_banner = (
                f"\nRUN SUMMARY\n"
                f"===========\n\n"
                f"run_id: {self.crawl_id}\n\n"
                f"pages_discovered: {stats.urls_discovered}\n"
                f"pages_crawled: {pages_crawled}\n"
                f"pages_skipped: {stats.urls_skipped}\n"
                f"pages_failed: {stats.urls_failed}\n\n"
                f"crawl_seconds: {self.pass_timings.get('P1_CRAWL', 0.0):.2f}\n"
                f"evidence_seconds: {self.pass_timings.get('P2_DETERMINISTIC_EVIDENCE', 0.0):.2f}\n"
                f"reduction_seconds: {self.pass_timings.get('P3_CANDIDATE_REDUCTION', 0.0):.2f}\n"
                f"laya_seconds: {self.pass_timings.get('P4_LAYA_DECISION_ENGINE', 0.0):.2f}\n"
                f"validated_opportunity_seconds: {self.pass_timings.get('P5_VALIDATED_OPPORTUNITIES', 0.0):.2f}\n"
                f"report_seconds: {self.pass_timings.get('P6_REPORTS', 0.0):.2f}\n\n"
                f"laya_initializations: {laya_analyzer.initialization_count}\n"
                f"laya_inference_calls: {p4_res.get('laya_summary', {}).get('inference_count', laya_analyzer.inference_calls)}\n"
                f"laya_cache_hits: {p4_res.get('laya_summary', {}).get('total_cache_hits', laya_analyzer.cache_hits)}\n"
                f"laya_decisions: {p4_res.get('laya_summary', {}).get('total_decisions', laya_analyzer.decisions_count)}\n"
                f"laya_p50_ms: {p4_res.get('laya_summary', {}).get('p50_ms', 0):.1f}\n"
                f"laya_p95_ms: {p4_res.get('laya_summary', {}).get('p95_ms', 0):.1f}\n"
                f"laya_queue_drops: {p4_res.get('laya_summary', {}).get('queue_drops', 0)}\n\n"
                f"db_write_seconds: {db_time:.2f}\n\n"
                f"total_seconds: {total_duration:.2f}\n"
                f"pages_per_second: {pages_per_sec:.2f}\n"
            )
            print(summary_banner)
            logger.info(summary_banner)

            return {
                "status": "completed",
                "crawl_id": self.crawl_id,
                "target_url": self.target_url,
                "duration_seconds": total_duration,
                "pass_timings": self.pass_timings,
                "stats": stats,
                "deliverables": p6_res,
                "laya_summary": p4_res.get("laya_summary", {})
            }

        except PipelineCancelledException as exc:
            self.storage.update_crawl_status(self.crawl_id, "cancelled", datetime.datetime.now().isoformat())
            self.emit_progress("CANCELLED", 0.0, f"Run cancelled: {str(exc)}")
            return {
                "status": "cancelled",
                "crawl_id": self.crawl_id,
                "target_url": self.target_url,
                "reason": str(exc),
                "pass_timings": self.pass_timings
            }
        except Exception as exc:
            self.storage.update_crawl_status(self.crawl_id, "failed", datetime.datetime.now().isoformat())
            self.emit_progress("FAILED", 0.0, f"Pipeline error: {str(exc)}")
            raise
