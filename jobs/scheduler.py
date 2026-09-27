"""
SEOJEV Stage 9 & 10c Watch and Audit Scheduler:
Discovers and executes due watch configurations and recurring scheduled audits.
Acquires database-level locks with FOR UPDATE SKIP LOCKED to prevent concurrent duplicate execution.
Supports:
  1. Lightweight health checks (robots.txt, sitemaps, top pages, template drift) via WatchRunner.
  2. Full scheduled crawl audits via RunQueue and execute_run_task with overlap prevention.
  3. Pre/post run snapshot diffing and automatic regression detection/alerting.
  4. Multi-channel alert dispatching via NotificationDispatcher.
"""
import os
import json
import time
import hashlib
import logging
import asyncio
import threading
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any
from croniter import croniter
from psycopg.types.json import Jsonb

from database.connection import get_connection
from verification.watch import WatchRunner
from verification.differ import SnapshotDiffer
from services.notifications import get_notification_dispatcher, NotificationDispatcher
from jobs.queue import RunQueue
from jobs.worker import execute_run_task

logger = logging.getLogger("seojev.scheduler")


class WatchScheduler:
    """
    Autonomous scheduler running due watch checks and recurring audits based on cron expressions.
    """
    def __init__(
        self,
        db_url: Optional[str] = None,
        poll_interval_sec: float = 1.0,
        watch_runner: Optional[WatchRunner] = None,
        dispatcher: Optional[NotificationDispatcher] = None,
        redis_url: Optional[str] = None
    ):
        self.db_url = db_url
        self.poll_interval_sec = poll_interval_sec
        self.watch_runner = watch_runner or WatchRunner(db_url=db_url)
        self.dispatcher = dispatcher or get_notification_dispatcher()
        self.redis_url = redis_url or os.environ.get("REDIS_URL", "redis://localhost:6379/0")
        self._stopped = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def start(self):
        """Starts the scheduler background worker thread."""
        if self._thread and self._thread.is_alive():
            return
        self._stopped.clear()
        self._thread = threading.Thread(target=self._run_loop, name="SEOJEVWatchScheduler", daemon=True)
        self._thread.start()
        logger.info("WatchScheduler started.")

    def stop(self, timeout: float = 5.0):
        """Stops the scheduler background worker thread."""
        self._stopped.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=timeout)
        logger.info("WatchScheduler stopped.")

    def is_running(self) -> bool:
        return bool(self._thread and self._thread.is_alive())

    def _run_loop(self):
        while not self._stopped.is_set():
            try:
                self.execute_due_watches()
            except Exception as exc:
                logger.error(f"Error in WatchScheduler execution loop: {exc}", exc_info=True)
            self._stopped.wait(timeout=self.poll_interval_sec)

    def _execute_full_audit(
        self,
        org_id: str,
        site_id: str,
        audit_config: Dict[str, Any],
        channels: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """
        Executes a scheduled full audit run:
        1. Checks overlap: skips if run is already running or queued for this site.
        2. Creates and enqueues run.
        3. Executes run via execute_run_task.
        4. Finds previous run, compares snapshots using SnapshotDiffer.
        5. If regressions detected, writes alerts and dispatches notifications.
        """
        with get_connection(self.db_url) as conn:
            with conn.cursor() as cur:
                # 1. Overlap prevention
                cur.execute(
                    """
                    SELECT id FROM runs
                    WHERE org_id = %s AND site_id = %s AND status IN ('running', 'queued')
                    LIMIT 1
                    """,
                    (org_id, site_id)
                )
                if cur.fetchone():
                    logger.info(f"Skipping scheduled audit for site {site_id}: an active run is already running or queued.")
                    return None

                # Fetch site target URL
                cur.execute("SELECT url, domain FROM sites WHERE org_id = %s AND id = %s", (org_id, site_id))
                site_row = cur.fetchone()
                if not site_row:
                    return None
                target_url = site_row["url"]

        now_utc = datetime.now(timezone.utc)
        run_id = f"crawl_sched_{hashlib.sha256(f'{site_id}:{now_utc.isoformat()}'.encode()).hexdigest()[:12]}"
        options = dict(audit_config or {})
        options.setdefault("max_pages", 15)
        options.setdefault("fresh", True)
        options.setdefault("source", "scheduled_audit")

        # 2. Insert into runs
        with get_connection(self.db_url) as conn:
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
            "target_url": target_url,
            "options": options
        }

        # 3. Execute run
        run_queue = RunQueue(redis_url=self.redis_url)
        try:
            asyncio.run(execute_run_task(job_data, run_queue))
        except Exception as e:
            logger.error(f"Error executing scheduled run {run_id}: {e}", exc_info=True)
            return None

        # 4. Compare with previous snapshot
        prev_run_id = None
        with get_connection(self.db_url) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id FROM runs
                    WHERE org_id = %s AND site_id = %s AND status = 'completed' AND id != %s
                    ORDER BY finished_at DESC LIMIT 1
                    """,
                    (org_id, site_id, run_id)
                )
                prev_row = cur.fetchone()
                if prev_row:
                    prev_run_id = prev_row["id"]

        if not prev_run_id:
            logger.info(f"Scheduled run {run_id} completed. No previous run found for snapshot diff.")
            return {"run_id": run_id, "regressions": 0}

        # 5. Snapshot Diff & Regression Detection
        from api.routers.diff import _fetch_snapshots_for_run, _fetch_template_map
        before_snaps = _fetch_snapshots_for_run(prev_run_id, org_id)
        after_snaps = _fetch_snapshots_for_run(run_id, org_id)
        tpl_map = _fetch_template_map(run_id, org_id)

        differ = SnapshotDiffer()
        diff_res = differ.diff_runs(
            before_run_id=prev_run_id,
            after_run_id=run_id,
            before_snapshots=before_snaps,
            after_snapshots=after_snaps,
            template_map=tpl_map
        )
        regressions_count = diff_res.get("summary", {}).get("REGRESSED", 0)

        if regressions_count > 0:
            regressed_items = diff_res.get("by_category", {}).get("REGRESSED", [])
            for item in regressed_items:
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

                # Reusing existing critical regression classifications
                if "noindex" in reasons_str:
                    alert_type = "NOINDEX_LEAK"
                    severity = "critical"
                    title = f"Critical Noindex Leak on {reg_url}"
                elif "canonical" in reasons_str:
                    alert_type = "CANONICAL_CHANGE"
                    severity = "high"
                    title = f"Canonical Tag Regression on {reg_url}"
                elif "500" in reasons_str or "status" in reasons_str:
                    alert_type = "STATUS_5XX_SPIKE"
                    severity = "critical"
                    title = f"Status Code Regression on {reg_url}"
                elif "sitemap" in reasons_str:
                    alert_type = "SITEMAP_DROP"
                    severity = "high"
                    title = f"Sitemap Regression on {reg_url}"
                else:
                    alert_type = "REGRESSION_DETECTED"
                    severity = "high"
                    title = f"Regression Detected on {reg_url}"

                alert_fingerprint = hashlib.sha256(f"{site_id}:{alert_type}:{reg_url}".encode()).hexdigest()[:16]
                alert_id = f"alert_reg_{alert_fingerprint}"
                msg = f"Scheduled audit comparison between {prev_run_id} and {run_id} detected regression: {'; '.join(reasons)}"

                with get_connection(self.db_url) as conn:
                    with conn.cursor() as cur:
                        cur.execute(
                            """
                            INSERT INTO alerts (
                                id, org_id, site_id, run_id, alert_type, severity, title, message,
                                source, fingerprint, affected_urls_json, status, detected_at
                            )
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'regression', %s, %s, 'open', %s)
                            ON CONFLICT (id) DO UPDATE SET
                                message = EXCLUDED.message,
                                run_id = EXCLUDED.run_id,
                                status = 'open',
                                detected_at = EXCLUDED.detected_at
                            RETURNING id, org_id, site_id, alert_type, severity, title, message;
                            """,
                            (
                                alert_id, org_id, site_id, run_id, alert_type, severity,
                                title, msg, alert_fingerprint, Jsonb([reg_url]), now_utc
                            )
                        )
                        alert_row = cur.fetchone()
                    conn.commit()

                if alert_row:
                    try:
                        self.dispatcher.dispatch_alert(dict(alert_row), channels=channels)
                    except Exception as disp_err:
                        logger.warning(f"Failed to dispatch regression alert: {disp_err}")

        return {"run_id": run_id, "prev_run_id": prev_run_id, "regressions": regressions_count}

    def execute_due_watches(self) -> List[Dict[str, Any]]:
        """
        Discovers due watch configs, atomically claims them, executes checks,
        and dispatches alerts.
        """
        claimed_jobs = []
        now_utc = datetime.now(timezone.utc)

        with get_connection(self.db_url) as conn:
            with conn.cursor() as cur:
                # Atomically claim due watches using FOR UPDATE SKIP LOCKED
                cur.execute(
                    """
                    WITH due_watches AS (
                        SELECT id, org_id, site_id, cron_expression, checks_json, top_pages_json,
                               notification_channels_json, audit_config_json
                        FROM watch_configs
                        WHERE is_active = TRUE AND (next_run_at IS NULL OR next_run_at <= %s)
                        ORDER BY COALESCE(next_run_at, created_at) ASC
                        FOR UPDATE SKIP LOCKED
                        LIMIT 50
                    )
                    UPDATE watch_configs w
                    SET last_run_at = %s,
                        next_run_at = %s + INTERVAL '10 minutes', -- temporary lease while running
                        updated_at = %s
                    FROM due_watches d
                    WHERE w.id = d.id
                    RETURNING w.id, w.org_id, w.site_id, w.cron_expression, w.checks_json,
                              w.top_pages_json, w.notification_channels_json, w.audit_config_json;
                    """,
                    (now_utc, now_utc, now_utc, now_utc)
                )
                claimed_jobs = cur.fetchall()
            conn.commit()

        executed = []
        for job in claimed_jobs:
            config_id = job["id"]
            org_id = job["org_id"]
            site_id = job["site_id"]
            cron_expr = job.get("cron_expression") or "0 0 * * *"
            raw_checks = job.get("checks_json") or []
            checks = raw_checks if isinstance(raw_checks, list) else json.loads(raw_checks)
            raw_pages = job.get("top_pages_json") or []
            top_pages = raw_pages if isinstance(raw_pages, list) else json.loads(raw_pages)
            raw_channels = job.get("notification_channels_json") or []
            channels = raw_channels if isinstance(raw_channels, list) else json.loads(raw_channels)
            raw_audit_cfg = job.get("audit_config_json") or {}
            audit_cfg = raw_audit_cfg if isinstance(raw_audit_cfg, dict) else json.loads(raw_audit_cfg)

            # Compute next true scheduled run time
            try:
                c_iter = croniter(cron_expr, now_utc)
                next_run = c_iter.get_next(datetime)
                if next_run.tzinfo is None:
                    next_run = next_run.replace(tzinfo=timezone.utc)
            except Exception as pe:
                logger.warning(f"Invalid cron expression '{cron_expr}' for watch {config_id}: {pe}")
                next_run = now_utc + timedelta(hours=24)

            # 1. Full Audit execution if configured
            if "full_audit" in checks or "scheduled_audit" in checks:
                try:
                    self._execute_full_audit(org_id, site_id, audit_cfg, channels)
                except Exception as audit_err:
                    logger.error(f"Error during scheduled full audit for site {site_id}: {audit_err}", exc_info=True)

            # 2. Lightweight checks execution if configured
            lightweight_checks = [c for c in checks if c in ("robots_txt", "sitemap", "top_pages", "template_drift")]
            alerts = []
            if lightweight_checks:
                try:
                    alerts = self.watch_runner.run_checks(
                        site_id=site_id,
                        org_id=org_id,
                        checks=lightweight_checks,
                        top_pages=top_pages
                    )
                except Exception as run_err:
                    logger.error(f"Failed to execute watch checks for site {site_id}: {run_err}", exc_info=True)

                # Fanout notifications for detected alerts
                for alert in alerts:
                    try:
                        self.dispatcher.dispatch_alert(alert, channels=channels)
                    except Exception as disp_err:
                        logger.warning(f"Failed to dispatch alert {alert.get('id')}: {disp_err}")

            # 3. GSC Anomaly Detection if configured
            if "gsc_anomaly" in checks or "search_decay" in checks:
                try:
                    from services.gsc_anomaly import get_gsc_anomaly_detector
                    gsc_detector = get_gsc_anomaly_detector()
                    gsc_detector.detect_anomalies(site_id=site_id, org_id=org_id, channels=channels)
                except Exception as gsc_err:
                    logger.error(f"Error during scheduled GSC anomaly detection for site {site_id}: {gsc_err}", exc_info=True)

            # Update final next_run_at
            with get_connection(self.db_url) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "UPDATE watch_configs SET next_run_at = %s, updated_at = %s WHERE id = %s",
                        (next_run, datetime.now(timezone.utc), config_id)
                    )
                conn.commit()

            executed.append({
                "watch_config_id": config_id,
                "site_id": site_id,
                "org_id": org_id,
                "alerts_count": len(alerts),
                "next_run_at": next_run.isoformat()
            })

        return executed


_global_scheduler: Optional[WatchScheduler] = None

def get_watch_scheduler() -> WatchScheduler:
    global _global_scheduler
    if _global_scheduler is None:
        _global_scheduler = WatchScheduler()
    return _global_scheduler
