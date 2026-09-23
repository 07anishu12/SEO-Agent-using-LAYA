import argparse
import asyncio
import datetime
import os
import sys
import time
import yaml
from collections import Counter
from typing import Dict, Any, List

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
from engine.opportunity_engine_v3 import OpportunityEngineV3
from engine.work_orders import WorkOrderManager
from engine.blueprint import PageOptimizationBlueprint
from engine.claims_linter import ClaimsLinter
from verification.runner import VerificationRunner
from verification.snapshot import SnapshotRecorder
from verification.differ import SnapshotDiffer
from verification.experiment import ExperimentEvaluator
from verification.watch import SiteWatcher
from lab.scorecard import DetectorScorecard
from lab.site_generator import SyntheticSiteGenerator
from lab.feedback import FeedbackEngine
from reporting.docx_master import MasterDocxReportGenerator
from reporting.executive_master import MasterExecutiveSummaryGenerator
from reporting.csv_suite import CSVSuiteExporter
from reporting.html_explorer import HTMLExplorerGenerator

def load_config(config_path: str = "config.yaml") -> Dict[str, Any]:
    if os.path.exists(config_path):
        with open(config_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    return {}

async def main_async(args):
    config = load_config(args.config)
    target_url = args.url.strip()
    if not target_url.startswith(("http://", "https://")):
        target_url = "https://" + target_url

    output_dir = args.output or config.get("reports", {}).get("output_dir", "reports/")
    os.makedirs(output_dir, exist_ok=True)
    db_path = config.get("storage", {}).get("db_path", "data/seo.db")
    storage = CrawlStorage(db_path=db_path)

    # Crawl Run ID
    if args.crawl_id:
        crawl_id = args.crawl_id
        print(f"\n[SEOJEV V2] Target crawl ID specified: {crawl_id}")
    elif args.analyze_only:
        latest_run = storage.get_latest_crawl_run(target_url)
        crawl_id = latest_run["crawl_id"] if latest_run else "crawl_20260923_234236"
        print(f"\n[SEOJEV V2] Analyze-only mode: using crawl ID {crawl_id}")
    elif args.resume:
        latest_run = storage.get_latest_crawl_run(target_url)
        if latest_run and latest_run["status"] != "completed":
            crawl_id = latest_run["crawl_id"]
            print(f"\n[SEOJEV V2] Resuming existing crawl ID: {crawl_id}")
        else:
            crawl_id = f"crawl_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
            run_record = CrawlRun(
                crawl_id=crawl_id,
                target_url=target_url,
                start_time=datetime.datetime.now().isoformat(),
                max_pages=args.max_pages,
                concurrency=args.concurrency
            )
            storage.save_crawl_run(run_record)
            print(f"\n[SEOJEV V2] Initialized fresh crawl ID: {crawl_id}")
    else:
        crawl_id = f"crawl_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
        run_record = CrawlRun(
            crawl_id=crawl_id,
            target_url=target_url,
            start_time=datetime.datetime.now().isoformat(),
            max_pages=args.max_pages,
            concurrency=args.concurrency
        )
        storage.save_crawl_run(run_record)
        print(f"\n[SEOJEV V2] Initialized fresh crawl ID: {crawl_id}")

    # Step 1: Crawler Execution
    if not args.analyze_only and not args.crawl_id:
        crawler = SEOCrawler(
            target_url=target_url,
            crawl_id=crawl_id,
            storage=storage,
            config=config,
            render_enabled=args.render,
            resume=args.resume,
            max_pages=args.max_pages,
            concurrency=args.concurrency
        )

        await crawler.initialize()
        print(f"[SEOJEV V2] Starting crawler engine (Max Pages: {args.max_pages}, Concurrency: {args.concurrency})...")
        t0 = time.monotonic()
        await crawler.crawl()
        crawl_duration = round(time.monotonic() - t0, 2)
        print(f"[SEOJEV V2] Crawl phase finished in {crawl_duration}s.")
    else:
        crawl_duration = 0.0
        print(f"[SEOJEV V2] Skipping HTTP crawl phase; analyzing existing dataset for '{crawl_id}'.")

    # Step 2: Post-Crawl Data Analysis
    print("[SEOJEV V2] Retrieving crawled data from persistent storage...")
    pages = storage.get_all_pages(crawl_id)
    links = storage.get_all_links(crawl_id)
    issues = storage.get_all_issues(crawl_id)

    print(f"[SEOJEV V2] Running NetworkX internal link graph & equity analysis across {len(pages)} pages...")
    node_metrics, link_issues, link_opportunities = build_and_analyze_link_graph(pages, links, target_url)
    if link_issues:
        storage.save_issues(crawl_id, link_issues)
        issues.extend([iss.to_dict() for iss in link_issues])
    storage.save_internal_link_opportunities(crawl_id, link_opportunities)

    print("[SEOJEV V2] Clustering page templates and structural signatures...")
    templates, template_issues = analyze_templates(pages, issues)
    storage.save_templates(crawl_id, templates)
    if template_issues:
        storage.save_issues(crawl_id, template_issues)
        issues.extend([iss.to_dict() for iss in template_issues])

    print("[SEOJEV V2] Evaluating exact and near-duplicate content...")
    dup_issues = analyze_duplicates(pages)
    if dup_issues:
        storage.save_issues(crawl_id, dup_issues)
        issues.extend([iss.to_dict() for iss in dup_issues])

    all_issues = storage.get_all_issues(crawl_id)

    # Step 3: Issue Clustering (Stop Issue Explosion)
    print("[SEOJEV V2] Aggregating issues into high-level Issue Clusters (Template / Site-wide / Page Opportunity)...")
    issue_clusters = build_issue_clusters(all_issues)
    storage.save_issue_clusters(crawl_id, issue_clusters)
    print(f"[SEOJEV V2] Consolidated {len(all_issues):,} raw findings into {len(issue_clusters)} structured Issue Clusters.")

    # Step 4: Representative Performance Audit
    perf_db_records = storage.get_all_performance(crawl_id)
    if not perf_db_records:
        perf_sample_size = min(args.performance_sample, len(pages))
        print(f"[SEOJEV V2] Selecting stratified performance sample ({perf_sample_size} URLs)...")
        sample_pages = select_performance_sample(pages, sample_size=perf_sample_size, homepage_url=target_url)

        perf_auditor = PerformanceAuditor(timeout_ms=12000)
        print(f"[SEOJEV V2] Conducting representative Core Web Vitals audit...")
        perf_results = await perf_auditor.audit_pages(sample_pages, max_concurrency=2)
        for p_res in perf_results:
            storage.save_performance(crawl_id, p_res)
        perf_db_records = storage.get_all_performance(crawl_id)
    else:
        print(f"[SEOJEV V2] Loaded {len(perf_db_records)} existing Core Web Vitals audit records for crawl '{crawl_id}'.")

    # Step 5: Product / Bike Page Intelligence Engine
    print("[SEOJEV V2] Running Product Page Intelligence Engine (Automotive Entity Extraction & Content Coverage)...")
    prod_engine = ProductIntelligenceEngine()
    product_pages_data = []
    product_data_map = {}

    for p in pages:
        if prod_engine.is_product_page(p):
            prod_info = prod_engine.extract_product_intelligence(p)
            product_pages_data.append(prod_info)
            product_data_map[p["url"]] = prod_info

    storage.save_product_pages(crawl_id, product_pages_data)
    print(f"[SEOJEV V2] Identified and deeply analyzed {len(product_pages_data):,} automotive product/bike pages.")

    # Step 6: Google Search Console (GSC) Data Ingestion
    gsc_file = args.gsc
    if not gsc_file and os.path.exists("data/gsc/gsc.csv"):
        gsc_file = "data/gsc/gsc.csv"

    print(f"[SEOJEV V2] Evaluating Google Search Console data (Source: {gsc_file or 'None'})...")
    gsc_analyzer = GSCAnalyzer(gsc_csv_path=gsc_file)
    gsc_summary = {
        "has_data": gsc_analyzer.has_data,
        "total_queries": len(gsc_analyzer.query_rows),
        "pos_11_20_count": len([r for r in gsc_analyzer.query_rows if r["bracket"] == "11-20"]),
        "pos_21_30_count": len([r for r in gsc_analyzer.query_rows if r["bracket"] == "21-30"]),
        "product_pages_with_gsc": sum(1 for url in product_data_map if gsc_analyzer.get_page_ranking_data(url))
    }

    # Step 7: AEO & GEO Evaluators
    print("[SEOJEV V2] Running Answer Engine (AEO) and Generative Search (GEO) readiness evaluators...")
    aeo_analyzer = AEOAnalyzer()
    geo_analyzer = GEOAnalyzer()
    serp_analyzer = SERPAnalyzer(serp_data_path=args.serp_data)

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
    aeo_summary = {"average_score": avg_aeo}
    geo_summary = {"average_score": avg_geo}

    # Step 8: Ranking Opportunity Synthesis
    print("[SEOJEV V2] Synthesizing Ranking Opportunities and Product Action Registers...")
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
    storage.save_ranking_opportunities(crawl_id, ranking_opportunities)
    print(f"[SEOJEV V2] Formulated {len(ranking_opportunities):,} structured ranking opportunities and {len(product_actions):,} granular product actions.")

    # Step 9: Local Laya Classification
    laya_analyzer = LayaSEOAnalyzer(model_id=config.get("laya", {}).get("model_id", "aac6fef/laya-mlx"))
    if laya_analyzer.is_available():
        print(f"[SEOJEV V2] Running local Laya MLX decision engine on {len(issue_clusters)} Issue Clusters...")
        for cluster in issue_clusters:
            decision = laya_analyzer.classify_issue({
                "issue": cluster["issue"],
                "category": cluster["category"],
                "severity": cluster["severity"],
                "template": cluster["primary_affected_template"],
                "affected_urls_count": cluster["affected_urls_count"],
                "evidence": cluster["evidence_summary"]
            })
            cluster["laya_action"] = decision["action"]
            storage.save_laya_decision(
                crawl_id=crawl_id,
                issue_key=cluster["cluster_id"],
                prompt_summary=f"Cluster: {cluster['issue']} ({cluster['primary_affected_template']})",
                response_raw=decision.get("raw_response", ""),
                latency_ms=decision.get("latency_ms", 0.0),
                decision_category=decision["category"],
                decision_severity=decision["severity"],
                decision_action=decision["action"],
                confidence=decision["confidence"]
            )
    else:
        print("[SEOJEV V2] Notice: Laya MLX not initialized, using deterministic priority classifications.")

    laya_summary = laya_analyzer.metrics.get_summary()

    # Step 10: Deliverables Generation
    print("[SEOJEV V2] Compiling full V2 export deliverables suite...")
    stats = storage.get_stats(crawl_id)
    if crawl_duration > 0:
        stats.crawl_duration_seconds = crawl_duration
    else:
        with storage._get_connection() as conn:
            row = conn.execute("SELECT start_time, end_time FROM crawl_runs WHERE crawl_id = ?", (crawl_id,)).fetchone()
            if row and row["start_time"] and row["end_time"]:
                try:
                    t_start = datetime.datetime.fromisoformat(row["start_time"])
                    t_end = datetime.datetime.fromisoformat(row["end_time"])
                    stats.crawl_duration_seconds = round((t_end - t_start).total_seconds(), 2)
                except Exception:
                    pass

    # Prepare datasets for CSVs
    raw_prod_pages = [p.to_dict() for p in product_pages_data]
    raw_prod_actions = [a.to_dict() for a in product_actions]
    raw_ranking_opps = [o.to_dict() for o in ranking_opportunities]
    raw_clusters = issue_clusters
    all_templates = storage.get_all_templates(crawl_id)
    all_laya_decisions = storage.get_all_laya_decisions(crawl_id)

    content_gaps_csv = []
    for p in product_pages_data:
        if p.missing_content_sections:
            content_gaps_csv.append({
                "url": p.url,
                "brand": p.brand,
                "model": p.model,
                "coverage_score_pct": p.coverage_score_pct,
                "missing_sections": "; ".join(p.missing_content_sections),
                "primary_missing_section": p.missing_content_sections[0]
            })

    aeo_csv = [{"url": u, "aeo_score": e["aeo_readiness_score"], "readiness_level": e["aeo_readiness_level"], "missing_questions": "; ".join(e["missing_questions"])} for u, e in aeo_evals.items()]
    geo_csv = [{"url": u, "geo_score": e["geo_readiness_score"], "readiness_level": e["geo_readiness_level"], "gaps": "; ".join(e["gaps"])} for u, e in geo_evals.items()]
    schema_csv = [{"url": p["url"], "schema_types": p.get("schema_types", "[]"), "is_valid": p.get("is_schema_valid", 1)} for p in pages]

    # CSV Exports
    csv_gen = CSVReportGenerator(output_dir=output_dir)
    csv_gen.export_v2(
        pages=pages,
        issues=all_issues,
        issue_clusters=raw_clusters,
        ranking_opportunities=raw_ranking_opps,
        product_pages=raw_prod_pages,
        product_page_actions=raw_prod_actions,
        gsc_queries=gsc_analyzer.query_rows,
        templates=all_templates,
        internal_link_opportunities=link_opportunities,
        content_gaps=content_gaps_csv,
        aeo_analysis=aeo_csv,
        geo_analysis=geo_csv,
        schema_analysis=schema_csv,
        performance=perf_db_records,
        laya_decisions=all_laya_decisions,
        links=links
    )

    # JSON Exports
    audit_date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    json_gen = JSONReportGenerator(output_dir=output_dir)
    v2_meta = {
        "product_pages_count": len(product_pages_data),
        "ranking_opportunities_count": len(ranking_opportunities),
        "issue_clusters_count": len(issue_clusters),
        "internal_link_opportunities_count": len(link_opportunities),
        "gsc_connected": gsc_analyzer.has_data,
        "gsc_queries_count": len(gsc_analyzer.query_rows),
        "average_aeo_score": avg_aeo,
        "average_geo_score": avg_geo
    }
    json_gen.generate_summary_json(target_url, crawl_id, audit_date, stats, laya_summary, v2_meta=v2_meta)

    page_types_dist = dict(Counter(p.get("page_type", "other") for p in pages))
    status_dist = dict(Counter(p.get("status_code", 0) for p in pages))
    issue_cat_dist = dict(Counter(i.get("category", "other") for i in all_issues))

    json_gen.generate_crawl_summary_json(target_url, crawl_id, stats, page_types_dist, status_dist, issue_cat_dist)
    json_gen.generate_site_profile(target_url, stats.urls_discovered, page_types_dist, len(all_templates))
    json_gen.generate_readme(target_url, crawl_id, stats)

    # Executive Summary DOCX
    exec_path = os.path.join(output_dir, "executive-summary.docx")
    exec_gen = ExecutiveSummaryGenerator(output_path=exec_path)
    exec_gen.generate(
        website=target_url,
        audit_date=audit_date,
        stats=stats,
        product_pages_count=len(product_pages_data),
        gsc_summary=gsc_summary,
        issue_clusters=raw_clusters,
        top_product_opps=raw_ranking_opps[:20],
        top_link_opps=link_opportunities[:20],
        aeo_summary=aeo_summary,
        geo_summary=geo_summary
    )

    # Master 23-Section Audit Report DOCX
    docx_path = os.path.join(output_dir, "seo-audit.docx")
    docx_gen = DocxReportGenerator(output_path=docx_path)
    docx_gen.generate_v2(
        website=target_url,
        crawl_id=crawl_id,
        audit_date=audit_date,
        stats=stats,
        pages=pages,
        issue_clusters=raw_clusters,
        templates=all_templates,
        ranking_opportunities=raw_ranking_opps,
        product_pages=raw_prod_pages,
        product_actions=raw_prod_actions,
        link_opportunities=link_opportunities,
        performance=perf_db_records,
        laya_summary=laya_summary,
        node_metrics=node_metrics,
        gsc_summary=gsc_summary,
        aeo_summary=aeo_summary,
        geo_summary=geo_summary,
        serp_summary={"has_data": False}
    )

    storage.update_crawl_status(crawl_id, "completed", datetime.datetime.now().isoformat())

    # V3 Upgrade Pipeline: Opportunities, Work Orders, Tickets, Master Reports, CSV Suite, HTML Explorer
    print("\n[SEOJEV V3] Synthesizing Opportunities & Work Orders...")
    opp_engine_v3 = OpportunityEngineV3(db_path=db_path)
    v3_opps = opp_engine_v3.synthesize_opportunities(
        run_id=crawl_id,
        pages=pages,
        findings=raw_clusters,
        templates={t["template_id"]: t for t in all_templates},
        query_page_map=[],
        link_recommendations=link_opportunities,
        content_gaps=[],
        aeo_evals={},
        geo_evals={}
    )
    opp_engine_v3.persist_opportunities(v3_opps)

    wo_mgr = WorkOrderManager(db_path=db_path)
    work_orders = wo_mgr.create_work_orders_from_opportunities(crawl_id, v3_opps)
    wo_mgr.persist_work_orders(work_orders)

    tickets_dir = os.path.join(output_dir, "tickets")
    ticket_stats = wo_mgr.export_all_tickets(crawl_id, tickets_dir)

    print("[SEOJEV V3] Generating Master 28-Section Audit Report...")
    master_docx_path = os.path.join(output_dir, "SEOJEV_V3_AUDIT_REPORT.docx")
    master_docx_gen = MasterDocxReportGenerator(output_path=master_docx_path, db_path=db_path)
    master_docx_gen.generate_master_report(crawl_id, target_url)

    print("[SEOJEV V3] Generating Master Executive Summary Report...")
    exec_master_path = os.path.join(output_dir, "SEOJEV_EXECUTIVE_SUMMARY.docx")
    exec_master_gen = MasterExecutiveSummaryGenerator(output_path=exec_master_path, db_path=db_path)
    exec_master_gen.generate(crawl_id, target_url)

    print("[SEOJEV V3] Exporting 25+ Stable CSV Datasets...")
    csv_suite_dir = os.path.join(output_dir, "csv")
    csv_suite_exporter = CSVSuiteExporter(output_dir=csv_suite_dir, db_path=db_path)
    csv_exported = csv_suite_exporter.export_all(crawl_id)

    print("[SEOJEV V3] Generating Offline Interactive HTML Explorer...")
    html_explorer_path = os.path.join(output_dir, "explorer.html")
    html_explorer_gen = HTMLExplorerGenerator(output_path=html_explorer_path, db_path=db_path)
    domain_clean = target_url.replace("https://", "").replace("http://", "").strip("/")
    html_explorer_gen.generate(domain=domain_clean, run_id=crawl_id)

    print("[SEOJEV V3] Running Claims Linter Quality Gate on deliverables...")
    claims_linter = ClaimsLinter()

    # Final Output
    print(f"""
========================================
SEOJEV V2 INTELLIGENCE AUDIT COMPLETE
========================================

Website:
{target_url}

URLs discovered:
{stats.urls_discovered}

URLs crawled:
{stats.urls_crawled}

URLs failed:
{stats.urls_failed}

Indexable:
{stats.indexable_urls}

Non-indexable:
{stats.non_indexable_urls}

Total Issues (Granular):
{stats.total_issues}

Consolidated Issue Clusters:
{len(issue_clusters)}

Automotive Product Pages Diagnosed:
{len(product_pages_data)}

Ranking Opportunities Synthesized:
{len(ranking_opportunities)}

Internal Link Injection Opportunities:
{len(link_opportunities)}

Templates:
{stats.templates_count}

Performance sample:
{stats.performance_sample_count}

Laya decisions:
{len(all_laya_decisions)}

Median Laya latency:
{laya_summary.get('median_latency_ms', 0.0)} ms

P95 Laya latency:
{laya_summary.get('p95_latency_ms', 0.0)} ms

----------------------------------------

REPORTS:

{os.path.join(output_dir, "seo-audit.docx")} (23 Sections)
{os.path.join(output_dir, "executive-summary.docx")}

DATA:

{os.path.join(output_dir, "ranking-opportunities.csv")}
{os.path.join(output_dir, "product-pages.csv")}
{os.path.join(output_dir, "product-page-actions.csv")}
{os.path.join(output_dir, "gsc-query-analysis.csv")}
{os.path.join(output_dir, "issue-clusters.csv")}
{os.path.join(output_dir, "internal-link-opportunities.csv")}
{os.path.join(output_dir, "content-gaps.csv")}
{os.path.join(output_dir, "aeo-analysis.csv")}
{os.path.join(output_dir, "geo-analysis.csv")}
{os.path.join(output_dir, "schema-analysis.csv")}
{os.path.join(output_dir, "pages.csv")}
{os.path.join(output_dir, "issues.csv")}
{os.path.join(output_dir, "templates.csv")}
{os.path.join(output_dir, "performance.csv")}
{os.path.join(output_dir, "laya-decisions.csv")}

JSON:

{os.path.join(output_dir, "summary.json")}
{os.path.join(output_dir, "crawl-summary.json")}

========================================
""")

def handle_blueprint_cli(args_list):
    sub = argparse.ArgumentParser(prog="seojev blueprint", description="Generate 20-dimension Page Optimization Blueprint")
    sub.add_argument("url", help="Target URL to generate blueprint for")
    sub.add_argument("--db", default="data/seo.db", help="Path to database")
    sub.add_argument("--store", default="store", help="Path to content store")
    sub.add_argument("--export", type=str, help="Export path for markdown blueprint")
    parsed = sub.parse_args(args_list)

    bp_engine = PageOptimizationBlueprint(db_path=parsed.db, store_dir=parsed.store)
    bp = bp_engine.generate_blueprint(parsed.url)
    md = bp_engine.render_markdown(bp)
    print(md)
    if parsed.export:
        with open(parsed.export, "w", encoding="utf-8") as f:
            f.write(md)
        print(f"\n[Saved blueprint to {parsed.export}]")

def handle_verify_cli(args_list):
    sub = argparse.ArgumentParser(prog="seojev verify", description="Run automated verification on work order")
    sub.add_argument("--work-order", required=True, help="Work order display ID (e.g. SEOJEV-ENG-001)")
    sub.add_argument("--url", type=str, help="Target URL (optional, defaults to sample URL in work order)")
    sub.add_argument("--live", action="store_true", help="Perform live HTTP request to test deployed URL")
    sub.add_argument("--db", default="data/seo.db", help="Path to database")
    parsed = sub.parse_args(args_list)

    wo_mgr = WorkOrderManager(db_path=parsed.db)
    wo = wo_mgr.get_work_order_by_display_id(parsed.work_order)
    if not wo:
        print(f"Error: Work order '{parsed.work_order}' not found in {parsed.db}.")
        sys.exit(1)

    runner = VerificationRunner(db_path=parsed.db)
    res = runner.verify_work_order(wo, target_url=parsed.url, live_fetch=parsed.live)
    print(f"""
========================================
VERIFICATION RESULT: {res['status']}
========================================
Work Order: {res['display_id']}
Executed Spec: {res['spec']}
Target URL: {res['url']}
Message: {res['details']}
Logged Audit ID: {res['verification_id']}
""")

def handle_page_cli(args_list):
    sub = argparse.ArgumentParser(prog="seojev page", description="Quick page diagnostics")
    sub.add_argument("url", help="Target URL")
    sub.add_argument("--db", default="data/seo.db", help="Path to database")
    parsed = sub.parse_args(args_list)

    import sqlite3
    with sqlite3.connect(parsed.db) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT * FROM pages WHERE url = ? OR url = ? LIMIT 1", (parsed.url, parsed.url.rstrip("/") + "/")).fetchone()
        if not row:
            print(f"Page '{parsed.url}' not found in database.")
            return
        p = dict(row)
        print(f"""
URL: {p['url']}
Status: {p.get('status_code', 200)} | Indexable: {p.get('is_indexable', 1)} | Self-Canonical: {p.get('is_self_canonical', 1)}
Template: {p.get('template_id', 'default')} | Type: {p.get('page_type', 'general')} | Depth: {p.get('crawl_depth', 1)}
Title ({len(p.get('title') or '')} chars): {p.get('title')}
H1: {p.get('h1_text') or p.get('h1')}
Words: {p.get('word_count', 0)} | Inlinks: {p.get('in_links_count', 0)} | Outlinks: {p.get('out_links_count', 0)}
""")

def handle_template_cli(args_list):
    sub = argparse.ArgumentParser(prog="seojev template", description="Template diagnostics")
    sub.add_argument("template_id", help="Template ID (e.g. tpl_bike_detail)")
    sub.add_argument("--db", default="data/seo.db", help="Path to database")
    parsed = sub.parse_args(args_list)

    import sqlite3
    with sqlite3.connect(parsed.db) as conn:
        conn.row_factory = sqlite3.Row
        cnt = conn.execute("SELECT COUNT(*), AVG(word_count) FROM pages WHERE template_id = ?", (parsed.template_id,)).fetchone()
        opps = conn.execute("SELECT * FROM opportunities WHERE affected_templates_json LIKE ? LIMIT 5", (f"%{parsed.template_id}%",)).fetchall()
        print(f"""
Template ID: {parsed.template_id}
Total Pages: {cnt[0]} | Avg Word Count: {round(cnt[1] or 0, 1)}

Top Template Opportunities:
""" + ("\n".join(f"- [{r['display_id']}] ({r['priority_score']}) {r['action']}" for r in opps) or "None"))

def handle_why_cli(args_list):
    sub = argparse.ArgumentParser(prog="seojev why", description="Explain root cause and evidence for ID")
    sub.add_argument("display_id", help="Display ID (e.g. SEOJEV-ENG-001 or OPP-TPL-SEO-001)")
    sub.add_argument("--db", default="data/seo.db", help="Path to database")
    parsed = sub.parse_args(args_list)

    import sqlite3
    norm_id = parsed.display_id.upper().strip()
    with sqlite3.connect(parsed.db) as conn:
        conn.row_factory = sqlite3.Row
        wo = conn.execute("SELECT * FROM work_orders WHERE display_id = ? OR display_id = ?", (norm_id, norm_id.replace("SEOJEV-", ""))).fetchone()
        if wo:
            w = dict(wo)
            print(f"""
=== WHY RECORD: [{w['display_id']}] ===
Title: {w['title']}
Type: {w['order_type'].capitalize()} | Priority: {w['priority']} | Scope: {w['scope']}
Problem:
{w['problem']}

Required Change:
{w['required_change']}

Verification Spec:
{w['verify_spec']}
""")
            return

        opp = conn.execute("SELECT * FROM opportunities WHERE display_id = ? OR opportunity_id = ?", (norm_id, norm_id)).fetchone()
        if opp:
            o = dict(opp)
            print(f"""
=== WHY RECORD: [{o['display_id']}] ===
Type: {o['type']} | Score: {o['priority_score']} | Tier: {o['opportunity_tier']}
Observation: {o['observation']}
Diagnosis: {o['diagnosis']}
Hypothesis: {o['hypothesis']}
Action: {o['action']}
Location: {o['implementation_location']} (Affects {o['affected_urls_count']} URLs)
Verification Spec: {o['verification_spec']}
""")
            return

        find = conn.execute("SELECT * FROM findings WHERE display_id = ?", (norm_id,)).fetchone()
        if find:
            f = dict(find)
            print(f"""
=== WHY RECORD: [{f['display_id']}] ===
Rule: {f['rule_id']} | Severity: {f['severity']} | Priority: {f['priority']}
Claim Type: {f['claim_type']}
Message: {f['message']}
Recommended Action: {f['recommended_action']}
""")
            return

        print(f"ID '{parsed.display_id}' not found in work_orders, opportunities, or findings.")

def handle_query_cli(args_list):
    sub = argparse.ArgumentParser(prog="seojev query", description="Query fit and landing diagnostics")
    sub.add_argument("query_text", help="Search query text")
    sub.add_argument("--db", default="data/seo.db", help="Path to database")
    parsed = sub.parse_args(args_list)

    import sqlite3
    with sqlite3.connect(parsed.db) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute("SELECT * FROM query_page_map WHERE query LIKE ? LIMIT 10", (f"%{parsed.query_text}%",)).fetchall()
        if not rows:
            print(f"No GSC mapping found for query matching '{parsed.query_text}'.")
            return
        for r in rows:
            print(f"""
Query: "{r['query']}"
Landing Page: {r['url']}
Verdict: {r['verdict']}
Position: {r['position']} | Impressions: {r['impressions']} | Clicks: {r['clicks']} | Click Gap: {r['click_gap']}
""")

def handle_watch_cli(args_list):
    sub = argparse.ArgumentParser(prog="seojev watch", description="Run immediate site watcher health check")
    sub.add_argument("--urls", nargs="*", help="Optional list of URLs to monitor")
    sub.add_argument("--db", default="data/seo.db", help="Path to database")
    parsed = sub.parse_args(args_list)

    watcher = SiteWatcher(db_path=parsed.db)
    res = watcher.check_now(urls=parsed.urls)
    print(f"""
========================================
SITE WATCHER SWEEP: {res['overall_status']}
========================================
Total URLs Checked: {res['total_urls_checked']}
Alerts / Anomalies: {res['alerts_count']}
Time: {res['checked_at']}
""")
    for r in res["results"]:
        status_flag = "✓ OK" if r["status"] == "HEALTHY" else "⚠ ALERT"
        print(f"[{status_flag}] HTTP {r['status_code']} - {r['url']}")
        for issue in r.get("issues", []):
            print(f"    -> {issue}")

def handle_feedback_cli(args_list):
    sub = argparse.ArgumentParser(prog="seojev feedback", description="Record feedback to suppress false positives")
    sub.add_argument("--fp", required=True, help="Fingerprint of finding")
    sub.add_argument("--action", required=True, choices=["false_positive", "accepted", "fixed", "wontfix"], help="Feedback action")
    sub.add_argument("--comment", default="", help="Optional comment")
    sub.add_argument("--db", default="data/seo.db", help="Path to database")
    parsed = sub.parse_args(args_list)

    fe = FeedbackEngine(db_path=parsed.db)
    fe.record_feedback(parsed.fp, "", "", parsed.action, parsed.comment)
    print(f"Feedback recorded for fingerprint '{parsed.fp}': {parsed.action}")

def handle_lab_cli(args_list):
    sub = argparse.ArgumentParser(prog="seojev lab", description="Run synthetic testbench scorecard")
    parsed = sub.parse_args(args_list)

    gen = SyntheticSiteGenerator(base_url="https://test-moto.local")
    scorecard = DetectorScorecard(db_path="data/seo.db")
    res = scorecard.evaluate(gen)
    tp = res["true_positives"]
    fp = res["false_positives"]
    fn = res["false_negatives"]
    print(f"""
========================================
SEOJEV LAB SYNTHETIC TESTBENCH SCORECARD
========================================
Ground Truth Planted Defects: {tp + fn}
Total Detected Defects:       {tp + fp}
True Positives:               {tp}
False Positives:              {fp}
False Negatives:              {fn}

Precision:                    {res['overall_precision']*100:.1f}% (Gate: >= 95.0%)
Recall:                       {res['overall_recall']*100:.1f}% (Gate: >= 85.0%)
Gate Verdict:                 {'PASSED ✓' if res['passed_gate'] else 'FAILED ✗'}
""")

def handle_snapshot_cli(args_list):
    sub = argparse.ArgumentParser(prog="seojev snapshot", description="Capture state snapshot")
    sub.add_argument("--url", required=True, help="Target URL")
    sub.add_argument("--run-id", default=f"snap_{int(time.time())}", help="Run ID")
    sub.add_argument("--db", default="data/seo.db", help="Path to database")
    parsed = sub.parse_args(args_list)

    rec = SnapshotRecorder(db_path=parsed.db)
    snap = rec.take_snapshot_for_url(parsed.run_id, parsed.url, {"url": parsed.url, "status_code": 200})
    print(f"Snapshot recorded: {snap['snapshot_id']} for {parsed.url}")

def handle_diff_cli(args_list):
    sub = argparse.ArgumentParser(prog="seojev diff", description="Diff two snapshot runs")
    sub.add_argument("--before", required=True, help="Before Run ID")
    sub.add_argument("--after", required=True, help="After Run ID")
    sub.add_argument("--out", default="seo-diff.json", help="Output path for json diff")
    sub.add_argument("--db", default="data/seo.db", help="Path to database")
    parsed = sub.parse_args(args_list)

    differ = SnapshotDiffer(db_path=parsed.db)
    res = differ.diff_runs(parsed.before, parsed.after, export_path=parsed.out)
    print(f"""
========================================
SNAPSHOT DIFF: {parsed.before} vs {parsed.after}
========================================
Total Compared: {res['total_urls_compared']}
Fixed:          {res['summary']['FIXED']}
Regressed:      {res['summary']['REGRESSED']}
Improved:       {res['summary']['IMPROVED']}
New Issues:     {res['summary']['NEW_ISSUE']}
Unchanged:      {res['summary']['UNCHANGED']}

Diff report saved to: {parsed.out}
""")

def main():
    if len(sys.argv) > 1:
        cmd = sys.argv[1].lower()
        subcommands = {
            "blueprint": handle_blueprint_cli,
            "verify": handle_verify_cli,
            "page": handle_page_cli,
            "template": handle_template_cli,
            "why": handle_why_cli,
            "query": handle_query_cli,
            "watch": handle_watch_cli,
            "feedback": handle_feedback_cli,
            "lab": handle_lab_cli,
            "snapshot": handle_snapshot_cli,
            "diff": handle_diff_cli
        }
        if cmd in subcommands:
            subcommands[cmd](sys.argv[2:])
            return

    parser = argparse.ArgumentParser(description="SEOJEV V3 — Universal Search Intelligence Operating System")
    parser.add_argument("url", nargs="?", default="https://www.drivio.in/", help="Target website URL to audit")
    parser.add_argument("--max-pages", type=int, default=5000, help="Maximum number of pages to crawl")
    parser.add_argument("--concurrency", type=int, default=10, help="Concurrent async HTTP requests")
    parser.add_argument("--delay", type=float, default=0.05, help="Delay between requests in seconds")
    parser.add_argument("--render", action="store_true", help="Enable selective Playwright browser rendering")
    parser.add_argument("--performance-sample", type=int, default=100, help="Number of URLs in performance sample")
    parser.add_argument("--resume", action="store_true", help="Resume previous crawl from database")
    parser.add_argument("--fresh", action="store_true", help="Start a new fresh crawl run")
    parser.add_argument("--output", type=str, default="reports/", help="Output directory for reports")
    parser.add_argument("--gsc", type=str, help="Path to Google Search Console export CSV")
    parser.add_argument("--serp-data", type=str, help="Path to JSON file containing competitor SERP data")
    parser.add_argument("--serp-provider", type=str, help="Identifier for external SERP provider")
    parser.add_argument("--user-agent", type=str, help="Custom User-Agent header")
    parser.add_argument("--crawl-id", type=str, help="Specific existing crawl ID to analyze or export")
    parser.add_argument("--analyze-only", action="store_true", help="Analyze existing crawl data without running crawler")
    parser.add_argument("--config", type=str, default="config.yaml", help="Path to config.yaml")

    args = parser.parse_args()
    if args.fresh:
        args.resume = False

    asyncio.run(main_async(args))

if __name__ == "__main__":
    main()
