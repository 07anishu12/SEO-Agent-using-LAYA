"""
SEOJEV Phase 2: Stage 9 Watch, Alerts & Notification Dispatcher Test Suite.

Validates the full Stage 9 capabilities:
1. Autonomous Watch Scheduler:
   - Configures a short interval/past due schedule for a site with planted SEO defects.
   - Starts WatchScheduler background daemon.
   - Confirms watch checks execute and write real alert rows to PostgreSQL without manual triggering.
2. Notification Dispatcher & Multi-Channel Fanout:
   - Dispatches regression and watch alerts across Slack, Generic Webhook, and Email.
   - Verifies actual payload delivery against a local HTTP webhook server and in-memory email sink.
   - Verifies delivery isolation: failure on Slack does not block Webhook or Email.
3. API Endpoints & Tenant Isolation:
   - Validates POST & GET /sites/{id}/watch (validating cron expressions).
   - Validates GET & PATCH /sites/{id}/alerts (filtering by severity and status).
   - Enforces strict cross-org isolation (Org B cannot view or update Org A's watch or alerts -> 404).
4. Frontend Watch & Alerts Screen:
   - Validates that UI renders real schedule configuration and real alert history from the database.
   - Validates schedule updates and resolving alerts via the interactive UI.
"""
import asyncio
import hashlib
import json
import os
import socket
import subprocess
import sys
import threading
import time
import urllib.request
from datetime import datetime, timezone, timedelta
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Dict, Any, List

import httpx
import pytest
from playwright.async_api import async_playwright
from psycopg.types.json import Jsonb

from database.connection import get_connection
from database.migrator import PostgresMigrator
from jobs.scheduler import WatchScheduler
from services.notifications import NotificationDispatcher, InMemoryEmailSink


def find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        return s.getsockname()[1]


SITE_PORT = find_free_port()
API_PORT = find_free_port()
FRONTEND_PORT = find_free_port()
DUMMY_WEBHOOK_PORT = find_free_port()


# ---------------------------------------------------------------------------
# Dummy Webhook & Sink Server
# ---------------------------------------------------------------------------
class DummySinkHandler(BaseHTTPRequestHandler):
    slack_payloads: List[Dict[str, Any]] = []
    webhook_payloads: List[Dict[str, Any]] = []

    def log_message(self, format, *args):
        pass

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length).decode("utf-8")
        try:
            data = json.loads(body)
        except Exception:
            data = {"raw": body}

        if self.path == "/dummy-slack":
            DummySinkHandler.slack_payloads.append(data)
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"ok": true}')
        elif self.path == "/dummy-webhook":
            DummySinkHandler.webhook_payloads.append(data)
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"status": "received"}')
        elif self.path == "/failing-slack":
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"error": "Simulated Slack failure"}')
        else:
            self.send_response(404)
            self.end_headers()


# ---------------------------------------------------------------------------
# Synthetic Defect Site Server for Watch Checks
# ---------------------------------------------------------------------------
class DefectSiteHandler(BaseHTTPRequestHandler):
    mode: str = "noindex"  # "noindex", "500_error", "sitemap_drop", "clean"

    def log_message(self, format, *args):
        pass

    def do_GET(self):
        if self.path == "/robots.txt":
            if DefectSiteHandler.mode == "robots_blocked":
                content = "User-agent: *\nDisallow: /\n"
            else:
                content = "User-agent: *\nAllow: /\n"
            data = content.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return

        if self.path == "/sitemap.xml":
            if DefectSiteHandler.mode == "sitemap_drop":
                content = '<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"></urlset>'
            else:
                content = (
                    '<?xml version="1.0" encoding="UTF-8"?>'
                    '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
                    f'<url><loc>http://127.0.0.1:{SITE_PORT}/p1</loc></url>'
                    f'<url><loc>http://127.0.0.1:{SITE_PORT}/p2</loc></url>'
                    '</urlset>'
                )
            data = content.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/xml")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return

        # Top pages / landing
        if DefectSiteHandler.mode == "500_error":
            self.send_response(500)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(b"<html><body>500 Internal Server Error</body></html>")
            return

        if DefectSiteHandler.mode == "noindex":
            content = (
                "<html><head><title>Defect Page</title>"
                '<meta name="robots" content="noindex, follow" />'
                f'<link rel="canonical" href="http://127.0.0.1:{SITE_PORT}/" />'
                "</head><body><h1>Landing</h1></body></html>"
            )
        else:
            content = (
                "<html><head><title>Healthy Page</title>"
                '<meta name="robots" content="index, follow" />'
                f'<link rel="canonical" href="http://127.0.0.1:{SITE_PORT}/" />'
                "</head><body><h1>Healthy Landing</h1></body></html>"
            )

        data = content.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


@pytest.fixture(scope="session", autouse=True)
def prepare_db():
    migrator = PostgresMigrator(db_url="postgresql:///seojev_test")
    migrator.run_migrations()


@pytest.fixture(scope="session")
def defect_site_server():
    server = HTTPServer(("127.0.0.1", SITE_PORT), DefectSiteHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{SITE_PORT}"
    server.shutdown()


@pytest.fixture(scope="session")
def dummy_webhook_server():
    DummySinkHandler.slack_payloads.clear()
    DummySinkHandler.webhook_payloads.clear()
    server = HTTPServer(("127.0.0.1", DUMMY_WEBHOOK_PORT), DummySinkHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{DUMMY_WEBHOOK_PORT}"
    server.shutdown()


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


# ---------------------------------------------------------------------------
# Test 1: Autonomous Watch Scheduler Execution (writes alert without manual trigger)
# ---------------------------------------------------------------------------
def test_watch_scheduler_autonomous_execution_writes_alert_row(defect_site_server):
    """
    Scheduler Test:
    Configures a short interval / due watch check.
    Starts WatchScheduler background thread.
    Confirms the scheduler discovers the due watch, executes checks against the site,
    and writes an alert row to the alerts table completely autonomously.
    """
    DefectSiteHandler.mode = "noindex"
    suffix = os.urandom(4).hex()
    org_id = f"org_sched_{suffix}"
    site_id = f"site_sched_{suffix}"
    target_url = f"http://127.0.0.1:{SITE_PORT}/"

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO orgs (id, name, slug) VALUES (%s, %s, %s)", (org_id, f"Sched Org {suffix}", f"sched-{suffix}"))
            cur.execute(
                "INSERT INTO sites (id, org_id, domain, url, vertical) VALUES (%s, %s, %s, %s, 'generic')",
                (site_id, org_id, f"127.0.0.1:{SITE_PORT}", target_url)
            )
            # Deactivate any leftover watch configs to prevent cross-test interference
            cur.execute("UPDATE watch_configs SET is_active = FALSE WHERE is_active = TRUE")

            # Create a watch config with next_run_at in the past so it triggers immediately
            cur.execute(
                """
                INSERT INTO watch_configs (
                    id, org_id, site_id, cron_expression, is_active, checks_json, top_pages_json, next_run_at
                )
                VALUES (%s, %s, %s, '* * * * *', TRUE, '["top_pages"]', %s, %s)
                """,
                (
                    f"watch_{suffix}",
                    org_id,
                    site_id,
                    Jsonb([target_url]),
                    datetime.now(timezone.utc) - timedelta(seconds=10)
                )
            )
        conn.commit()

    # Start scheduler daemon
    scheduler = WatchScheduler(poll_interval_sec=0.2)
    scheduler.start()
    assert scheduler.is_running()

    # Wait up to 6 seconds for the background daemon to pick up the job and write alert
    alert_found = None
    for _ in range(30):
        time.sleep(0.2)
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id, alert_type, severity, title, status FROM alerts WHERE org_id = %s AND site_id = %s",
                    (org_id, site_id)
                )
                rows = cur.fetchall()
                if rows:
                    alert_found = rows[0]
                    break

    scheduler.stop()

    assert alert_found is not None, "Scheduler failed to execute and write alert row autonomously"
    assert alert_found["alert_type"] == "NOINDEX_LEAK"
    assert alert_found["severity"] == "critical"
    assert alert_found["status"] == "open"

    # Confirm next_run_at was advanced into the future
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT next_run_at, last_run_at FROM watch_configs WHERE id = %s", (f"watch_{suffix}",))
            cfg_row = cur.fetchone()
            assert cfg_row["last_run_at"] is not None
            assert cfg_row["next_run_at"] > datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Test 2: Notification Dispatcher Fanout & Delivery Proof
# ---------------------------------------------------------------------------
def test_notification_dispatcher_fanout_and_delivery_verification(dummy_webhook_server):
    """
    Dispatcher Test:
    Dispatches regression and watch alert events to Slack incoming webhook,
    dummy email sink, and generic outgoing webhook.
    Proves all destinations actually receive the message payload.
    Also proves delivery isolation when one channel fails (failing Slack endpoint).
    """
    email_sink = InMemoryEmailSink()
    dispatcher = NotificationDispatcher(email_sink=email_sink)

    slack_url = f"{dummy_webhook_server}/dummy-slack"
    webhook_url = f"{dummy_webhook_server}/dummy-webhook"
    failing_slack_url = f"{dummy_webhook_server}/failing-slack"

    channels = [
        {"type": "slack", "webhook_url": slack_url},
        {"type": "email", "recipients": ["alerts-seo@example.com", "devops@example.com"]},
        {"type": "webhook", "url": webhook_url}
    ]

    event_payload = {
        "id": "alert_test_001",
        "site_id": "site_test_123",
        "org_id": "org_test_123",
        "severity": "critical",
        "alert_type": "NOINDEX_LEAK",
        "title": "Critical Noindex Leak Detected",
        "message": "Homepage is serving a noindex directive blocking search crawlers.",
        "affected_urls": ["http://example.com/"],
        "detected_at": datetime.now(timezone.utc).isoformat()
    }

    # 1. Dispatch event across all 3 channels
    DummySinkHandler.slack_payloads.clear()
    DummySinkHandler.webhook_payloads.clear()
    email_sink.clear()

    res = dispatcher.dispatch_event("regression.detected", event_payload, channels=channels)
    assert res["delivered"] is True

    # VERIFY DELIVERY PROOF:
    # A. Slack Webhook delivery verified
    assert len(DummySinkHandler.slack_payloads) == 1
    slack_msg = DummySinkHandler.slack_payloads[0]
    assert "attachments" in slack_msg
    assert "Critical Noindex Leak" in slack_msg["attachments"][0]["title"]
    assert any(f["value"] == "CRITICAL" for f in slack_msg["attachments"][0]["fields"])

    # B. Outgoing Generic Webhook delivery verified
    assert len(DummySinkHandler.webhook_payloads) == 1
    webhook_msg = DummySinkHandler.webhook_payloads[0]
    assert webhook_msg["event"] == "regression.detected"
    assert webhook_msg["data"]["alert_type"] == "NOINDEX_LEAK"

    # C. Email Sink delivery verified
    emails = email_sink.get_messages()
    assert len(emails) == 1
    assert "alerts-seo@example.com" in emails[0]["recipients"]
    assert "[SEOJEV CRITICAL] Critical Noindex Leak Detected" in emails[0]["subject"]
    assert "Event: regression.detected" in emails[0]["body"]

    # 2. Test Channel Failure Isolation
    # One channel fails (Slack HTTP 500) -> other channels MUST still succeed
    failing_channels = [
        {"type": "slack", "webhook_url": failing_slack_url},
        {"type": "email", "recipients": ["isolated@example.com"]},
        {"type": "webhook", "url": webhook_url}
    ]

    DummySinkHandler.webhook_payloads.clear()
    email_sink.clear()

    res_iso = dispatcher.dispatch_event("watch.alert", event_payload, channels=failing_channels)
    # Overall delivered has error recorded for slack, but email and webhook succeeded!
    assert len(res_iso["channel_results"]["slack"]) == 1
    assert res_iso["channel_results"]["slack"][0]["success"] is False

    assert len(res_iso["channel_results"]["email"]) == 1
    assert res_iso["channel_results"]["email"][0]["success"] is True

    assert len(res_iso["channel_results"]["webhook"]) == 1
    assert res_iso["channel_results"]["webhook"][0]["success"] is True

    assert len(DummySinkHandler.webhook_payloads) == 1
    assert len(email_sink.get_messages()) == 1


# ---------------------------------------------------------------------------
# Test 3: Watch & Alerts API Endpoints & Tenant Isolation
# ---------------------------------------------------------------------------
def test_watch_and_alerts_api_and_isolation(api_server):
    """
    API & Multi-Tenant Isolation Test:
    - POST /sites/{id}/watch saves schedule config and validates cron syntax.
    - GET /sites/{id}/watch returns config.
    - GET /sites/{id}/alerts returns filtered alert records.
    - PATCH /sites/{id}/alerts/{alert_id} resolves alerts.
    - Cross-tenant isolation: Org B requests to Org A's watch or alert endpoints return 404.
    """
    client = httpx.Client(base_url=api_server, timeout=10.0)

    # Register Org A
    suffix_a = os.urandom(4).hex()
    reg_a = client.post("/auth/register", json={
        "email": f"org_a_{suffix_a}@example.com",
        "password": "Password123!",
        "org_name": f"Org A {suffix_a}"
    }).json()
    token_a = reg_a["access_token"]
    headers_a = {"Authorization": f"Bearer {token_a}"}

    # Register Org B
    suffix_b = os.urandom(4).hex()
    reg_b = client.post("/auth/register", json={
        "email": f"org_b_{suffix_b}@example.com",
        "password": "Password123!",
        "org_name": f"Org B {suffix_b}"
    }).json()
    token_b = reg_b["access_token"]
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # Org A creates Site
    site_a = client.post("/sites", json={
        "url": "https://site-a.example.com",
        "domain": f"site-a-{suffix_a}.com"
    }, headers=headers_a).json()
    site_a_id = site_a["id"]

    # 1. Org A configures watch
    watch_req = {
        "cron_expression": "*/10 * * * *",
        "is_active": True,
        "timezone": "UTC",
        "checks": ["robots_txt", "top_pages"],
        "top_pages": ["https://site-a.example.com/products"],
        "notification_channels": [{"type": "slack", "webhook_url": "https://hooks.slack.com/dummy"}]
    }
    resp = client.post(f"/sites/{site_a_id}/watch", json=watch_req, headers=headers_a)
    assert resp.status_code == 200
    cfg = resp.json()
    assert cfg["cron_expression"] == "*/10 * * * *"
    assert cfg["is_active"] is True
    assert "robots_txt" in cfg["checks"]
    assert cfg["next_run_at"] is not None

    # Invalid cron expression returns 400
    bad_resp = client.post(f"/sites/{site_a_id}/watch", json={"cron_expression": "invalid-cron"}, headers=headers_a)
    assert bad_resp.status_code == 400

    # GET /sites/{id}/watch
    get_cfg = client.get(f"/sites/{site_a_id}/watch", headers=headers_a)
    assert get_cfg.status_code == 200
    assert get_cfg.json()["cron_expression"] == "*/10 * * * *"

    # Seed alerts for Site A
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO alerts (id, org_id, site_id, alert_type, severity, title, message, status)
                VALUES
                    (%s, %s, %s, 'NOINDEX_LEAK', 'critical', 'Critical Noindex Leak', 'Accidental noindex meta tag', 'open'),
                    (%s, %s, %s, 'SITEMAP_DROP', 'high', 'Sitemap Count Dropped', 'Sitemap lost 30 percent of URLs', 'open')
                """,
                (
                    f"alert_a1_{suffix_a}", reg_a["user"]["org_id"], site_a_id,
                    f"alert_a2_{suffix_a}", reg_a["user"]["org_id"], site_a_id
                )
            )
        conn.commit()

    # GET /sites/{id}/alerts
    alerts_resp = client.get(f"/sites/{site_a_id}/alerts", headers=headers_a)
    assert alerts_resp.status_code == 200
    alert_data = alerts_resp.json()
    assert alert_data["total"] >= 2

    # Filtering by severity
    crit_resp = client.get(f"/sites/{site_a_id}/alerts?severity=critical", headers=headers_a)
    assert crit_resp.status_code == 200
    assert all(a["severity"] == "critical" for a in crit_resp.json()["alerts"])

    # PATCH /sites/{id}/alerts/{alert_id} (resolve alert)
    resolve_resp = client.patch(
        f"/sites/{site_a_id}/alerts/alert_a1_{suffix_a}",
        json={"status": "resolved"},
        headers=headers_a
    )
    assert resolve_resp.status_code == 200
    assert resolve_resp.json()["status"] == "resolved"
    assert resolve_resp.json()["is_resolved"] is True

    # MULTI-TENANT ISOLATION CHECKS (Org B attempting to access Org A)
    # All cross-org access attempts must return 404
    b_watch_get = client.get(f"/sites/{site_a_id}/watch", headers=headers_b)
    assert b_watch_get.status_code == 404

    b_watch_post = client.post(f"/sites/{site_a_id}/watch", json=watch_req, headers=headers_b)
    assert b_watch_post.status_code == 404

    b_alerts_get = client.get(f"/sites/{site_a_id}/alerts", headers=headers_b)
    assert b_alerts_get.status_code == 404

    b_alert_patch = client.patch(
        f"/sites/{site_a_id}/alerts/alert_a1_{suffix_a}",
        json={"status": "open"},
        headers=headers_b
    )
    assert b_alert_patch.status_code == 404


# ---------------------------------------------------------------------------
# Test 4: UI Watch & Alerts Screen Rendering Real API Data
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_ui_watch_and_alerts_renders_real_data(frontend_server, api_server):
    """
    UI Test:
    Logs in with Playwright.
    Navigates to /sites/{id}/watch.
    Confirms Watch Schedule Configuration form renders and saves real data.
    Confirms Alert History Ledger renders real alerts from PostgreSQL.
    Confirms resolving an alert in the UI updates status to Resolved in real time.
    """
    suffix = os.urandom(4).hex()
    email = f"ui_watch_{suffix}@example.com"
    password = "Password123!"

    # 1. Register & Setup site via API
    client = httpx.Client(base_url=api_server, timeout=10.0)
    reg = client.post("/auth/register", json={
        "email": email,
        "password": password,
        "org_name": f"UI Watch Org {suffix}"
    }).json()
    token = reg["access_token"]
    user = reg["user"]
    org_id = user["org_id"]

    site = client.post("/sites", json={
        "url": f"http://127.0.0.1:{SITE_PORT}/",
        "domain": f"watch-ui-{suffix}.com"
    }, headers={"Authorization": f"Bearer {token}"}).json()
    site_id = site["id"]

    # 2. Plant real alert in database for this site
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO alerts (
                    id, org_id, site_id, alert_type, severity, title, message,
                    affected_urls_json, status, detected_at
                )
                VALUES (%s, %s, %s, 'NOINDEX_LEAK', 'critical', 'Critical Noindex Directive on Homepage',
                        'Homepage is serving an accidental noindex meta tag blocking search crawlers.',
                        %s, 'open', %s)
                """,
                (
                    f"alert_ui_{suffix}",
                    org_id,
                    site_id,
                    Jsonb([f"http://127.0.0.1:{SITE_PORT}/"]),
                    datetime.now(timezone.utc)
                )
            )
        conn.commit()

    # 3. Launch Playwright
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
            [token, json.dumps(user), api_server],
        )

        # Navigate directly to the Watch & Alerts screen
        await page.goto(f"{frontend_server}/sites/{site_id}/watch")

        # Verify page header
        await page.wait_for_selector("h1:has-text('Watch & Alerts Center')", timeout=8000)
        await page.wait_for_selector(f"text={site['domain']}", timeout=8000)
        assert await page.is_visible(f"text={site['domain']}")

        # Verify Alert History Ledger renders the planted real alert from DB
        await page.wait_for_selector(f"h4:has-text('Critical Noindex Directive on Homepage')", timeout=6000)
        assert await page.is_visible("span:has-text('critical')")
        assert await page.is_visible("span:has-text('NOINDEX_LEAK')")

        # Test Interactive Schedule Update
        # Click "Hourly" preset button
        await page.click("button:has-text('Hourly')")
        # Click Save Schedule Configuration
        await page.click("button[type='submit']:has-text('Save Schedule Configuration')")

        # Verify success banner appears
        await page.wait_for_selector("text=Watch schedule configuration saved and activated successfully", timeout=6000)

        # Test resolving an alert in the UI
        resolve_button = page.locator("button:has-text('Resolve')").first
        await resolve_button.click()

        # Verify badge updates to "Resolved"
        await page.wait_for_selector("span:has-text('Resolved')", timeout=6000)

        await browser.close()
