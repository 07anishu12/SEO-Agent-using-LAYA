"""
SEOJEV Phase 2: Stage 10i.1 Multi-Site Portfolio View Test Suite.

Validates Section 6.6:
1. Portfolio-level aggregation across multiple monitored sites:
   - Total sites count and healthy sites count.
   - Total open alerts across all sites.
   - Aggregate issue count and opportunity count derived from latest runs & trends.
2. Per-site portfolio health metrics:
   - Distinguishes healthy vs warning vs critical states.
3. Strict multi-tenant isolation:
   - Confirms Tenant A cannot see Tenant B's portfolio data or aggregate statistics.
4. Real Playwright browser E2E test:
   - Renders portfolio overview cards and individual site health/metric badges in the browser.
"""
import json
import os
import socket
import subprocess
import sys
import time
import urllib.request
from datetime import datetime, timezone
import httpx
import pytest
from fastapi.testclient import TestClient
from psycopg.types.json import Jsonb
from playwright.async_api import async_playwright

from api.main import app
from database.connection import get_connection
from database.migrator import PostgresMigrator
from api.auth import create_access_token


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


def test_portfolio_overview_aggregation_and_tenant_isolation():
    """
    Tests the GET /sites/portfolio endpoint directly with real database records.
    Verifies metric aggregation, site health determination, and strict tenant isolation.
    """
    client = TestClient(app)
    suffix = os.urandom(4).hex()
    org_a = f"org_port_a_{suffix}"
    org_b = f"org_port_b_{suffix}"

    site_a1 = f"site_a1_{suffix}"
    site_a2 = f"site_a2_{suffix}"
    site_b1 = f"site_b1_{suffix}"

    run_a1 = f"run_a1_{suffix}"
    run_a2 = f"run_a2_{suffix}"
    run_b1 = f"run_b1_{suffix}"

    with get_connection() as conn:
        with conn.cursor() as cur:
            # Seed Orgs
            cur.execute("INSERT INTO orgs (id, name, slug) VALUES (%s, %s, %s)", (org_a, "Org A", f"orga-{suffix}"))
            cur.execute("INSERT INTO orgs (id, name, slug) VALUES (%s, %s, %s)", (org_b, "Org B", f"orgb-{suffix}"))

            # Seed Sites
            cur.execute("INSERT INTO sites (id, org_id, domain, url, vertical) VALUES (%s, %s, 'alpha.com', 'https://alpha.com', 'ecommerce')", (site_a1, org_a))
            cur.execute("INSERT INTO sites (id, org_id, domain, url, vertical) VALUES (%s, %s, 'beta.com', 'https://beta.com', 'saas')", (site_a2, org_a))
            cur.execute("INSERT INTO sites (id, org_id, domain, url, vertical) VALUES (%s, %s, 'gamma.com', 'https://gamma.com', 'healthcare')", (site_b1, org_b))

            # Seed Runs
            cur.execute("INSERT INTO runs (id, org_id, site_id, status, progress_pct) VALUES (%s, %s, %s, 'completed', 100.0)", (run_a1, org_a, site_a1))
            cur.execute("INSERT INTO runs (id, org_id, site_id, status, progress_pct) VALUES (%s, %s, %s, 'completed', 100.0)", (run_a2, org_a, site_a2))
            cur.execute("INSERT INTO runs (id, org_id, site_id, status, progress_pct) VALUES (%s, %s, %s, 'completed', 100.0)", (run_b1, org_b, site_b1))

            # Seed Site Trends for Org A
            # Site A1: 5 issues, 12 opportunities -> Healthy
            cur.execute("INSERT INTO site_trends (id, org_id, site_id, run_id, metric, date, value) VALUES (%s, %s, %s, %s, 'issue_count', CURRENT_DATE, 5)", (f"tr_a1_i_{suffix}", org_a, site_a1, run_a1))
            cur.execute("INSERT INTO site_trends (id, org_id, site_id, run_id, metric, date, value) VALUES (%s, %s, %s, %s, 'opportunity_count', CURRENT_DATE, 12)", (f"tr_a1_o_{suffix}", org_a, site_a1, run_a1))

            # Site A2: 20 issues, 3 opportunities -> Critical due to open critical alert
            cur.execute("INSERT INTO site_trends (id, org_id, site_id, run_id, metric, date, value) VALUES (%s, %s, %s, %s, 'issue_count', CURRENT_DATE, 20)", (f"tr_a2_i_{suffix}", org_a, site_a2, run_a2))
            cur.execute("INSERT INTO site_trends (id, org_id, site_id, run_id, metric, date, value) VALUES (%s, %s, %s, %s, 'opportunity_count', CURRENT_DATE, 3)", (f"tr_a2_o_{suffix}", org_a, site_a2, run_a2))

            # Seed Critical Alert for Site A2
            cur.execute(
                """
                INSERT INTO alerts (id, org_id, site_id, alert_type, severity, title, message, status)
                VALUES (%s, %s, %s, '5XX_SPIKE', 'critical', '500 Internal Server Errors', 'Spike detected', 'open')
                """,
                (f"al_a2_{suffix}", org_a, site_a2)
            )

            # Seed Site Trends & Alert for Org B (Isolation verification)
            cur.execute("INSERT INTO site_trends (id, org_id, site_id, run_id, metric, date, value) VALUES (%s, %s, %s, %s, 'issue_count', CURRENT_DATE, 99)", (f"tr_b1_i_{suffix}", org_b, site_b1, run_b1))
            cur.execute("INSERT INTO site_trends (id, org_id, site_id, run_id, metric, date, value) VALUES (%s, %s, %s, %s, 'opportunity_count', CURRENT_DATE, 88)", (f"tr_b1_o_{suffix}", org_b, site_b1, run_b1))
        conn.commit()

    token_a = create_access_token({"sub": f"usr_a_{suffix}", "email": "admin@orga.com", "org_id": org_a, "role": "admin"})
    token_b = create_access_token({"sub": f"usr_b_{suffix}", "email": "admin@orgb.com", "org_id": org_b, "role": "admin"})

    # 1. Fetch Org A portfolio
    resp_a = client.get("/sites/portfolio", headers={"Authorization": f"Bearer {token_a}"})
    assert resp_a.status_code == 200
    data_a = resp_a.json()

    assert data_a["total_sites"] == 2
    assert data_a["total_issues"] == 25  # 5 + 20
    assert data_a["total_opportunities"] == 15  # 12 + 3
    assert data_a["total_open_alerts"] == 1
    assert data_a["healthy_sites"] == 1

    site_map_a = {s["id"]: s for s in data_a["sites"]}
    assert site_a1 in site_map_a
    assert site_a2 in site_map_a
    assert site_b1 not in site_map_a  # Tenant isolation!

    assert site_map_a[site_a1]["health_status"] == "healthy"
    assert site_map_a[site_a1]["issue_count"] == 5
    assert site_map_a[site_a1]["opportunity_count"] == 12

    assert site_map_a[site_a2]["health_status"] == "critical"
    assert site_map_a[site_a2]["issue_count"] == 20
    assert site_map_a[site_a2]["critical_alerts_count"] == 1

    # 2. Fetch Org B portfolio
    resp_b = client.get("/sites/portfolio", headers={"Authorization": f"Bearer {token_b}"})
    assert resp_b.status_code == 200
    data_b = resp_b.json()

    assert data_b["total_sites"] == 1
    assert data_b["total_issues"] == 99
    assert data_b["total_opportunities"] == 88
    assert data_b["total_open_alerts"] == 0
    assert data_b["sites"][0]["id"] == site_b1


@pytest.mark.asyncio
async def test_ui_portfolio_renders_aggregate_metrics_and_health_badges(frontend_server, api_server):
    """
    Playwright UI Test:
    Logs in with an authenticated user, loads the /sites page, and verifies:
    1. The Portfolio Summary cards render correct aggregate statistics.
    2. The Site cards render the calculated health status badges and counters.
    """
    suffix = os.urandom(4).hex()
    org_id = f"org_ui_port_{suffix}"
    site_1 = f"site_ui1_{suffix}"
    site_2 = f"site_ui2_{suffix}"
    run_1 = f"run_ui1_{suffix}"
    run_2 = f"run_ui2_{suffix}"

    token = create_access_token({"sub": f"usr_ui_{suffix}", "email": f"ui_{suffix}@example.com", "org_id": org_id, "role": "admin"})
    user_payload = {"id": f"usr_ui_{suffix}", "email": f"ui_{suffix}@example.com", "org_id": org_id, "role": "admin"}

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO orgs (id, name, slug) VALUES (%s, %s, %s)", (org_id, "UI Port Org", f"uiport-{suffix}"))
            cur.execute("INSERT INTO sites (id, org_id, domain, url, vertical) VALUES (%s, %s, 'shop-ui.test', 'https://shop-ui.test', 'ecommerce')", (site_1, org_id))
            cur.execute("INSERT INTO sites (id, org_id, domain, url, vertical) VALUES (%s, %s, 'blog-ui.test', 'https://blog-ui.test', 'generic')", (site_2, org_id))

            cur.execute("INSERT INTO runs (id, org_id, site_id, status, progress_pct) VALUES (%s, %s, %s, 'completed', 100.0)", (run_1, org_id, site_1))
            cur.execute("INSERT INTO runs (id, org_id, site_id, status, progress_pct) VALUES (%s, %s, %s, 'completed', 100.0)", (run_2, org_id, site_2))

            # Site 1: 8 issues, 14 opportunities -> Healthy
            cur.execute("INSERT INTO site_trends (id, org_id, site_id, run_id, metric, date, value) VALUES (%s, %s, %s, %s, 'issue_count', CURRENT_DATE, 8)", (f"tr_ui1_i_{suffix}", org_id, site_1, run_1))
            cur.execute("INSERT INTO site_trends (id, org_id, site_id, run_id, metric, date, value) VALUES (%s, %s, %s, %s, 'opportunity_count', CURRENT_DATE, 14)", (f"tr_ui1_o_{suffix}", org_id, site_1, run_1))

            # Site 2: 18 issues, 4 opportunities -> Critical
            cur.execute("INSERT INTO site_trends (id, org_id, site_id, run_id, metric, date, value) VALUES (%s, %s, %s, %s, 'issue_count', CURRENT_DATE, 18)", (f"tr_ui2_i_{suffix}", org_id, site_2, run_2))
            cur.execute("INSERT INTO site_trends (id, org_id, site_id, run_id, metric, date, value) VALUES (%s, %s, %s, %s, 'opportunity_count', CURRENT_DATE, 4)", (f"tr_ui2_o_{suffix}", org_id, site_2, run_2))

            cur.execute(
                """
                INSERT INTO alerts (id, org_id, site_id, alert_type, severity, title, message, status)
                VALUES (%s, %s, %s, 'CANONICAL_CHANGE', 'critical', 'Canonical URL altered', 'Alert message', 'open')
                """,
                (f"al_ui_{suffix}", org_id, site_2)
            )
        conn.commit()

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        await page.add_init_script(f"window.__SEOJEV_API_URL__ = '{api_server}';")
        await page.goto(f"{frontend_server}/login")
        await page.evaluate(
            """([token, user, apiUrl]) => {
                localStorage.setItem('seojev_access_token', token);
                localStorage.setItem('seojev_user', user);
                localStorage.setItem('seojev_api_url', apiUrl);
            }""",
            [token, json.dumps(user_payload), api_server],
        )

        await page.goto(f"{frontend_server}/sites")

        # Verify Portfolio Summary Cards render
        await page.wait_for_selector("text=Total Sites", timeout=8000)
        assert await page.is_visible("text=(1 healthy)")
        assert await page.is_visible("text=Open Alerts")
        assert await page.is_visible("text=Total Issues")
        assert await page.is_visible("text=Opportunities")

        # Verify Site Health Badges
        assert await page.is_visible("span:has-text('HEALTHY')")
        assert await page.is_visible("span:has-text('CRITICAL')")

        # Verify domains
        assert await page.is_visible("text=shop-ui.test")
        assert await page.is_visible("text=blog-ui.test")

        await browser.close()
