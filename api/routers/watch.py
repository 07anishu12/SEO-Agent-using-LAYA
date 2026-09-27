"""
SEOJEV Stage 9 Watch Config Router:
Configures cron-style recurring lightweight checks for a site.
Strictly scoped to current_user["org_id"].
"""
import hashlib
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from croniter import croniter
from psycopg.types.json import Jsonb

from database.connection import get_connection
from database.scoped_query import ScopedQuery
from ..auth import get_current_user, require_editor_or_admin
from ..schemas import WatchConfigRequest, WatchConfigResponse

router = APIRouter(prefix="/sites/{id}/watch", tags=["watch"])


def _verify_site_access(site_id: str, org_id: str):
    with ScopedQuery(org_id=org_id) as sq:
        site = sq.fetch_one("sites", where="id = %(id)s", params={"id": site_id})
    if not site:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Site not found")
    return site


@router.post("", response_model=WatchConfigResponse)
def update_watch_config(
    id: str,
    req: WatchConfigRequest,
    current_user: dict = Depends(require_editor_or_admin)
):
    org_id = current_user["org_id"]
    _verify_site_access(id, org_id)

    cron_expr = (req.cron_expression or "0 0 * * *").strip()
    if not croniter.is_valid(cron_expr):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid cron expression: '{cron_expr}'"
        )

    now_utc = datetime.now(timezone.utc)
    try:
        c_iter = croniter(cron_expr, now_utc)
        next_run = c_iter.get_next(datetime)
        if next_run.tzinfo is None:
            next_run = next_run.replace(tzinfo=timezone.utc)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error evaluating cron schedule: {str(exc)}"
        )

    config_id = f"watch_{hashlib.sha256(f'{org_id}:{id}'.encode('utf-8')).hexdigest()[:16]}"
    checks = req.checks if req.checks is not None else ["robots_txt", "sitemap", "top_pages", "template_drift"]
    top_pages = req.top_pages or []
    notification_channels = req.notification_channels or []

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO watch_configs (
                    id, org_id, site_id, cron_expression, is_active, timezone,
                    checks_json, top_pages_json, notification_channels_json,
                    next_run_at, updated_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (org_id, site_id) DO UPDATE SET
                    cron_expression = EXCLUDED.cron_expression,
                    is_active = EXCLUDED.is_active,
                    timezone = EXCLUDED.timezone,
                    checks_json = EXCLUDED.checks_json,
                    top_pages_json = EXCLUDED.top_pages_json,
                    notification_channels_json = EXCLUDED.notification_channels_json,
                    next_run_at = EXCLUDED.next_run_at,
                    updated_at = EXCLUDED.updated_at
                RETURNING id, org_id, site_id, cron_expression, is_active, timezone,
                          checks_json, top_pages_json, notification_channels_json,
                          last_run_at, next_run_at, created_at, updated_at;
                """,
                (
                    config_id,
                    org_id,
                    id,
                    cron_expr,
                    req.is_active if req.is_active is not None else True,
                    req.timezone or "UTC",
                    Jsonb(checks),
                    Jsonb(top_pages),
                    Jsonb(notification_channels),
                    next_run,
                    now_utc
                )
            )
            row = cur.fetchone()
        conn.commit()

    return WatchConfigResponse(
        id=row["id"],
        org_id=row["org_id"],
        site_id=row["site_id"],
        cron_expression=row["cron_expression"],
        is_active=row["is_active"],
        timezone=row.get("timezone") or "UTC",
        checks=row.get("checks_json") or [],
        top_pages=row.get("top_pages_json") or [],
        notification_channels=row.get("notification_channels_json") or [],
        last_run_at=row.get("last_run_at"),
        next_run_at=row.get("next_run_at"),
        created_at=row.get("created_at"),
        updated_at=row.get("updated_at")
    )


@router.get("", response_model=WatchConfigResponse)
def get_watch_config(
    id: str,
    current_user: dict = Depends(get_current_user)
):
    org_id = current_user["org_id"]
    _verify_site_access(id, org_id)

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, org_id, site_id, cron_expression, is_active, timezone,
                       checks_json, top_pages_json, notification_channels_json,
                       last_run_at, next_run_at, created_at, updated_at
                FROM watch_configs
                WHERE org_id = %s AND site_id = %s
                """,
                (org_id, id)
            )
            row = cur.fetchone()

    if not row:
        # Return default schedule config for this site
        return WatchConfigResponse(
            id=f"watch_default_{id}",
            org_id=org_id,
            site_id=id,
            cron_expression="0 0 * * *",
            is_active=True,
            timezone="UTC",
            checks=["robots_txt", "sitemap", "top_pages", "template_drift"],
            top_pages=[],
            notification_channels=[]
        )

    return WatchConfigResponse(
        id=row["id"],
        org_id=row["org_id"],
        site_id=row["site_id"],
        cron_expression=row["cron_expression"] or "0 0 * * *",
        is_active=row["is_active"] if row["is_active"] is not None else True,
        timezone=row.get("timezone") or "UTC",
        checks=row.get("checks_json") or [],
        top_pages=row.get("top_pages_json") or [],
        notification_channels=row.get("notification_channels_json") or [],
        last_run_at=row.get("last_run_at"),
        next_run_at=row.get("next_run_at"),
        created_at=row.get("created_at"),
        updated_at=row.get("updated_at")
    )
