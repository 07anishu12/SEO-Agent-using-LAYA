"""
Blueprints Router: 20-Dimension Page Optimization Blueprint Generator & Page Inventory.
"""
import os
import sqlite3
import hashlib
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from database.connection import get_connection
from database.scoped_query import ScopedQuery
from engine.blueprint import PageOptimizationBlueprint
from ..auth import get_current_user

router = APIRouter(tags=["blueprints"])


class BlueprintPageSummary(BaseModel):
    url: str
    template_id: Optional[str] = None
    page_type: Optional[str] = None
    status_code: int = 200
    title: Optional[str] = None
    inlinks_count: int = 0
    word_count: int = 0


class BlueprintDetailResponse(BaseModel):
    url: str
    run_id: str
    blueprint: Dict[str, Any]
    markdown: Optional[str] = None


@router.get("/runs/{run_id}/blueprints", response_model=List[BlueprintPageSummary])
def list_run_blueprint_pages(
    run_id: str,
    search: Optional[str] = Query(None, description="Filter pages by URL or title"),
    template_id: Optional[str] = Query(None, description="Filter pages by template ID"),
    limit: int = Query(100, ge=1, le=500),
    current_user: dict = Depends(get_current_user)
):
    """
    Lists crawled pages for a run available for deep 20-dimension blueprint inspection.
    Strictly scoped to user's organization.
    """
    org_id = current_user["org_id"]

    # Verify run ownership
    with ScopedQuery(org_id=org_id) as sq:
        run = sq.fetch_one("runs", where="id = %(id)s", params={"id": run_id})
    if not run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")

    db_path = f"data/{run_id}.db"
    pages: List[BlueprintPageSummary] = []

    if os.path.exists(db_path):
        try:
            with sqlite3.connect(db_path) as conn:
                conn.row_factory = sqlite3.Row
                query = "SELECT url, template_id, page_type, status_code, title, internal_links_count, word_count FROM pages WHERE crawl_id = ?"
                params: List[Any] = [run_id]

                if template_id:
                    query += " AND template_id = ?"
                    params.append(template_id)
                if search:
                    query += " AND (url LIKE ? OR title LIKE ?)"
                    params.extend([f"%{search}%", f"%{search}%"])

                query += f" ORDER BY internal_links_count DESC, url ASC LIMIT {limit}"

                for r in conn.execute(query, params).fetchall():
                    pages.append(
                        BlueprintPageSummary(
                            url=r["url"],
                            template_id=r["template_id"],
                            page_type=r["page_type"],
                            status_code=r["status_code"] or 200,
                            title=r["title"],
                            inlinks_count=r["internal_links_count"] or 0,
                            word_count=r["word_count"] or 0
                        )
                    )
        except Exception:
            pass

    # Fallback to PostgreSQL snapshots if SQLite file not present
    if not pages:
        with ScopedQuery(org_id=org_id) as sq:
            snaps = sq.fetch_all("snapshots", where="run_id = %(r)s", params={"r": run_id}, limit=limit)
            for s in snaps:
                data = s.get("snapshot_data") or {}
                pages.append(
                    BlueprintPageSummary(
                        url=s["url"],
                        status_code=data.get("status_code", 200),
                        title=data.get("title")
                    )
                )

    return pages


@router.get("/runs/{run_id}/blueprints/detail", response_model=BlueprintDetailResponse)
def get_page_blueprint_detail(
    run_id: str,
    url: str = Query(..., description="Target URL to inspect"),
    current_user: dict = Depends(get_current_user)
):
    """
    Generates and returns the complete 20-dimension Page Optimization Blueprint
    produced by the engine for the specified URL.
    """
    org_id = current_user["org_id"]

    # Verify run ownership
    with ScopedQuery(org_id=org_id) as sq:
        run = sq.fetch_one("runs", where="id = %(id)s", params={"id": run_id})
    if not run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")

    db_path = f"data/{run_id}.db"
    if not os.path.exists(db_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Run database '{db_path}' not available on server"
        )

    bp_engine = PageOptimizationBlueprint(db_path=db_path, store_dir="store")
    try:
        blueprint_data = bp_engine.generate_blueprint(url)
        markdown = bp_engine.render_markdown(blueprint_data)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate blueprint: {str(e)}"
        )

    # Persist reference in Postgres blueprints table
    bp_id = f"bp_{hashlib.sha256(f'{run_id}:{url}'.encode()).hexdigest()[:16]}"
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO blueprints (id, org_id, run_id, site_id, url, page_ref, artifact_path)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO NOTHING
                """,
                (bp_id, org_id, run_id, run["site_id"], url, url, f"reports/{run_id}/blueprints/{bp_id}.md")
            )
        conn.commit()

    return BlueprintDetailResponse(
        url=url,
        run_id=run_id,
        blueprint=blueprint_data,
        markdown=markdown
    )
