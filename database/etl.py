"""
SEOJEV Phase 2: Idempotent SQLite -> PostgreSQL ETL Pipeline.
Ingests completed crawl runs and normalizes them into PostgreSQL with strict org_id isolation.
"""
import os
import json
import sqlite3
import hashlib
import urllib.parse
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import psycopg
from psycopg.types.json import Jsonb

from .connection import get_connection


def _safe_json_parse(value: Any, default: Any = None) -> Any:
    """Parses JSON string or returns default if invalid or already a collection."""
    if value is None:
        return default
    if isinstance(value, (dict, list)):
        return value
    if isinstance(value, str):
        s = value.strip()
        if not s:
            return default
        try:
            return json.loads(s)
        except Exception:
            return default
    return default


def _get_sqlite_tables(cursor: sqlite3.Cursor) -> set[str]:
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    return {row[0] for row in cursor.fetchall()}


def run_etl(
    sqlite_db_path: str,
    crawl_id: str,
    org_id: str = "org_default",
    site_id: Optional[str] = None,
    db_url: Optional[str] = None,
    pg_conn: Optional[psycopg.Connection] = None
) -> Dict[str, Any]:
    """
    Idempotent ETL job: extracts a crawl run from an SQLite database and
    upserts all records into multi-tenant PostgreSQL tables.
    """
    if not os.path.exists(sqlite_db_path):
        raise FileNotFoundError(f"SQLite database not found at '{sqlite_db_path}'")

    sqlite_conn = sqlite3.connect(sqlite_db_path)
    sqlite_conn.row_factory = sqlite3.Row
    sqlite_cur = sqlite_conn.cursor()

    active_tables = _get_sqlite_tables(sqlite_cur)

    # 1. Inspect crawl_runs / runs
    target_url = "http://unknown.local"
    start_time = None
    end_time = None
    status = "completed"
    config_json_raw = "{}"

    if "crawl_runs" in active_tables:
        sqlite_cur.execute(
            "SELECT * FROM crawl_runs WHERE crawl_id = ?",
            (crawl_id,)
        )
        run_row = sqlite_cur.fetchone()
        if run_row:
            target_url = run_row["target_url"] or target_url
            start_time = run_row["start_time"]
            end_time = run_row["end_time"]
            status = run_row["status"] or status
            config_json_raw = run_row["config_json"] or "{}"

    if "runs" in active_tables and target_url == "http://unknown.local":
        sqlite_cur.execute(
            "SELECT * FROM runs WHERE run_id = ?",
            (crawl_id,)
        )
        r_row = sqlite_cur.fetchone()
        if r_row:
            target_url = r_row["target_url"] or target_url
            start_time = r_row["start_time"] or start_time
            end_time = r_row["end_time"] or end_time
            status = r_row["status"] or status
            config_json_raw = r_row["config_json"] or config_json_raw

    # Compute domain and resolve site_id
    parsed = urllib.parse.urlsplit(target_url)
    domain = (parsed.netloc or parsed.path or "unknown.domain").lower()
    if not site_id:
        domain_hash = hashlib.sha256(f"{org_id}:{domain}".encode("utf-8")).hexdigest()[:16]
        site_id = f"site_{domain_hash}"

    # Calculate frontier counts from SQLite
    urls_discovered = 0
    urls_crawled = 0
    urls_failed = 0
    total_issues = 0

    if "urls" in active_tables:
        sqlite_cur.execute("SELECT count(*) FROM urls WHERE crawl_id = ?", (crawl_id,))
        urls_discovered = sqlite_cur.fetchone()[0]
        sqlite_cur.execute("SELECT count(*) FROM urls WHERE crawl_id = ? AND status = 'crawled'", (crawl_id,))
        urls_crawled = sqlite_cur.fetchone()[0]
        sqlite_cur.execute("SELECT count(*) FROM urls WHERE crawl_id = ? AND status = 'failed'", (crawl_id,))
        urls_failed = sqlite_cur.fetchone()[0]

    if "pages" in active_tables and urls_crawled == 0:
        sqlite_cur.execute("SELECT count(*) FROM pages WHERE crawl_id = ?", (crawl_id,))
        urls_crawled = sqlite_cur.fetchone()[0]

    if "issues" in active_tables:
        sqlite_cur.execute("SELECT count(*) FROM issues WHERE crawl_id = ?", (crawl_id,))
        total_issues = sqlite_cur.fetchone()[0]

    counts = {
        "orgs": 1,
        "sites": 1,
        "runs": 1,
        "templates": 0,
        "findings": 0,
        "opportunities": 0,
        "work_orders": 0,
        "snapshots": 0,
        "gsc_summary": 0,
        "feedback": 0,
    }

    # Connect to PostgreSQL
    conn_managed = False
    conn = pg_conn
    if conn is None:
        conn = get_connection(db_url)
        conn_managed = True

    try:
        with conn.cursor() as cur:
            # 1. UPSERT Organization
            cur.execute(
                """
                INSERT INTO orgs (id, name, slug)
                VALUES (%(id)s, %(name)s, %(slug)s)
                ON CONFLICT (id) DO NOTHING
                """,
                {
                    "id": org_id,
                    "name": f"Org {org_id}",
                    "slug": org_id.lower().replace("_", "-")
                }
            )

            # 2. UPSERT Site
            cur.execute(
                """
                INSERT INTO sites (id, org_id, domain, url, vertical, config_json)
                VALUES (%(id)s, %(org_id)s, %(domain)s, %(url)s, 'generic', %(config_json)s)
                ON CONFLICT (org_id, domain) DO UPDATE SET
                    url = EXCLUDED.url
                RETURNING id;
                """,
                {
                    "id": site_id,
                    "org_id": org_id,
                    "domain": domain,
                    "url": target_url,
                    "config_json": Jsonb(_safe_json_parse(config_json_raw, default={}))
                }
            )
            site_row = cur.fetchone()
            resolved_site_id = site_row["id"] if site_row else site_id

            # 3. UPSERT Run
            cur.execute(
                """
                INSERT INTO runs (
                    id, org_id, site_id, status, started_at, finished_at,
                    progress_pct, current_pass, config_snapshot_json,
                    urls_discovered, urls_crawled, urls_failed, total_issues
                )
                VALUES (
                    %(id)s, %(org_id)s, %(site_id)s, %(status)s, %(started_at)s, %(finished_at)s,
                    %(progress_pct)s, %(current_pass)s, %(config_snapshot_json)s,
                    %(urls_discovered)s, %(urls_crawled)s, %(urls_failed)s, %(total_issues)s
                )
                ON CONFLICT (id) DO UPDATE SET
                    org_id = EXCLUDED.org_id,
                    site_id = EXCLUDED.site_id,
                    status = EXCLUDED.status,
                    finished_at = EXCLUDED.finished_at,
                    progress_pct = EXCLUDED.progress_pct,
                    current_pass = EXCLUDED.current_pass,
                    urls_discovered = EXCLUDED.urls_discovered,
                    urls_crawled = EXCLUDED.urls_crawled,
                    urls_failed = EXCLUDED.urls_failed,
                    total_issues = EXCLUDED.total_issues;
                """,
                {
                    "id": crawl_id,
                    "org_id": org_id,
                    "site_id": resolved_site_id,
                    "status": status,
                    "started_at": start_time or datetime.now(timezone.utc).isoformat(),
                    "finished_at": end_time or datetime.now(timezone.utc).isoformat(),
                    "progress_pct": 100.0 if status == "completed" else 0.0,
                    "current_pass": "P6_DELIVERABLES" if status == "completed" else "UNKNOWN",
                    "config_snapshot_json": Jsonb(_safe_json_parse(config_json_raw, default={})),
                    "urls_discovered": urls_discovered,
                    "urls_crawled": urls_crawled,
                    "urls_failed": urls_failed,
                    "total_issues": total_issues
                }
            )

            # 4. UPSERT Templates
            if "templates" in active_tables:
                sqlite_cur.execute("SELECT * FROM templates WHERE crawl_id = ?", (crawl_id,))
                t_rows = sqlite_cur.fetchall()
                for tr in t_rows:
                    tid = tr["template_id"]
                    unique_id = f"{crawl_id}_{tid}"
                    chars = _safe_json_parse(tr["characteristics_json"], default={})
                    cur.execute(
                        """
                        INSERT INTO templates (
                            id, org_id, run_id, site_id, template_id,
                            page_type, page_count, avg_word_count, avg_inlinks, structural_signature
                        )
                        VALUES (
                            %(id)s, %(org_id)s, %(run_id)s, %(site_id)s, %(template_id)s,
                            %(page_type)s, %(page_count)s, %(avg_word_count)s, %(avg_inlinks)s, %(structural_signature)s
                        )
                        ON CONFLICT (id) DO UPDATE SET
                            org_id = EXCLUDED.org_id,
                            site_id = EXCLUDED.site_id,
                            page_type = EXCLUDED.page_type,
                            page_count = EXCLUDED.page_count,
                            avg_word_count = EXCLUDED.avg_word_count,
                            avg_inlinks = EXCLUDED.avg_inlinks,
                            structural_signature = EXCLUDED.structural_signature;
                        """,
                        {
                            "id": unique_id,
                            "org_id": org_id,
                            "run_id": crawl_id,
                            "site_id": resolved_site_id,
                            "template_id": tid,
                            "page_type": tr["dominant_page_type"],
                            "page_count": tr["page_count"] or 0,
                            "avg_word_count": chars.get("avg_word_count") if isinstance(chars, dict) else None,
                            "avg_inlinks": chars.get("avg_inlinks") if isinstance(chars, dict) else None,
                            "structural_signature": str(tr["characteristics_json"] or tr["sample_urls"] or "")
                        }
                    )
                    counts["templates"] += 1

            # 5. UPSERT Findings
            if "findings" in active_tables:
                sqlite_cur.execute("SELECT * FROM findings WHERE run_id = ?", (crawl_id,))
                f_rows = sqlite_cur.fetchall()
                for fr in f_rows:
                    fp = fr["fingerprint"]
                    unique_id = f"{crawl_id}_{fp}"
                    ev_refs = _safe_json_parse(fr["evidence_refs_json"], default=[])
                    cur.execute(
                        """
                        INSERT INTO findings (
                            id, org_id, run_id, site_id, display_id,
                            rule_id, scope_key, subject, claim_type,
                            severity, priority, template_id, url,
                            message, evidence_refs, recommended_action
                        )
                        VALUES (
                            %(id)s, %(org_id)s, %(run_id)s, %(site_id)s, %(display_id)s,
                            %(rule_id)s, %(scope_key)s, %(subject)s, %(claim_type)s,
                            %(severity)s, %(priority)s, %(template_id)s, %(url)s,
                            %(message)s, %(evidence_refs)s, %(recommended_action)s
                        )
                        ON CONFLICT (id) DO UPDATE SET
                            org_id = EXCLUDED.org_id,
                            site_id = EXCLUDED.site_id,
                            display_id = EXCLUDED.display_id,
                            severity = EXCLUDED.severity,
                            priority = EXCLUDED.priority,
                            message = EXCLUDED.message,
                            evidence_refs = EXCLUDED.evidence_refs,
                            recommended_action = EXCLUDED.recommended_action;
                        """,
                        {
                            "id": unique_id,
                            "org_id": org_id,
                            "run_id": crawl_id,
                            "site_id": resolved_site_id,
                            "display_id": fr["display_id"],
                            "rule_id": fr["rule_id"],
                            "scope_key": fr["scope_key"],
                            "subject": fr["subject"],
                            "claim_type": fr["claim_type"] or "OBSERVED",
                            "severity": fr["severity"],
                            "priority": fr["priority"],
                            "template_id": fr["template_id"],
                            "url": fr["url"],
                            "message": fr["message"],
                            "evidence_refs": Jsonb(ev_refs if isinstance(ev_refs, list) else []),
                            "recommended_action": fr["recommended_action"]
                        }
                    )
                    counts["findings"] += 1

            # 6. UPSERT Opportunities
            if "opportunities" in active_tables:
                sqlite_cur.execute("SELECT * FROM opportunities WHERE run_id = ?", (crawl_id,))
                opp_rows = sqlite_cur.fetchall()
                for opp in opp_rows:
                    fp = opp["fingerprint"]
                    unique_id = f"{crawl_id}_{fp}"
                    factors = _safe_json_parse(opp["priority_factors_json"], default={})
                    aff_tpls = _safe_json_parse(opp["affected_templates_json"], default=[])
                    sample_urls = _safe_json_parse(opp["sample_urls_json"], default=[])

                    cur.execute(
                        """
                        INSERT INTO opportunities (
                            id, org_id, run_id, site_id, fingerprint, display_id,
                            type, tier, confidence, effort, priority_score,
                            factors_json, evidence_refs, observation, diagnosis,
                            hypothesis, action, implementation_location,
                            affected_templates, affected_urls_count, sample_urls, verification_spec
                        )
                        VALUES (
                            %(id)s, %(org_id)s, %(run_id)s, %(site_id)s, %(fingerprint)s, %(display_id)s,
                            %(type)s, %(tier)s, %(confidence)s, %(effort)s, %(priority_score)s,
                            %(factors_json)s, %(evidence_refs)s, %(observation)s, %(diagnosis)s,
                            %(hypothesis)s, %(action)s, %(implementation_location)s,
                            %(affected_templates)s, %(affected_urls_count)s, %(sample_urls)s, %(verification_spec)s
                        )
                        ON CONFLICT (id) DO UPDATE SET
                            org_id = EXCLUDED.org_id,
                            site_id = EXCLUDED.site_id,
                            tier = EXCLUDED.tier,
                            confidence = EXCLUDED.confidence,
                            effort = EXCLUDED.effort,
                            priority_score = EXCLUDED.priority_score,
                            factors_json = EXCLUDED.factors_json,
                            action = EXCLUDED.action,
                            diagnosis = EXCLUDED.diagnosis,
                            affected_templates = EXCLUDED.affected_templates,
                            affected_urls_count = EXCLUDED.affected_urls_count,
                            verification_spec = EXCLUDED.verification_spec;
                        """,
                        {
                            "id": unique_id,
                            "org_id": org_id,
                            "run_id": crawl_id,
                            "site_id": resolved_site_id,
                            "fingerprint": fp,
                            "display_id": opp["display_id"],
                            "type": opp["type"],
                            "tier": opp["opportunity_tier"],
                            "confidence": opp["confidence_tier"],
                            "effort": opp["effort"],
                            "priority_score": opp["priority_score"],
                            "factors_json": Jsonb(factors if isinstance(factors, dict) else {}),
                            "evidence_refs": Jsonb([]),
                            "observation": opp["observation"],
                            "diagnosis": opp["diagnosis"],
                            "hypothesis": opp["hypothesis"],
                            "action": opp["action"],
                            "implementation_location": opp["implementation_location"],
                            "affected_templates": Jsonb(affpl := aff_tpls if isinstance(aff_tpls, list) else []),
                            "affected_urls_count": opp["affected_urls_count"] or 0,
                            "sample_urls": Jsonb(s_urls := sample_urls if isinstance(sample_urls, list) else []),
                            "verification_spec": opp["verification_spec"]
                        }
                    )
                    counts["opportunities"] += 1

            # 7. UPSERT Work Orders
            if "work_orders" in active_tables:
                sqlite_cur.execute("SELECT * FROM work_orders WHERE run_id = ?", (crawl_id,))
                wo_rows = sqlite_cur.fetchall()
                for wo in wo_rows:
                    raw_wo_id = wo["work_order_id"] or wo["display_id"]
                    wid = f"{crawl_id}_{raw_wo_id}"
                    fp = wo["fingerprint"]
                    opp_ref_id = f"{crawl_id}_{fp}" if fp else None
                    cur.execute(
                        """
                        INSERT INTO work_orders (
                            id, org_id, run_id, site_id, opportunity_id,
                            display_id, title, order_type, status, priority,
                            scope, problem, required_change, verify_spec
                        )
                        VALUES (
                            %(id)s, %(org_id)s, %(run_id)s, %(site_id)s, %(opportunity_id)s,
                            %(display_id)s, %(title)s, %(order_type)s, %(status)s, %(priority)s,
                            %(scope)s, %(problem)s, %(required_change)s, %(verify_spec)s
                        )
                        ON CONFLICT (id) DO UPDATE SET
                            org_id = EXCLUDED.org_id,
                            run_id = EXCLUDED.run_id,
                            site_id = EXCLUDED.site_id,
                            opportunity_id = EXCLUDED.opportunity_id,
                            display_id = EXCLUDED.display_id,
                            title = EXCLUDED.title,
                            problem = EXCLUDED.problem,
                            required_change = EXCLUDED.required_change,
                            verify_spec = EXCLUDED.verify_spec,
                            priority = EXCLUDED.priority;
                        """,
                        {
                            "id": wid,
                            "org_id": org_id,
                            "run_id": crawl_id,
                            "site_id": resolved_site_id,
                            "opportunity_id": opp_ref_id,
                            "display_id": wo["display_id"],
                            "title": wo["title"],
                            "order_type": wo["order_type"] or "technical",
                            "status": "open",
                            "priority": wo["priority"],
                            "scope": wo["scope"],
                            "problem": wo["problem"],
                            "required_change": wo["required_change"],
                            "verify_spec": wo["verify_spec"]
                        }
                    )
                    counts["work_orders"] += 1

            # 8. Snapshots (optional)
            if "snapshots" in active_tables:
                sqlite_cur.execute("SELECT * FROM snapshots WHERE run_id = ?", (crawl_id,))
                snap_rows = sqlite_cur.fetchall()
                for snap in snap_rows:
                    sid = snap["snapshot_id"] or f"{crawl_id}_{hashlib.sha256(snap['url'].encode()).hexdigest()[:16]}"
                    snap_data = {
                        "url": snap["url"],
                        "title": snap["title"],
                        "canonical": snap["canonical"],
                        "meta_robots": snap["meta_robots"],
                        "h1_text": snap["h1_text"],
                        "status_code": snap["status_code"],
                        "schema_hash": snap["schema_hash"],
                        "content_hash": snap["content_hash"],
                        "metrics": _safe_json_parse(snap["metrics_json"], default={}),
                        "captured_at": snap["captured_at"]
                    }
                    cur.execute(
                        """
                        INSERT INTO snapshots (id, org_id, run_id, site_id, url, snapshot_data)
                        VALUES (%(id)s, %(org_id)s, %(run_id)s, %(site_id)s, %(url)s, %(snapshot_data)s)
                        ON CONFLICT (id) DO UPDATE SET
                            snapshot_data = EXCLUDED.snapshot_data;
                        """,
                        {
                            "id": sid,
                            "org_id": org_id,
                            "run_id": crawl_id,
                            "site_id": resolved_site_id,
                            "url": snap["url"],
                            "snapshot_data": Jsonb(snap_data)
                        }
                    )
                    counts["snapshots"] += 1

            # 9. GSC Summary (optional)
            if "gsc_rows" in active_tables:
                sqlite_cur.execute(
                    """
                    SELECT count(*) as total_q, sum(clicks) as total_c, sum(impressions) as total_i, avg(position) as avg_p
                    FROM gsc_rows WHERE run_id = ?
                    """,
                    (crawl_id,)
                )
                gsc_stat = sqlite_cur.fetchone()
                if gsc_stat and gsc_stat["total_q"] and gsc_stat["total_q"] > 0:
                    cur.execute(
                        """
                        INSERT INTO gsc_summary (
                            id, org_id, run_id, site_id, total_queries,
                            total_clicks, total_impressions, avg_position, striking_distance_count
                        )
                        VALUES (
                            %(id)s, %(org_id)s, %(run_id)s, %(site_id)s, %(total_queries)s,
                            %(total_clicks)s, %(total_impressions)s, %(avg_position)s, 0
                        )
                        ON CONFLICT (id) DO UPDATE SET
                            total_queries = EXCLUDED.total_queries,
                            total_clicks = EXCLUDED.total_clicks,
                            total_impressions = EXCLUDED.total_impressions,
                            avg_position = EXCLUDED.avg_position;
                        """,
                        {
                            "id": f"{crawl_id}_gsc",
                            "org_id": org_id,
                            "run_id": crawl_id,
                            "site_id": resolved_site_id,
                            "total_queries": gsc_stat["total_q"] or 0,
                            "total_clicks": gsc_stat["total_c"] or 0,
                            "total_impressions": gsc_stat["total_i"] or 0,
                            "avg_position": round(float(gsc_stat["avg_p"] or 0), 2)
                        }
                    )
                    counts["gsc_summary"] += 1

            # 10. Audit Log
            audit_id = f"audit_etl_{crawl_id}_{int(datetime.now(timezone.utc).timestamp())}"
            cur.execute(
                """
                INSERT INTO audit_log (
                    id, org_id, user_id, action, resource_type, resource_id, details_json
                )
                VALUES (
                    %(id)s, %(org_id)s, %(user_id)s, %(action)s, %(resource_type)s, %(resource_id)s, %(details_json)s
                )
                ON CONFLICT (id) DO NOTHING;
                """,
                {
                    "id": audit_id,
                    "org_id": org_id,
                    "user_id": "system_etl",
                    "action": "ETL_RUN_POPULATED",
                    "resource_type": "runs",
                    "resource_id": crawl_id,
                    "details_json": Jsonb(counts)
                }
            )

        conn.commit()

    finally:
        sqlite_conn.close()
        if conn_managed and conn is not None:
            conn.close()

    return {
        "status": "success",
        "crawl_id": crawl_id,
        "org_id": org_id,
        "site_id": resolved_site_id,
        "counts": counts
    }
