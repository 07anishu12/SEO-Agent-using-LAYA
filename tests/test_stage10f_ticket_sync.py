"""
SEOJEV Phase 2: Stage 10f Bi-directional Ticket Sync Test Suite.

Validates Section 6.3:
1. Event Parsing for GitHub, Jira, and Linear.
2. Verification Execution on Ticket Closed:
   - Evaluates deterministic verify_spec.
   - Successful verification -> Final status "Verified".
   - Failing verification -> Final status "Verification failed".
3. Never blindly verifies: verifies that external close without passing DOM fails.
4. Idempotency: duplicate webhook calls skip redundant re-verification.
5. Multi-tenant Isolation: cross-tenant ticket sync events are strictly rejected / ignored.
"""
import os
from datetime import datetime, timezone
from typing import Dict, Any

import pytest
from fastapi.testclient import TestClient

from api.main import app
from database.connection import get_connection
from database.migrator import PostgresMigrator
from services.ticket_sync import TicketSyncManager


@pytest.fixture(scope="session", autouse=True)
def prepare_db():
    migrator = PostgresMigrator(db_url="postgresql:///seojev_test")
    migrator.run_migrations()


def create_token(org_id: str, email: str = "lead@example.com") -> str:
    from api.auth import create_access_token
    return create_access_token({"sub": f"usr_{org_id}", "email": email, "org_id": org_id, "role": "admin"})


def test_ticket_sync_pass_and_fail_lifecycle():
    """
    E2E Test:
    1. Creates work order with verify_spec: "has_selector('meta[name=\"description\"][content]') and text_length('meta[name=\"description\"][content]') >= 50"
    2. Simulates ticket opened -> state updated, not verified.
    3. Simulates ticket closed with passing HTML -> Executes verification -> Final state "Verified".
    4. Simulates second work order with failing HTML -> Final state "Verification failed".
    5. Confirms idempotency on resending closed event.
    """
    client = TestClient(app)
    suffix = os.urandom(4).hex()
    org_id = f"org_sync_{suffix}"
    site_id = f"site_sync_{suffix}"
    run_id = f"run_sync_{suffix}"
    wo_pass_id = f"wo_pass_{suffix}"
    wo_fail_id = f"wo_fail_{suffix}"

    token = create_token(org_id)
    target_url = "https://acme.test/product/alpha"

    # Setup DB
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO orgs (id, name, slug) VALUES (%s, %s, %s)", (org_id, f"Sync Org {suffix}", f"sync-{suffix}"))
            cur.execute(
                "INSERT INTO sites (id, org_id, domain, url, vertical) VALUES (%s, %s, %s, %s, 'ecommerce')",
                (site_id, org_id, "acme.test", "https://acme.test")
            )
            cur.execute(
                "INSERT INTO runs (id, org_id, site_id, status, progress_pct) VALUES (%s, %s, %s, 'completed', 100.0)",
                (run_id, org_id, site_id)
            )

            # 1. Seed Work Order A (will PASS verification)
            spec_desc = 'has_selector("meta[name=\'description\'][content]") and text_length("meta[name=\'description\'][content]") >= 50'
            cur.execute(
                """
                INSERT INTO work_orders (
                    id, org_id, run_id, site_id, display_id, title, order_type,
                    status, verify_spec, ticket_ref
                )
                VALUES (%s, %s, %s, %s, %s, %s, 'engineering', 'Open', %s, %s)
                """,
                (wo_pass_id, org_id, run_id, site_id, f"WO-P-{suffix}", "Add Meta Description", spec_desc, f"GH-101")
            )

            # 2. Seed Work Order B (will FAIL verification)
            spec_h1 = 'selector_count("h1") == 1 and text_length("h1") >= 10'
            cur.execute(
                """
                INSERT INTO work_orders (
                    id, org_id, run_id, site_id, display_id, title, order_type,
                    status, verify_spec, ticket_ref
                )
                VALUES (%s, %s, %s, %s, %s, %s, 'engineering', 'Open', %s, %s)
                """,
                (wo_fail_id, org_id, run_id, site_id, f"WO-F-{suffix}", "Add Valid H1 Heading", spec_h1, f"JIRA-202")
            )
        conn.commit()

    # STEP 1: Simulate Ticket Opened (GitHub)
    open_payload = {
        "provider": "github",
        "payload": {
            "action": "opened",
            "issue": {
                "number": 101,
                "title": f"[WO-P-{suffix}] Add Meta Description",
                "state": "open"
            }
        },
        "live_fetch": False
    }
    resp_open = client.post("/work-orders/ticket-sync", json=open_payload, headers={"Authorization": f"Bearer {token}"})
    assert resp_open.status_code == 200
    data_open = resp_open.json()
    assert data_open["status"] == "processed"
    assert data_open["verified"] is False

    # Work order status remains Open
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT status FROM work_orders WHERE id = %s", (wo_pass_id,))
            assert cur.fetchone()["status"] == "Open"

    # STEP 2: Simulate Ticket Closed with PASSING HTML
    good_html = """
    <!DOCTYPE html>
    <html>
      <head>
        <title>Alpha Product</title>
        <meta name="description" content="This is a comprehensive description that easily exceeds the required fifty characters limit for testing." />
      </head>
      <body><h1>Alpha Product</h1></body>
    </html>
    """

    close_pass_payload = {
        "provider": "github",
        "payload": {
            "action": "closed",
            "issue": {
                "number": 101,
                "title": f"[WO-P-{suffix}] Add Meta Description",
                "state": "closed"
            }
        },
        "target_url": target_url,
        "html_content": good_html,
        "live_fetch": False
    }

    resp_close_pass = client.post("/work-orders/ticket-sync", json=close_pass_payload, headers={"Authorization": f"Bearer {token}"})
    assert resp_close_pass.status_code == 200
    data_pass = resp_close_pass.json()

    assert data_pass["status"] == "completed"
    assert data_pass["verification_status"] == "PASSED"
    assert data_pass["final_work_order_status"] == "Verified"
    assert data_pass["failure_reason"] is None

    # Verify DB state is "Verified"
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT status, verify_last_result FROM work_orders WHERE id = %s", (wo_pass_id,))
            wo_row = cur.fetchone()
            assert wo_row["status"] == "Verified"
            assert wo_row["verify_last_result"] == "PASSED"

    # STEP 3: Test Idempotency on Resending Closed Event
    resp_duplicate = client.post("/work-orders/ticket-sync", json=close_pass_payload, headers={"Authorization": f"Bearer {token}"})
    assert resp_duplicate.status_code == 200
    data_dup = resp_duplicate.json()
    assert data_dup["status"] == "skipped"
    assert data_dup["reason"] == "idempotent_duplicate"

    # STEP 4: Simulate Ticket Closed with FAILING HTML (Jira)
    bad_html = """
    <!DOCTYPE html>
    <html>
      <head><title>Bad H1 Page</title></head>
      <body><!-- missing H1 entirely --></body>
    </html>
    """

    close_fail_payload = {
        "provider": "jira",
        "payload": {
            "webhookEvent": "jira:issue_updated",
            "issue": {
                "key": "JIRA-202",
                "fields": {
                    "summary": f"[WO-F-{suffix}] Add Valid H1 Heading",
                    "status": {"name": "Done"}
                }
            }
        },
        "target_url": target_url,
        "html_content": bad_html,
        "live_fetch": False
    }

    resp_close_fail = client.post("/work-orders/ticket-sync", json=close_fail_payload, headers={"Authorization": f"Bearer {token}"})
    assert resp_close_fail.status_code == 200
    data_fail = resp_close_fail.json()

    assert data_fail["status"] == "completed"
    assert data_fail["verification_status"] == "FAILED"
    assert data_fail["final_work_order_status"] == "Verification failed"
    assert data_fail["failure_reason"] is not None

    # Verify DB state is "Verification failed"
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT status, verify_last_result FROM work_orders WHERE id = %s", (wo_fail_id,))
            wo_fail_row = cur.fetchone()
            assert wo_fail_row["status"] == "Verification failed"
            assert wo_fail_row["verify_last_result"] == "FAILED"

    # STEP 5: Verify Audit History Endpoint
    resp_hist = client.get(f"/work-orders/{wo_pass_id}/sync-history", headers={"Authorization": f"Bearer {token}"})
    assert resp_hist.status_code == 200
    history = resp_hist.json()["history"]
    assert len(history) >= 2  # opened + closed events
    assert history[0]["new_status"] in ("closed", "Done")


def test_ticket_sync_linear_and_tenant_isolation():
    """
    Validates Linear payload parsing and confirms Org B cannot trigger verification on Org A's ticket.
    """
    client = TestClient(app)
    suffix = os.urandom(4).hex()
    org_a = f"org_t_a_{suffix}"
    org_b = f"org_t_b_{suffix}"
    site_a = f"site_t_a_{suffix}"
    run_a = f"run_t_a_{suffix}"
    wo_a = f"wo_t_a_{suffix}"

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO orgs (id, name, slug) VALUES (%s, %s, %s)", (org_a, "Org A", f"t-a-{suffix}"))
            cur.execute("INSERT INTO orgs (id, name, slug) VALUES (%s, %s, %s)", (org_b, "Org B", f"t-b-{suffix}"))
            cur.execute("INSERT INTO sites (id, org_id, domain, url) VALUES (%s, %s, %s, %s)", (site_a, org_a, "a.test", "https://a.test"))
            cur.execute("INSERT INTO runs (id, org_id, site_id, status) VALUES (%s, %s, %s, 'completed')", (run_a, org_a, site_a))
            cur.execute(
                """
                INSERT INTO work_orders (id, org_id, run_id, site_id, display_id, title, order_type, status, verify_spec, ticket_ref)
                VALUES (%s, %s, %s, %s, %s, %s, 'engineering', 'Open', 'True', %s)
                """,
                (wo_a, org_a, run_a, site_a, f"WO-LIN-{suffix}", "Linear Test", "LIN-77")
            )
        conn.commit()

    token_b = create_token(org_b)

    # Org B sends webhook matching Org A's ticket
    linear_payload = {
        "provider": "linear",
        "payload": {
            "action": "update",
            "type": "Issue",
            "data": {
                "identifier": "LIN-77",
                "title": f"[WO-LIN-{suffix}] Linear Test",
                "state": {"name": "Done", "type": "completed"}
            }
        },
        "live_fetch": False
    }

    resp_isolated = client.post(
        "/work-orders/ticket-sync",
        json=linear_payload,
        headers={"Authorization": f"Bearer {token_b}"}
    )
    assert resp_isolated.status_code == 200
    res = resp_isolated.json()
    assert res["status"] == "ignored"
    assert res["reason"] == "no_linked_work_order"

    # Confirm Org A's work order is untouched
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT status FROM work_orders WHERE id = %s", (wo_a,))
            assert cur.fetchone()["status"] == "Open"
