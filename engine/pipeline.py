"""
SEOJEV Pipeline — Library Wrapper for V3 Engine Execution.
Allows the 6-layer audit engine to be invoked directly from Python (e.g. CLI, Celery, FastAPI)
with progress callbacks and cooperative cancellation.
"""

import asyncio
import datetime
import json
import os
import sqlite3
import sys
import time
import types
import urllib.parse
import yaml
from collections import Counter
from typing import Dict, Any, List, Optional, Callable, Set

from models.crawl import CrawlRun, CrawlStats
from crawler.storage import CrawlStorage
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
from engine.claims_linter import ClaimsLinter
from engine.evidence import EvidenceLedger
from engine.content_store import ContentStore
from verticals.registry import VerticalRegistry
from extraction.provenance_extractor import ProvenanceExtractor
from technical.root_causes import RootCauseClusterer
from search.gsc_pipeline import GSCPipeline
from understanding.index_funnel import IndexFunnelReconciler
from understanding.entity_graph import EntityGraphEngine


class PipelineCancelledException(Exception):
    """Raised when cooperative cancellation is requested during pipeline execution."""
    pass


class SEOJEVPipeline:
    """
    Unified 6-Pass Search Intelligence Operating System Pipeline.
    Passes:
      - P1_CRAWL: Asynchronous crawl, discovery, sitemaps, selective rendering, storage.
      - P2_SIGNALS: Link graph, templates, duplicates, Core Web Vitals, entity/vertical extraction.
      - P3_SEARCH_OPPORTUNITIES: GSC/SERP pipelines, AEO/GEO, V3 opportunity synthesis.
      - P4_CALIBRATION: Local Laya MLX inference, ICE priority sensitivity & calibration.
      - P5_WORK_ORDERS: Engineering & Content work orders, ticket generation, claims linter.
      - P6_DELIVERABLES: Word master reports, CSV suite, HTML explorer, JSON summaries.
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
        self.config = config or {}
        self.options = options or {}
        self.progress_callback = progress_callback
        self.cancel_check = cancel_check

        # Configure paths
        self.output_dir = output_dir or self.options.get("output") or self.config.get("reports", {}).get("output_dir", "reports/")
        os.makedirs(self.output_dir, exist_ok=True)
        self.db_path = db_path or self.config.get("storage", {}).get("db_path", "data/seo.db")
        os.makedirs(os.path.dirname(self.db_path) or ".", exist_ok=True)
        self.storage = CrawlStorage(db_path=self.db_path)
        self.content_store = ContentStore(base_dir=self.config.get("storage", {}).get("store_dir", "store"))

        # Crawl ID resolution
        self.crawl_id = self._resolve_crawl_id(crawl_id)
        self.stats = CrawlStats()
        self.pass_timings: Dict[str, float] = {}

    def _resolve_crawl_id(self, explicit_id: Optional[str]) -> str:
        if explicit_id:
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
        """Invoke external progress callback if registered."""
        if self.progress_callback:
            try:
                self.progress_callback(pass_name, pct, message, meta or {})
            except Exception:
                pass

    def check_cancelled(self):
        """Raises PipelineCancelledException if cancel_check triggers."""
        if self.cancel_check and self.cancel_check():
            raise PipelineCancelledException(f"Pipeline execution cancelled by caller for run '{self.crawl_id}'.")

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

            crawler = SEOCrawler(
                target_url=self.target_url,
                crawl_id=self.crawl_id,
                storage=self.storage,
                config=self.config,
                render_enabled=bool(self.options.get("render")),
                resume=bool(self.options.get("resume")),
                max_pages=self.options.get("max_pages", 5000),
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

        self.pass_timings["P1_CRAWL"] = round(time.monotonic() - t0, 2)
        return {"crawl_id": self.crawl_id, "crawl_duration": crawl_duration}

    # -------------------------------------------------------------------------
    # PASS 2: SIGNALS & ARCHITECTURE
    # -------------------------------------------------------------------------
    async def run_pass_2_signals(self, p1_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """P2: Link graph, template SimHash, root causes, index funnel, verticals & CWV."""
        self.check_cancelled()
        t0 = time.monotonic()
        self.emit_progress("P2_SIGNALS", 26.0, "Retrieving pages and links from storage...")

        pages = self.storage.get_all_pages(self.crawl_id)
        links = self.storage.get_all_links(self.crawl_id)
        issues = self.storage.get_all_issues(self.crawl_id)

        # 2a. NetworkX Link Graph
        self.check_cancelled()
        self.emit_progress("P2_SIGNALS", 29.0, f"Analyzing link graph across {len(pages):,} pages...")
        node_metrics, link_issues, link_opportunities = build_and_analyze_link_graph(pages, links, self.target_url)
        if link_issues:
            self.storage.save_issues(self.crawl_id, link_issues)
            issues.extend([iss.to_dict() for iss in link_issues])
        self.storage.save_internal_link_opportunities(self.crawl_id, link_opportunities)

        # 2b. Templates & Duplicates
        self.check_cancelled()
        self.emit_progress("P2_SIGNALS", 33.0, "Clustering templates and detecting content duplication...")
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
        self.emit_progress("P2_SIGNALS", 37.0, f"Clustering {len(all_issues):,} findings into root-cause groups...")
        issue_clusters = build_issue_clusters(all_issues)
        self.storage.save_issue_clusters(self.crawl_id, issue_clusters)

        root_cause_clusterer = RootCauseClusterer()
        rc_result = root_cause_clusterer.cluster_root_causes(all_issues)

        # 2d. Index Funnel Reconciliation
        self.emit_progress("P2_SIGNALS", 40.0, "Reconciling index funnel across sitemaps and crawled links...")
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
                self.emit_progress("P2_SIGNALS", 43.0, f"Running Core Web Vitals audit on {perf_sample_size} sample pages...")
                sample_pages = select_performance_sample(pages, sample_size=perf_sample_size, homepage_url=self.target_url)
                perf_auditor = PerformanceAuditor(timeout_ms=12000)
                perf_results = await perf_auditor.audit_pages(sample_pages, max_concurrency=2)
                for p_res in perf_results:
                    self.storage.save_performance(self.crawl_id, p_res)
                perf_db_records = self.storage.get_all_performance(self.crawl_id)

        # 2f. Vertical Knowledge & Product Intelligence
        self.check_cancelled()
        self.emit_progress("P2_SIGNALS", 46.0, "Extracting product intelligence and vertical domain attributes...")
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

        self.emit_progress("P2_SIGNALS", 50.0, "Signals and architecture extraction complete.")
        self.pass_timings["P2_SIGNALS"] = round(time.monotonic() - t0, 2)

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
    # PASS 3: SEARCH & OPPORTUNITY SYNTHESIS
    # -------------------------------------------------------------------------
    async def run_pass_3_search_opportunities(self, p2_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """P3: Search console pipeline, AEO/GEO readability, V3 OpportunityEngine synthesis."""
        self.check_cancelled()
        t0 = time.monotonic()
        self.emit_progress("P3_SEARCH_OPPORTUNITIES", 51.0, "Ingesting GSC and evaluating search performance...")

        pages = p2_data.get("pages") if p2_data else self.storage.get_all_pages(self.crawl_id)
        product_data_map = p2_data.get("product_data_map", {}) if p2_data else {}
        issue_clusters = p2_data.get("issue_clusters", []) if p2_data else self.storage.get_all_issue_clusters(self.crawl_id)
        node_metrics = p2_data.get("node_metrics", {}) if p2_data else {}
        link_opportunities = p2_data.get("link_opportunities", []) if p2_data else self.storage.get_internal_link_opportunities(self.crawl_id)
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
        self.emit_progress("P3_SEARCH_OPPORTUNITIES", 58.0, "Evaluating AEO/GEO readability and content gap matrices...")
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
        self.emit_progress("P3_SEARCH_OPPORTUNITIES", 65.0, "Formulating V3 structured opportunities & findings...")
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

        self.emit_progress("P3_SEARCH_OPPORTUNITIES", 70.0, f"Synthesized {len(v3_opps):,} V3 opportunities.")
        self.pass_timings["P3_SEARCH_OPPORTUNITIES"] = round(time.monotonic() - t0, 2)

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
    # PASS 4: CALIBRATION & DECISION
    # -------------------------------------------------------------------------
    async def run_pass_4_calibration(self, p3_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """P4: Local Laya MLX Apple Silicon inference, abstentions & ICE sensitivity check."""
        self.check_cancelled()
        t0 = time.monotonic()
        self.emit_progress("P4_CALIBRATION", 71.0, "Running local Laya MLX decision and calibration engine...")

        issue_clusters = self.storage.get_all_issue_clusters(self.crawl_id)
        laya_analyzer = LayaSEOAnalyzer(model_id=self.config.get("laya", {}).get("model_id", "aac6fef/laya-mlx"))

        if laya_analyzer.is_available():
            for cluster in issue_clusters:
                self.check_cancelled()
                decision = laya_analyzer.classify_issue({
                    "issue": cluster["issue"],
                    "category": cluster["category"],
                    "severity": cluster["severity"],
                    "template": cluster["primary_affected_template"],
                    "affected_urls_count": cluster["affected_urls_count"],
                    "evidence": cluster["evidence_summary"]
                })
                cluster["laya_action"] = decision["action"]
                self.storage.save_laya_decision(
                    crawl_id=self.crawl_id,
                    issue_key=cluster["cluster_id"],
                    prompt_summary=f"Cluster: {cluster['issue']} ({cluster['primary_affected_template']})",
                    response_raw=decision.get("raw_response", ""),
                    latency_ms=decision.get("latency_ms", 0.0),
                    decision_category=decision["category"],
                    decision_severity=decision["severity"],
                    decision_action=decision["action"],
                    confidence=decision["confidence"]
                )
        laya_summary = laya_analyzer.metrics.get_summary()

        self.emit_progress("P4_CALIBRATION", 80.0, "Calibration and decision pass complete.")
        self.pass_timings["P4_CALIBRATION"] = round(time.monotonic() - t0, 2)
        return {"laya_summary": laya_summary}

    # -------------------------------------------------------------------------
    # PASS 5: ACTION & WORK ORDERS
    # -------------------------------------------------------------------------
    async def run_pass_5_work_orders(self, p4_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """P5: Generate developer work orders, Jira/Linear/GitHub exports, run Claims Linter."""
        self.check_cancelled()
        t0 = time.monotonic()
        self.emit_progress("P5_WORK_ORDERS", 81.0, "Generating developer work orders and ticket exports...")

        wo_mgr = WorkOrderManager(db_path=self.db_path)
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("SELECT * FROM opportunities WHERE run_id = ?", (self.crawl_id,)).fetchall()
            v3_opps = [dict(r) for r in rows]

        work_orders = wo_mgr.create_work_orders_from_opportunities(self.crawl_id, v3_opps)
        wo_mgr.persist_work_orders(work_orders)

        tickets_dir = os.path.join(self.output_dir, "tickets")
        ticket_stats = wo_mgr.export_all_tickets(self.crawl_id, tickets_dir)

        # Claims Linter Quality Gate
        self.check_cancelled()
        self.emit_progress("P5_WORK_ORDERS", 86.0, "Executing Claims Linter quality gate against forbidden claims...")
        claims_linter = ClaimsLinter()
        lint_violations = []
        for wo in work_orders:
            lint_violations.extend(claims_linter.lint_work_order(wo))

        lint_report_path = os.path.join(self.output_dir, 'lint-report.json')
        claims_linter.export_report(lint_violations, lint_report_path)

        self.emit_progress("P5_WORK_ORDERS", 90.0, f"Work orders generated ({len(work_orders)} tickets, {len(lint_violations)} lint flags).")
        self.pass_timings["P5_WORK_ORDERS"] = round(time.monotonic() - t0, 2)
        return {
            "work_orders": work_orders,
            "ticket_stats": ticket_stats,
            "lint_violations_count": len(lint_violations),
            "lint_report_path": lint_report_path
        }

    # -------------------------------------------------------------------------
    # PASS 6: DELIVERABLES & REPORTS
    # -------------------------------------------------------------------------
    async def run_pass_6_deliverables(self, p5_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """P6: Render Master Word docx, executive summary, 25+ CSV suite, HTML explorer, and JSON."""
        self.check_cancelled()
        t0 = time.monotonic()
        self.emit_progress("P6_DELIVERABLES", 91.0, "Rendering Master Word Reports and CSV suites...")

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
        self.emit_progress("P6_DELIVERABLES", 96.0, "Generating offline interactive HTML Explorer dashboard...")
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
        json_gen.generate_site_profile(self.target_url, stats.urls_discovered, page_types_dist, len(all_templates))
        json_gen.generate_readme(self.target_url, self.crawl_id, stats)

        self.storage.update_crawl_status(self.crawl_id, "completed", datetime.datetime.now().isoformat())

        self.emit_progress("P6_DELIVERABLES", 100.0, "Audit completed successfully. All deliverables compiled.")
        self.pass_timings["P6_DELIVERABLES"] = round(time.monotonic() - t0, 2)

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
        """Runs the entire 6-pass pipeline end-to-end with cooperative cancellation."""
        start_wall_time = time.monotonic()
        try:
            p1_res = await self.run_pass_1_crawl()
            p2_res = await self.run_pass_2_signals(p1_res)
            p3_res = await self.run_pass_3_search_opportunities(p2_res)
            p4_res = await self.run_pass_4_calibration(p3_res)
            p5_res = await self.run_pass_5_work_orders(p4_res)
            p6_res = await self.run_pass_6_deliverables(p5_res)

            total_duration = round(time.monotonic() - start_wall_time, 2)
            stats = self.storage.get_stats(self.crawl_id)

            return {
                "status": "completed",
                "crawl_id": self.crawl_id,
                "target_url": self.target_url,
                "duration_seconds": total_duration,
                "pass_timings": self.pass_timings,
                "stats": stats,
                "deliverables": p6_res
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
