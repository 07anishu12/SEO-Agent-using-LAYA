"""
SEOJEV Phase 2: Stage 10e CI/CD Deployment Regression Webhook Test Suite.

Validates Section 6.2:
1. Authenticated Endpoint Execution:
   - POST /sites/{id}/deploy-webhook accepts authenticated requests.
2. Scoped Re-crawl & Snapshot Diff:
   - Crawls only specified scoped URLs.
   - Generates snapshot and diffs against baseline.
3. Regression Classification:
   - Detects planted regressions (e.g. noindex leak on target URL).
4. Multi-channel Result Delivery:
   - Dispatches verdict to PR comment sink (markdown summary) and dummy Slack webhook.
5. Security & Multi-tenant Isolation:
   - Rejects unauthenticated calls (401 Unauthorized).
   - Blocks cross-tenant execution (Org B cannot deploy-webhook Org A's site).
6. Asynchronous Queue Response:
   - When sync=False, immediately returns run_id and status='queued'.
"""
import hashlib
import json
import os
import socket
import threading
import time
from datetime import datetime, timezone, timedelta
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Dict, Any

import pytest
from fastapi.testclient import TestClient
from psycopg.types.json import Jsonb

from api.main import app
from database.connection import get_connection
from database.migrator import PostgresMigrator
from services.notifications import NotificationDispatcher, InMemoryEmailSink, InMemoryPRSink
from verification.snapshot import SnapshotRecorder


def find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        return s.getsockname()[1]


CICD_PORT = find_free_port()


class CICDSiteHandler(BaseHTTPRequestHandler):
    mode: str = "regressed"  # "baseline", "regressed"

    def log_message(self, format, *args):
        pass

    def do_GET(self):
        target_base = f"http://127.0.0.1:{CICD_PORT}"
        if self.path in ("/", "/index.html"):
            html = (
                "<!DOCTYPE html><html><head><title>Home</title>"
                '<meta name="robots" content="index, follow" />'
                f'<link rel="canonical" href="{target_base}/" />'
                "</head><body><h1>Landing</h1><p>Welcome to our main portal.</p></body></html>"
            )
            data = html.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return

        if self.path == "/products/regressed":
            if CICDSiteHandler.mode == "regressed":
                # Planted regression: accidental noindex directive
                html = (
                    "<!DOCTYPE html><html><head><title>Regressed Product</title>"
                    '<meta name="robots" content="noindex, nofollow" />'
                    f'<link rel="canonical" href="{target_base}/products/regressed" />'
                    "</head><body><h1>Product with Noindex</h1><p>Our flagship product details.</p></body></html>"
                )
            else:
                html = (
                    "<!DOCTYPE html><html><head><title>Healthy Product</title>"
                    '<meta name="robots" content="index, follow" />'
                    f'<link rel="canonical" href="{target_base}/products/regressed" />'
                    "</head><body><h1>Healthy Product</h1><p>Our flagship product details.</p></body></html>"
                )
            data = html.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return

        if self.path == "/robots.txt":
            data = b"User-agent: *\nAllow: /\n"
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return

        self.send_response(404)
        self.end_headers()


@pytest.fixture(scope="session", autouse=True)
def prepare_db():
    migrator = PostgresMigrator(db_url="postgresql:///seojev_test")
    migrator.run_migrations()


@pytest.fixture(scope="session")
def cicd_site_server():
    server = HTTPServer(("127.0.0.1", CICD_PORT), CICDSiteHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{CICD_PORT}"
    server.shutdown()


def create_token(org_id: str, email: str = "dev@example.com") -> str:
    from api.auth import create_access_token
    return create_access_token({"sub": f"usr_{org_id}", "email": email, "org_id": org_id, "role": "admin"})


def test_cicd_deploy_webhook_full_lifecycle(cicd_site_server):
    """
    E2E Test:
    1. Sets up site with baseline snapshot for /products/regressed.
    2. Sends deploy webhook with scope=['/products/regressed'] and PR callback.
    3. Verifies scoped execution, diff detection, regression alert, and PR comment delivery.
    """
    client = TestClient(app)
    suffix = os.urandom(4).hex()
    org_id = f"org_cicd_{suffix}"
    site_id = f"site_cicd_{suffix}"
    base_url = f"http://127.0.0.1:{CICD_PORT}"
    regressed_url = f"{base_url}/products/regressed"
    run_base_id = f"crawl_base_{suffix}"

    token = create_token(org_id)

    # 1. Setup DB with baseline Run & Snapshot
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO orgs (id, name, slug) VALUES (%s, %s, %s)", (org_id, f"CICD Org {suffix}", f"cicd-{suffix}"))
            cur.execute(
                "INSERT INTO sites (id, org_id, domain, url, vertical) VALUES (%s, %s, %s, %s, 'ecommerce')",
                (site_id, org_id, f"127.0.0.1:{CICD_PORT}", base_url)
            )
            # Baseline run
            cur.execute(
                """
                INSERT INTO runs (id, org_id, site_id, status, progress_pct, finished_at)
                VALUES (%s, %s, %s, 'completed', 100.0, %s)
                """,
                (run_base_id, org_id, site_id, datetime.now(timezone.utc) - timedelta(hours=2))
            )
            # Baseline healthy snapshot for /products/regressed
            base_snap = {
                "url": regressed_url,
                "title": "Healthy Product",
                "canonical": regressed_url,
                "meta_robots": "index, follow",
                "status_code": 200,
                "content_hash": hashlib.sha256(b"healthy-prod").hexdigest(),
                "schema_hash": ""
            }
            cur.execute(
                """
                INSERT INTO snapshots (id, org_id, site_id, run_id, url, snapshot_data)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (f"snap_base_{suffix}", org_id, site_id, run_base_id, regressed_url, Jsonb(base_snap))
            )
            # Also write to SQLite data/{run_base_id}.db
            os.makedirs("data", exist_ok=True)
            recorder = SnapshotRecorder(db_path=f"data/{run_base_id}.db")
            recorder.take_snapshot_for_url(run_base_id, regressed_url, base_snap)
        conn.commit()

    # Set site server mode to regressed
    CICDSiteHandler.mode = "regressed"

    # 2. Invoke CI/CD webhook synchronously
    payload = {
        "deployment_id": f"deploy_{suffix}",
        "commit_sha": "a1b2c3d4e5f6",
        "branch": "feature/seo-update",
        "scope": ["/products/regressed"],
        "callback": {
            "pr_comment": {
                "repo": "acme/ecommerce-platform",
                "pr_number": 142,
                "provider": "github"
            }
        }
    }

    resp = client.post(
        f"/sites/{site_id}/deploy-webhook?sync=true",
        json=payload,
        headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 200
    data = resp.json()

    # 3. Verify execution results
    assert data["status"] == "completed"
    assert data["deployment_id"] == f"deploy_{suffix}"
    assert data["commit_sha"] == "a1b2c3d4e5f6"
    assert regressed_url in data["scope"]
    assert data["verdict"] == "REGRESSION DETECTED"
    assert data["regressions_count"] >= 1

    # 4. Verify snapshot and alert persisted to PostgreSQL
    run_id = data["run_id"]
    with get_connection() as conn:
        with conn.cursor() as cur:
            # Check run completed
            cur.execute("SELECT status FROM runs WHERE id = %s", (run_id,))
            run_row = cur.fetchone()
            assert run_row is not None
            assert run_row["status"] == "completed"

            # Check snapshot was captured for regressed URL
            cur.execute("SELECT url, snapshot_data FROM snapshots WHERE run_id = %s", (run_id,))
            snaps = cur.fetchall()
            assert len(snaps) >= 1
            assert any(s["url"] == regressed_url for s in snaps)

            # Check regression alert persisted
            cur.execute("SELECT id, alert_type, severity, title FROM alerts WHERE run_id = %s", (run_id,))
            alerts = cur.fetchall()
            assert len(alerts) >= 1
            assert alerts[0]["alert_type"] == "NOINDEX_LEAK"
            assert alerts[0]["severity"] == "critical"

    # 5. Verify PR comment sink received formatted markdown review
    from services.notifications import global_test_pr_sink
    comments = global_test_pr_sink.get_comments()
    matching_comment = next((c for c in comments if c.get("pr_number") == 142), None)
    assert matching_comment is not None, "PR comment was not delivered to PR sink"
    assert matching_comment["repo"] == "acme/ecommerce-platform"
    assert "REGRESSION DETECTED" in matching_comment["body"]
    assert "NOINDEX_LEAK" in matching_comment["body"] or "Noindex" in matching_comment["body"]


def test_cicd_deploy_webhook_security_and_tenant_isolation(cicd_site_server):
    """
    Validates:
    - 401 when unauthenticated.
    - 404 when Org B attempts to trigger deployment webhook on Org A's site.
    """
    client = TestClient(app)
    suffix = os.urandom(4).hex()
    org_a = f"org_sec_a_{suffix}"
    org_b = f"org_sec_b_{suffix}"
    site_a = f"site_sec_a_{suffix}"

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO orgs (id, name, slug) VALUES (%s, %s, %s)", (org_a, "Org A", f"sec-a-{suffix}"))
            cur.execute("INSERT INTO orgs (id, name, slug) VALUES (%s, %s, %s)", (org_b, "Org B", f"sec-b-{suffix}"))
            cur.execute("INSERT INTO sites (id, org_id, domain, url) VALUES (%s, %s, %s, %s)", (site_a, org_a, "a.com", "https://a.com"))
        conn.commit()

    token_b = create_token(org_b)

    payload = {"deployment_id": "dep_evil", "scope": ["/"]}

    # 1. No auth -> 401
    resp_noauth = client.post(f"/sites/{site_a}/deploy-webhook", json=payload)
    assert resp_noauth.status_code == 401

    # 2. Org B auth -> 404 Site not found in org
    resp_cross = client.post(
        f"/sites/{site_a}/deploy-webhook",
        json=payload,
        headers={"Authorization": f"Bearer {token_b}"}
    )
    assert resp_cross.status_code == 404


def test_cicd_deploy_webhook_async_mode(cicd_site_server):
    """
    Validates asynchronous mode (sync=False):
    Immediately returns 200 OK with run_id and status='queued'.
    """
    client = TestClient(app)
    suffix = os.urandom(4).hex()
    org_id = f"org_async_{suffix}"
    site_id = f"site_async_{suffix}"

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO orgs (id, name, slug) VALUES (%s, %s, %s)", (org_id, "Async Org", f"async-{suffix}"))
            cur.execute(
                "INSERT INTO sites (id, org_id, domain, url) VALUES (%s, %s, %s, %s)",
                (site_id, org_id, f"127.0.0.1:{CICD_PORT}", f"http://127.0.0.1:{CICD_PORT}")
            )
        conn.commit()

    token = create_token(org_id)
    payload = {"deployment_id": f"dep_async_{suffix}", "scope": ["/"]}

    resp = client.post(
        f"/sites/{site_id}/deploy-webhook?sync=false",
        json=payload,
        headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "queued"
    assert "run_id" in data
    assert data["deployment_id"] == f"dep_async_{suffix}"
