"""
SEOJEV Stage 9 Watch Scheduler:
Discovers and executes due watch configurations autonomously in a background worker thread.
Acquires database-level locks with FOR UPDATE SKIP LOCKED to prevent concurrent duplicate execution.
Executes lightweight checks (robots.txt, sitemaps, top pages, template drift) via WatchRunner,
persists alert records to the database, and fans out alerts via NotificationDispatcher.
"""
import os
import json
import time
import logging
import threading
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any
from croniter import croniter
from psycopg.types.json import Jsonb

from database.connection import get_connection
from verification.watch import WatchRunner
from services.notifications import get_notification_dispatcher, NotificationDispatcher

logger = logging.getLogger("seojev.scheduler")


class WatchScheduler:
    """
    Autonomous scheduler running due watch checks based on cron expressions.
    """
    def __init__(
        self,
        db_url: Optional[str] = None,
        poll_interval_sec: float = 1.0,
        watch_runner: Optional[WatchRunner] = None,
        dispatcher: Optional[NotificationDispatcher] = None
    ):
        self.db_url = db_url
        self.poll_interval_sec = poll_interval_sec
        self.watch_runner = watch_runner or WatchRunner(db_url=db_url)
        self.dispatcher = dispatcher or get_notification_dispatcher()
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
                        SELECT id, org_id, site_id, cron_expression, checks_json, top_pages_json, notification_channels_json
                        FROM watch_configs
                        WHERE is_active = TRUE AND (next_run_at IS NULL OR next_run_at <= %s)
                        ORDER BY COALESCE(next_run_at, created_at) ASC
                        FOR UPDATE SKIP LOCKED
                        LIMIT 10
                    )
                    UPDATE watch_configs w
                    SET last_run_at = %s,
                        next_run_at = %s + INTERVAL '10 minutes', -- temporary lease while running
                        updated_at = %s
                    FROM due_watches d
                    WHERE w.id = d.id
                    RETURNING w.id, w.org_id, w.site_id, w.cron_expression, w.checks_json,
                              w.top_pages_json, w.notification_channels_json;
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

            # Compute next true scheduled run time
            try:
                c_iter = croniter(cron_expr, now_utc)
                next_run = c_iter.get_next(datetime)
                if next_run.tzinfo is None:
                    next_run = next_run.replace(tzinfo=timezone.utc)
            except Exception as pe:
                logger.warning(f"Invalid cron expression '{cron_expr}' for watch {config_id}: {pe}")
                next_run = now_utc + timedelta(hours=24)

            # Execute lightweight checks
            alerts = []
            try:
                alerts = self.watch_runner.run_checks(
                    site_id=site_id,
                    org_id=org_id,
                    checks=checks,
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
