"""
Runs Router: Async Queue Enqueuing, SSE Progress Streaming, Cancellation, and Resume.
"""
import asyncio
import json
import os
import time
from datetime import datetime, timezone
from uuid import uuid4
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse

import redis.asyncio as aioredis
from api.config import REDIS_URL
from database.connection import get_connection
from database.scoped_query import ScopedQuery
from jobs.queue import RunQueue
from jobs.worker import execute_run_task
from services.object_store import get_storage_service
from ..auth import get_current_user, require_editor_or_admin
from ..schemas import (
    RunCreateRequest,
    RunResponse,
    ArtifactResponse,
    SignedDownloadResponse
)
from ..security import rate_limit_runs

router = APIRouter(prefix="/runs", tags=["runs"])


@router.post("", response_model=RunResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(rate_limit_runs)])
async def create_and_enqueue_run(
    req: RunCreateRequest,
    sync: bool = False,
    current_user: dict = Depends(require_editor_or_admin)
):
    """
    Enqueues an asynchronous crawl run job in the Redis queue and returns immediately with status 'queued'.
    If sync=True (or req.sync=True), executes synchronously and returns the completed run.
    """
    org_id = current_user["org_id"]
    is_sync = sync or bool(req.sync)

    # 1. Fetch site strictly scoped to org_id
    with ScopedQuery(org_id=org_id) as sq:
        site = sq.fetch_one("sites", where="id = %(id)s", params={"id": req.site_id})
    if not site:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Site not found")

    target_url = site["url"]
    crawl_id = req.crawl_id or f"crawl_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid4().hex[:6]}"

    # Idempotency check: if run is already running, queued, or completed without fresh=True, return it
    if req.crawl_id:
        with ScopedQuery(org_id=org_id) as sq:
            existing_run = sq.fetch_one("runs", where="id = %(id)s", params={"id": req.crawl_id})
            if existing_run and (existing_run["status"] in ("running", "queued") or (existing_run["status"] == "completed" and not req.fresh)):
                return RunResponse(
                    id=existing_run["id"],
                    org_id=existing_run["org_id"],
                    site_id=existing_run["site_id"],
                    status=existing_run["status"],
                    started_at=existing_run.get("started_at"),
                    finished_at=existing_run.get("finished_at"),
                    progress_pct=float(existing_run.get("progress_pct") or (100.0 if existing_run["status"] == "completed" else 0.0)),
                    current_pass=existing_run.get("current_pass") or ("COMPLETED" if existing_run["status"] == "completed" else "QUEUED"),
                    urls_discovered=existing_run.get("urls_discovered") or 0,
                    urls_crawled=existing_run.get("urls_crawled") or 0,
                    urls_failed=existing_run.get("urls_failed") or 0,
                    total_issues=existing_run.get("total_issues") or 0
                )

    options = {
        "max_pages": req.max_pages or 50,
        "concurrency": req.concurrency or 2,
        "render": req.render or False,
        "fresh": req.fresh if req.fresh is not None else True,
        "show_live_display": False
    }
    if req.options:
        options.update(req.options)

    queue = RunQueue(redis_url=REDIS_URL)

    if is_sync:
        # Record run as 'running' in Postgres
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO runs (
                        id, org_id, site_id, status, progress_pct, current_pass,
                        urls_discovered, urls_crawled, urls_failed, total_issues
                    )
                    VALUES (%s, %s, %s, 'running', 0.0, 'P1_CRAWL', 0, 0, 0, 0)
                    ON CONFLICT (id) DO UPDATE SET
                        status = 'running',
                        progress_pct = 0.0,
                        current_pass = 'P1_CRAWL'
                    RETURNING id, org_id, site_id, status, started_at, finished_at,
                              progress_pct, current_pass, urls_discovered, urls_crawled,
                              urls_failed, total_issues;
                    """,
                    (crawl_id, org_id, req.site_id)
                )
            conn.commit()

        job_data = {
            "run_id": crawl_id,
            "org_id": org_id,
            "site_id": req.site_id,
            "target_url": target_url,
            "options": options
        }
        task_res = await execute_run_task(job_data, queue)

        with ScopedQuery(org_id=org_id) as sq:
            run_row = sq.fetch_one("runs", where="id = %(id)s", params={"id": crawl_id})

        return RunResponse(
            id=run_row["id"],
            org_id=run_row["org_id"],
            site_id=run_row["site_id"],
            status=run_row["status"],
            started_at=run_row["started_at"],
            finished_at=run_row["finished_at"],
            progress_pct=float(run_row["progress_pct"] or 100.0),
            current_pass=run_row["current_pass"],
            urls_discovered=run_row["urls_discovered"] or 0,
            urls_crawled=run_row["urls_crawled"] or 0,
            urls_failed=run_row["urls_failed"] or 0,
            total_issues=run_row["total_issues"] or 0,
            counts=task_res.get("counts"),
            deliverables=task_res.get("deliverables")
        )

    # 2. Record run as 'queued' in Postgres
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO runs (
                    id, org_id, site_id, status, progress_pct, current_pass,
                    urls_discovered, urls_crawled, urls_failed, total_issues
                )
                VALUES (%s, %s, %s, 'queued', 0.0, 'QUEUED', 0, 0, 0, 0)
                ON CONFLICT (id) DO UPDATE SET
                    status = 'queued',
                    progress_pct = 0.0,
                    current_pass = 'QUEUED'
                RETURNING id, org_id, site_id, status, started_at, finished_at,
                          progress_pct, current_pass, urls_discovered, urls_crawled,
                          urls_failed, total_issues;
                """,
                (crawl_id, org_id, req.site_id)
            )
            row = cur.fetchone()
        conn.commit()

    # 3. Enqueue job into Redis
    queue.enqueue_run(
        run_id=crawl_id,
        org_id=org_id,
        site_id=req.site_id,
        target_url=target_url,
        options=options
    )

    return RunResponse(
        id=row["id"],
        org_id=row["org_id"],
        site_id=row["site_id"],
        status="queued",
        started_at=row["started_at"],
        finished_at=row["finished_at"],
        progress_pct=0.0,
        current_pass="QUEUED",
        urls_discovered=0,
        urls_crawled=0,
        urls_failed=0,
        total_issues=0
    )


@router.get("", response_model=List[RunResponse])
def list_runs(
    site_id: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: dict = Depends(get_current_user)
):
    org_id = current_user["org_id"]
    where = "site_id = %(site_id)s" if site_id else None
    params = {"site_id": site_id} if site_id else None

    with ScopedQuery(org_id=org_id) as sq:
        runs = sq.fetch_all(
            "runs",
            where=where,
            params=params,
            order_by="created_at DESC",
            limit=limit,
            offset=offset
        )

    return [
        RunResponse(
            id=r["id"],
            org_id=r["org_id"],
            site_id=r["site_id"],
            status=r["status"],
            started_at=r["started_at"],
            finished_at=r["finished_at"],
            progress_pct=float(r["progress_pct"] or 0.0),
            current_pass=r["current_pass"],
            urls_discovered=r["urls_discovered"] or 0,
            urls_crawled=r["urls_crawled"] or 0,
            urls_failed=r["urls_failed"] or 0,
            total_issues=r["total_issues"] or 0
        )
        for r in runs
    ]


@router.get("/{id}", response_model=RunResponse)
def get_run(
    id: str,
    current_user: dict = Depends(get_current_user)
):
    org_id = current_user["org_id"]
    with ScopedQuery(org_id=org_id) as sq:
        run = sq.fetch_one("runs", where="id = %(id)s", params={"id": id})
        if not run:
            # Return 404 to avoid leaking existence of cross-org resources
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")

        findings_cnt = sq.count("findings", where="run_id = %(r)s", params={"r": id})
        opps_cnt = sq.count("opportunities", where="run_id = %(r)s", params={"r": id})
        wos_cnt = sq.count("work_orders", where="run_id = %(r)s", params={"r": id})
        tpls_cnt = sq.count("templates", where="run_id = %(r)s", params={"r": id})

    return RunResponse(
        id=run["id"],
        org_id=run["org_id"],
        site_id=run["site_id"],
        status=run["status"],
        started_at=run["started_at"],
        finished_at=run["finished_at"],
        progress_pct=float(run["progress_pct"] or 0.0),
        current_pass=run["current_pass"],
        urls_discovered=run["urls_discovered"] or 0,
        urls_crawled=run["urls_crawled"] or 0,
        urls_failed=run["urls_failed"] or 0,
        total_issues=run["total_issues"] or 0,
        counts={
            "findings": findings_cnt,
            "opportunities": opps_cnt,
            "work_orders": wos_cnt,
            "templates": tpls_cnt
        }
    )


@router.get("/{id}/progress")
async def stream_run_progress(
    id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Server-Sent Events endpoint subscribing to Redis pub/sub channel run:{id}:progress.
    Streams events until the run reaches a terminal state.
    """
    org_id = current_user["org_id"]
    with ScopedQuery(org_id=org_id) as sq:
        run = sq.fetch_one("runs", where="id = %(id)s", params={"id": id})
    if not run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")

    async def event_generator():
        r = aioredis.from_url(REDIS_URL, decode_responses=True)
        pubsub = r.pubsub()
        await pubsub.subscribe(f"run:{id}:progress")

        try:
            # Check if run already finalized
            with ScopedQuery(org_id=org_id) as sq:
                current_run = sq.fetch_one("runs", where="id = %(id)s", params={"id": id})
            curr_status = current_run["status"] if current_run else "unknown"

            if curr_status in ("completed", "cancelled", "failed", "needs_attention"):
                payload = {
                    "run_id": id,
                    "status": curr_status,
                    "pct": float(current_run.get("progress_pct") or 100.0),
                    "message": f"Run is already in terminal state '{curr_status}'"
                }
                yield f"data: {json.dumps(payload)}\n\n"
                return

            init_payload = {
                "run_id": id,
                "status": curr_status,
                "pct": float(current_run.get("progress_pct") or 0.0),
                "message": f"Subscribed to progress stream for run {id}"
            }
            yield f"data: {json.dumps(init_payload)}\n\n"

            # Stream incoming events from pub/sub
            while True:
                message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                if message and message.get("data"):
                    raw = message["data"]
                    yield f"data: {raw}\n\n"
                    try:
                        parsed = json.loads(raw)
                        if parsed.get("status") in ("completed", "cancelled", "failed", "needs_attention"):
                            break
                    except Exception:
                        pass
                else:
                    # Check DB state periodically to guard against missed events
                    with ScopedQuery(org_id=org_id) as sq:
                        check_run = sq.fetch_one("runs", where="id = %(id)s", params={"id": id})
                    if check_run and check_run["status"] in ("completed", "cancelled", "failed", "needs_attention"):
                        terminal_payload = {
                            "run_id": id,
                            "status": check_run["status"],
                            "pct": float(check_run.get("progress_pct") or 100.0),
                            "message": f"Run reached terminal state '{check_run['status']}'"
                        }
                        yield f"data: {json.dumps(terminal_payload)}\n\n"
                        break
                    yield ": ping\n\n"
        finally:
            try:
                await pubsub.unsubscribe(f"run:{id}:progress")
                await r.aclose()
            except Exception:
                pass

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@router.post("/{id}/cancel")
async def cancel_run(
    id: str,
    current_user: dict = Depends(require_editor_or_admin)
):
    """
    Sets the cooperative cancellation flag in Redis and confirms the run has stopped.
    """
    org_id = current_user["org_id"]
    with ScopedQuery(org_id=org_id) as sq:
        run = sq.fetch_one("runs", where="id = %(id)s", params={"id": id})
    if not run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")

    queue = RunQueue(redis_url=REDIS_URL)
    queue.request_cancellation(id)

    if run["status"] == "queued":
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE runs SET status = 'cancelled', finished_at = %s WHERE id = %s",
                    (datetime.now(timezone.utc), id)
                )
            conn.commit()
        queue.publish_progress(id, {
            "run_id": id,
            "status": "cancelled",
            "pct": 0.0,
            "message": "Run cancelled while queued."
        })
        return {"status": "cancelled", "run_id": id}

    # Poll for terminal state confirmation
    final_status = run["status"]
    poll_start = time.time()
    while time.time() - poll_start < 10.0:
        with ScopedQuery(org_id=org_id) as sq:
            current_run = sq.fetch_one("runs", where="id = %(id)s", params={"id": id})
        if current_run and current_run["status"] in ("cancelled", "completed", "failed", "needs_attention"):
            final_status = current_run["status"]
            break
        await asyncio.sleep(0.1)

    return {"status": final_status, "run_id": id}


@router.post("/{id}/resume")
async def resume_run(
    id: str,
    current_user: dict = Depends(require_editor_or_admin)
):
    """
    Re-enqueues a run using the existing resumable frontier.
    """
    org_id = current_user["org_id"]
    with ScopedQuery(org_id=org_id) as sq:
        run = sq.fetch_one("runs", where="id = %(id)s", params={"id": id})
        if not run:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")
        site = sq.fetch_one("sites", where="id = %(id)s", params={"id": run["site_id"]})
        if not site:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Site not found")

    # Clear cancellation flag
    queue = RunQueue(redis_url=REDIS_URL)
    queue.clear_cancellation(id)

    # Re-enqueue with resumable options
    options = {
        "resume": True,
        "fresh": False,
        "max_pages": 50,
        "concurrency": 2,
        "show_live_display": False
    }

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE runs SET status = 'queued', current_pass = 'RESUMING' WHERE id = %s",
                (id,)
            )
        conn.commit()

    queue.enqueue_run(
        run_id=id,
        org_id=org_id,
        site_id=run["site_id"],
        target_url=site["url"],
        options=options
    )

    return {"status": "queued", "run_id": id, "resumed": True}


@router.get("/{id}/artifacts", response_model=List[ArtifactResponse])
def list_run_artifacts(
    id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Lists every uploaded artifact with type, size, and ID for a given run.
    Strictly scoped to the user's organization.
    """
    org_id = current_user["org_id"]
    with ScopedQuery(org_id=org_id) as sq:
        run = sq.fetch_one("runs", where="id = %(id)s", params={"id": id})
        if not run:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")

        artifacts = sq.fetch_all(
            "artifacts",
            where="run_id = %(run_id)s",
            params={"run_id": id},
            order_by="created_at ASC, filename ASC"
        )

    return [
        ArtifactResponse(
            id=a["id"],
            org_id=a["org_id"],
            site_id=a["site_id"],
            run_id=a["run_id"],
            filename=a["filename"],
            artifact_type=a["artifact_type"],
            size_bytes=a["size_bytes"],
            checksum_sha256=a["checksum_sha256"],
            content_type=a["content_type"],
            created_at=a["created_at"]
        )
        for a in artifacts
    ]


@router.get("/{id}/export.zip", response_model=SignedDownloadResponse)
def export_run_zip(
    id: str,
    expires_in: int = 3600,
    current_user: dict = Depends(get_current_user)
):
    """
    Bundles every artifact for that run into a single zip, uploads it to object storage,
    and returns a direct, time-limited presigned URL.
    """
    org_id = current_user["org_id"]
    with ScopedQuery(org_id=org_id) as sq:
        run = sq.fetch_one("runs", where="id = %(id)s", params={"id": id})
        if not run:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")
        site_id = run["site_id"]

    output_dir = f"reports/{id}/"
    storage_service = get_storage_service()
    zip_res = storage_service.create_and_upload_export_zip(
        org_id=org_id,
        site_id=site_id,
        run_id=id,
        output_dir=output_dir if os.path.exists(output_dir) else None
    )

    return SignedDownloadResponse(
        artifact_id=zip_res["artifact_id"],
        filename=zip_res["filename"],
        download_url=zip_res["download_url"],
        expires_in=zip_res["expires_in"],
        size_bytes=zip_res["size_bytes"],
        checksum_sha256=zip_res["checksum_sha256"]
    )
