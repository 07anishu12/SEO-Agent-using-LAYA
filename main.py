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

def main():
    parser = argparse.ArgumentParser(description="SEOJEV V2 — Universal Scalable SEO / AEO / GEO Intelligence Engine")
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
