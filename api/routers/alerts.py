"""
SEOJEV Stage 9 Alerts Router:
Lists, filters, and manages alerts for a monitored site.
Strictly scoped to current_user["org_id"].
"""
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status

from database.connection import get_connection
from database.scoped_query import ScopedQuery
from ..auth import get_current_user
from ..schemas import AlertResponse, AlertListResponse, AlertUpdateRequest

router = APIRouter(prefix="/sites/{id}/alerts", tags=["alerts"])


def _verify_site_access(site_id: str, org_id: str):
    with ScopedQuery(org_id=org_id) as sq:
        site = sq.fetch_one("sites", where="id = %(id)s", params={"id": site_id})
    if not site:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Site not found")
    return site


@router.get("", response_model=AlertListResponse)
def list_alerts(
    id: str,
    severity: Optional[str] = Query(None, description="Filter by severity: critical, high, medium, low"),
    alert_type: Optional[str] = Query(None, description="Filter by alert_type"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status: open, resolved"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: dict = Depends(get_current_user)
):
    org_id = current_user["org_id"]
    _verify_site_access(id, org_id)

    query_parts = ["org_id = %(org_id)s", "site_id = %(site_id)s"]
    params: Dict[str, Any] = {"org_id": org_id, "site_id": id, "limit": limit, "offset": offset}

    if severity:
        query_parts.append("LOWER(severity) = %(severity)s")
        params["severity"] = severity.lower()

    if alert_type:
        query_parts.append("alert_type = %(alert_type)s")
        params["alert_type"] = alert_type

    if status_filter:
        query_parts.append("status = %(status)s")
        params["status"] = status_filter.lower()

    where_clause = " AND ".join(query_parts)

    with get_connection() as conn:
        with conn.cursor() as cur:
            # Count total matching alerts
            cur.execute(f"SELECT COUNT(*) as total FROM alerts WHERE {where_clause}", params)
            total = cur.fetchone()["total"]

            # Fetch paginated rows
            cur.execute(
                f"""
                SELECT id, org_id, site_id, run_id, alert_type, severity, title, message,
                       source, fingerprint, affected_urls_json, previous_value, current_value,
                       status, is_resolved, dispatched, dispatch_status, dispatch_error,
                       payload_json, detected_at, created_at
                FROM alerts
                WHERE {where_clause}
                ORDER BY detected_at DESC
                LIMIT %(limit)s OFFSET %(offset)s
                """,
                params
            )
            rows = cur.fetchall()

    alert_items = []
    for r in rows:
        aff = r.get("affected_urls_json") or []
        aff_list = aff if isinstance(aff, list) else []
        alert_items.append(
            AlertResponse(
                id=r["id"],
                org_id=r["org_id"],
                site_id=r["site_id"],
                run_id=r.get("run_id"),
                alert_type=r["alert_type"],
                severity=r["severity"],
                title=r.get("title") or r["alert_type"],
                message=r["message"],
                source=r.get("source") or "watch",
                fingerprint=r.get("fingerprint"),
                affected_urls=aff_list,
                previous_value=r.get("previous_value"),
                current_value=r.get("current_value"),
                status=r.get("status") or ("resolved" if r.get("is_resolved") else "open"),
                is_resolved=r.get("is_resolved", False),
                dispatched=r.get("dispatched", False),
                dispatch_status=r.get("dispatch_status") or "pending",
                dispatch_error=r.get("dispatch_error"),
                payload_json=r.get("payload_json") or {},
                detected_at=r.get("detected_at"),
                created_at=r.get("created_at")
            )
        )

    return AlertListResponse(alerts=alert_items, total=total)


@router.patch("/{alert_id}", response_model=AlertResponse)
def update_alert(
    id: str,
    alert_id: str,
    req: AlertUpdateRequest,
    current_user: dict = Depends(get_current_user)
):
    org_id = current_user["org_id"]
    _verify_site_access(id, org_id)

    new_status = req.status.lower()
    is_resolved = (new_status == "resolved")

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE alerts
                SET status = %s,
                    is_resolved = %s
                WHERE id = %s AND org_id = %s AND site_id = %s
                RETURNING id, org_id, site_id, run_id, alert_type, severity, title, message,
                          source, fingerprint, affected_urls_json, previous_value, current_value,
                          status, is_resolved, dispatched, dispatch_status, dispatch_error,
                          payload_json, detected_at, created_at;
                """,
                (new_status, is_resolved, alert_id, org_id, id)
            )
            row = cur.fetchone()
        conn.commit()

    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found")

    aff = row.get("affected_urls_json") or []
    aff_list = aff if isinstance(aff, list) else []

    return AlertResponse(
        id=row["id"],
        org_id=row["org_id"],
        site_id=row["site_id"],
        run_id=row.get("run_id"),
        alert_type=row["alert_type"],
        severity=row["severity"],
        title=row.get("title") or row["alert_type"],
        message=row["message"],
        source=row.get("source") or "watch",
        fingerprint=row.get("fingerprint"),
        affected_urls=aff_list,
        previous_value=row.get("previous_value"),
        current_value=row.get("current_value"),
        status=row.get("status") or ("resolved" if row.get("is_resolved") else "open"),
        is_resolved=row.get("is_resolved", False),
        dispatched=row.get("dispatched", False),
        dispatch_status=row.get("dispatch_status") or "pending",
        dispatch_error=row.get("dispatch_error"),
        payload_json=row.get("payload_json") or {},
        detected_at=row.get("detected_at"),
        created_at=row.get("created_at")
    )
