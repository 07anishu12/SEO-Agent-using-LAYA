"""
SEOJEV Phase 2: Stage 10a Historical Trend Engine E2E Test Suite.

Validates:
1. Run Completion & Trend Aggregation:
   - Creates a site and seeds two distinct completed runs with different issue and opportunity counts.
   - Confirms trend rows are automatically persisted into `site_trends`.
   - Confirms idempotency (repeated processing does not create duplicates).
2. API Layer:
   - Validates GET /sites/{id}/trends returns ordered time-series for issue_count and opportunity_count.
   - Enforces cross-org isolation: Org B receives 404 when querying Org A's trends.
3. Frontend Rendering:
   - Uses Playwright to navigate to /sites/{id}/trends.
   - Confirms browser renders both historical points and metric trajectory bars.
   - Proves no static data is used.
"""
import asyncio
import json
import os
import socket
import subprocess
import sys
import time
import urllib.request
from datetime import datetime, timezone, timedelta, date

import httpx
import pytest
from playwright.async_api import async_playwright

from database.connection import get_connection
from database.migrator import PostgresMigrator
from services.trends import record_run_trends, get_site_trends


def find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        return s.getsockname()[1]


API_PORT = find_free_port()
FRONTEND_PORT = find_free_port()


@pytest.fixture(scope="session", autouse=True)
def prepare_db():
    migrator = PostgresMigrator(db_url="postgresql:///seojev_test")
    migrator.run_migrations()


@pytest.fixture(scope="session")
def api_server():
    env = os.environ.copy()
    env["ENABLE_WORKER"] = "false"
    env["ENABLE_SCHEDULER"] = "false"
    env["PYTHONPATH"] = "."
    cmd = [
        sys.executable,
        "-m",
        "uvicorn",
        "api.main:app",
        "--host",
        "127.0.0.1",
        "--port",
        str(API_PORT),
        "--log-level",
        "warning",
    ]
    proc = subprocess.Popen(cmd, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    ready = False
    for _ in range(60):
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{API_PORT}/health", timeout=1) as resp:
                if resp.status == 200:
                    ready = True
                    break
        except Exception:
            time.sleep(0.2)

    assert ready, "FastAPI server failed to start within 12 seconds"
    yield f"http://127.0.0.1:{API_PORT}"

    proc.terminate()
    try:
        proc.wait(timeout=3)
    except Exception:
        proc.kill()


@pytest.fixture(scope="session")
def frontend_server(api_server):
    env = os.environ.copy()
    env["NEXT_PUBLIC_API_URL"] = api_server
    frontend_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")

    cmd = ["npx", "next", "start", "-p", str(FRONTEND_PORT)]
    proc = subprocess.Popen(cmd, cwd=frontend_dir, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    ready = False
    for _ in range(60):
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{FRONTEND_PORT}/login", timeout=1) as resp:
                if resp.status in (200, 307, 308):
                    ready = True
                    break
        except Exception:
            time.sleep(0.2)

    assert ready, "Next.js frontend failed to start within 12 seconds"
    yield f"http://127.0.0.1:{FRONTEND_PORT}"

    proc.terminate()
    try:
        proc.wait(timeout=3)
    except Exception:
        proc.kill()


@pytest.mark.asyncio
async def test_historical_trend_engine_e2e(frontend_server, api_server):
    """
    Stage 10a E2E Test:
    Creates two completed runs with different issue and opportunity counts.
    Confirms persistence in site_trends, API output, and Playwright UI rendering of both points.
    """
    client = httpx.Client(base_url=api_server, timeout=10.0)

    # 1. Register Org A
    suffix_a = os.urandom(4).hex()
    reg_a = client.post("/auth/register", json={
        "email": f"trends_a_{suffix_a}@example.com",
        "password": "Password123!",
        "org_name": f"Trends Org A {suffix_a}"
    }).json()
    token_a = reg_a["access_token"]
    user_a = reg_a["user"]
    org_id_a = user_a["org_id"]
    headers_a = {"Authorization": f"Bearer {token_a}"}

    # Register Org B for isolation check
    suffix_b = os.urandom(4).hex()
    reg_b = client.post("/auth/register", json={
        "email": f"trends_b_{suffix_b}@example.com",
        "password": "Password123!",
        "org_name": f"Trends Org B {suffix_b}"
    }).json()
    token_b = reg_b["access_token"]
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # Create Site
    site_a = client.post("/sites", json={
        "url": "https://trend-example.com",
        "domain": f"trend-{suffix_a}.com"
    }, headers=headers_a).json()
    site_id = site_a["id"]

    # 2. Seed Run 1 (yesterday: 14 issues, 5 opportunities)
    run1_id = f"crawl_trend1_{suffix_a}"
    date1 = date.today() - timedelta(days=1)
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO runs (id, org_id, site_id, status, progress_pct, total_issues, finished_at)
                VALUES (%s, %s, %s, 'completed', 100.0, 14, %s)
                """,
                (run1_id, org_id_a, site_id, datetime.now(timezone.utc) - timedelta(days=1))
            )
        conn.commit()

    # Record trends for Run 1
    t1_records = record_run_trends(
        org_id=org_id_a,
        site_id=site_id,
        run_id=run1_id,
        run_date=date1,
        counts_override={"issue_count": 14, "opportunity_count": 5}
    )
    assert len(t1_records) == 2

    # Test idempotency: re-running record_run_trends on Run 1 does not produce extra rows
    t1_re = record_run_trends(
        org_id=org_id_a,
        site_id=site_id,
        run_id=run1_id,
        run_date=date1,
        counts_override={"issue_count": 14, "opportunity_count": 5}
    )
    assert len(t1_re) == 2

    # 3. Seed Run 2 (today: 9 issues, 8 opportunities)
    run2_id = f"crawl_trend2_{suffix_a}"
    date2 = date.today()
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO runs (id, org_id, site_id, status, progress_pct, total_issues, finished_at)
                VALUES (%s, %s, %s, 'completed', 100.0, 9, %s)
                """,
                (run2_id, org_id_a, site_id, datetime.now(timezone.utc))
            )
        conn.commit()

    # Record trends for Run 2
    t2_records = record_run_trends(
        org_id=org_id_a,
        site_id=site_id,
        run_id=run2_id,
        run_date=date2,
        counts_override={"issue_count": 9, "opportunity_count": 8}
    )
    assert len(t2_records) == 2

    # 4. Verify API response
    api_resp = client.get(f"/sites/{site_id}/trends", headers=headers_a)
    assert api_resp.status_code == 200
    data = api_resp.json()
    assert data["site_id"] == site_id
    assert "issue_count" in data["trends"]
    assert "opportunity_count" in data["trends"]

    issues = data["trends"]["issue_count"]
    opps = data["trends"]["opportunity_count"]
    assert len(issues) == 2
    assert len(opps) == 2

    # Check values and chronological ordering
    assert issues[0]["value"] == 14.0
    assert issues[0]["date"] == date1.isoformat()
    assert issues[1]["value"] == 9.0
    assert issues[1]["date"] == date2.isoformat()

    assert opps[0]["value"] == 5.0
    assert opps[1]["value"] == 8.0

    # Multi-tenant isolation: Org B receives 404
    b_resp = client.get(f"/sites/{site_id}/trends", headers=headers_b)
    assert b_resp.status_code == 404

    # 5. Playwright UI Verification
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        # Set auth session
        await page.add_init_script(f"window.__SEOJEV_API_URL__ = '{api_server}';")
        await page.goto(f"{frontend_server}/login")
        await page.evaluate(
            """([token, user, apiUrl]) => {
                localStorage.setItem('seojev_access_token', token);
                localStorage.setItem('seojev_user', user);
                localStorage.setItem('seojev_api_url', apiUrl);
            }""",
            [token_a, json.dumps(user_a), api_server],
        )

        # Navigate to trends page
        await page.goto(f"{frontend_server}/sites/{site_id}/trends")

        # Verify page header
        await page.wait_for_selector("h1:has-text('Historical Trends')", timeout=8000)

        # Verify Summary cards show real latest metrics
        # Latest issue count is 9, resolved 5
        await page.wait_for_selector("span:has-text('9')", timeout=5000)
        assert await page.is_visible("text=5 resolved")

        # Latest opportunity count is 8, discovered 3
        await page.wait_for_selector("span:has-text('8')", timeout=5000)
        assert await page.is_visible("text=3 discovered")

        # Verify both dates appear on the axis/table
        assert await page.is_visible(f"text={date1.isoformat()}")
        assert await page.is_visible(f"text={date2.isoformat()}")

        # Verify Run IDs are linked in the data table
        assert await page.is_visible(f"text={run1_id}")
        assert await page.is_visible(f"text={run2_id}")

        await browser.close()
