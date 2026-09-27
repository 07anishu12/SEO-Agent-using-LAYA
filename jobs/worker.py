"""
SEOJEV Stage 4 Worker: Executes background crawl jobs, streams pub/sub progress,
handles cooperative cancellation, retries with backoff, and triggers Stage-2 ETL.
"""
import asyncio
import json
import logging
import os
import time
from datetime import datetime, timezone
from typing import Any, Dict, Optional
import psycopg

from api.config import REDIS_URL
from database.connection import get_connection
from database.etl import run_etl
from engine.pipeline import SEOJEVPipeline, PipelineCancelledException
from .queue import RunQueue, QUEUE_KEY

logger = logging.getLogger("seojev.worker")


async def execute_run_task(job_data: Dict[str, Any], queue: RunQueue) -> Dict[str, Any]:
    """
    Executes a single crawl run job with live Redis pub/sub progress dispatch,
    cooperative cancellation checks, Stage-2 ETL, and 1-attempt retry on failure.
    """
    run_id = job_data["run_id"]
    org_id = job_data["org_id"]
    site_id = job_data["site_id"]
    target_url = job_data["target_url"]
    options = dict(job_data.get("options", {}))

    db_path = options.get("db_path") or f"data/{run_id}.db"
    output_dir = f"reports/{run_id}/"

    if queue.is_cancelled(run_id):
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE runs SET status = 'cancelled', finished_at = %s WHERE id = %s",
                    (datetime.now(timezone.utc), run_id)
                )
            conn.commit()
        queue.publish_progress(run_id, {
            "run_id": run_id,
            "status": "cancelled",
            "pct": 0.0,
            "message": "Run was cancelled before execution started."
        })
        return {"status": "cancelled", "run_id": run_id}

    # Mark run as "running" in Postgres
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE runs
                SET status = 'running',
                    started_at = %s,
                    current_pass = 'P1_CRAWL'
                WHERE id = %s
                """,
                (datetime.now(timezone.utc), run_id)
            )
        conn.commit()

    queue.publish_progress(run_id, {
        "run_id": run_id,
        "status": "running",
        "pass": "P1_CRAWL",
        "pct": 0.0,
        "message": f"Worker picked up run for {target_url}"
    })

    def progress_callback(pass_name: str, pct: float, message: str, meta: Optional[Dict[str, Any]] = None):
        logger.info(f"[worker] run_id={run_id} site_id={site_id} stage={pass_name} pct={pct:.1f}% msg={message[:80]}")
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE runs
                    SET progress_pct = %s,
                        current_pass = %s
                    WHERE id = %s
                    """,
                    (pct, pass_name, run_id)
                )
            conn.commit()

        queue.publish_progress(run_id, {
            "run_id": run_id,
            "status": "running",
            "pass": pass_name,
            "pct": pct,
            "message": message,
            "meta": meta or {}
        })

    def cancel_check() -> bool:
        return queue.is_cancelled(run_id)

    try:
        pipeline = SEOJEVPipeline(
            target_url=target_url,
            crawl_id=run_id,
            db_path=db_path,
            output_dir=output_dir,
            progress_callback=progress_callback,
            cancel_check=cancel_check,
            options=options
        )

        pipeline_result = await pipeline.run_all()

        # Check for cooperative cancellation
        if pipeline_result.get("status") == "cancelled" or cancel_check():
            with get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        UPDATE runs
                        SET status = 'cancelled',
                            finished_at = %s
                        WHERE id = %s
                        """,
                        (datetime.now(timezone.utc), run_id)
                    )
                conn.commit()

            queue.publish_progress(run_id, {
                "run_id": run_id,
                "status": "cancelled",
                "pct": getattr(pipeline, "_last_pct", 0.0),
                "message": "Run cancelled cooperatively. No ETL performed."
            })
            return {"status": "cancelled", "run_id": run_id}

        # Successful completion -> Execute Stage-2 ETL
        etl_result = run_etl(
            sqlite_db_path=db_path,
            crawl_id=run_id,
            org_id=org_id,
            site_id=site_id
        )

        # Stage 5: Upload all artifacts to S3/MinIO object storage
        try:
            from services.object_store import get_storage_service
            storage_service = get_storage_service()
            storage_service.upload_run_artifacts(
                org_id=org_id,
                site_id=site_id,
                run_id=run_id,
                output_dir=output_dir
            )
        except Exception as upload_err:
            logger.error(f"Failed to upload artifacts for run {run_id}: {upload_err}", exc_info=True)

        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE runs
                    SET status = 'completed',
                        progress_pct = 100.0,
        current_pass = 'P6_REPORTS',
                        finished_at = %s
                    WHERE id = %s
                    """,
                    (datetime.now(timezone.utc), run_id)
                )
            conn.commit()

        # Stage 9: Dispatch run.completed notification
        try:
            from services.notifications import get_notification_dispatcher
            get_notification_dispatcher().dispatch_event("run.completed", {
                "run_id": run_id,
                "org_id": org_id,
                "site_id": site_id,
                "status": "completed",
                "counts": etl_result.get("counts"),
                "finished_at": datetime.now(timezone.utc).isoformat()
            })
        except Exception as notify_err:
            logger.warning(f"Failed to dispatch run.completed notification: {notify_err}")

        # Stage 10a: Record Historical Trends
        try:
            from services.trends import record_run_trends
            record_run_trends(
                org_id=org_id,
                site_id=site_id,
                run_id=run_id,
                counts_override=etl_result.get("counts")
            )
        except Exception as trend_err:
            logger.warning(f"Failed to record historical trends for run {run_id}: {trend_err}")

        # Stage 9 & 10c: Compare with previous snapshot, record regressions and dispatch alerts
        try:
            _check_regressions_and_alert(org_id=org_id, site_id=site_id, run_id=run_id)
        except Exception as diff_err:
            logger.warning(f"Failed to calculate regressions/diff for run {run_id}: {diff_err}")

        queue.publish_progress(run_id, {
            "run_id": run_id,
            "status": "completed",
            "pass": "P6_REPORTS",
            "pct": 100.0,
            "counts": etl_result.get("counts"),
            "message": "Run and ETL completed successfully."
        })
        return {
            "status": "completed",
            "run_id": run_id,
            "counts": etl_result.get("counts"),
            "deliverables": pipeline_result.get("deliverables")
        }

    except PipelineCancelledException:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE runs SET status = 'cancelled', finished_at = %s WHERE id = %s",
                    (datetime.now(timezone.utc), run_id)
                )
            conn.commit()

        queue.publish_progress(run_id, {
            "run_id": run_id,
            "status": "cancelled",
            "message": "Pipeline cancelled. No partial ETL performed."
        })
        return {"status": "cancelled", "run_id": run_id}

    except Exception as exc:
        retries = queue.get_retry_count(run_id)
        if retries < 1:
            # First failure -> Retry once with backoff
            queue.increment_retry_count(run_id)
            backoff_sec = 1.0
            logger.warning(f"Run {run_id} failed with error '{exc}'. Retrying in {backoff_sec}s (attempt 1/1)...")

            with get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "UPDATE runs SET status = 'retrying' WHERE id = %s",
                        (run_id,)
                    )
                conn.commit()

            queue.publish_progress(run_id, {
                "run_id": run_id,
                "status": "retrying",
                "message": f"Run failed ({str(exc)}). Retrying in {backoff_sec}s..."
            })

            await asyncio.sleep(backoff_sec)
            return await execute_run_task(job_data, queue)
        else:
            # Second failure -> Mark "needs_attention"
            logger.error(f"Run {run_id} failed twice. Marking 'needs_attention'. Error: {exc}")
            with get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        UPDATE runs
                        SET status = 'needs_attention',
                            finished_at = %s
                        WHERE id = %s
                        """,
                        (datetime.now(timezone.utc), run_id)
                    )
                conn.commit()

            # Stage 9: Dispatch run.failed notification
            try:
                from services.notifications import get_notification_dispatcher
                get_notification_dispatcher().dispatch_event("run.failed", {
                    "run_id": run_id,
                    "org_id": org_id,
                    "site_id": site_id,
                    "status": "failed",
                    "error": str(exc),
                    "finished_at": datetime.now(timezone.utc).isoformat()
                })
            except Exception as notify_err:
                logger.warning(f"Failed to dispatch run.failed notification: {notify_err}")

            queue.publish_progress(run_id, {
                "run_id": run_id,
                "status": "needs_attention",
                "error": str(exc),
                "message": f"Run failed after retry: {str(exc)}"
            })
            return {"status": "needs_attention", "run_id": run_id, "error": str(exc)}


def _check_regressions_and_alert(org_id: str, site_id: str, run_id: str):
    """
    Compares the newly completed run with the site's previous completed run.
    Detects regressions using SnapshotDiffer, creates alerts in PostgreSQL, and dispatches them.
    """
    import hashlib
    from psycopg.types.json import Jsonb
    from verification.differ import SnapshotDiffer
    from services.notifications import get_notification_dispatcher
    from api.routers.diff import _fetch_snapshots_for_run, _fetch_template_map

    prev_run_id = None
    with get_connection() as conn:
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
        logger.info(f"[worker] run_id={run_id} completed. No previous run found for site {site_id} snapshot diff.")
        return

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
        logger.info(f"[worker] run_id={run_id} detected {regressions_count} regressions against previous run {prev_run_id}")
        now_utc = datetime.now(timezone.utc)
        regressed_items = diff_res.get("by_category", {}).get("REGRESSED", [])
        dispatcher = get_notification_dispatcher()

        # Fetch watch config notification channels for site if available
        channels = []
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT notification_channels_json FROM watch_configs WHERE org_id = %s AND site_id = %s AND is_active = TRUE LIMIT 1",
                    (org_id, site_id)
                )
                wch = cur.fetchone()
                if wch and wch["notification_channels_json"]:
                    raw_ch = wch["notification_channels_json"]
                    channels = raw_ch if isinstance(raw_ch, list) else json.loads(raw_ch)

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
            msg = f"Audit comparison between {prev_run_id} and {run_id} detected regression: {'; '.join(reasons)}"

            alert_row = None
            with get_connection() as conn:
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
                    dispatcher.dispatch_alert(dict(alert_row), channels=channels)
                except Exception as disp_err:
                    logger.warning(f"Failed to dispatch regression alert: {disp_err}")


class RunWorker:
    def __init__(self, redis_url: Optional[str] = None):
        self.queue = RunQueue(redis_url=redis_url or REDIS_URL)
        self.stopped = False
        self._task: Optional[asyncio.Task] = None

    async def process_next_job(self, timeout: int = 1) -> Optional[Dict[str, Any]]:
        job_data = await asyncio.to_thread(self.queue.dequeue_run, timeout)
        if job_data:
            return await execute_run_task(job_data, self.queue)
        return None

    async def run_loop(self):
        logger.info("SEOJEV RunWorker started. Polling queue...")
        while not self.stopped:
            try:
                job_data = await asyncio.to_thread(self.queue.dequeue_run, 1)
                if job_data:
                    if self.stopped:
                        self.queue.client.lpush(QUEUE_KEY, json.dumps(job_data))
                        break
                    await execute_run_task(job_data, self.queue)
                else:
                    await asyncio.sleep(0.05)
            except Exception as e:
                logger.error(f"Error in worker loop: {e}", exc_info=True)
                await asyncio.sleep(0.5)

    def start_background(self) -> asyncio.Task:
        self.stopped = False
        self._task = asyncio.create_task(self.run_loop())
        return self._task

    def stop(self):
        self.stopped = True
        if self._task and not self._task.done():
            self._task.cancel()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    worker = RunWorker()
    try:
        asyncio.run(worker.run_loop())
    except KeyboardInterrupt:
        logger.info("Worker stopped by user.")
