"""
SEOJEV Stage 10a Historical Trend Engine:
Tracks time-series metrics (issue_count, opportunity_count) across audit runs.
Populates time-series rows idempotently after run completion.
Strictly tenant-scoped to org_id.
"""
import hashlib
import logging
from datetime import datetime, timezone, date
from typing import Dict, Any, List, Optional
from psycopg.types.json import Jsonb

from database.connection import get_connection

logger = logging.getLogger("seojev.trends")


def record_run_trends(
    org_id: str,
    site_id: str,
    run_id: str,
    run_date: Optional[date] = None,
    counts_override: Optional[Dict[str, int]] = None,
    db_url: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Computes and persists trend metrics for a completed run into site_trends.
    Idempotent: updates existing rows if already processed for this run_id.
    """
    with get_connection(db_url) as conn:
        with conn.cursor() as cur:
            # 1. Determine run date and fallback counts if not provided
            issue_count = 0
            opp_count = 0
            target_date = run_date

            if counts_override:
                issue_count = counts_override.get("issue_count", counts_override.get("findings", 0))
                opp_count = counts_override.get("opportunity_count", counts_override.get("opportunities", 0))

            cur.execute(
                "SELECT finished_at, created_at, total_issues FROM runs WHERE org_id = %s AND id = %s",
                (org_id, run_id)
            )
            run_row = cur.fetchone()
            if run_row:
                if not target_date:
                    ts = run_row.get("finished_at") or run_row.get("created_at") or datetime.now(timezone.utc)
                    target_date = ts.date() if isinstance(ts, datetime) else date.today()
                if not counts_override:
                    issue_count = run_row.get("total_issues") or 0

            target_date = target_date or date.today()

            # If counts not explicitly provided, query findings and opportunities tables
            if not counts_override:
                cur.execute(
                    "SELECT COUNT(*) as cnt FROM findings WHERE org_id = %s AND run_id = %s",
                    (org_id, run_id)
                )
                f_row = cur.fetchone()
                if f_row and f_row["cnt"] > 0:
                    issue_count = f_row["cnt"]

                cur.execute(
                    "SELECT COUNT(*) as cnt FROM opportunities WHERE org_id = %s AND run_id = %s",
                    (org_id, run_id)
                )
                o_row = cur.fetchone()
                if o_row and o_row["cnt"] > 0:
                    opp_count = o_row["cnt"]

            metrics_to_record = [
                ("issue_count", float(issue_count)),
                ("opportunity_count", float(opp_count)),
            ]

            persisted = []
            for metric, val in metrics_to_record:
                trend_id = f"trnd_{hashlib.sha256(f'{org_id}:{site_id}:{metric}:{run_id}'.encode()).hexdigest()[:16]}"
                cur.execute(
                    """
                    INSERT INTO site_trends (
                        id, org_id, site_id, run_id, metric, date, value, metadata_json
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (org_id, site_id, metric, run_id) DO UPDATE SET
                        date = EXCLUDED.date,
                        value = EXCLUDED.value,
                        metadata_json = EXCLUDED.metadata_json
                    RETURNING id, org_id, site_id, run_id, metric, date, value, created_at;
                    """,
                    (
                        trend_id,
                        org_id,
                        site_id,
                        run_id,
                        metric,
                        target_date,
                        val,
                        Jsonb({"run_id": run_id, "recorded_at": datetime.now(timezone.utc).isoformat()})
                    )
                )
                row = cur.fetchone()
                if row:
                    persisted.append(dict(row))
        conn.commit()

    logger.info(f"Recorded {len(persisted)} trend metrics for site {site_id}, run {run_id}")
    return persisted


def get_site_trends(
    org_id: str,
    site_id: str,
    metric: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    db_url: Optional[str] = None
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Returns ordered time-series points grouped by metric for a site.
    Strictly scoped to org_id.
    """
    query_parts = ["org_id = %(org_id)s", "site_id = %(site_id)s"]
    params: Dict[str, Any] = {"org_id": org_id, "site_id": site_id}

    if metric:
        query_parts.append("metric = %(metric)s")
        params["metric"] = metric

    if start_date:
        query_parts.append("date >= %(start_date)s")
        params["start_date"] = start_date

    if end_date:
        query_parts.append("date <= %(end_date)s")
        params["end_date"] = end_date

    where_clause = " AND ".join(query_parts)

    with get_connection(db_url) as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"""
                SELECT id, site_id, run_id, metric, date, value, created_at
                FROM site_trends
                WHERE {where_clause}
                ORDER BY date ASC, created_at ASC
                """,
                params
            )
            rows = cur.fetchall()

    trends: Dict[str, List[Dict[str, Any]]] = {}
    for r in rows:
        m = r["metric"]
        if m not in trends:
            trends[m] = []
        trends[m].append({
            "id": r["id"],
            "run_id": r.get("run_id"),
            "date": r["date"].isoformat() if hasattr(r["date"], "isoformat") else str(r["date"]),
            "value": float(r["value"]),
            "created_at": r["created_at"].isoformat() if hasattr(r["created_at"], "isoformat") else str(r["created_at"])
        })

    return trends
