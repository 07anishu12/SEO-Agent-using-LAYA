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
# V3 Intelligence modules
from verticals.registry import VerticalRegistry
from extraction.provenance_extractor import ProvenanceExtractor
from technical.root_causes import RootCauseClusterer
from search.gsc_pipeline import GSCPipeline
from engine.evidence import EvidenceLedger, EvidenceRef
from understanding.index_funnel import IndexFunnelReconciler
from understanding.entity_graph import EntityGraphEngine
from engine.pipeline import SEOJEVPipeline, PipelineCancelledException

def load_config(config_path: str = "config.yaml") -> Dict[str, Any]:
    if os.path.exists(config_path):
        with open(config_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    return {}

async def main_async(args):
    config = load_config(args.config)
    options = {
        "max_pages": args.max_pages,
        "concurrency": args.concurrency,
        "delay": args.delay,
        "render": args.render,
        "performance_sample": args.performance_sample,
        "resume": args.resume,
        "fresh": args.fresh,
        "crawl_id": args.crawl_id,
        "analyze_only": args.analyze_only,
        "gsc": args.gsc,
        "serp_data": args.serp_data,
        "serp_provider": args.serp_provider,
        "user_agent": args.user_agent,
        "show_live_display": True
    }

    last_pass = None
    def cli_progress(pass_name: str, pct: float, message: str, meta: Optional[dict] = None):
        nonlocal last_pass
        if pass_name != last_pass:
            print(f"\n[{pass_name}] ({pct:.1f}%) {message}")
            last_pass = pass_name
        else:
            print(f"  -> [{pct:.1f}%] {message}")

    pipeline = SEOJEVPipeline(
        target_url=args.url,
        crawl_id=args.crawl_id,
        config=config,
        output_dir=args.output,
        progress_callback=cli_progress,
        options=options
    )

    result = await pipeline.run_all()
    if result.get("status") == "cancelled":
        print(f"\n[SEOJEV] Run was cancelled: {result.get('reason')}")
        return

    stats = result.get("stats")
    crawl_id = result.get("crawl_id")
    output_dir = args.output or config.get("reports", {}).get("output_dir", "reports/")
    target_url = pipeline.target_url

    print(f"""
========================================
SEOJEV INTELLIGENCE AUDIT COMPLETE
========================================

Website:
{target_url}

Crawl ID:
{crawl_id}

Duration:
{result.get('duration_seconds')}s

URLs discovered:
{getattr(stats, 'urls_discovered', 0)}

URLs crawled:
{getattr(stats, 'urls_crawled', 0)}

URLs failed:
{getattr(stats, 'urls_failed', 0)}

Indexable:
{getattr(stats, 'indexable_urls', 0)}

Non-indexable:
{getattr(stats, 'non_indexable_urls', 0)}

Total Issues (Granular):
{getattr(stats, 'total_issues', 0)}

Templates:
{getattr(stats, 'templates_count', 0)}

Performance sample:
{getattr(stats, 'performance_sample_count', 0)}

----------------------------------------

REPORTS:
{os.path.join(output_dir, "SEOJEV_V3_AUDIT_REPORT.docx")}
{os.path.join(output_dir, "SEOJEV_EXECUTIVE_SUMMARY.docx")}
{os.path.join(output_dir, "explorer.html")}

DATA SUITE:
{os.path.join(output_dir, "csv")} (25+ CSV tables)
{os.path.join(output_dir, "tickets")} (Jira, Linear, GitHub issues)

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
