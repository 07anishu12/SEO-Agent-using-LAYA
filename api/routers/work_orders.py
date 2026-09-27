"""
Work Orders Router: Engineering & Content Ticket Management, Platform Exports (GitHub, Jira, Linear),
and Real Automated Spec Verification.
"""
import json
import os
import sqlite3
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from database.connection import get_connection
from database.scoped_query import ScopedQuery
from engine.work_orders import WorkOrderManager
from verification.runner import VerificationRunner
from ..auth import get_current_user, require_editor_or_admin

router = APIRouter(tags=["work-orders"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------
class WorkOrderResponse(BaseModel):
    id: str
    org_id: str
    run_id: str
    site_id: str
    opportunity_id: Optional[str] = None
    display_id: str
    title: str
    order_type: str
    status: str
    priority: Optional[str] = None
    scope: Optional[str] = None
    problem: Optional[str] = None
    required_change: Optional[str] = None
    acceptance_criteria: Optional[str] = None
    verify_spec: Optional[str] = None
    evidence: Optional[Dict[str, Any]] = None
    file_locations: Optional[List[str]] = None
    ticket_ref: Optional[str] = None
    verify_last_result: Optional[str] = None
    created_at: Optional[datetime] = None


class WorkOrderExportRequest(BaseModel):
    platform: str = "github"  # github, jira, linear, markdown


class WorkOrderExportResponse(BaseModel):
    work_order_id: str
    display_id: str
    platform: str
    filename: str
    payload: Dict[str, Any]
    file_content: str


class WorkOrderVerifyRequest(BaseModel):
    target_url: Optional[str] = None
    html_content: Optional[str] = None
    live_fetch: bool = True


class WorkOrderVerifyResponse(BaseModel):
    verification_id: str
    work_order_id: str
    display_id: str
    status: str  # PASS, FAIL, ERROR
    spec: str
    target_url: Optional[str] = None
    details: str
    executed_at: str


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@router.get("/runs/{run_id}/work-orders", response_model=List[WorkOrderResponse])
def list_run_work_orders(
    run_id: str,
    order_type: Optional[str] = Query(None, description="engineering or content"),
    priority: Optional[str] = Query(None, description="P0, P1, P2, P3"),
    search: Optional[str] = Query(None, description="Search by title, display_id, or problem"),
    current_user: dict = Depends(get_current_user)
):
    """
    Lists work orders for a run, strictly scoped to the user's organization.
    Supports filtering by order_type (engineering vs content), priority, and text search.
    """
    org_id = current_user["org_id"]

    # Verify run ownership
    with ScopedQuery(org_id=org_id) as sq:
        run = sq.fetch_one("runs", where="id = %(id)s", params={"id": run_id})
    if not run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")

    conditions = ["org_id = %(org_id)s", "run_id = %(run_id)s"]
    params: Dict[str, Any] = {"org_id": org_id, "run_id": run_id}

    if order_type:
        conditions.append("order_type = %(order_type)s")
        params["order_type"] = order_type.lower()

    if priority:
        conditions.append("priority = %(priority)s")
        params["priority"] = priority.upper()

    if search:
        conditions.append("(title ILIKE %(search)s OR display_id ILIKE %(search)s OR problem ILIKE %(search)s)")
        params["search"] = f"%{search}%"

    where_clause = " AND ".join(conditions)

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"""
                SELECT id, org_id, run_id, site_id, opportunity_id, display_id,
                       title, order_type, status, priority, scope, problem,
                       required_change, acceptance_criteria, verify_spec,
                       evidence_json, file_locations_json, ticket_ref,
                       verify_last_result, created_at
                FROM work_orders
                WHERE {where_clause}
                ORDER BY 
                    CASE priority
                        WHEN 'P0' THEN 1
                        WHEN 'P1' THEN 2
                        WHEN 'P2' THEN 3
                        WHEN 'P3' THEN 4
                        ELSE 5
                    END,
                    display_id ASC
                """,
                params
            )
            rows = cur.fetchall()

    result = []
    for r in rows:
        ev = r.get("evidence_json")
        evidence_dict = ev if isinstance(ev, dict) else (json.loads(ev) if ev else {})
        fl = r.get("file_locations_json")
        file_locs = fl if isinstance(fl, list) else (json.loads(fl) if fl else [])

        result.append(
            WorkOrderResponse(
                id=r["id"],
                org_id=r["org_id"],
                run_id=r["run_id"],
                site_id=r["site_id"],
                opportunity_id=r.get("opportunity_id"),
                display_id=r["display_id"],
                title=r["title"],
                order_type=r["order_type"],
                status=r.get("status") or "open",
                priority=r.get("priority"),
                scope=r.get("scope"),
                problem=r.get("problem"),
                required_change=r.get("required_change"),
                acceptance_criteria=r.get("acceptance_criteria"),
                verify_spec=r.get("verify_spec"),
                evidence=evidence_dict,
                file_locations=file_locs,
                ticket_ref=r.get("ticket_ref"),
                verify_last_result=r.get("verify_last_result"),
                created_at=r.get("created_at")
            )
        )

    return result


@router.get("/work-orders/{id}", response_model=WorkOrderResponse)
def get_work_order(
    id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Retrieves full details for a single work order by ID or display_id.
    """
    org_id = current_user["org_id"]

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, org_id, run_id, site_id, opportunity_id, display_id,
                       title, order_type, status, priority, scope, problem,
                       required_change, acceptance_criteria, verify_spec,
                       evidence_json, file_locations_json, ticket_ref,
                       verify_last_result, created_at
                FROM work_orders
                WHERE org_id = %s AND (id = %s OR display_id = %s)
                LIMIT 1
                """,
                (org_id, id, id)
            )
            r = cur.fetchone()

    if not r:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Work order not found")

    ev = r.get("evidence_json")
    evidence_dict = ev if isinstance(ev, dict) else (json.loads(ev) if ev else {})
    fl = r.get("file_locations_json")
    file_locs = fl if isinstance(fl, list) else (json.loads(fl) if fl else [])

    return WorkOrderResponse(
        id=r["id"],
        org_id=r["org_id"],
        run_id=r["run_id"],
        site_id=r["site_id"],
        opportunity_id=r.get("opportunity_id"),
        display_id=r["display_id"],
        title=r["title"],
        order_type=r["order_type"],
        status=r.get("status") or "open",
        priority=r.get("priority"),
        scope=r.get("scope"),
        problem=r.get("problem"),
        required_change=r.get("required_change"),
        acceptance_criteria=r.get("acceptance_criteria"),
        verify_spec=r.get("verify_spec"),
        evidence=evidence_dict,
        file_locations=file_locs,
        ticket_ref=r.get("ticket_ref"),
        verify_last_result=r.get("verify_last_result"),
        created_at=r.get("created_at")
    )


@router.post("/work-orders/{id}/export", response_model=WorkOrderExportResponse)
def export_work_order(
    id: str,
    req: Optional[WorkOrderExportRequest] = None,
    platform: Optional[str] = Query(None),
    current_user: dict = Depends(require_editor_or_admin)
):
    """
    Exports a work order to a real platform-specific ticket payload (GitHub, Jira, Linear, or Markdown).
    Produces a downloadable payload file.
    """
    org_id = current_user["org_id"]
    target_platform = (platform or (req.platform if req else "github")).lower().strip()

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, org_id, run_id, site_id, opportunity_id, display_id,
                       title, order_type, status, priority, scope, problem,
                       required_change, acceptance_criteria, verify_spec,
                       evidence_json, file_locations_json
                FROM work_orders
                WHERE org_id = %s AND (id = %s OR display_id = %s)
                LIMIT 1
                """,
                (org_id, id, id)
            )
            r = cur.fetchone()

    if not r:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Work order not found")

    wo_dict = {
        "work_order_id": r["id"],
        "display_id": r["display_id"],
        "title": r["title"],
        "order_type": r["order_type"],
        "priority": r["priority"] or "P2",
        "scope": r["scope"] or "page",
        "problem": r["problem"] or "",
        "required_change": r["required_change"] or "",
        "acceptance_criteria": r["acceptance_criteria"] or "",
        "verify_spec": r["verify_spec"] or "status_code == 200",
        "evidence_json": json.dumps(r.get("evidence_json") or {}),
        "file_locations_json": json.dumps(r.get("file_locations_json") or [])
    }

    wo_mgr = WorkOrderManager()

    if target_platform == "jira":
        payload = wo_mgr.export_jira_issue(wo_dict)
        filename = f"{r['display_id']}_jira.json"
        file_content = json.dumps(payload, indent=2)
    elif target_platform == "linear":
        payload = wo_mgr.export_linear_issue(wo_dict)
        filename = f"{r['display_id']}_linear.json"
        file_content = json.dumps(payload, indent=2)
    elif target_platform == "markdown":
        md = wo_mgr.export_markdown(wo_dict)
        payload = {"markdown": md}
        filename = f"{r['display_id']}.md"
        file_content = md
    else:  # default github
        target_platform = "github"
        payload = wo_mgr.export_github_issue(wo_dict)
        filename = f"{r['display_id']}_github.json"
        file_content = json.dumps(payload, indent=2)

    return WorkOrderExportResponse(
        work_order_id=r["id"],
        display_id=r["display_id"],
        platform=target_platform,
        filename=filename,
        payload=payload,
        file_content=file_content
    )


@router.post("/work-orders/{id}/verify", response_model=WorkOrderVerifyResponse)
def verify_work_order(
    id: str,
    req: Optional[WorkOrderVerifyRequest] = None,
    current_user: dict = Depends(require_editor_or_admin)
):
    """
    Executes automated verification on a work order against real HTTP targets / HTML content.
    Returns and records PASS, FAIL, or ERROR / INCONCLUSIVE.
    """
    org_id = current_user["org_id"]
    target_url = req.target_url if req else None
    html_content = req.html_content if req else None
    live_fetch = req.live_fetch if req is not None else True

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT wo.id, wo.org_id, wo.run_id, wo.site_id, wo.opportunity_id,
                       wo.display_id, wo.title, wo.order_type, wo.status, wo.priority,
                       wo.scope, wo.problem, wo.required_change, wo.acceptance_criteria,
                       wo.verify_spec, wo.evidence_json, s.url as site_url
                FROM work_orders wo
                JOIN sites s ON s.id = wo.site_id
                WHERE wo.org_id = %s AND (wo.id = %s OR wo.display_id = %s)
                LIMIT 1
                """,
                (org_id, id, id)
            )
            r = cur.fetchone()

    if not r:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Work order not found")

    evidence = r.get("evidence_json")
    evidence_dict = evidence if isinstance(evidence, dict) else (json.loads(evidence) if evidence else {})
    sample_urls = evidence_dict.get("sample_urls", [])

    # Resolve evaluation target URL
    eval_url = target_url
    if not eval_url:
        if sample_urls:
            eval_url = sample_urls[0]
        else:
            eval_url = r["site_url"]

    # If relative path, join with site_url
    if eval_url and eval_url.startswith("/") and r.get("site_url"):
        eval_url = r["site_url"].rstrip("/") + eval_url

    wo_dict = {
        "work_order_id": r["id"],
        "display_id": r["display_id"],
        "run_id": r["run_id"],
        "verify_spec": r["verify_spec"] or "status_code == 200",
        "evidence_json": json.dumps(evidence_dict)
    }

    # Resolve SQLite db if exists
    db_path = f"data/{r['run_id']}.db"
    if not os.path.exists(db_path):
        db_path = "data/seo.db"

    runner = VerificationRunner(db_path=db_path)
    res = runner.verify_work_order(
        work_order=wo_dict,
        target_url=eval_url,
        html_content=html_content,
        live_fetch=live_fetch
    )

    raw_status = res.get("status", "FAILED").upper()
    details_str = str(res.get("details", ""))

    # Distinguish PASS, FAIL, ERROR
    if "Evaluation error" in details_str or "Fetch failed" in details_str or "SyntaxError" in details_str:
        norm_status = "ERROR"
    elif raw_status in ("PASSED", "PASS"):
        norm_status = "PASS"
    else:
        norm_status = "FAIL"

    # Persist verify_last_result in PostgreSQL work_orders and verifications ledger
    timestamp = datetime.now(timezone.utc)
    verif_id = f"verif_{r['display_id']}_{uuid4().hex[:12]}"

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE work_orders
                SET verify_last_result = %s
                WHERE id = %s AND org_id = %s
                """,
                (norm_status, r["id"], org_id)
            )
            cur.execute(
                """
                INSERT INTO verifications (
                    id, org_id, run_id, work_order_id, status, spec, target_url, details, executed_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    verif_id, org_id, r["run_id"], r["id"], norm_status,
                    wo_dict["verify_spec"], eval_url, details_str, timestamp
                )
            )
        conn.commit()

    return WorkOrderVerifyResponse(
        verification_id=verif_id,
        work_order_id=r["id"],
        display_id=r["display_id"],
        status=norm_status,
        spec=wo_dict["verify_spec"],
        target_url=eval_url,
        details=details_str,
        executed_at=timestamp.isoformat()
    )


class TicketSyncRequest(BaseModel):
    provider: str = "github"
    payload: Dict[str, Any] = {}
    target_url: Optional[str] = None
    html_content: Optional[str] = None
    live_fetch: bool = True


@router.post("/work-orders/ticket-sync")
def sync_external_ticket_state(
    req: TicketSyncRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Bi-directional External Ticket Sync (Section 6.3):
    Accepts state changes from GitHub, Jira, Linear.
    When a ticket is closed, executes the work order's verify_spec and updates status to Verified or Verification failed.
    Idempotent and strictly scoped to current_user's org_id.
    """
    org_id = current_user["org_id"]
    from services.ticket_sync import get_ticket_sync_manager
    manager = get_ticket_sync_manager()

    result = manager.process_ticket_event(
        org_id=org_id,
        provider=req.provider,
        payload=req.payload,
        target_url=req.target_url,
        html_content=req.html_content,
        live_fetch=req.live_fetch
    )
    return result


@router.get("/work-orders/{id}/sync-history")
def get_work_order_sync_history(
    id: str,
    current_user: dict = Depends(get_current_user)
):
    """Returns the ticket sync and verification history for a work order."""
    org_id = current_user["org_id"]

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT tse.id, tse.provider, tse.external_ticket_id, tse.event_type,
                       tse.previous_status, tse.new_status, tse.verification_id,
                       tse.verification_result, tse.failure_reason, tse.processed_at
                FROM ticket_sync_events tse
                JOIN work_orders wo ON wo.id = tse.work_order_id
                WHERE tse.org_id = %s AND (wo.id = %s OR wo.display_id = %s)
                ORDER BY tse.processed_at DESC
                """,
                (org_id, id, id)
            )
            rows = cur.fetchall()

    return {"work_order_id": id, "history": [dict(r) for r in rows]}

