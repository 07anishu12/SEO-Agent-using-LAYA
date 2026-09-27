"""
Templates Router: Structural Template Clustering, Member Counts, and Affected URLs.
"""
import os
import json
import sqlite3
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from database.connection import get_connection
from database.scoped_query import ScopedQuery
from ..auth import get_current_user

router = APIRouter(tags=["templates"])


class TemplateSummaryResponse(BaseModel):
    id: str
    org_id: str
    run_id: str
    site_id: str
    template_id: str
    page_type: Optional[str] = None
    page_count: int = 0
    issue_count: int = 0
    avg_word_count: Optional[float] = None
    avg_inlinks: Optional[float] = None
    structural_signature: Optional[str] = None
    sample_urls: List[str] = []


class TemplateDetailResponse(BaseModel):
    template: TemplateSummaryResponse
    member_urls: List[str] = []
    associated_findings: List[Dict[str, Any]] = []


@router.get("/runs/{run_id}/templates", response_model=List[TemplateSummaryResponse])
def list_run_templates(
    run_id: str,
    search: Optional[str] = Query(None, description="Search by template_id or page_type"),
    current_user: dict = Depends(get_current_user)
):
    """
    Lists all structural templates discovered for a run, with member counts and issue counts.
    Strictly scoped to the user's organization.
    """
    org_id = current_user["org_id"]

    # Verify run ownership
    with ScopedQuery(org_id=org_id) as sq:
        run = sq.fetch_one("runs", where="id = %(id)s", params={"id": run_id})
    if not run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")

    query = """
        SELECT 
            t.id, t.org_id, t.run_id, t.site_id, t.template_id,
            t.page_type, t.page_count, t.avg_word_count, t.avg_inlinks,
            t.structural_signature,
            (
                SELECT count(*) 
                FROM findings f 
                WHERE f.org_id = t.org_id 
                  AND f.run_id = t.run_id 
                  AND f.template_id = t.template_id
            ) as issue_count
        FROM templates t
        WHERE t.org_id = %(org_id)s AND t.run_id = %(run_id)s
    """
    params: Dict[str, Any] = {"org_id": org_id, "run_id": run_id}

    if search:
        query += " AND (t.template_id ILIKE %(search)s OR t.page_type ILIKE %(search)s)"
        params["search"] = f"%{search}%"

    query += " ORDER BY t.page_count DESC, t.template_id ASC"

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, params)
            rows = cur.fetchall()

    # Also inspect SQLite for sample URLs if available
    db_path = f"data/{run_id}.db"
    sample_urls_map: Dict[str, List[str]] = {}
    if os.path.exists(db_path):
        try:
            with sqlite3.connect(db_path) as s_conn:
                s_conn.row_factory = sqlite3.Row
                for r in s_conn.execute("SELECT template_id, sample_urls FROM templates WHERE crawl_id = ?", (run_id,)).fetchall():
                    raw = r["sample_urls"]
                    if raw:
                        try:
                            sample_urls_map[r["template_id"]] = json.loads(raw) if isinstance(raw, str) else list(raw)
                        except Exception:
                            sample_urls_map[r["template_id"]] = [raw]
        except Exception:
            pass

    results = []
    for r in rows:
        tid = r["template_id"]
        samples = sample_urls_map.get(tid, [])
        results.append(
            TemplateSummaryResponse(
                id=r["id"],
                org_id=r["org_id"],
                run_id=r["run_id"],
                site_id=r["site_id"],
                template_id=tid,
                page_type=r["page_type"],
                page_count=r["page_count"] or 0,
                issue_count=r["issue_count"] or 0,
                avg_word_count=float(r["avg_word_count"]) if r["avg_word_count"] is not None else None,
                avg_inlinks=float(r["avg_inlinks"]) if r["avg_inlinks"] is not None else None,
                structural_signature=r["structural_signature"],
                sample_urls=samples
            )
        )

    return results


@router.get("/runs/{run_id}/templates/{template_id}", response_model=TemplateDetailResponse)
def get_template_detail(
    run_id: str,
    template_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Returns granular template details, including all member URLs crawled for this template
    and the associated root-cause findings.
    """
    org_id = current_user["org_id"]

    # Verify run ownership
    with ScopedQuery(org_id=org_id) as sq:
        run = sq.fetch_one("runs", where="id = %(id)s", params={"id": run_id})
    if not run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT 
                    t.id, t.org_id, t.run_id, t.site_id, t.template_id,
                    t.page_type, t.page_count, t.avg_word_count, t.avg_inlinks,
                    t.structural_signature,
                    (
                        SELECT count(*) 
                        FROM findings f 
                        WHERE f.org_id = t.org_id 
                          AND f.run_id = t.run_id 
                          AND f.template_id = t.template_id
                    ) as issue_count
                FROM templates t
                WHERE t.org_id = %s AND t.run_id = %s AND t.template_id = %s
                LIMIT 1
                """,
                (org_id, run_id, template_id)
            )
            tpl = cur.fetchone()

            if not tpl:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found")

            # Fetch associated findings
            cur.execute(
                """
                SELECT display_id, rule_id, severity, priority, url, message, recommended_action
                FROM findings
                WHERE org_id = %s AND run_id = %s AND template_id = %s
                ORDER BY priority ASC, created_at DESC
                LIMIT 50
                """,
                (org_id, run_id, template_id)
            )
            findings = cur.fetchall()

    # Retrieve all member URLs from SQLite
    db_path = f"data/{run_id}.db"
    member_urls: List[str] = []
    samples: List[str] = []

    if os.path.exists(db_path):
        try:
            with sqlite3.connect(db_path) as s_conn:
                s_conn.row_factory = sqlite3.Row
                # 1. Check pages table
                p_rows = s_conn.execute(
                    "SELECT url FROM pages WHERE crawl_id = ? AND template_id = ? LIMIT 100",
                    (run_id, template_id)
                ).fetchall()
                member_urls = [r["url"] for r in p_rows]

                # 2. Check template_members table if empty
                if not member_urls:
                    tm_rows = s_conn.execute(
                        "SELECT url FROM template_members WHERE crawl_id = ? AND template_id = ? LIMIT 100",
                        (run_id, template_id)
                    ).fetchall()
                    member_urls = [r["url"] for r in tm_rows]

                # 3. Check sample_urls
                t_row = s_conn.execute(
                    "SELECT sample_urls FROM templates WHERE crawl_id = ? AND template_id = ?",
                    (run_id, template_id)
                ).fetchone()
                if t_row and t_row["sample_urls"]:
                    try:
                        raw = t_row["sample_urls"]
                        samples = json.loads(raw) if isinstance(raw, str) else list(raw)
                    except Exception:
                        samples = [t_row["sample_urls"]]
        except Exception:
            pass

    if not member_urls and samples:
        member_urls = samples

    summary = TemplateSummaryResponse(
        id=tpl["id"],
        org_id=tpl["org_id"],
        run_id=tpl["run_id"],
        site_id=tpl["site_id"],
        template_id=tpl["template_id"],
        page_type=tpl["page_type"],
        page_count=tpl["page_count"] or len(member_urls),
        issue_count=tpl["issue_count"] or len(findings),
        avg_word_count=float(tpl["avg_word_count"]) if tpl["avg_word_count"] is not None else None,
        avg_inlinks=float(tpl["avg_inlinks"]) if tpl["avg_inlinks"] is not None else None,
        structural_signature=tpl["structural_signature"],
        sample_urls=samples or member_urls[:5]
    )

    return TemplateDetailResponse(
        template=summary,
        member_urls=member_urls,
        associated_findings=findings
    )
