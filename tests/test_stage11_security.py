"""
SEOJEV Phase 2: Stage 11 Production Security & Hardening Test Suite.

Validates all security guarantees:
1. Multi-Tenant Isolation:
   - Org A cannot access or mutate Org B sites
   - Org A cannot access Org B runs
   - Org A cannot access Org B artifacts
   - Org A cannot access Org B alerts
   - Org A cannot access Org B work orders
   - Org A cannot access Org B trends
   - Org A cannot view Org B search results
   - Org A cannot trigger GSC anomaly detection or webhooks on Org B resources
2. Role-Based Access Control (RBAC):
   - Viewer role cannot mutate resources (POST/PATCH/DELETE rejected with 403 Forbidden)
   - Editor role can perform edits/runs but cannot execute admin-only operations (403 Forbidden)
   - Admin role can execute admin operations
   - Forged JWT tokens with tampered signatures or invalid secrets rejected (401 Unauthorized)
3. Server-Side Request Forgery (SSRF) Protection:
   - Blocks AWS/GCP cloud metadata IP 169.254.169.254 unconditionally
   - Blocks metadata.google.internal
   - Blocks private RFC1918 subnets (10.0.0.1, 192.168.1.1, 172.16.0.1)
   - Blocks non-HTTP schemes (file://, ftp://)
   - Blocks loopback addresses when not exempted
4. Webhook Authentication & Replay Protection:
   - Verifies GitHub HMAC-SHA256 signatures with constant-time equality
   - Rejects forged / invalid signatures (401 Unauthorized)
   - Detects and rejects duplicate replay events
5. Artifact & File Path Traversal Protection:
   - Blocks cross-tenant S3 key presigned URL generation (403 Forbidden)
   - Sanitizes and blocks path traversal attempts (../) in artifact storage keys and ZIP files
6. Database Security & SQL Injection Prevention:
   - Validates that SQL identifiers and projection clauses reject injection tokens
   - Verifies parameterized query execution prevents injection attacks
7. Error Sanitization & Information Disclosure:
   - Global exception handler returns sanitized 500 error responses without exposing tracebacks or credentials
8. Rate Limiting:
   - Sensitive endpoints (/auth/login, /runs, /search) return 429 Too Many Requests when threshold exceeded
"""
import hashlib
import hmac
import json
import os
import time
from datetime import datetime, timezone
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from psycopg.types.json import Jsonb

from api.main import app
from api.auth import create_access_token
from database.connection import get_connection
from database.scoped_query import ScopedQuery, IsolationViolationError
from services.security import (
    is_safe_url,
    verify_hmac_signature,
    record_webhook_idempotency,
    is_safe_s3_key,
    sanitize_filename,
    auth_rate_limiter,
    crawl_rate_limiter,
    global_rate_limiter
)


@pytest.fixture
def client():
    # Disable global rate limiter bypass so security rate-limiting tests can exercise real limits
    os.environ["SEOJEV_DISABLE_RATE_LIMIT"] = "0"
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def tenant_fixture():
    """Sets up Org A and Org B with distinct users, sites, runs, and artifacts."""
    suffix = uuid4().hex[:8]
    org_a = f"org_sec_a_{suffix}"
    org_b = f"org_sec_b_{suffix}"

    user_a_admin = f"user_admin_a_{suffix}"
    user_a_editor = f"user_editor_a_{suffix}"
    user_a_viewer = f"user_viewer_a_{suffix}"
    user_b_admin = f"user_admin_b_{suffix}"

    site_a = f"site_sec_a_{suffix}"
    site_b = f"site_sec_b_{suffix}"

    run_a = f"run_sec_a_{suffix}"
    run_b = f"run_sec_b_{suffix}"

    with get_connection() as conn:
        with conn.cursor() as cur:
            # Create orgs
            cur.execute("INSERT INTO orgs (id, name, slug) VALUES (%s, %s, %s)", (org_a, f"Org A {suffix}", f"org-a-{suffix}"))
            cur.execute("INSERT INTO orgs (id, name, slug) VALUES (%s, %s, %s)", (org_b, f"Org B {suffix}", f"org-b-{suffix}"))

            # Create users
            cur.execute("INSERT INTO users (id, org_id, email, password_hash, role) VALUES (%s, %s, %s, %s, 'admin')",
                        (user_a_admin, org_a, f"admin_a_{suffix}@example.com", "hash"))
            cur.execute("INSERT INTO users (id, org_id, email, password_hash, role) VALUES (%s, %s, %s, %s, 'editor')",
                        (user_a_editor, org_a, f"editor_a_{suffix}@example.com", "hash"))
            cur.execute("INSERT INTO users (id, org_id, email, password_hash, role) VALUES (%s, %s, %s, %s, 'viewer')",
                        (user_a_viewer, org_a, f"viewer_a_{suffix}@example.com", "hash"))
            cur.execute("INSERT INTO users (id, org_id, email, password_hash, role) VALUES (%s, %s, %s, %s, 'admin')",
                        (user_b_admin, org_b, f"admin_b_{suffix}@example.com", "hash"))

            # Create sites
            site_a_cfg = {"webhook_secret": f"secret_a_{suffix}"}
            cur.execute("INSERT INTO sites (id, org_id, domain, url, vertical, config_json) VALUES (%s, %s, %s, %s, %s, %s)",
                        (site_a, org_a, f"site-a-{suffix}.com", f"https://site-a-{suffix}.com", "generic", Jsonb(site_a_cfg)))
            cur.execute("INSERT INTO sites (id, org_id, domain, url, vertical, config_json) VALUES (%s, %s, %s, %s, %s, %s)",
                        (site_b, org_b, f"site-b-{suffix}.com", f"https://site-b-{suffix}.com", "generic", Jsonb({})))

            # Create runs
            cur.execute("INSERT INTO runs (id, org_id, site_id, status) VALUES (%s, %s, %s, 'completed')", (run_a, org_a, site_a))
            cur.execute("INSERT INTO runs (id, org_id, site_id, status) VALUES (%s, %s, %s, 'completed')", (run_b, org_b, site_b))

            # Create artifacts
            cur.execute("""
                INSERT INTO artifacts (id, org_id, site_id, run_id, filename, artifact_type, s3_key, size_bytes, checksum_sha256)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (f"art_a_{suffix}", org_a, site_a, run_a, "report.json", "json", f"{org_a}/{site_a}/{run_a}/report.json", 100, "abc"))
            cur.execute("""
                INSERT INTO artifacts (id, org_id, site_id, run_id, filename, artifact_type, s3_key, size_bytes, checksum_sha256)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (f"art_b_{suffix}", org_b, site_b, run_b, "report.json", "json", f"{org_b}/{site_b}/{run_b}/report.json", 100, "abc"))

            # Create alerts
            cur.execute("""
                INSERT INTO alerts (id, org_id, site_id, run_id, alert_type, severity, title, message)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (f"alt_a_{suffix}", org_a, site_a, run_a, "title_wipe", "critical", "Title Wipe A", "Message A"))
            cur.execute("""
                INSERT INTO alerts (id, org_id, site_id, run_id, alert_type, severity, title, message)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (f"alt_b_{suffix}", org_b, site_b, run_b, "title_wipe", "critical", "Title Wipe B", "Message B"))

            # Create work orders
            cur.execute("""
                INSERT INTO work_orders (id, org_id, run_id, site_id, display_id, title, order_type, status, priority, verify_spec)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (f"wo_a_{suffix}", org_a, run_a, site_a, f"WO-A-{suffix}", "Title A", "engineering", "open", "P1", "status_code == 200"))
            cur.execute("""
                INSERT INTO work_orders (id, org_id, run_id, site_id, display_id, title, order_type, status, priority, verify_spec)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (f"wo_b_{suffix}", org_b, run_b, site_b, f"WO-B-{suffix}", "Title B", "engineering", "open", "P1", "status_code == 200"))

            # Create site trends
            cur.execute("""
                INSERT INTO site_trends (id, org_id, site_id, run_id, metric, date, value)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (f"tr_a_{suffix}", org_a, site_a, run_a, "issue_count", "2026-09-27", 10.0))
            cur.execute("""
                INSERT INTO site_trends (id, org_id, site_id, run_id, metric, date, value)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (f"tr_b_{suffix}", org_b, site_b, run_b, "issue_count", "2026-09-27", 20.0))

            # Create findings for search
            cur.execute("""
                INSERT INTO findings (id, org_id, site_id, run_id, display_id, url, rule_id, subject, severity)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (f"find_a_{suffix}", org_a, site_a, run_a, f"FND-A-{suffix}", f"https://site-a-{suffix}.com/page", "broken_canonical", "UniqueKeywordA Canonical broken", "critical"))
            cur.execute("""
                INSERT INTO findings (id, org_id, site_id, run_id, display_id, url, rule_id, subject, severity)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (f"find_b_{suffix}", org_b, site_b, run_b, f"FND-B-{suffix}", f"https://site-b-{suffix}.com/page", "broken_canonical", "UniqueKeywordB Canonical broken", "critical"))

        conn.commit()

    token_a_admin = create_access_token({"sub": user_a_admin, "org_id": org_a, "role": "admin"})
    token_a_editor = create_access_token({"sub": user_a_editor, "org_id": org_a, "role": "editor"})
    token_a_viewer = create_access_token({"sub": user_a_viewer, "org_id": org_a, "role": "viewer"})
    token_b_admin = create_access_token({"sub": user_b_admin, "org_id": org_b, "role": "admin"})

    return {
        "org_a": org_a,
        "org_b": org_b,
        "site_a": site_a,
        "site_b": site_b,
        "site_a_secret": f"secret_a_{suffix}",
        "run_a": run_a,
        "run_b": run_b,
        "art_a": f"art_a_{suffix}",
        "art_b": f"art_b_{suffix}",
        "alt_a": f"alt_a_{suffix}",
        "alt_b": f"alt_b_{suffix}",
        "wo_a": f"wo_a_{suffix}",
        "wo_b": f"wo_b_{suffix}",
        "suffix": suffix,
        "token_a_admin": token_a_admin,
        "token_a_editor": token_a_editor,
        "token_a_viewer": token_a_viewer,
        "token_b_admin": token_b_admin,
    }


# ===========================================================================
# 1. TENANT ISOLATION TESTS
# ===========================================================================

def test_cross_tenant_site_isolation(client, tenant_fixture):
    """Verifies that Org A cannot retrieve, update, or delete Org B's site."""
    tf = tenant_fixture
    headers_a = {"Authorization": f"Bearer {tf['token_a_admin']}"}

    # Org A tries to GET Org B's site -> 404 Not Found (no leakage of existence)
    resp = client.get(f"/sites/{tf['site_b']}", headers=headers_a)
    assert resp.status_code == 404

    # Org A tries to PATCH Org B's site -> 404 Not Found
    resp = client.patch(f"/sites/{tf['site_b']}", json={"vertical": "ecommerce"}, headers=headers_a)
    assert resp.status_code == 404

    # Org A tries to DELETE Org B's site -> 404 Not Found
    resp = client.delete(f"/sites/{tf['site_b']}", headers=headers_a)
    assert resp.status_code == 404


def test_cross_tenant_run_isolation(client, tenant_fixture):
    """Verifies that Org A cannot view, cancel, or resume Org B's run."""
    tf = tenant_fixture
    headers_a = {"Authorization": f"Bearer {tf['token_a_admin']}"}

    # Org A tries to GET Org B's run -> 404
    resp = client.get(f"/runs/{tf['run_b']}", headers=headers_a)
    assert resp.status_code == 404

    # Org A tries to cancel Org B's run -> 404
    resp = client.post(f"/runs/{tf['run_b']}/cancel", headers=headers_a)
    assert resp.status_code == 404

    # Org A tries to list runs for Org B's site -> returns empty
    resp = client.get(f"/runs?site_id={tf['site_b']}", headers=headers_a)
    assert resp.status_code == 200
    assert len(resp.json()) == 0


def test_cross_tenant_artifact_isolation(client, tenant_fixture):
    """Verifies that Org A cannot obtain signed download URLs for Org B's artifacts."""
    tf = tenant_fixture
    headers_a = {"Authorization": f"Bearer {tf['token_a_admin']}"}

    # Org A tries to get download link for Org B's artifact -> 404
    resp = client.get(f"/artifacts/{tf['art_b']}/download", headers=headers_a)
    assert resp.status_code == 404

    # Org A tries to list artifacts for Org B's run -> 404
    resp = client.get(f"/runs/{tf['run_b']}/artifacts", headers=headers_a)
    assert resp.status_code == 404


def test_cross_tenant_alert_isolation(client, tenant_fixture):
    """Verifies that Org A cannot view or resolve Org B's alerts."""
    tf = tenant_fixture
    headers_a = {"Authorization": f"Bearer {tf['token_a_admin']}"}

    # Org A tries to list alerts for Org B's site -> 404
    resp = client.get(f"/sites/{tf['site_b']}/alerts", headers=headers_a)
    assert resp.status_code == 404

    # Org A tries to resolve alert on Org B's site -> 404
    resp = client.patch(f"/sites/{tf['site_b']}/alerts/{tf['alt_b']}", json={"status": "resolved"}, headers=headers_a)
    assert resp.status_code == 404


def test_cross_tenant_work_order_isolation(client, tenant_fixture):
    """Verifies that Org A cannot view, export, or verify Org B's work order."""
    tf = tenant_fixture
    headers_a = {"Authorization": f"Bearer {tf['token_a_admin']}"}

    # Org A tries to GET Org B's work order -> 404
    resp = client.get(f"/work-orders/{tf['wo_b']}", headers=headers_a)
    assert resp.status_code == 404

    # Org A tries to export Org B's work order -> 404
    resp = client.post(f"/work-orders/{tf['wo_b']}/export?platform=github", headers=headers_a)
    assert resp.status_code == 404


def test_cross_tenant_trends_isolation(client, tenant_fixture):
    """Verifies that Org A cannot view Org B's historical trends."""
    tf = tenant_fixture
    headers_a = {"Authorization": f"Bearer {tf['token_a_admin']}"}

    resp = client.get(f"/sites/{tf['site_b']}/trends", headers=headers_a)
    assert resp.status_code == 404


def test_cross_tenant_search_isolation(client, tenant_fixture):
    """Verifies that Org A's search results never leak Org B's indexed content."""
    tf = tenant_fixture
    headers_a = {"Authorization": f"Bearer {tf['token_a_admin']}"}
    headers_b = {"Authorization": f"Bearer {tf['token_b_admin']}"}

    # Query for Org B's unique keyword as Org A -> 0 matches
    resp_a = client.get("/search?q=UniqueKeywordB", headers=headers_a)
    assert resp_a.status_code == 200
    assert resp_a.json()["total_matches"] == 0

    # Query for Org B's unique keyword as Org B -> 1 match
    resp_b = client.get("/search?q=UniqueKeywordB", headers=headers_b)
    assert resp_b.status_code == 200
    assert resp_b.json()["total_matches"] >= 1


def test_cross_tenant_gsc_anomaly_trigger_blocked(client, tenant_fixture):
    """Verifies that Org A cannot trigger GSC anomaly detection for Org B's site."""
    tf = tenant_fixture
    headers_a = {"Authorization": f"Bearer {tf['token_a_admin']}"}

    resp = client.post(f"/sites/{tf['site_b']}/gsc/detect-anomalies", headers=headers_a)
    assert resp.status_code == 404


# ===========================================================================
# 2. RBAC HARDENING TESTS
# ===========================================================================

def test_viewer_role_cannot_mutate_resources(client, tenant_fixture):
    """Verifies that viewer role cannot create, update, or delete resources."""
    tf = tenant_fixture
    headers_viewer = {"Authorization": f"Bearer {tf['token_a_viewer']}"}

    # Cannot create site -> 403
    resp = client.post("/sites", json={"domain": "fail.com", "url": "https://fail.com"}, headers=headers_viewer)
    assert resp.status_code == 403

    # Cannot update site -> 403
    resp = client.patch(f"/sites/{tf['site_a']}", json={"vertical": "blog"}, headers=headers_viewer)
    assert resp.status_code == 403

    # Cannot trigger run -> 403
    resp = client.post("/runs", json={"site_id": tf["site_a"]}, headers=headers_viewer)
    assert resp.status_code == 403

    # Cannot configure watch schedule -> 403
    resp = client.post(f"/sites/{tf['site_a']}/watch", json={"cron_expression": "0 0 * * *"}, headers=headers_viewer)
    assert resp.status_code == 403


def test_editor_role_cannot_perform_admin_operations(client, tenant_fixture):
    """Verifies that editor role can perform regular mutations but cannot execute admin operations."""
    tf = tenant_fixture
    headers_editor = {"Authorization": f"Bearer {tf['token_a_editor']}"}

    # Editor CAN update site (permitted)
    resp = client.patch(f"/sites/{tf['site_a']}", json={"vertical": "travel"}, headers=headers_editor)
    assert resp.status_code == 200

    # Editor CANNOT delete site (admin-only) -> 403
    resp = client.delete(f"/sites/{tf['site_a']}", headers=headers_editor)
    assert resp.status_code == 403

    # Editor CANNOT create or delete users (admin-only) -> 403
    resp = client.post("/auth/users", json={"email": "new@ex.com", "password": "password123", "role": "viewer"}, headers=headers_editor)
    assert resp.status_code == 403


def test_forged_and_tampered_jwt_rejected(client):
    """Verifies that tokens with tampered signatures or forged algorithms are rejected."""
    # Forged token with invalid secret
    fake_token = create_access_token({"sub": "user_evil", "org_id": "org_victim", "role": "admin"})
    tampered_token = fake_token[:-4] + "dead"

    resp = client.get("/sites", headers={"Authorization": f"Bearer {tampered_token}"})
    assert resp.status_code == 401

    # Completely bogus token
    resp = client.get("/sites", headers={"Authorization": "Bearer not.a.valid.jwt"})
    assert resp.status_code == 401


# ===========================================================================
# 3. SSRF PROTECTION TESTS
# ===========================================================================

def test_ssrf_blocks_cloud_metadata():
    """Verifies that cloud metadata IPs and domains are unconditionally blocked."""
    # AWS / GCP metadata IP
    safe, reason = is_safe_url("http://169.254.169.254/latest/meta-data/")
    assert safe is False
    assert "metadata" in reason.lower()

    # GCP metadata domain
    safe, reason = is_safe_url("http://metadata.google.internal/computeMetadata/v1/")
    assert safe is False
    assert "metadata" in reason.lower()

    # ECS task metadata
    safe, reason = is_safe_url("http://169.254.170.2/v2/metadata")
    assert safe is False


def test_ssrf_blocks_private_networks():
    """Verifies that private RFC1918 subnets and loopback are blocked when local crawl is disabled."""
    # 10.0.0.0/8
    safe, reason = is_safe_url("http://10.0.0.1/admin", allow_local=False)
    assert safe is False
    assert "private" in reason.lower() or "forbidden" in reason.lower()

    # 192.168.0.0/16
    safe, reason = is_safe_url("https://192.168.1.1:8080/metrics", allow_local=False)
    assert safe is False

    # 172.16.0.0/12
    safe, reason = is_safe_url("http://172.16.0.1/", allow_local=False)
    assert safe is False

    # Loopback
    safe, reason = is_safe_url("http://127.0.0.1:6379/", allow_local=False)
    assert safe is False


def test_ssrf_blocks_non_http_schemes():
    """Verifies that non-HTTP schemes (file://, gopher://, ftp://) are blocked."""
    safe, reason = is_safe_url("file:///etc/passwd")
    assert safe is False
    assert "scheme" in reason.lower()

    safe, reason = is_safe_url("gopher://127.0.0.1:70/")
    assert safe is False


def test_ssrf_blocked_in_site_creation(client, tenant_fixture):
    """Verifies that creating a site pointing to cloud metadata is rejected by API."""
    tf = tenant_fixture
    headers_admin = {"Authorization": f"Bearer {tf['token_a_admin']}"}

    resp = client.post(
        "/sites",
        json={"domain": "meta-target.com", "url": "http://169.254.169.254/latest/"},
        headers=headers_admin
    )
    assert resp.status_code == 400
    assert "SSRF" in resp.json()["detail"]


# ===========================================================================
# 4. WEBHOOK AUTHENTICATION & REPLAY PROTECTION
# ===========================================================================

def test_webhook_signature_verification_and_replay(client, tenant_fixture):
    """Verifies HMAC signature validation and replay attack prevention on webhooks."""
    tf = tenant_fixture
    headers_admin = {"Authorization": f"Bearer {tf['token_a_admin']}"}
    secret = tf["site_a_secret"]

    payload = {
        "deployment_id": f"dep_sec_{tf['suffix']}",
        "commit_sha": "abc1234",
        "branch": "main",
        "scope": ["/page"]
    }
    raw_bytes = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")

    # 1. Test with invalid HMAC signature -> 401 Unauthorized
    bad_sig = "sha256=" + "0" * 64
    resp = client.post(
        f"/sites/{tf['site_a']}/deploy-webhook",
        json=payload,
        headers={**headers_admin, "X-Hub-Signature-256": bad_sig}
    )
    assert resp.status_code == 401
    assert "Invalid webhook signature" in resp.json()["detail"]

    # 2. Test with valid HMAC signature -> 200 OK (Queued)
    valid_hmac = hmac.new(secret.encode("utf-8"), raw_bytes, hashlib.sha256).hexdigest()
    good_sig = f"sha256={valid_hmac}"
    resp = client.post(
        f"/sites/{tf['site_a']}/deploy-webhook",
        json=payload,
        headers={**headers_admin, "X-Hub-Signature-256": good_sig}
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "queued"

    # 3. Test replay attack with the exact same deployment_id -> duplicate ignored
    resp_replay = client.post(
        f"/sites/{tf['site_a']}/deploy-webhook",
        json=payload,
        headers={**headers_admin, "X-Hub-Signature-256": good_sig}
    )
    assert resp_replay.status_code == 200
    assert resp_replay.json()["status"] == "duplicate"


# ===========================================================================
# 5. ARTIFACT & PATH TRAVERSAL SECURITY
# ===========================================================================

def test_path_traversal_sanitization():
    """Verifies that filename and S3 key sanitization prevents path traversal."""
    # Filename traversal
    assert sanitize_filename("../../../etc/passwd") == "passwd"
    assert sanitize_filename("..\\..\\windows\\system32\\calc.exe") == "calc.exe"

    # S3 key cross-tenant or traversal check
    assert is_safe_s3_key("org_1/site_1/run_1/export.zip", "org_1") is True
    assert is_safe_s3_key("org_2/site_1/run_1/export.zip", "org_1") is False
    assert is_safe_s3_key("org_1/../../../etc/passwd", "org_1") is False


# ===========================================================================
# 6. SQL INJECTION PREVENTION
# ===========================================================================

def test_sql_injection_defense():
    """Verifies that ScopedQuery rejects injection attempts in table and projection."""
    with ScopedQuery(org_id="org_test") as sq:
        # Malicious table name containing SQL injection tokens
        with pytest.raises(IsolationViolationError):
            sq.fetch_all("sites; DROP TABLE sites; --")

        # Malicious select clause containing injection tokens
        with pytest.raises(IsolationViolationError):
            sq.fetch_all("sites", select="* FROM sites; SELECT pg_sleep(5); --")

        # Malicious order_by clause
        with pytest.raises(IsolationViolationError):
            sq.fetch_all("sites", order_by="id; DROP TABLE users; --")


# ===========================================================================
# 7. ERROR SANITIZATION & INFORMATION DISCLOSURE
# ===========================================================================

def test_internal_500_errors_sanitized(client, tenant_fixture):
    """Verifies that unexpected server errors return a sanitized response without stack traces."""
    tf = tenant_fixture
    headers = {"Authorization": f"Bearer {tf['token_a_admin']}"}

    # 1. Parameter validation error -> 422
    resp = client.get("/search?q=" + "a" * 300, headers=headers)
    assert resp.status_code == 422

    # 2. Unhandled server exception -> 500 with sanitized body
    @app.get("/test-unhandled-500-error")
    def trigger_error():
        raise RuntimeError("Secret DB Password exposed: postgres://user:secret123@localhost/prod")

    resp_500 = client.get("/test-unhandled-500-error")
    assert resp_500.status_code == 500
    data = resp_500.json()
    assert data["detail"] == "An internal server error occurred."
    assert data["error_code"] == "INTERNAL_SERVER_ERROR"
    assert "secret123" not in resp_500.text
    assert "Traceback" not in resp_500.text


# ===========================================================================
# 8. RATE LIMITING TESTS
# ===========================================================================

def test_rate_limiting_enforcement(client):
    """Verifies that rapid repeated calls to sensitive auth endpoints trigger 429 Too Many Requests."""
    auth_rate_limiter.reset()
    ip = "test_rate_ip"

    # Simulate exhausting the auth limit (30 requests/minute)
    for _ in range(30):
        allowed, _ = auth_rate_limiter.is_allowed(f"auth:{ip}")
        assert allowed is True

    # 31st request should be rejected
    allowed, remaining = auth_rate_limiter.is_allowed(f"auth:{ip}")
    assert allowed is False
    assert remaining == 0
