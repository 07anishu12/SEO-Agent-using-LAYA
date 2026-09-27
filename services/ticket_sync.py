"""
SEOJEV Phase 2: Bi-directional Ticket Sync Service (Stage 10f).

Implements Section 6.3:
When an external ticket (GitHub, Jira, Linear) is closed:
  ticket closed
      ↓
  identify linked SEOJEV work order
      ↓
  load verification specification
      ↓
  execute verification
      ↓
  update work-order status -> "Verified" or "Verification failed"

Guarantees:
1. Genuine Verification: Never marks a work order "Verified" merely because the external ticket was closed.
2. Idempotency: Prevents duplicate execution of verifications on duplicate webhooks/poll events.
3. Multi-tenant Isolation: Scoped strictly to authenticated org_id.
4. Comprehensive Audit Trail: Persists external ticket ID, provider, statuses, verification ID, and failure reasons.
"""
import hashlib
import json
import logging
import os
import re
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from uuid import uuid4

from psycopg.types.json import Jsonb

from database.connection import get_connection
from verification.runner import VerificationRunner

logger = logging.getLogger("seojev.ticket_sync")

CLOSED_STATUSES = {"closed", "done", "resolved", "completed", "finished"}


class TicketSyncManager:
    """
    Manages bi-directional ticket state synchronization with external issue trackers.
    """
    def __init__(
        self,
        db_url: Optional[str] = None,
        verification_runner: Optional[VerificationRunner] = None
    ):
        self.db_url = db_url or os.environ.get("DATABASE_URL", "postgresql:///seojev_test")
        self.runner = verification_runner or VerificationRunner()

    def parse_event(
        self,
        provider: str,
        payload: Dict[str, Any],
        headers: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Parses provider-specific payloads (GitHub, Jira, Linear, or Generic) into a standardized event.
        """
        prov = provider.lower().strip()
        hdrs = {k.lower(): v for k, v in (headers or {}).items()}

        external_ticket_id = ""
        action = ""
        status_val = ""
        title = ""
        work_order_hint = ""

        if prov == "github":
            action = str(payload.get("action") or hdrs.get("x-github-event") or "")
            issue = payload.get("issue") or {}
            external_ticket_id = str(issue.get("number") or issue.get("id") or "")
            status_val = str(issue.get("state") or ("closed" if action == "closed" else "open")).lower()
            title = str(issue.get("title") or "")
            body = str(issue.get("body") or "")

            # Look for [WO-123] or WO-123 in title or body
            m = re.search(r"\[?(WO-[A-Za-z0-9_\-]+)\]?", title + " " + body, re.IGNORECASE)
            if m:
                work_order_hint = m.group(1).upper()

        elif prov == "jira":
            action = str(payload.get("webhookEvent") or "jira:issue_updated")
            issue = payload.get("issue") or {}
            external_ticket_id = str(issue.get("key") or issue.get("id") or "")
            fields = issue.get("fields") or {}
            status_obj = fields.get("status") or {}
            status_val = str(status_obj.get("name") or "").lower()
            title = str(fields.get("summary") or "")

            m = re.search(r"\[?(WO-[A-Za-z0-9_\-]+)\]?", title, re.IGNORECASE)
            if m:
                work_order_hint = m.group(1).upper()

        elif prov == "linear":
            action = str(payload.get("action") or "update")
            data = payload.get("data") or {}
            external_ticket_id = str(data.get("identifier") or data.get("id") or "")
            state_obj = data.get("state") or {}
            status_val = str(state_obj.get("name") or state_obj.get("type") or "").lower()
            title = str(data.get("title") or "")

            m = re.search(r"\[?(WO-[A-Za-z0-9_\-]+)\]?", title, re.IGNORECASE)
            if m:
                work_order_hint = m.group(1).upper()

        else:
            # Generic / direct test payload
            prov = payload.get("provider") or prov or "generic"
            action = str(payload.get("action") or "update")
            external_ticket_id = str(payload.get("external_ticket_id") or payload.get("ticket_id") or "")
            status_val = str(payload.get("new_status") or payload.get("status") or ("closed" if action == "closed" else "open")).lower()
            title = str(payload.get("title") or "")
            work_order_hint = str(payload.get("work_order_id") or payload.get("display_id") or "")

        return {
            "provider": prov,
            "external_ticket_id": external_ticket_id,
            "action": action,
            "status": status_val,
            "title": title,
            "work_order_hint": work_order_hint
        }

    def process_ticket_event(
        self,
        org_id: str,
        provider: str,
        payload: Dict[str, Any],
        headers: Optional[Dict[str, str]] = None,
        target_url: Optional[str] = None,
        html_content: Optional[str] = None,
        live_fetch: bool = True
    ) -> Dict[str, Any]:
        """
        Processes an incoming ticket event:
        1. Identifies linked work order under org_id.
        2. Enforces idempotency to prevent redundant verification.
        3. If ticket is closed, executes verify_spec.
        4. Updates work order status to "Verified" or "Verification failed".
        """
        event = self.parse_event(provider, payload, headers)
        prov = event["provider"]
        ext_id = event["external_ticket_id"]
        new_status = event["status"]
        hint = event["work_order_hint"] or payload.get("work_order_id") or payload.get("display_id")

        if not ext_id and not hint:
            return {"status": "ignored", "reason": "missing_ticket_or_work_order_identifier"}

        # 1. Identify linked work order in PostgreSQL
        with get_connection(self.db_url) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT wo.id, wo.org_id, wo.run_id, wo.site_id, wo.display_id,
                           wo.title, wo.status, wo.verify_spec, wo.evidence_json,
                           wo.ticket_ref, s.url as site_url
                    FROM work_orders wo
                    JOIN sites s ON s.id = wo.site_id
                    WHERE wo.org_id = %s AND (
                        wo.id = %s OR wo.display_id = %s OR wo.ticket_ref = %s
                        OR wo.ticket_ref = %s OR wo.ticket_ref LIKE %s
                    )
                    LIMIT 1
                    """,
                    (
                        org_id,
                        hint or "NONE",
                        hint or "NONE",
                        ext_id or "NONE",
                        f"{prov.upper()}-{ext_id}",
                        f"%{ext_id}%"
                    )
                )
                wo = cur.fetchone()

        if not wo:
            logger.warning(f"No linked work order found for {prov} ticket {ext_id} in org {org_id}")
            return {
                "status": "ignored",
                "reason": "no_linked_work_order",
                "provider": prov,
                "external_ticket_id": ext_id
            }

        wo_id = wo["id"]
        display_id = wo["display_id"]
        prev_status = wo["status"]

        # 2. Check Idempotency: Prevent duplicate execution of same state transition
        with get_connection(self.db_url) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, verification_id, verification_result
                    FROM ticket_sync_events
                    WHERE org_id = %s AND provider = %s AND external_ticket_id = %s AND new_status = %s
                    LIMIT 1
                    """,
                    (org_id, prov, ext_id, new_status)
                )
                existing_event = cur.fetchone()

        if existing_event:
            logger.info(f"Duplicate ticket sync event received for {prov}:{ext_id} ({new_status}). Skipping execution.")
            return {
                "status": "skipped",
                "reason": "idempotent_duplicate",
                "event_id": existing_event["id"],
                "verification_result": existing_event["verification_result"],
                "work_order_id": wo_id,
                "work_order_status": prev_status
            }

        is_closed_transition = new_status in CLOSED_STATUSES

        # 3. If NOT closed, record state and update work order
        if not is_closed_transition:
            event_id = f"evt_{uuid4().hex[:16]}"
            with get_connection(self.db_url) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO ticket_sync_events (
                            id, org_id, work_order_id, provider, external_ticket_id,
                            event_type, previous_status, new_status, verification_result, payload_json
                        ) VALUES (%s, %s, %s, %s, %s, 'state_change', %s, %s, 'Skipped', %s)
                        """,
                        (event_id, org_id, wo_id, prov, ext_id, prev_status, new_status, Jsonb(payload))
                    )
                conn.commit()

            return {
                "status": "processed",
                "action": "status_updated",
                "work_order_id": wo_id,
                "display_id": display_id,
                "previous_status": prev_status,
                "new_status": new_status,
                "verified": False
            }

        # 4. Ticket is CLOSED -> Run automated verification specification
        evidence = wo.get("evidence_json")
        evidence_dict = evidence if isinstance(evidence, dict) else (json.loads(evidence) if evidence else {})
        sample_urls = evidence_dict.get("sample_urls", [])

        eval_url = target_url or (sample_urls[0] if sample_urls else wo["site_url"])
        if eval_url.startswith("/") and wo.get("site_url"):
            eval_url = wo["site_url"].rstrip("/") + eval_url

        wo_spec = wo.get("verify_spec") or "status_code == 200"

        # Resolve DB path for verification runner
        db_path = f"data/{wo['run_id']}.db" if os.path.exists(f"data/{wo['run_id']}.db") else "data/seo.db"
        runner = VerificationRunner(db_path=db_path)

        verif_run = runner.verify_work_order(
            work_order={
                "work_order_id": wo_id,
                "display_id": display_id,
                "run_id": wo["run_id"],
                "verify_spec": wo_spec,
                "evidence_json": json.dumps(evidence_dict)
            },
            target_url=eval_url,
            html_content=html_content,
            live_fetch=live_fetch
        )

        verif_status = verif_run.get("status", "FAILED").upper()
        verif_details = verif_run.get("details", "")

        # 5. Evaluate final state: PASS -> Verified, FAIL -> Verification failed
        if verif_status in ("PASSED", "PASS"):
            final_wo_status = "Verified"
            verif_result = "Verified"
            failure_reason = None
        else:
            final_wo_status = "Verification failed"
            verif_result = "Verification failed"
            failure_reason = verif_details

        now_utc = datetime.now(timezone.utc)
        verif_id = f"verif_sync_{uuid4().hex[:12]}"
        event_id = f"sync_evt_{uuid4().hex[:16]}"

        # 6. Update PostgreSQL work_orders and persist audit records
        with get_connection(self.db_url) as conn:
            with conn.cursor() as cur:
                # Update work order state
                cur.execute(
                    """
                    UPDATE work_orders
                    SET status = %s,
                        verify_last_result = %s
                    WHERE id = %s AND org_id = %s
                    """,
                    (final_wo_status, verif_status, wo_id, org_id)
                )

                # Insert verification audit record
                cur.execute(
                    """
                    INSERT INTO verifications (
                        id, org_id, run_id, work_order_id, status, spec, target_url, details, executed_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        verif_id, org_id, wo["run_id"], wo_id, verif_status,
                        wo_spec, eval_url, verif_details, now_utc
                    )
                )

                # Insert ticket sync event record for idempotency and traceability
                cur.execute(
                    """
                    INSERT INTO ticket_sync_events (
                        id, org_id, work_order_id, provider, external_ticket_id,
                        event_type, previous_status, new_status, verification_id,
                        verification_result, failure_reason, payload_json, processed_at
                    ) VALUES (%s, %s, %s, %s, %s, 'ticket_closed', %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        event_id, org_id, wo_id, prov, ext_id,
                        prev_status, new_status, verif_id,
                        verif_result, failure_reason, Jsonb(payload), now_utc
                    )
                )
            conn.commit()

        logger.info(
            f"Ticket sync for {prov}:{ext_id} executed verification on {wo_id}: "
            f"Result={verif_result}, Status={final_wo_status}"
        )

        return {
            "status": "completed",
            "provider": prov,
            "external_ticket_id": ext_id,
            "work_order_id": wo_id,
            "display_id": display_id,
            "previous_status": prev_status,
            "final_work_order_status": final_wo_status,
            "verification_id": verif_id,
            "verification_status": verif_status,
            "verification_result": verif_result,
            "spec": wo_spec,
            "failure_reason": failure_reason,
            "evaluated_url": eval_url
        }


_global_ticket_sync: Optional[TicketSyncManager] = None

def get_ticket_sync_manager() -> TicketSyncManager:
    global _global_ticket_sync
    if _global_ticket_sync is None:
        _global_ticket_sync = TicketSyncManager()
    return _global_ticket_sync
