"""
SEOJEV Phase 2: Full-Text Search Router (Stage 10g).
Implements Section 6.10: PostgreSQL tsvector, GIN index search across
findings/opportunities, blueprints, and queries with ranking and excerpts.
Strictly scoped to user's organization (org_id).
"""
import re
from typing import Dict, List, Optional, Any
from urllib.parse import quote
from fastapi import APIRouter, Depends, Query, HTTPException, status
from pydantic import BaseModel

from database.connection import get_connection
from ..auth import get_current_user
from ..security import rate_limit_search

router = APIRouter(tags=["search"])


class SearchResultItem(BaseModel):
    id: str
    title: str
    category: str
    excerpt: str
    score: float
    target_url: str
    run_id: Optional[str] = None
    site_id: Optional[str] = None
    display_id: Optional[str] = None
    severity: Optional[str] = None
    metadata: Dict[str, Any] = {}


class CategorizedSearchResults(BaseModel):
    findings: List[SearchResultItem] = []
    blueprints: List[SearchResultItem] = []
    queries: List[SearchResultItem] = []


class SearchResponse(BaseModel):
    query: str
    results: CategorizedSearchResults
    total_matches: int


def _build_prefix_query(query: str) -> str:
    tokens = [re.sub(r'[^a-zA-Z0-9]', '', w) for w in query.split() if re.sub(r'[^a-zA-Z0-9]', '', w)]
    return ' & '.join(f"{t}:*" for t in tokens) if tokens else ""


def execute_full_text_search(
    org_id: str,
    query_str: str,
    site_id: Optional[str] = None,
    category: Optional[str] = None,
    limit: int = 20
) -> SearchResponse:
    raw_query = query_str.strip()
    if not raw_query:
        return SearchResponse(
            query="",
            results=CategorizedSearchResults(),
            total_matches=0
        )

    prefix_query = _build_prefix_query(raw_query)

    params: Dict[str, Any] = {
        "raw": raw_query,
        "prefix": prefix_query,
        "org_id": org_id,
        "limit": limit
    }
    site_filter = ""
    if site_id:
        site_filter = " AND f.site_id = %(site_id)s"
        params["site_id"] = site_id

    cat_filter = (category or "all").lower()

    findings_results: List[SearchResultItem] = []
    blueprints_results: List[SearchResultItem] = []
    queries_results: List[SearchResultItem] = []

    with get_connection() as conn:
        with conn.cursor() as cur:
            # 1. Findings & Opportunities Search
            if cat_filter in ("all", "findings", "opportunities"):
                # Findings table search
                cur.execute(
                    f"""
                    WITH q AS (
                        SELECT 
                            websearch_to_tsquery('english', %(raw)s) as wq,
                            CASE WHEN %(prefix)s != '' THEN to_tsquery('english', %(prefix)s) ELSE ''::tsquery END as pq
                    )
                    SELECT 
                        f.id,
                        f.display_id,
                        f.subject as title,
                        f.url,
                        f.run_id,
                        f.site_id,
                        f.severity,
                        'finding' as kind,
                        GREATEST(
                            CASE WHEN q.wq != ''::tsquery AND f.search_vector @@ q.wq THEN ts_rank(f.search_vector, q.wq) ELSE 0 END,
                            CASE WHEN q.pq != ''::tsquery AND f.search_vector @@ q.pq THEN ts_rank(f.search_vector, q.pq) ELSE 0 END
                        ) as score,
                        ts_headline(
                            'english',
                            coalesce(f.subject, '') || ' — ' || coalesce(f.message, '') || ' ' || coalesce(f.recommended_action, ''),
                            CASE WHEN q.wq != ''::tsquery THEN q.wq ELSE q.pq END,
                            'StartSel=<mark>, StopSel=</mark>, MaxWords=30, MinWords=10'
                        ) as excerpt
                    FROM findings f, q
                    WHERE f.org_id = %(org_id)s
                      {site_filter}
                      AND (
                          (q.wq != ''::tsquery AND f.search_vector @@ q.wq)
                          OR
                          (q.pq != ''::tsquery AND f.search_vector @@ q.pq)
                      )
                    ORDER BY score DESC
                    LIMIT %(limit)s;
                    """,
                    params
                )
                for r in cur.fetchall():
                    disp = r["display_id"] or r["id"]
                    run_id = r["run_id"]
                    findings_results.append(
                        SearchResultItem(
                            id=r["id"],
                            title=r["title"] or f"Finding {disp}",
                            category="findings",
                            excerpt=r["excerpt"] or "",
                            score=round(float(r["score"] or 0.0), 4),
                            target_url=f"/runs/{run_id}/opportunities?id={quote(disp)}" if run_id else f"/sites/{r['site_id']}",
                            run_id=run_id,
                            site_id=r["site_id"],
                            display_id=disp,
                            severity=r["severity"],
                            metadata={"kind": "finding", "url": r["url"]}
                        )
                    )

                # Opportunities table search (appended to findings)
                opp_site_filter = " AND o.site_id = %(site_id)s" if site_id else ""
                cur.execute(
                    f"""
                    WITH q AS (
                        SELECT 
                            websearch_to_tsquery('english', %(raw)s) as wq,
                            CASE WHEN %(prefix)s != '' THEN to_tsquery('english', %(prefix)s) ELSE ''::tsquery END as pq
                    )
                    SELECT 
                        o.id,
                        o.display_id,
                        (coalesce(o.display_id, '') || ': ' || coalesce(o.observation, '')) as title,
                        o.run_id,
                        o.site_id,
                        o.tier as severity,
                        'opportunity' as kind,
                        GREATEST(
                            CASE WHEN q.wq != ''::tsquery AND o.search_vector @@ q.wq THEN ts_rank(o.search_vector, q.wq) ELSE 0 END,
                            CASE WHEN q.pq != ''::tsquery AND o.search_vector @@ q.pq THEN ts_rank(o.search_vector, q.pq) ELSE 0 END
                        ) as score,
                        ts_headline(
                            'english',
                            coalesce(o.observation, '') || ' — ' || coalesce(o.action, '') || ' ' || coalesce(o.diagnosis, ''),
                            CASE WHEN q.wq != ''::tsquery THEN q.wq ELSE q.pq END,
                            'StartSel=<mark>, StopSel=</mark>, MaxWords=30, MinWords=10'
                        ) as excerpt
                    FROM opportunities o, q
                    WHERE o.org_id = %(org_id)s
                      {opp_site_filter}
                      AND (
                          (q.wq != ''::tsquery AND o.search_vector @@ q.wq)
                          OR
                          (q.pq != ''::tsquery AND o.search_vector @@ q.pq)
                      )
                    ORDER BY score DESC
                    LIMIT %(limit)s;
                    """,
                    params
                )
                for r in cur.fetchall():
                    disp = r["display_id"] or r["id"]
                    run_id = r["run_id"]
                    findings_results.append(
                        SearchResultItem(
                            id=r["id"],
                            title=r["title"] or f"Opportunity {disp}",
                            category="findings",
                            excerpt=r["excerpt"] or "",
                            score=round(float(r["score"] or 0.0), 4),
                            target_url=f"/runs/{run_id}/opportunities?id={quote(disp)}" if run_id else f"/sites/{r['site_id']}",
                            run_id=run_id,
                            site_id=r["site_id"],
                            display_id=disp,
                            severity=r["severity"],
                            metadata={"kind": "opportunity"}
                        )
                    )

                findings_results.sort(key=lambda x: x.score, reverse=True)
                findings_results = findings_results[:limit]

            # 2. Blueprints Search
            if cat_filter in ("all", "blueprints"):
                bp_site_filter = " AND b.site_id = %(site_id)s" if site_id else ""
                cur.execute(
                    f"""
                    WITH q AS (
                        SELECT 
                            websearch_to_tsquery('english', %(raw)s) as wq,
                            CASE WHEN %(prefix)s != '' THEN to_tsquery('english', %(prefix)s) ELSE ''::tsquery END as pq
                    )
                    SELECT 
                        b.id,
                        coalesce(b.title, b.url) as title,
                        b.url,
                        b.page_ref,
                        b.run_id,
                        b.site_id,
                        GREATEST(
                            CASE WHEN q.wq != ''::tsquery AND b.search_vector @@ q.wq THEN ts_rank(b.search_vector, q.wq) ELSE 0 END,
                            CASE WHEN q.pq != ''::tsquery AND b.search_vector @@ q.pq THEN ts_rank(b.search_vector, q.pq) ELSE 0 END
                        ) as score,
                        ts_headline(
                            'english',
                            coalesce(b.title, '') || ' ' || coalesce(b.url, '') || ' ' || coalesce(b.page_ref, ''),
                            CASE WHEN q.wq != ''::tsquery THEN q.wq ELSE q.pq END,
                            'StartSel=<mark>, StopSel=</mark>, MaxWords=30, MinWords=10'
                        ) as excerpt
                    FROM blueprints b, q
                    WHERE b.org_id = %(org_id)s
                      {bp_site_filter}
                      AND (
                          (q.wq != ''::tsquery AND b.search_vector @@ q.wq)
                          OR
                          (q.pq != ''::tsquery AND b.search_vector @@ q.pq)
                      )
                    ORDER BY score DESC
                    LIMIT %(limit)s;
                    """,
                    params
                )
                for r in cur.fetchall():
                    run_id = r["run_id"]
                    url = r["url"]
                    blueprints_results.append(
                        SearchResultItem(
                            id=r["id"],
                            title=r["title"],
                            category="blueprints",
                            excerpt=r["excerpt"] or "",
                            score=round(float(r["score"] or 0.0), 4),
                            target_url=f"/runs/{run_id}/blueprints/detail?url={quote(url)}" if run_id else url,
                            run_id=run_id,
                            site_id=r["site_id"],
                            metadata={"url": url, "page_ref": r["page_ref"]}
                        )
                    )

            # 3. Queries Search
            if cat_filter in ("all", "queries"):
                qry_site_filter = " AND qry.site_id = %(site_id)s" if site_id else ""
                cur.execute(
                    f"""
                    WITH q AS (
                        SELECT 
                            websearch_to_tsquery('english', %(raw)s) as wq,
                            CASE WHEN %(prefix)s != '' THEN to_tsquery('english', %(prefix)s) ELSE ''::tsquery END as pq
                    )
                    SELECT 
                        qry.id,
                        qry.query as title,
                        qry.page_url,
                        qry.clicks,
                        qry.impressions,
                        qry.position,
                        qry.intent,
                        qry.run_id,
                        qry.site_id,
                        GREATEST(
                            CASE WHEN q.wq != ''::tsquery AND qry.search_vector @@ q.wq THEN ts_rank(qry.search_vector, q.wq) ELSE 0 END,
                            CASE WHEN q.pq != ''::tsquery AND qry.search_vector @@ q.pq THEN ts_rank(qry.search_vector, q.pq) ELSE 0 END
                        ) as score,
                        ts_headline(
                            'english',
                            coalesce(qry.query, '') || ' ' || coalesce(qry.page_url, '') || ' ' || coalesce(qry.intent, ''),
                            CASE WHEN q.wq != ''::tsquery THEN q.wq ELSE q.pq END,
                            'StartSel=<mark>, StopSel=</mark>, MaxWords=30, MinWords=10'
                        ) as excerpt
                    FROM queries qry, q
                    WHERE qry.org_id = %(org_id)s
                      {qry_site_filter}
                      AND (
                          (q.wq != ''::tsquery AND qry.search_vector @@ q.wq)
                          OR
                          (q.pq != ''::tsquery AND qry.search_vector @@ q.pq)
                      )
                    ORDER BY score DESC
                    LIMIT %(limit)s;
                    """,
                    params
                )
                for r in cur.fetchall():
                    run_id = r["run_id"]
                    q_text = r["title"]
                    queries_results.append(
                        SearchResultItem(
                            id=r["id"],
                            title=q_text,
                            category="queries",
                            excerpt=r["excerpt"] or "",
                            score=round(float(r["score"] or 0.0), 4),
                            target_url=f"/runs/{run_id}/gsc?q={quote(q_text)}" if run_id else f"/sites/{r['site_id']}",
                            run_id=run_id,
                            site_id=r["site_id"],
                            metadata={
                                "page_url": r["page_url"],
                                "clicks": r["clicks"],
                                "impressions": r["impressions"],
                                "position": float(r["position"] or 0.0),
                                "intent": r["intent"]
                            }
                        )
                    )

    total_matches = len(findings_results) + len(blueprints_results) + len(queries_results)

    return SearchResponse(
        query=raw_query,
        results=CategorizedSearchResults(
            findings=findings_results,
            blueprints=blueprints_results,
            queries=queries_results
        ),
        total_matches=total_matches
    )


@router.get("/search", response_model=SearchResponse, dependencies=[Depends(rate_limit_search)])
def search_global(
    q: str = Query(..., min_length=1, max_length=200, description="Search query string"),
    site_id: Optional[str] = Query(None, description="Optional site ID to filter results"),
    category: Optional[str] = Query(None, description="Filter category: all, findings, blueprints, queries"),
    limit: int = Query(20, ge=1, le=100, description="Max results per category"),
    current_user: dict = Depends(get_current_user)
):
    """
    Unified Full-Text Search across findings/opportunities, blueprints, and queries.
    Ranked via PostgreSQL tsvector and GIN indexes, strictly scoped to current user's organization.
    """
    org_id = current_user["org_id"]
    return execute_full_text_search(
        org_id=org_id,
        query_str=q,
        site_id=site_id,
        category=category,
        limit=limit
    )


@router.get("/sites/{site_id}/search", response_model=SearchResponse, dependencies=[Depends(rate_limit_search)])
def search_site_scoped(
    site_id: str,
    q: str = Query(..., min_length=1, max_length=200, description="Search query string"),
    category: Optional[str] = Query(None, description="Filter category: all, findings, blueprints, queries"),
    limit: int = Query(20, ge=1, le=100, description="Max results per category"),
    current_user: dict = Depends(get_current_user)
):
    """
    Site-scoped Full-Text Search across findings, blueprints, and queries.
    Strictly scoped to current user's organization.
    """
    org_id = current_user["org_id"]
    return execute_full_text_search(
        org_id=org_id,
        query_str=q,
        site_id=site_id,
        category=category,
        limit=limit
    )
