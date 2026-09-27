"""
Google Search Console (GSC) & Search Performance Router.
Extracts real striking-distance targets, cannibalization evidence, and search trends.
"""
import os
import csv
import io
import sqlite3
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from pydantic import BaseModel

from database.connection import get_connection
from database.scoped_query import ScopedQuery
from lab.gsc_generator import SyntheticGSCGenerator
from search.gsc_pipeline import GSCPipeline
from search.fit_analyzer import QueryFitAnalyzer
from ..auth import get_current_user

router = APIRouter(tags=["gsc"])


class GscSummaryResponse(BaseModel):
    has_data: bool
    total_queries: int = 0
    total_clicks: int = 0
    total_impressions: int = 0
    avg_position: float = 0.0
    striking_distance_count: int = 0
    striking_distance_queries: List[Dict[str, Any]] = []
    cannibalization_queries: List[Dict[str, Any]] = []
    query_clusters: List[Dict[str, Any]] = []
    impression_trends: List[Dict[str, Any]] = []
    click_trends: List[Dict[str, Any]] = []


@router.get("/runs/{run_id}/gsc", response_model=GscSummaryResponse)
def get_run_gsc_analysis(
    run_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Returns search performance analytics, striking-distance queries,
    cannibalization risks, and trend distributions for a completed crawl.
    """
    org_id = current_user["org_id"]

    # Verify run ownership
    with ScopedQuery(org_id=org_id) as sq:
        run = sq.fetch_one("runs", where="id = %(id)s", params={"id": run_id})
    if not run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")

    db_path = f"data/{run_id}.db"
    if not os.path.exists(db_path):
        return GscSummaryResponse(has_data=False)

    try:
        with sqlite3.connect(db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # Check if gsc_rows table exists and has records
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='gsc_rows'")
            if not cursor.fetchone():
                return GscSummaryResponse(has_data=False)

            cursor.execute("SELECT count(*) as count FROM gsc_rows")
            row_count = cursor.fetchone()["count"]
            if row_count == 0:
                return GscSummaryResponse(has_data=False)

            # Aggregate stats
            cursor.execute(
                """
                SELECT 
                    count(distinct query) as total_q,
                    coalesce(sum(clicks), 0) as total_c,
                    coalesce(sum(impressions), 0) as total_i,
                    coalesce(avg(position), 0.0) as avg_p
                FROM gsc_rows
                """
            )
            agg = cursor.fetchone()
            total_queries = agg["total_q"] or 0
            total_clicks = agg["total_c"] or 0
            total_impressions = agg["total_i"] or 0
            avg_pos = round(float(agg["avg_p"] or 0.0), 2)

            # Striking-distance queries (Position 11 - 25)
            cursor.execute(
                """
                SELECT query, page as url, clicks, impressions, ctr, position
                FROM gsc_rows
                WHERE position >= 10.0 AND position <= 25.0
                ORDER BY impressions DESC
                LIMIT 50
                """
            )
            striking_rows = [dict(r) for r in cursor.fetchall()]

            # Cannibalization detection: queries where >1 distinct pages rank
            cursor.execute(
                """
                SELECT query, count(distinct page) as page_count,
                       sum(impressions) as total_imp, sum(clicks) as total_clk
                FROM gsc_rows
                GROUP BY query
                HAVING page_count > 1
                ORDER BY total_imp DESC
                LIMIT 20
                """
            )
            cannibal_queries_summary = cursor.fetchall()
            cannibal_results = []
            for cq in cannibal_queries_summary:
                q_text = cq["query"]
                cursor.execute(
                    """
                    SELECT page as url, clicks, impressions, ctr, position
                    FROM gsc_rows
                    WHERE query = ?
                    ORDER BY impressions DESC
                    """,
                    (q_text,)
                )
                ranking_pages = [dict(p) for p in cursor.fetchall()]
                cannibal_results.append({
                    "query": q_text,
                    "pages_count": cq["page_count"],
                    "total_impressions": cq["total_imp"],
                    "total_clicks": cq["total_clk"],
                    "pages": ranking_pages
                })

            # Query clusters
            cursor.execute(
                """
                SELECT substr(query, 1, instr(query || ' ', ' ') - 1) as root_term,
                       count(*) as query_count,
                       sum(clicks) as cluster_clicks,
                       sum(impressions) as cluster_impressions,
                       avg(position) as cluster_pos
                FROM gsc_rows
                GROUP BY root_term
                HAVING length(root_term) > 3 AND query_count >= 1
                ORDER BY cluster_impressions DESC
                LIMIT 10
                """
            )
            clusters = [
                {
                    "cluster_name": r["root_term"],
                    "query_count": r["query_count"],
                    "clicks": r["cluster_clicks"],
                    "impressions": r["cluster_impressions"],
                    "avg_position": round(float(r["cluster_pos"] or 0), 1)
                }
                for r in cursor.fetchall()
            ]

            # Position Tier Trend Distribution (Position Brackets: 1-3, 4-10, 11-20, 21-50, 50+)
            cursor.execute(
                """
                SELECT 
                    CASE 
                        WHEN position <= 3 THEN 'Top 3 (Pos 1-3)'
                        WHEN position <= 10 THEN 'Page 1 (Pos 4-10)'
                        WHEN position <= 20 THEN 'Striking Distance (Pos 11-20)'
                        WHEN position <= 50 THEN 'Page 2-5 (Pos 21-50)'
                        ELSE 'Deep (Pos 50+)'
                    END as bracket,
                    count(*) as query_count,
                    sum(impressions) as impressions,
                    sum(clicks) as clicks
                FROM gsc_rows
                GROUP BY bracket
                ORDER BY min(position) ASC
                """
            )
            trends_raw = cursor.fetchall()
            imp_trends = [
                {"bracket": r["bracket"], "impressions": r["impressions"] or 0, "query_count": r["query_count"]}
                for r in trends_raw
            ]
            clk_trends = [
                {"bracket": r["bracket"], "clicks": r["clicks"] or 0, "query_count": r["query_count"]}
                for r in trends_raw
            ]

            return GscSummaryResponse(
                has_data=True,
                total_queries=total_queries,
                total_clicks=total_clicks,
                total_impressions=total_impressions,
                avg_position=avg_pos,
                striking_distance_count=len(striking_rows),
                striking_distance_queries=striking_rows,
                cannibalization_queries=cannibal_results,
                query_clusters=clusters,
                impression_trends=imp_trends,
                click_trends=clk_trends
            )
    except Exception as e:
        return GscSummaryResponse(has_data=False)


class GscImportRequest(BaseModel):
    csv_content: Optional[str] = None
    generate_synthetic: bool = False
    rows: Optional[List[Dict[str, Any]]] = None


@router.post("/runs/{run_id}/gsc")
def import_gsc_data(
    run_id: str,
    req: GscImportRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Imports Google Search Console performance data for a completed run from a CSV string
    or generates representative synthetic search traffic.
    """
    org_id = current_user["org_id"]

    with ScopedQuery(org_id=org_id) as sq:
        run = sq.fetch_one("runs", where="id = %(id)s", params={"id": run_id})
    if not run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")

    db_path = f"data/{run_id}.db"
    if not os.path.exists(db_path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run database file not found")

    rows: List[Dict[str, Any]] = []

    if req.csv_content:
        decoded = req.csv_content.strip()
        reader = csv.DictReader(io.StringIO(decoded))
        for r in reader:
            q = r.get("Top queries") or r.get("Query") or r.get("query")
            p = r.get("Top pages") or r.get("Page") or r.get("page") or r.get("url")
            if not q or not p:
                continue
            clk = int(float(r.get("Clicks") or r.get("clicks") or 0))
            imp = int(float(r.get("Impressions") or r.get("impressions") or 0))
            ctr_val = float(str(r.get("CTR") or r.get("ctr") or "0").replace("%", "")) / 100.0 if "%" in str(r.get("CTR") or "") else float(r.get("CTR") or r.get("ctr") or 0)
            pos_val = float(r.get("Position") or r.get("position") or 0)
            rows.append({
                "query": q,
                "page": p,
                "clicks": clk,
                "impressions": imp,
                "ctr": ctr_val,
                "position": pos_val
            })
    elif req.generate_synthetic:
        gen = SyntheticGSCGenerator(base_url=f"http://127.0.0.1:8961")
        rows = gen.generate_rows()
    elif req.rows:
        rows = req.rows
    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Must provide csv_content, rows, or generate_synthetic=true")

    # Ingest rows into SQLite
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS gsc_rows (
                run_id TEXT,
                query TEXT,
                page TEXT,
                url TEXT,
                clicks INTEGER,
                impressions INTEGER,
                ctr REAL,
                position REAL,
                date TEXT,
                PRIMARY KEY (query, page)
            )
            """
        )
        for r in rows:
            conn.execute(
                """
                INSERT OR REPLACE INTO gsc_rows (run_id, query, page, clicks, impressions, ctr, position)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (run_id, r["query"], r["page"], r["clicks"], r["impressions"], r["ctr"], r["position"])
            )
        conn.commit()

    # Update PostgreSQL gsc_summary table
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO gsc_summary (
                    id, org_id, run_id, site_id, total_queries,
                    total_clicks, total_impressions, avg_position, striking_distance_count
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE SET
                    total_queries = EXCLUDED.total_queries,
                    total_clicks = EXCLUDED.total_clicks,
                    total_impressions = EXCLUDED.total_impressions,
                    avg_position = EXCLUDED.avg_position,
                    striking_distance_count = EXCLUDED.striking_distance_count;
                """,
                (
                    f"{run_id}_gsc",
                    org_id,
                    run_id,
                    run["site_id"],
                    len(rows),
                    sum(r["clicks"] for r in rows),
                    sum(r["impressions"] for r in rows),
                    round(sum(r["position"] for r in rows) / len(rows), 2) if rows else 0.0,
                    sum(1 for r in rows if 10.0 <= r["position"] <= 25.0)
                )
            )
        conn.commit()

    return {"imported": len(rows), "run_id": run_id}


@router.post("/sites/{site_id}/gsc/detect-anomalies")
def trigger_gsc_anomaly_detection(
    site_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Triggers autonomous statistical anomaly detection across daily GSC metrics.
    Validates tenant isolation via JWT org_id.
    """
    org_id = current_user["org_id"]
    from services.gsc_anomaly import get_gsc_anomaly_detector
    detector = get_gsc_anomaly_detector()
    res = detector.detect_anomalies(site_id=site_id, org_id=org_id)
    return res
