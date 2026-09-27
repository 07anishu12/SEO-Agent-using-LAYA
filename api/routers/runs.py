"""
Runs Router: Synchronous Pipeline Execution and Postgres Run Queries.
"""
from datetime import datetime
from uuid import uuid4
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status

from database.scoped_query import ScopedQuery
from database.etl import run_etl
from engine.pipeline import SEOJEVPipeline
from ..auth import get_current_user
from ..schemas import RunCreateRequest, RunResponse

router = APIRouter(prefix="/runs", tags=["runs"])


@router.post("", response_model=RunResponse, status_code=status.HTTP_201_CREATED)
async def create_and_execute_run(
    req: RunCreateRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Synchronously triggers a pipeline crawl run, runs Stage-2 ETL, and stores results in Postgres.
    """
    org_id = current_user["org_id"]

    # 1. Fetch site strictly scoped to org_id
    with ScopedQuery(org_id=org_id) as sq:
        site = sq.fetch_one("sites", where="id = %(id)s", params={"id": req.site_id})
    if not site:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Site not found")

    target_url = site["url"]
    crawl_id = req.crawl_id or f"crawl_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid4().hex[:6]}"
    db_path = f"data/{crawl_id}.db"
    reports_dir = f"reports/{crawl_id}/"

    # 2. Synchronous Stage-1 pipeline invocation
    pipeline = SEOJEVPipeline(
        target_url=target_url,
        crawl_id=crawl_id,
        db_path=db_path,
        output_dir=reports_dir,
        options={
            "max_pages": req.max_pages or 50,
            "concurrency": req.concurrency or 2,
            "render": req.render or False,
            "fresh": req.fresh if req.fresh is not None else True,
            "show_live_display": False
        }
    )
    pipeline_res = await pipeline.run_all()

    # 3. Stage-2 ETL into PostgreSQL
    etl_res = run_etl(
        sqlite_db_path=db_path,
        crawl_id=crawl_id,
        org_id=org_id,
        site_id=req.site_id
    )

    # 4. Fetch the newly populated run record from Postgres
    with ScopedQuery(org_id=org_id) as sq:
        run_row = sq.fetch_one("runs", where="id = %(id)s", params={"id": crawl_id})

    if not run_row:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve completed run record from database"
        )

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
        counts=etl_res.get("counts"),
        deliverables=pipeline_res.get("deliverables")
    )


@router.get("", response_model=List[RunResponse])
def list_runs(
    site_id: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
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
