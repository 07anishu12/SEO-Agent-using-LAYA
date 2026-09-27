"""
SEOJEV Phase 2: Stage 10h Role-Based Permissions (RBAC) Test Suite.

Validates Section 6.11:
1. Viewer:
   - Allowed reads: GET /sites, GET /runs, GET /search.
   - Denied mutations: POST /sites, POST /runs, POST /watch, POST /export, POST /verify -> 403 Forbidden.
2. Editor:
   - Allowed operational mutations: POST /sites, PATCH /sites, POST /watch, POST /verify.
   - Denied administrative operations: DELETE /sites, POST /auth/users, PATCH /auth/users/role -> 403 Forbidden.
3. Admin:
   - Allowed administrative operations: POST /auth/users, PATCH /auth/users/role, DELETE /sites, DELETE /auth/users.
4. Privilege Escalation Prevention:
   - Tampering with JWT claims or signature is rejected with 401 Unauthorized.
   - Client request payloads cannot override server-side JWT authorization.
"""
import json
import os
import socket
import subprocess
import sys
import time
import urllib.request
import jwt
from typing import Dict, Any
import httpx
import pytest
from fastapi.testclient import TestClient
from playwright.async_api import async_playwright

from api.main import app
from database.connection import get_connection
from database.migrator import PostgresMigrator
from api.auth import create_access_token
from api.config import JWT_SECRET, JWT_ALGORITHM


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


def create_role_token(org_id: str, role: str, email: str = "user@example.com", user_id: str = None) -> str:
    uid = user_id or f"usr_{role}_{org_id}"
    return create_access_token({"sub": uid, "email": email, "org_id": org_id, "role": role})


def test_viewer_role_permissions():
    """
    Viewer should be able to read sites, runs, search, but strictly denied any mutations (403).
    """
    client = TestClient(app)
    suffix = os.urandom(4).hex()
    org_id = f"org_v_{suffix}"
    site_id = f"site_v_{suffix}"
    run_id = f"run_v_{suffix}"
    wo_id = f"wo_v_{suffix}"

    # Setup DB
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO orgs (id, name, slug) VALUES (%s, %s, %s)", (org_id, "Viewer Org", f"vorg-{suffix}"))
            cur.execute("INSERT INTO sites (id, org_id, domain, url, vertical) VALUES (%s, %s, 'v.test', 'https://v.test', 'auto')", (site_id, org_id))
            cur.execute("INSERT INTO runs (id, org_id, site_id, status, progress_pct) VALUES (%s, %s, %s, 'completed', 100.0)", (run_id, org_id, site_id))
            cur.execute(
                """
                INSERT INTO work_orders (id, org_id, run_id, site_id, display_id, title, order_type, status, verify_spec)
                VALUES (%s, %s, %s, %s, 'WO-V', 'Test Work Order', 'engineering', 'Open', 'status_code == 200')
                """,
                (wo_id, org_id, run_id, site_id)
            )
        conn.commit()

    token = create_role_token(org_id, role="viewer")
    auth_header = {"Authorization": f"Bearer {token}"}

    # 1. Allowed Reads
    resp_sites = client.get("/sites", headers=auth_header)
    assert resp_sites.status_code == 200

    resp_site = client.get(f"/sites/{site_id}", headers=auth_header)
    assert resp_site.status_code == 200

    resp_runs = client.get(f"/runs?site_id={site_id}", headers=auth_header)
    assert resp_runs.status_code == 200

    resp_search = client.get("/search?q=test", headers=auth_header)
    assert resp_search.status_code == 200

    # 2. Denied Mutations (Must return 403 Forbidden)
    resp_create_site = client.post("/sites", json={"url": "https://forbidden.test"}, headers=auth_header)
    assert resp_create_site.status_code == 403
    assert "Operation not permitted" in resp_create_site.json()["detail"]

    resp_update_site = client.patch(f"/sites/{site_id}", json={"vertical": "ecommerce"}, headers=auth_header)
    assert resp_update_site.status_code == 403

    resp_delete_site = client.delete(f"/sites/{site_id}", headers=auth_header)
    assert resp_delete_site.status_code == 403

    resp_create_run = client.post("/runs", json={"site_id": site_id}, headers=auth_header)
    assert resp_create_run.status_code == 403

    resp_watch = client.post(f"/sites/{site_id}/watch", json={"cron_expression": "0 0 * * *"}, headers=auth_header)
    assert resp_watch.status_code == 403

    resp_export = client.post(f"/work-orders/{wo_id}/export?platform=github", headers=auth_header)
    assert resp_export.status_code == 403

    resp_verify = client.post(f"/work-orders/{wo_id}/verify", json={"live_fetch": False}, headers=auth_header)
    assert resp_verify.status_code == 403

    resp_admin_user = client.post("/auth/users", json={"email": "new@test.com", "password": "pass", "role": "viewer"}, headers=auth_header)
    assert resp_admin_user.status_code == 403


def test_editor_role_permissions():
    """
    Editor can perform operational actions (create run, configure watch, export/verify tickets),
    but cannot perform administrative actions (delete site, manage users).
    """
    client = TestClient(app)
    suffix = os.urandom(4).hex()
    org_id = f"org_ed_{suffix}"
    site_id = f"site_ed_{suffix}"
    run_id = f"run_ed_{suffix}"
    wo_id = f"wo_ed_{suffix}"

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO orgs (id, name, slug) VALUES (%s, %s, %s)", (org_id, "Editor Org", f"edorg-{suffix}"))
            cur.execute("INSERT INTO sites (id, org_id, domain, url, vertical) VALUES (%s, %s, 'editor.test', 'https://editor.test', 'auto')", (site_id, org_id))
            cur.execute("INSERT INTO runs (id, org_id, site_id, status, progress_pct) VALUES (%s, %s, %s, 'completed', 100.0)", (run_id, org_id, site_id))
            cur.execute(
                """
                INSERT INTO work_orders (id, org_id, run_id, site_id, display_id, title, order_type, status, verify_spec)
                VALUES (%s, %s, %s, %s, 'WO-ED', 'Editor WO', 'engineering', 'Open', 'status_code == 200')
                """,
                (wo_id, org_id, run_id, site_id)
            )
        conn.commit()

    token = create_role_token(org_id, role="editor")
    auth_header = {"Authorization": f"Bearer {token}"}

    # 1. Allowed Operational Actions
    resp_create_site = client.post("/sites", json={"url": "https://new-by-editor.test"}, headers=auth_header)
    assert resp_create_site.status_code == 201

    resp_update_site = client.patch(f"/sites/{site_id}", json={"vertical": "ecommerce"}, headers=auth_header)
    assert resp_update_site.status_code == 200

    resp_watch = client.post(f"/sites/{site_id}/watch", json={"cron_expression": "0 12 * * *"}, headers=auth_header)
    assert resp_watch.status_code == 200

    resp_export = client.post(f"/work-orders/{wo_id}/export?platform=github", headers=auth_header)
    assert resp_export.status_code == 200

    resp_verify = client.post(f"/work-orders/{wo_id}/verify", json={"live_fetch": False, "html_content": "<html></html>"}, headers=auth_header)
    assert resp_verify.status_code == 200

    # 2. Denied Administrative Operations (403 Forbidden)
    resp_del_site = client.delete(f"/sites/{site_id}", headers=auth_header)
    assert resp_del_site.status_code == 403

    resp_admin_user = client.post("/auth/users", json={"email": "sub@test.com", "password": "password123", "role": "viewer"}, headers=auth_header)
    assert resp_admin_user.status_code == 403

    resp_update_role = client.patch("/auth/users/usr_dummy/role", json={"role": "admin"}, headers=auth_header)
    assert resp_update_role.status_code == 403

    resp_delete_user = client.delete("/auth/users/usr_dummy", headers=auth_header)
    assert resp_delete_user.status_code == 403


def test_admin_role_and_user_management():
    """
    Admin can perform administrative operations including inviting users, updating roles, and deleting resources.
    """
    client = TestClient(app)
    suffix = os.urandom(4).hex()
    org_id = f"org_adm_{suffix}"
    site_id = f"site_adm_{suffix}"
    admin_uid = f"usr_admin_{suffix}"

    token = create_role_token(org_id, role="admin", user_id=admin_uid)
    auth_header = {"Authorization": f"Bearer {token}"}

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO orgs (id, name, slug) VALUES (%s, %s, %s)", (org_id, "Admin Org", f"admorg-{suffix}"))
            cur.execute("INSERT INTO sites (id, org_id, domain, url, vertical) VALUES (%s, %s, 'admin.test', 'https://admin.test', 'auto')", (site_id, org_id))
            cur.execute("INSERT INTO users (id, org_id, email, password_hash, role) VALUES (%s, %s, %s, 'hash', 'admin')", (admin_uid, org_id, f"admin_{suffix}@test.com"))
        conn.commit()

    # 1. Admin creates a new viewer user
    new_email = f"invited_{suffix}@test.com"
    resp_invite = client.post(
        "/auth/users",
        json={"email": new_email, "password": "securepassword123", "role": "viewer"},
        headers=auth_header
    )
    assert resp_invite.status_code == 201
    invited_user = resp_invite.json()
    assert invited_user["email"] == new_email
    assert invited_user["role"] == "viewer"
    invited_id = invited_user["id"]

    # 2. Admin lists users
    resp_list = client.get("/auth/users", headers=auth_header)
    assert resp_list.status_code == 200
    users = resp_list.json()
    assert any(u["id"] == invited_id for u in users)

    # 3. Admin promotes user from viewer to editor
    resp_promote = client.patch(
        f"/auth/users/{invited_id}/role",
        json={"role": "editor"},
        headers=auth_header
    )
    assert resp_promote.status_code == 200
    assert resp_promote.json()["role"] == "editor"

    # 4. Admin deletes site
    resp_del_site = client.delete(f"/sites/{site_id}", headers=auth_header)
    assert resp_del_site.status_code == 200

    # 5. Admin deletes invited user
    resp_del_user = client.delete(f"/auth/users/{invited_id}", headers=auth_header)
    assert resp_del_user.status_code == 204


def test_privilege_escalation_prevention():
    """
    Confirms cryptographic JWT integrity:
    1. Altering a viewer JWT's payload to role='admin' without a valid signature fails with 401.
    2. Passing an invalid signature fails with 401.
    """
    client = TestClient(app)
    suffix = os.urandom(4).hex()
    org_id = f"org_esc_{suffix}"

    # Generate legitimate viewer token
    viewer_token = create_role_token(org_id, role="viewer")

    # Decode and tamper payload to 'admin' signed with a fake secret
    fake_token = jwt.encode(
        {"sub": f"usr_attacker_{suffix}", "email": "attacker@evil.com", "org_id": org_id, "role": "admin"},
        "wrong-fake-secret-key-32-bytes-long",
        algorithm=JWT_ALGORITHM
    )

    # Attempt administrative action with fake token -> MUST BE REJECTED 401
    resp_tamper = client.post("/auth/users", json={"email": "fake@evil.com", "password": "pass", "role": "admin"}, headers={"Authorization": f"Bearer {fake_token}"})
    assert resp_tamper.status_code == 401
    assert "credentials" in resp_tamper.json()["detail"].lower()

    # Attempt with none algorithm / garbage token -> MUST BE REJECTED 401
    resp_garbage = client.post("/auth/users", json={"email": "fake@evil.com", "password": "pass"}, headers={"Authorization": "Bearer not.a.real.token"})
    assert resp_garbage.status_code == 401


@pytest.mark.asyncio
async def test_ui_rbac_role_indicators_and_action_hiding(frontend_server, api_server):
    """
    Playwright UI Test:
    Confirms frontend renders the authenticated user's role and suppresses privileged mutation actions for Viewer:
    1. Viewer: Navbar displays 'Viewer (Read-Only)' and badge 'VIEWER', and does NOT render the 'New Run' button.
    2. Editor: Navbar displays badge 'EDITOR' and renders the 'New Run' button.
    3. Admin: Navbar displays badge 'ADMIN' and renders the 'New Run' button.
    """
    suffix = os.urandom(4).hex()
    org_id = f"org_ui_rbac_{suffix}"

    viewer_token = create_role_token(org_id, role="viewer", email=f"viewer_{suffix}@example.com", user_id=f"usr_v_{suffix}")
    viewer_user = {"id": f"usr_v_{suffix}", "email": f"viewer_{suffix}@example.com", "org_id": org_id, "role": "viewer"}

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
            [viewer_token, json.dumps(viewer_user), api_server],
        )

        await page.goto(f"{frontend_server}/sites")
        await page.wait_for_selector("text=Viewer (Read-Only)", timeout=8000)
        assert await page.is_visible("span:has-text('VIEWER')")
        # Ensure New Run link is NOT visible for viewer
        assert not await page.is_visible("a[href='/runs/new']")

        # 2. Editor check
        editor_token = create_role_token(org_id, role="editor", email=f"editor_{suffix}@example.com", user_id=f"usr_ed_{suffix}")
        editor_user = {"id": f"usr_ed_{suffix}", "email": f"editor_{suffix}@example.com", "org_id": org_id, "role": "editor"}
        await page.evaluate(
            """([token, user]) => {
                localStorage.setItem('seojev_access_token', token);
                localStorage.setItem('seojev_user', user);
            }""",
            [editor_token, json.dumps(editor_user)],
        )
        await page.goto(f"{frontend_server}/sites")
        await page.wait_for_selector("a[href='/runs/new']", timeout=8000)
        assert await page.is_visible("span:has-text('EDITOR')")
        assert not await page.is_visible("text=Viewer (Read-Only)")

        # 3. Admin check
        admin_token = create_role_token(org_id, role="admin", email=f"admin_{suffix}@example.com", user_id=f"usr_ad_{suffix}")
        admin_user = {"id": f"usr_ad_{suffix}", "email": f"admin_{suffix}@example.com", "org_id": org_id, "role": "admin"}
        await page.evaluate(
            """([token, user]) => {
                localStorage.setItem('seojev_access_token', token);
                localStorage.setItem('seojev_user', user);
            }""",
            [admin_token, json.dumps(admin_user)],
        )
        await page.goto(f"{frontend_server}/sites")
        await page.wait_for_selector("a[href='/runs/new']", timeout=8000)
        assert await page.is_visible("span:has-text('ADMIN')")

        await browser.close()

