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
from .queue import RunQueue

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
                        current_pass = 'P6_DELIVERABLES',
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

        queue.publish_progress(run_id, {
            "run_id": run_id,
            "status": "completed",
            "pass": "P6_DELIVERABLES",
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
