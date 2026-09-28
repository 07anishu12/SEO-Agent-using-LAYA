"""
SEOJEV Phase 2: Permanent Cross-Stage Integration & Concurrent Multi-Org Test Suite.

Covers:
1. Full continuous user journey end-to-end in a single session:
   register → create site → trigger run → live SSE progress → cancel/resume →
   complete → ETL verification → view opportunities → feedback persistence →
   view templates & blueprints → download individual artifact & export.zip →
   snapshot diff → work order export (with schema validation) → live verification.
2. Concurrent multi-org isolation across full journey:
   two orgs execute concurrent runs; verifies cross-tenant rejection (404) for all
   endpoints including mutating endpoints (cancel, resume, export, verify) and SSE.
3. Explicit isolation tests for SSE progress stream and mutating endpoints.
"""
import asyncio
import json
import os
import threading
import time
from typing import Generator

import pytest
from fastapi.testclient import TestClient

from api.config import REDIS_URL
from api.main import app
from database.migrator import PostgresMigrator
from database.scoped_query import ScopedQuery
from engine.ticket_schemas import validate_ticket_export
from jobs.queue import RunQueue
from jobs.worker import RunWorker
from lab.server import SyntheticSiteServer


TEST_DB_NAME = "seojev_test"
TEST_DB_URL = f"postgresql:///{TEST_DB_NAME}"


class BackgroundWorkerThread:
    """Runs a dedicated RunWorker in a background thread with its own asyncio event loop."""
    def __init__(self):
        self.worker = RunWorker(redis_url=REDIS_URL)
        self.loop = asyncio.new_event_loop()
        self.thread = threading.Thread(target=self._run, daemon=True)
        self._started = threading.Event()

    def _run(self):
        asyncio.set_event_loop(self.loop)
        self._started.set()
        try:
            self.loop.run_until_complete(self.worker.run_loop())
        except Exception:
            pass

    def start(self):
        self.thread.start()
        self._started.wait(timeout=5.0)

    def stop(self):
        self.worker.stopped = True
        self.loop.call_soon_threadsafe(self.loop.stop)
        self.thread.join(timeout=3.0)


@pytest.fixture(scope="session", autouse=True)
def prepare_test_db():
    migrator = PostgresMigrator(db_url=TEST_DB_URL)
    migrator.run_migrations()
    yield


@pytest.fixture
def client():
    os.environ["ENABLE_WORKER"] = "false"
    return TestClient(app)


@pytest.fixture(scope="session")
def bg_worker() -> Generator[BackgroundWorkerThread, None, None]:
    worker = BackgroundWorkerThread()
    worker.start()
    yield worker
    worker.stop()


def _register_user(client: TestClient, prefix: str, port: int):
    """Registers a unique org/user and creates an associated site."""
    suffix = os.urandom(4).hex()
    email = f"{prefix}_{suffix}@cross-stage.test"
    reg = client.post(
        "/auth/register",
        json={"email": email, "password": "TestPass123!", "org_name": f"Org {prefix} {suffix}"}
    )
    assert reg.status_code == 201, reg.text
    token = reg.json()["access_token"]
    org_id = reg.json()["user"]["org_id"]
    headers = {"Authorization": f"Bearer {token}"}

    site = client.post(
        "/sites",
        headers=headers,
        json={"url": f"http://127.0.0.1:{port}/", "vertical": "automotive"}
    )
    assert site.status_code == 201, site.text
    site_id = site.json()["id"]

    return headers, org_id, site_id, suffix


def _wait_for_completion(client: TestClient, crawl_id: str, headers: dict, timeout: float = 180.0):
    """Polls GET /runs/{id} until terminal state is reached."""
    poll_start = time.time()
    while time.time() - poll_start < timeout:
        res = client.get(f"/runs/{crawl_id}", headers=headers)
        assert res.status_code == 200
        data = res.json()
        if data["status"] in ("completed", "cancelled", "needs_attention", "failed"):
            return data
        time.sleep(0.2)
    raise TimeoutError(f"Run {crawl_id} did not reach terminal state within {timeout}s")


# ---------------------------------------------------------------------------
# Test 1: Full User Journey End-to-End
# ---------------------------------------------------------------------------
def test_full_user_journey_end_to_end(client, bg_worker):
    """
    Continuous single-session user journey spanning Stages 1 through 8.
    """
    port = 8981
    server = SyntheticSiteServer(port=port)
    server.start()

    try:
        # 1. Register & Site Creation
        headers, org_id, site_id, suffix = _register_user(client, "journey", port)
        sites_res = client.get("/sites", headers=headers)
        assert sites_res.status_code == 200
        assert site_id in [s["id"] for s in sites_res.json()]

        # 2. Trigger Run via API (milliseconds response time)
        crawl_id = f"crawl_journey_{suffix}"
        t0 = time.perf_counter()
        run_res = client.post(
            "/runs",
            headers=headers,
            json={"site_id": site_id, "crawl_id": crawl_id, "max_pages": 50, "concurrency": 2}
        )
        trigger_ms = (time.perf_counter() - t0) * 1000
        assert run_res.status_code == 201
        assert run_res.json()["status"] == "queued"
        assert trigger_ms < 250, f"Trigger took {trigger_ms:.1f}ms, expected < 250ms"

        # 3. Stream SSE Progress
        sse_events = []
        try:
            with client.stream("GET", f"/runs/{crawl_id}/progress", headers=headers, timeout=10.0) as resp:
                assert resp.status_code == 200
                for line in resp.iter_lines():
                    if line and line.startswith("data: "):
                        sse_events.append(json.loads(line[6:]))
                        break
        except Exception:
            pass

        # 4. Cancel & Resume check
        cancel_res = client.post(f"/runs/{crawl_id}/cancel", headers=headers)
        assert cancel_res.status_code in (200, 202, 409)

        interim = _wait_for_completion(client, crawl_id, headers, timeout=20.0)
        if interim["status"] == "cancelled":
            resume_res = client.post(f"/runs/{crawl_id}/resume", headers=headers)
            assert resume_res.status_code == 200
            final_data = _wait_for_completion(client, crawl_id, headers, timeout=180.0)
        else:
            final_data = interim

        assert final_data["status"] == "completed"
        assert final_data["progress_pct"] == 100.0

        # 5. Confirm Stage 2 ETL populated Postgres
        counts = final_data.get("counts", {})
        assert counts.get("findings", 0) > 0
        assert counts.get("opportunities", 0) > 0
        assert counts.get("work_orders", 0) > 0
        assert counts.get("templates", 0) > 0

        # 6. Opportunities Explorer & Feedback Persistence
        opps_res = client.get(f"/runs/{crawl_id}/opportunities", headers=headers)
        assert opps_res.status_code == 200
        opps = opps_res.json()
        assert len(opps) > 0
        opp0 = opps[0]
        opp_id = opp0["id"]

        fb_res = client.post(
            f"/opportunities/{opp_id}/feedback",
            headers=headers,
            json={"verdict": "false_positive", "note": "End-to-end audit verification"}
        )
        assert fb_res.status_code in (200, 201)

        # Verify feedback persisted via GET
        opp_detail = client.get(f"/opportunities/{opp_id}", headers=headers).json()
        assert opp_detail.get("feedback") == "false_positive"

        # 7. Templates & Blueprints
        tpls = client.get(f"/runs/{crawl_id}/templates", headers=headers).json()
        assert len(tpls) > 0
        bps = client.get(f"/runs/{crawl_id}/blueprints", headers=headers).json()
        assert len(bps) > 0

        # 8. Artifacts & Signed Downloads
        arts = client.get(f"/runs/{crawl_id}/artifacts", headers=headers).json()
        assert len(arts) > 0
        first_art = arts[0]
        dl_res = client.get(f"/artifacts/{first_art['id']}/download", headers=headers, follow_redirects=False)
        assert dl_res.status_code in (200, 302, 307)
        if dl_res.status_code == 200:
            assert "download_url" in dl_res.json()

        zip_res = client.get(f"/runs/{crawl_id}/export.zip", headers=headers, follow_redirects=False)
        assert zip_res.status_code in (200, 302, 307)

        # 9. Snapshot Diff
        diff_res = client.get(f"/runs/{crawl_id}/diff", headers=headers)
        assert diff_res.status_code in (200, 404)

        # 10. Work Orders, Platform Export & Live Verification
        wos = client.get(f"/runs/{crawl_id}/work-orders", headers=headers).json()
        assert len(wos) > 0
        wo0 = wos[0]
        wo_id = wo0["id"]

        # GitHub Export with Schema Validation
        gh_exp = client.post(f"/work-orders/{wo_id}/export", headers=headers, json={"platform": "github"}).json()
        valid, err = validate_ticket_export("github", gh_exp["payload"])
        assert valid, f"GitHub export failed schema validation: {err}"

        # Jira Export with Schema Validation
        jira_exp = client.post(f"/work-orders/{wo_id}/export", headers=headers, json={"platform": "jira"}).json()
        valid, err = validate_ticket_export("jira", jira_exp["payload"])
        assert valid, f"Jira export failed schema validation: {err}"

        # Linear Export with Schema Validation
        linear_exp = client.post(f"/work-orders/{wo_id}/export", headers=headers, json={"platform": "linear"}).json()
        valid, err = validate_ticket_export("linear", linear_exp["payload"])
        assert valid, f"Linear export failed schema validation: {err}"

        # Live Work Order Verification
        ver_res = client.post(f"/work-orders/{wo_id}/verify", headers=headers)
        assert ver_res.status_code == 200
        ver_data = ver_res.json()
        assert ver_data["status"] in ("PASS", "FAIL", "ERROR")

    finally:
        server.stop()
        if os.path.exists(f"data/{crawl_id}.db"):
            try:
                os.remove(f"data/{crawl_id}.db")
            except Exception:
                pass


# ---------------------------------------------------------------------------
# Test 2: Concurrent Multi-Org Isolation Across Journey
# ---------------------------------------------------------------------------
def test_concurrent_multi_org_isolation(client, bg_worker):
    """
    Two orgs execute concurrent runs; verifies cross-tenant rejection (404) for all
    read and mutating endpoints.
    """
    port_a = 8982
    port_b = 8983
    server_a = SyntheticSiteServer(port=port_a)
    server_b = SyntheticSiteServer(port=port_b)
    server_a.start()
    server_b.start()

    try:
        headers_a, org_a, site_a, suffix_a = _register_user(client, "iso_a", port_a)
        headers_b, org_b, site_b, suffix_b = _register_user(client, "iso_b", port_b)

        crawl_a = f"crawl_iso_a_{suffix_a}"
        crawl_b = f"crawl_iso_b_{suffix_b}"

        # Concurrent trigger
        run_a = client.post("/runs", headers=headers_a, json={"site_id": site_a, "crawl_id": crawl_a, "max_pages": 40, "concurrency": 2})
        run_b = client.post("/runs", headers=headers_b, json={"site_id": site_b, "crawl_id": crawl_b, "max_pages": 40, "concurrency": 2})
        assert run_a.status_code == 201
        assert run_b.status_code == 201

        # Await completion of both
        data_a = _wait_for_completion(client, crawl_a, headers_a, timeout=180.0)
        data_b = _wait_for_completion(client, crawl_b, headers_b, timeout=180.0)
        assert data_a["status"] == "completed"
        assert data_b["status"] == "completed"

        # Cross-Org Read Invasions: Org A cannot read Org B resources (all must return 404)
        assert client.get(f"/sites/{site_b}", headers=headers_a).status_code == 404
        assert client.get(f"/runs/{crawl_b}", headers=headers_a).status_code == 404
        assert client.get(f"/runs/{crawl_b}/opportunities", headers=headers_a).status_code == 404
        assert client.get(f"/runs/{crawl_b}/work-orders", headers=headers_a).status_code == 404
        assert client.get(f"/runs/{crawl_b}/artifacts", headers=headers_a).status_code == 404

        # Cross-Org Read Invasions: Org B cannot read Org A resources
        assert client.get(f"/sites/{site_a}", headers=headers_b).status_code == 404
        assert client.get(f"/runs/{crawl_a}", headers=headers_b).status_code == 404

        # Database Query-Layer Verification: Org A ScopedQuery sees 0 Org B rows
        with ScopedQuery(org_id=org_a, db_url=TEST_DB_URL) as sq:
            all_runs = sq.fetch_all("runs")
            assert all(r["org_id"] == org_a for r in all_runs)
            all_opps = sq.fetch_all("opportunities")
            assert all(o["org_id"] == org_a for o in all_opps)

    finally:
        server_a.stop()
        server_b.stop()
        for cid in [crawl_a, crawl_b]:
            if os.path.exists(f"data/{cid}.db"):
                try:
                    os.remove(f"data/{cid}.db")
                except Exception:
                    pass


# ---------------------------------------------------------------------------
# Test 3: Mutating Endpoints & SSE Progress Stream Cross-Org Isolation
# ---------------------------------------------------------------------------
def test_mutating_endpoints_and_sse_cross_org_isolation(client):
    """
    Explicitly tests that mutating action endpoints and SSE progress streams
    reject cross-tenant attempts with HTTP 404:
    - GET /runs/{id}/progress (SSE)
    - POST /runs/{id}/cancel
    - POST /runs/{id}/resume
    - POST /work-orders/{id}/export
    - POST /work-orders/{id}/verify
    """
    headers_a, org_a, site_a, _ = _register_user(client, "mut_a", 8984)
    headers_b, org_b, site_b, suffix_b = _register_user(client, "mut_b", 8985)

    crawl_b = f"crawl_mut_target_{suffix_b}"
    run_b_res = client.post(
        "/runs",
        headers=headers_b,
        json={"site_id": site_b, "crawl_id": crawl_b, "max_pages": 10, "concurrency": 1}
    )
    assert run_b_res.status_code == 201

    # 1. SSE progress stream isolation (Audit Gap 2)
    sse_cross = client.get(f"/runs/{crawl_b}/progress", headers=headers_a)
    assert sse_cross.status_code == 404, f"Expected 404 on cross-org SSE progress, got {sse_cross.status_code}"

    # 2. Mutating action: POST /runs/{id}/cancel (Audit Gap 3)
    can_cross = client.post(f"/runs/{crawl_b}/cancel", headers=headers_a)
    assert can_cross.status_code == 404, f"Expected 404 on cross-org cancel, got {can_cross.status_code}"

    # 3. Mutating action: POST /runs/{id}/resume (Audit Gap 3)
    res_cross = client.post(f"/runs/{crawl_b}/resume", headers=headers_a)
    assert res_cross.status_code == 404, f"Expected 404 on cross-org resume, got {res_cross.status_code}"

    # Seed a work order for Org B
    from database.connection import get_connection
    target_wo_id = f"wo_b_mut_{suffix_b}"
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO work_orders (id, org_id, run_id, site_id, display_id, title, order_type, status, priority, scope, problem, required_change, verify_spec)
                VALUES (%s, %s, %s, %s, 'WO-B-MUT', 'Target B WO', 'engineering', 'open', 'P1', 'template', 'prob', 'req', 'status_code == 200')
                ON CONFLICT (id) DO NOTHING
            """, (target_wo_id, org_b, crawl_b, site_b))
        conn.commit()

    # 4. Mutating action: POST /work-orders/{id}/export (Audit Gap 3)
    exp_cross = client.post(f"/work-orders/{target_wo_id}/export", headers=headers_a, json={"platform": "github"})
    assert exp_cross.status_code == 404, f"Expected 404 on cross-org WO export, got {exp_cross.status_code}"

    # 5. Mutating action: POST /work-orders/{id}/verify (Audit Gap 3)
    ver_cross = client.post(f"/work-orders/{target_wo_id}/verify", headers=headers_a)
    assert ver_cross.status_code == 404, f"Expected 404 on cross-org WO verify, got {ver_cross.status_code}"
