"""
SEOJEV Phase 2: CI/CD Deployment Regression Webhook Service (Stage 10e).

Implements Section 6.2:
deploy webhook -> scoped re-crawl -> snapshot -> previous snapshot -> diff -> regression classification -> result delivery
"""
import asyncio
import hashlib
import json
import logging
import os
import time
import urllib.parse
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

from psycopg.types.json import Jsonb

from database.connection import get_connection
from jobs.queue import RunQueue
from jobs.worker import execute_run_task
from verification.differ import SnapshotDiffer
from api.routers.diff import _fetch_snapshots_for_run, _fetch_template_map
from services.notifications import NotificationDispatcher

logger = logging.getLogger("seojev.cicd")


def execute_cicd_deploy_check(
    site_id: str,
    org_id: str,
    payload: Dict[str, Any],
    dispatcher: Optional[NotificationDispatcher] = None,
    redis_url: Optional[str] = None
) -> Dict[str, Any]:
    """
    Executes an end-to-end CI/CD regression check:
    1. Validates site ownership and tenant isolation.
    2. Resolves scoped URLs.
    3. Runs scoped crawl and captures snapshots.
    4. Finds previous baseline snapshot and computes diff.
    5. Classifies regressions reusing SEOJEV's classification.
    6. Delivers results to Slack, PR comment sink, and webhooks.
    """
    db_url = os.environ.get("DATABASE_URL", "postgresql:///seojev_test")
    disp = dispatcher or NotificationDispatcher(db_url=db_url)
    r_url = redis_url or os.environ.get("REDIS_URL", "redis://localhost:6379/0")

    # 1. Site ownership & tenant isolation
    with get_connection(db_url) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, org_id, domain, url FROM sites WHERE id = %s AND org_id = %s",
                (site_id, org_id)
            )
            site = cur.fetchone()

    if not site:
        raise ValueError(f"Site {site_id} not found for org {org_id}")

    base_url = site["url"].rstrip("/")

    # 2. Extract deployment parameters & scope
    deployment_id = str(payload.get("deployment_id") or payload.get("deploy_id") or f"dep_{int(time.time())}")
    commit_sha = str(payload.get("commit_sha") or payload.get("commit") or "HEAD")
    branch = str(payload.get("branch") or "main")
    raw_scope = payload.get("scope")

    # Normalize scoped target URLs
    target_urls: List[str] = []
    if isinstance(raw_scope, list):
        for s in raw_scope:
            s_str = str(s).strip()
            if s_str.startswith("http://") or s_str.startswith("https://"):
                target_urls.append(s_str)
            else:
                target_urls.append(f"{base_url}/{s_str.lstrip('/')}")
    elif isinstance(raw_scope, dict) and "urls" in raw_scope:
        for s in raw_scope["urls"]:
            s_str = str(s).strip()
            if s_str.startswith("http://") or s_str.startswith("https://"):
                target_urls.append(s_str)
            else:
                target_urls.append(f"{base_url}/{s_str.lstrip('/')}")
    else:
        # Default site root
        target_urls = [site["url"]]

    # Callback channels setup
    callback = payload.get("callback") or {}
    channels: List[Dict[str, Any]] = []

    slack_url = callback.get("slack_webhook_url") or callback.get("slack_channel") or callback.get("slack_url")
    if slack_url and str(slack_url).startswith("http"):
        channels.append({"type": "slack", "webhook_url": str(slack_url)})

    pr_cfg = callback.get("pr_comment") or callback.get("pr")
    if pr_cfg:
        channels.append({"type": "pr_comment", **pr_cfg})

    webhook_url = callback.get("webhook_url") or callback.get("callback_url")
    if webhook_url and str(webhook_url).startswith("http"):
        channels.append({"type": "webhook", "url": str(webhook_url)})

    # If no channels in callback, check site configuration
    if not channels:
        channels = disp.get_channels_for_site(org_id, site_id)

    # 3. Locate previous completed baseline run
    prev_run_id = None
    with get_connection(db_url) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id FROM runs
                WHERE org_id = %s AND site_id = %s AND status = 'completed'
                ORDER BY finished_at DESC LIMIT 1
                """,
                (org_id, site_id)
            )
            prev_row = cur.fetchone()
            if prev_row:
                prev_run_id = prev_row["id"]

    # 4. Create and execute scoped run
    now_utc = datetime.now(timezone.utc)
    fp_seed = f"{site_id}:{deployment_id}:{commit_sha}:{now_utc.isoformat()}"
    run_id = f"crawl_dep_{hashlib.sha256(fp_seed.encode()).hexdigest()[:12]}"

    with get_connection(db_url) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO runs (id, org_id, site_id, status, progress_pct, current_pass, started_at)
                VALUES (%s, %s, %s, 'queued', 0.0, 'P1_DISCOVERY', %s)
                """,
                (run_id, org_id, site_id, now_utc)
            )
        conn.commit()

    job_data = {
        "run_id": run_id,
        "org_id": org_id,
        "site_id": site_id,
        "target_url": site["url"],
        "options": {
            "scope_urls": target_urls,
            "max_pages": len(target_urls),
            "fresh": True,
            "source": "cicd_deploy",
            "deployment_id": deployment_id,
            "commit_sha": commit_sha
        }
    }

    run_queue = RunQueue(redis_url=r_url)
    try:
        asyncio.run(execute_run_task(job_data, run_queue))
    except Exception as e:
        logger.error(f"Error executing scoped run {run_id}: {e}", exc_info=True)
        return {
            "status": "failed",
            "run_id": run_id,
            "error": str(e),
            "deployment_id": deployment_id
        }

    # 5. Snapshot Diffing
    before_snaps = _fetch_snapshots_for_run(prev_run_id, org_id) if prev_run_id else []
    after_snaps = _fetch_snapshots_for_run(run_id, org_id)
    tpl_map = _fetch_template_map(run_id, org_id)

    differ = SnapshotDiffer()
    diff_res = differ.diff_runs(
        before_run_id=prev_run_id or "NONE",
        after_run_id=run_id,
        before_snapshots=before_snaps,
        after_snapshots=after_snaps,
        template_map=tpl_map
    )

    # Filter differences strictly to scoped URLs if specific URLs were requested
    scoped_url_set = set(target_urls)
    raw_regressions = diff_res.get("by_category", {}).get("REGRESSED", [])
    scoped_regressions = [r for r in raw_regressions if r.get("url") in scoped_url_set] if raw_scope and raw_scope != "all" else raw_regressions

    regressions_count = len(scoped_regressions)
    verdict = "REGRESSION DETECTED" if regressions_count > 0 else "PASSED"
    is_failed = regressions_count > 0

    # 6. Critical Regression Classification & Alerts Persistence
    created_alerts = []
    if regressions_count > 0:
        for item in scoped_regressions:
            reg_url = item.get("url", "")
            reg_details = item.get("details", {})
            if isinstance(reg_details, str):
                try:
                    reg_details = json.loads(reg_details)
                except Exception:
                    reg_details = {}
            reasons = reg_details.get("regressions", [])
            if not reasons and "event" in reg_details:
                reasons = [reg_details["event"]]
            reasons_str = " ".join(str(r) for r in reasons).lower()

            if "noindex" in reasons_str:
                alert_type = "NOINDEX_LEAK"
                severity = "critical"
                title = f"Critical Noindex Leak in Deployment {deployment_id} on {reg_url}"
            elif "canonical" in reasons_str:
                alert_type = "CANONICAL_CHANGE"
                severity = "high"
                title = f"Canonical Tag Regression in Deployment {deployment_id} on {reg_url}"
            elif "500" in reasons_str or "status" in reasons_str:
                alert_type = "STATUS_5XX_SPIKE"
                severity = "critical"
                title = f"Status Code Regression in Deployment {deployment_id} on {reg_url}"
            elif "sitemap" in reasons_str:
                alert_type = "SITEMAP_DROP"
                severity = "high"
                title = f"Sitemap Drop in Deployment {deployment_id} on {reg_url}"
            else:
                alert_type = "REGRESSION_DETECTED"
                severity = "high"
                title = f"Regression Detected in Deployment {deployment_id} on {reg_url}"

            alert_fp = hashlib.sha256(f"{site_id}:{deployment_id}:{alert_type}:{reg_url}".encode()).hexdigest()[:16]
            alert_id = f"alert_dep_{alert_fp}"
            msg = f"Deployment {deployment_id} ({commit_sha[:7]}) introduced regression: {'; '.join(reasons)}"

            with get_connection(db_url) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO alerts (
                            id, org_id, site_id, run_id, alert_type, severity, title, message,
                            source, fingerprint, affected_urls_json, payload_json, status, detected_at
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'cicd_deploy', %s, %s, %s, 'open', %s)
                        ON CONFLICT (id) DO UPDATE SET
                            message = EXCLUDED.message,
                            run_id = EXCLUDED.run_id,
                            status = 'open',
                            detected_at = EXCLUDED.detected_at
                        RETURNING id, org_id, site_id, alert_type, severity, title, message;
                        """,
                        (
                            alert_id, org_id, site_id, run_id, alert_type, severity, title, msg,
                            alert_fp, Jsonb([reg_url]), Jsonb({"deployment_id": deployment_id, "commit_sha": commit_sha, "reasons": reasons}), now_utc
                        )
                    )
                    a_row = cur.fetchone()
                conn.commit()

            if a_row:
                created_alerts.append(dict(a_row))

    # 7. Result Delivery via NotificationDispatcher
    event_type = "regression.detected" if is_failed else "deploy.verified"
    event_payload = {
        "org_id": org_id,
        "site_id": site_id,
        "run_id": run_id,
        "deployment_id": deployment_id,
        "commit_sha": commit_sha,
        "branch": branch,
        "scope": f"{len(target_urls)} URLs",
        "verdict": verdict,
        "regressions_count": regressions_count,
        "diff_summary": diff_res.get("summary", {}),
        "alerts": created_alerts,
        "title": f"Deployment {deployment_id} Regression Check: {verdict}",
        "message": f"Deployment {deployment_id} ({commit_sha[:7]}) completed check across {len(target_urls)} scoped URLs. Found {regressions_count} regressions."
    }

    try:
        disp.dispatch_event(event_type, event_payload, channels=channels)
    except Exception as disp_err:
        logger.warning(f"Error dispatching CI/CD result notifications: {disp_err}")

    return {
        "status": "completed",
        "run_id": run_id,
        "prev_run_id": prev_run_id,
        "deployment_id": deployment_id,
        "commit_sha": commit_sha,
        "branch": branch,
        "scope": target_urls,
        "verdict": verdict,
        "regressions_count": regressions_count,
        "diff_summary": diff_res.get("summary", {}),
        "alerts": created_alerts
    }
