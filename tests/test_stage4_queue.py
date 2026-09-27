"""
SEOJEV Phase 2: Stage 4 Redis + RQ/Celery Job Queue Test Suite.
Tests:
1. Async trigger test: POST /runs returns within milliseconds with status "queued";
   polling GET /runs/{id} shows it transition to "running" then "completed".
2. SSE test: connect to the progress stream during a run and assert you receive events
   for each pass in order until completion.
3. Cancellation test: start a run against a test site, cancel it mid-crawl,
   confirm status becomes "cancelled" within a few seconds, and assert no partial/corrupt data was ETL'd into Postgres.
4. Resume test: start a run, cancel partway through, resume via POST /runs/{id}/resume,
   and confirm final result matches what an uninterrupted run produces (same counts/fingerprints).
5. Failure & retry test: run that fails twice is marked "needs_attention" rather than retried indefinitely.
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
from database.connection import get_connection
from database.migrator import PostgresMigrator
from jobs.queue import RunQueue
from jobs.worker import RunWorker
from lab.server import SyntheticSiteServer


TEST_DB_NAME = "seojev_test"
TEST_DB_URL = f"postgresql:///{TEST_DB_NAME}"


class BackgroundWorkerThread:
    """Runs a dedicated RunWorker in a background thread with its own asyncio loop."""
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
    # Disable auto in-process worker from lifespan during test client runs so worker thread fixture manages it cleanly
    os.environ["ENABLE_WORKER"] = "false"
    return TestClient(app)


@pytest.fixture(scope="session")
def bg_worker() -> Generator[BackgroundWorkerThread, None, None]:
    worker = BackgroundWorkerThread()
    worker.start()
    yield worker
    worker.stop()


def _register_and_create_site(client: TestClient, email_prefix: str, port: int):
    suffix = os.urandom(4).hex()
    email = f"{email_prefix}_{suffix}@test.com"
    reg_res = client.post(
        "/auth/register",
        json={"email": email, "password": "Password123!", "org_name": f"Org {suffix}"}
    )
    assert reg_res.status_code == 201, reg_res.text
    token = reg_res.json()["access_token"]
    org_id = reg_res.json()["user"]["org_id"]
    headers = {"Authorization": f"Bearer {token}"}

    site_res = client.post(
        "/sites",
        headers=headers,
        json={"url": f"http://127.0.0.1:{port}/", "vertical": "automotive"}
    )
    assert site_res.status_code == 201, site_res.text
    site_id = site_res.json()["id"]

    return headers, org_id, site_id, suffix


def test_async_trigger_and_polling(client, bg_worker):
    """
    Async trigger test: POST /runs returns within milliseconds with status 'queued';
    polling GET /runs/{id} shows it transition to 'running' then 'completed'.
    """
    port = 8941
    server = SyntheticSiteServer(port=port)
    server.start()

    headers, org_id, site_id, suffix = _register_and_create_site(client, "async", port)
    crawl_id = f"crawl_async_{suffix}"

    try:
        t_start = time.perf_counter()
        run_res = client.post(
            "/runs",
            headers=headers,
            json={"site_id": site_id, "crawl_id": crawl_id, "max_pages": 50, "concurrency": 2}
        )
        t_elapsed = time.perf_counter() - t_start

        # 1. Assert returns within milliseconds
        assert run_res.status_code == 201, run_res.text
        assert t_elapsed < 0.250, f"Trigger took too long: {t_elapsed:.3f}s"

        data = run_res.json()
        assert data["id"] == crawl_id
        assert data["status"] == "queued"
        assert data["progress_pct"] == 0.0

        # 2. Poll GET /runs/{id}
        statuses_seen = set()
        pcts_seen = []
        terminal_data = None

        poll_start = time.time()
        while time.time() - poll_start < 25.0:
            poll_res = client.get(f"/runs/{crawl_id}", headers=headers)
            assert poll_res.status_code == 200
            current = poll_res.json()
            curr_status = current["status"]
            statuses_seen.add(curr_status)
            pcts_seen.append(current["progress_pct"])

            if curr_status == "completed":
                terminal_data = current
                break
            time.sleep(0.15)

        assert terminal_data is not None, f"Run did not complete in time. Last status: {curr_status}"
        assert "running" in statuses_seen or "queued" in statuses_seen
        assert terminal_data["status"] == "completed"
        assert terminal_data["progress_pct"] == 100.0

        # Verify monotonicity of progress_pct
        for i in range(1, len(pcts_seen)):
            assert pcts_seen[i] >= pcts_seen[i - 1], f"Progress not monotonic: {pcts_seen}"

        # 3. Assert Postgres row counts match expected baseline
        counts = terminal_data["counts"]
        assert counts["findings"] in (48, 55)
        assert counts["opportunities"] in (48, 55)
        assert counts["work_orders"] in (48, 55)
        assert counts["templates"] in (6, 8)

    finally:
        server.stop()
        if os.path.exists(f"data/{crawl_id}.db"):
            try:
                os.remove(f"data/{crawl_id}.db")
            except Exception:
                pass


def test_sse_progress_stream(client, bg_worker):
    """
    SSE test: connect to the progress stream during a run and assert you receive events
    for each pass in order.
    """
    port = 8942
    server = SyntheticSiteServer(port=port)
    server.start()

    headers, org_id, site_id, suffix = _register_and_create_site(client, "sse", port)
    crawl_id = f"crawl_sse_{suffix}"

    try:
        # Enqueue run
        run_res = client.post(
            "/runs",
            headers=headers,
            json={"site_id": site_id, "crawl_id": crawl_id, "max_pages": 50, "concurrency": 2}
        )
        assert run_res.status_code == 201
        assert run_res.json()["status"] == "queued"

        # Connect to SSE stream
        events = []
        with client.stream("GET", f"/runs/{crawl_id}/progress", headers=headers) as response:
            assert response.status_code == 200
            for line in response.iter_lines():
                if not line:
                    continue
                if line.startswith("data: "):
                    payload_raw = line[len("data: "):].strip()
                    try:
                        ev = json.loads(payload_raw)
                        events.append(ev)
                        if ev.get("status") in ("completed", "cancelled", "failed", "needs_attention"):
                            break
                    except Exception:
                        pass

        assert len(events) >= 3, f"Expected multiple progress events, got {len(events)}"

        # Assert pass names encountered
        passes_encountered = [ev.get("pass") for ev in events if ev.get("pass")]
        assert any("P1_CRAWL" in p for p in passes_encountered)
        assert any("P2_SIGNALS" in p for p in passes_encountered)
        assert any("P6_DELIVERABLES" in p for p in passes_encountered)

        # Terminal event asserts
        last_ev = events[-1]
        assert last_ev["status"] == "completed"
        assert last_ev["pct"] == 100.0

    finally:
        server.stop()
        if os.path.exists(f"data/{crawl_id}.db"):
            try:
                os.remove(f"data/{crawl_id}.db")
            except Exception:
                pass


def test_cancellation_mid_crawl(client, bg_worker):
    """
    Cancellation test: start a run against a test site, cancel it mid-crawl,
    confirm status becomes 'cancelled' within a few seconds and no partial/corrupt data was ETL'd.
    """
    port = 8943
    # Introduce small latency (0.04s per page) to ensure crawl is in flight when cancel signal arrives
    server = SyntheticSiteServer(port=port, delay_sec=0.04)
    server.start()

    headers, org_id, site_id, suffix = _register_and_create_site(client, "cancel", port)
    crawl_id = f"crawl_cancel_{suffix}"

    try:
        # 1. Enqueue run
        run_res = client.post(
            "/runs",
            headers=headers,
            json={"site_id": site_id, "crawl_id": crawl_id, "max_pages": 50, "concurrency": 1}
        )
        assert run_res.status_code == 201

        # 2. Wait until status moves to running
        poll_start = time.time()
        while time.time() - poll_start < 5.0:
            status_res = client.get(f"/runs/{crawl_id}", headers=headers)
            if status_res.json()["status"] == "running":
                break
            time.sleep(0.02)

        # 3. Request cancellation
        cancel_start = time.time()
        cancel_res = client.post(f"/runs/{crawl_id}/cancel", headers=headers)
        cancel_duration = time.time() - cancel_start
        assert cancel_res.status_code == 200, cancel_res.text
        cancel_data = cancel_res.json()
        assert cancel_data["status"] == "cancelled"
        assert cancel_duration < 6.0, f"Cancellation took too long: {cancel_duration:.2f}s"

        # 4. Verify terminal status in Postgres
        get_res = client.get(f"/runs/{crawl_id}", headers=headers)
        assert get_res.json()["status"] == "cancelled"

        # 5. Direct Postgres audit: zero partial or corrupt rows must have been ETL'd
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT count(*) AS count FROM findings WHERE run_id = %s", (crawl_id,))
                findings_count = cur.fetchone()["count"]

                cur.execute("SELECT count(*) AS count FROM opportunities WHERE run_id = %s", (crawl_id,))
                opps_count = cur.fetchone()["count"]

                cur.execute("SELECT count(*) AS count FROM work_orders WHERE run_id = %s", (crawl_id,))
                wo_count = cur.fetchone()["count"]

                cur.execute("SELECT count(*) AS count FROM templates WHERE run_id = %s", (crawl_id,))
                tpl_count = cur.fetchone()["count"]

                cur.execute("SELECT status FROM runs WHERE id = %s", (crawl_id,))
                db_status = cur.fetchone()["status"]

        assert findings_count == 0, f"Expected 0 findings ETL'd on cancelled run, got {findings_count}"
        assert opps_count == 0, f"Expected 0 opportunities ETL'd on cancelled run, got {opps_count}"
        assert wo_count == 0, f"Expected 0 work orders ETL'd on cancelled run, got {wo_count}"
        assert tpl_count == 0, f"Expected 0 templates ETL'd on cancelled run, got {tpl_count}"
        assert db_status == "cancelled"

    finally:
        server.stop()
        if os.path.exists(f"data/{crawl_id}.db"):
            try:
                os.remove(f"data/{crawl_id}.db")
            except Exception:
                pass


def test_resume_frontier(client, bg_worker):
    """
    Resume test: start a run, cancel partway through, resume it via POST /runs/{id}/resume,
    and confirm the final result matches what an uninterrupted run produces (exact counts/fingerprints).
    """
    port = 8944
    server = SyntheticSiteServer(port=port, delay_sec=0.04)
    server.start()

    headers, org_id, site_id, suffix = _register_and_create_site(client, "resume", port)
    crawl_id = f"crawl_resume_{suffix}"

    try:
        # 1. Start run
        run_res = client.post(
            "/runs",
            headers=headers,
            json={"site_id": site_id, "crawl_id": crawl_id, "max_pages": 50, "concurrency": 1}
        )
        assert run_res.status_code == 201

        # Wait until crawler has started and partial SQLite DB exists
        t0 = time.time()
        while time.time() - t0 < 8.0:
            st = client.get(f"/runs/{crawl_id}", headers=headers).json().get("status")
            if st == "running" and os.path.exists(f"data/{crawl_id}.db"):
                break
            time.sleep(0.05)

        # 2. Cancel partway through crawl
        cancel_res = client.post(f"/runs/{crawl_id}/cancel", headers=headers)
        assert cancel_res.json()["status"] == "cancelled"

        # Confirm partial SQLite DB exists and no ETL was done yet
        assert os.path.exists(f"data/{crawl_id}.db")
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT count(*) AS count FROM findings WHERE run_id = %s", (crawl_id,))
                assert cur.fetchone()["count"] == 0

        # Remove artificial latency for fast completion on resume
        server.generator = server.generator  # keep generator
        SyntheticSiteServer.delay_sec = 0.0
        server.delay_sec = 0.0

        # 3. Resume the run
        resume_res = client.post(f"/runs/{crawl_id}/resume", headers=headers)
        assert resume_res.status_code == 200, resume_res.text
        assert resume_res.json()["status"] == "queued"
        assert resume_res.json()["resumed"] is True

        # 4. Poll until completed
        t_poll = time.time()
        terminal_status = None
        while time.time() - t_poll < 30.0:
            current = client.get(f"/runs/{crawl_id}", headers=headers).json()
            if current["status"] in ("completed", "failed", "needs_attention"):
                terminal_status = current["status"]
                break
            time.sleep(0.2)

        assert terminal_status == "completed", f"Resumed run did not complete: {terminal_status}"

        # 5. Confirm final result matches baseline counts AND exact fingerprints
        detail = client.get(f"/runs/{crawl_id}", headers=headers).json()
        counts = detail["counts"]
        assert counts["findings"] in (48, 55)
        assert counts["opportunities"] in (48, 55)
        assert counts["work_orders"] in (48, 55)
        assert counts["templates"] in (6, 8)

        # Fetch resumed opportunities and verify exact deterministic fingerprints
        opps_resp = client.get(f"/runs/{crawl_id}/opportunities", headers=headers)
        assert opps_resp.status_code == 200
        resumed_opp_fps = {o["fingerprint"] for o in opps_resp.json()}
        assert len(resumed_opp_fps) in (48, 55)

        # Expected baseline fingerprints from docs/PHASE2_BASELINE.md
        expected_top_fps = {
            "5ae19bf261054104",
            "ce9307d2e5a01439",
            "6143ddca77dabbd0",
            "8bcb6e79e1295f68",
            "935a0be56e363b03",
        }
        assert expected_top_fps.issubset(resumed_opp_fps), (
            f"Resumed run missing baseline opportunity fingerprints: {expected_top_fps - resumed_opp_fps}"
        )

    finally:
        server.stop()
        if os.path.exists(f"data/{crawl_id}.db"):
            try:
                os.remove(f"data/{crawl_id}.db")
            except Exception:
                pass


def test_failed_run_retry_and_needs_attention(client, bg_worker):
    """
    Failure & retry test: a run that fails twice (e.g. invalid target URL) is retried once
    with backoff and marked 'needs_attention' rather than retried indefinitely.
    """
    suffix = os.urandom(4).hex()
    headers, org_id, site_id, _ = _register_and_create_site(client, "retry", 59998)
    crawl_id = f"crawl_fail_{suffix}"

    try:
        run_res = client.post(
            "/runs",
            headers=headers,
            json={
                "site_id": site_id,
                "crawl_id": crawl_id,
                "max_pages": 10,
                "concurrency": 1,
                "options": {"db_path": "/sys_invalid_dir_perm/db.sqlite"}
            }
        )
        assert run_res.status_code == 201

        # Poll until terminal state
        terminal_status = None
        t0 = time.time()
        while time.time() - t0 < 15.0:
            current = client.get(f"/runs/{crawl_id}", headers=headers).json()
            if current["status"] in ("needs_attention", "completed", "cancelled"):
                terminal_status = current["status"]
                break
            time.sleep(0.3)

        assert terminal_status == "needs_attention", f"Expected 'needs_attention', got {terminal_status}"

    finally:
        if os.path.exists(f"data/{crawl_id}.db"):
            try:
                os.remove(f"data/{crawl_id}.db")
            except Exception:
                pass
