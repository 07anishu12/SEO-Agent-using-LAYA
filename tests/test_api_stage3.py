"""
SEOJEV Phase 2: Stage 3 FastAPI API Test Suite.
Tests:
1. Auth test: register, login, receive a valid JWT, reject invalid credentials, create API key.
2. Cross-org isolation test at API level: org A cannot GET org B's site or run (expects 404, not 403).
3. End-to-end test: register, create site (Stage-1 baseline site), POST /runs (synchronous),
   GET /runs/{id} and confirm counts match Stage 2 ETL / Phase 2 Baseline.
"""
import os
import pytest
from fastapi.testclient import TestClient

from api.main import app
from database.migrator import PostgresMigrator
from lab.server import SyntheticSiteServer


TEST_DB_NAME = "seojev_test"
TEST_DB_URL = f"postgresql:///{TEST_DB_NAME}"


@pytest.fixture(scope="session", autouse=True)
def prepare_test_db():
    migrator = PostgresMigrator(db_url=TEST_DB_URL)
    migrator.run_migrations()
    yield


@pytest.fixture
def client():
    return TestClient(app)


def test_auth_flow_and_api_keys(client):
    """
    Auth test: register, login, receive a valid JWT, reject invalid credentials,
    and generate/use API keys.
    """
    unique_suffix = os.urandom(4).hex()
    email = f"user_{unique_suffix}@example.com"
    password = "securePassword123!"

    # 1. Register new user
    reg_res = client.post(
        "/auth/register",
        json={"email": email, "password": password, "org_name": f"Org {unique_suffix}"}
    )
    assert reg_res.status_code == 201, reg_res.text
    reg_data = reg_res.json()
    assert "access_token" in reg_data
    assert reg_data["user"]["email"] == email
    token = reg_data["access_token"]
    org_id = reg_data["user"]["org_id"]
    assert org_id

    # 2. Reject duplicate email registration
    dup_res = client.post(
        "/auth/register",
        json={"email": email, "password": password}
    )
    assert dup_res.status_code == 400
    assert "already registered" in dup_res.json()["detail"].lower()

    # 3. Successful login
    login_res = client.post(
        "/auth/login",
        json={"email": email, "password": password}
    )
    assert login_res.status_code == 200
    login_token = login_res.json()["access_token"]
    assert login_token

    # 4. Reject invalid login credentials
    bad_login = client.post(
        "/auth/login",
        json={"email": email, "password": "wrong_password"}
    )
    assert bad_login.status_code == 401

    # 5. Access protected route with Bearer token
    headers = {"Authorization": f"Bearer {token}"}
    sites_res = client.get("/sites", headers=headers)
    assert sites_res.status_code == 200
    assert sites_res.json() == []

    # 6. Generate API key
    key_res = client.post(
        "/auth/api-keys",
        headers=headers,
        json={"name": "CI Runner Key"}
    )
    assert key_res.status_code == 201
    key_data = key_res.json()
    api_key = key_data["api_key"]
    assert api_key.startswith("sjev_")

    # 7. Access protected route using X-API-Key
    api_key_headers = {"X-API-Key": api_key}
    ak_sites_res = client.get("/sites", headers=api_key_headers)
    assert ak_sites_res.status_code == 200

    # 8. Reject invalid/missing auth
    unauth_res = client.get("/sites")
    assert unauth_res.status_code == 401

    fake_header = {"Authorization": "Bearer invalid.jwt.token"}
    bad_jwt_res = client.get("/sites", headers=fake_header)
    assert bad_jwt_res.status_code == 401


def test_cross_org_isolation_api_level(client):
    """
    Cross-org isolation test at the API level:
    Org A cannot GET, PATCH, or DELETE Org B's site or run by ID.
    Must return 404 (not 403) to prevent leaking existence.
    """
    suffix_a = os.urandom(4).hex()
    suffix_b = os.urandom(4).hex()

    # Register Org A user
    res_a = client.post(
        "/auth/register",
        json={"email": f"alice_{suffix_a}@org-a.com", "password": "Password123!"}
    )
    token_a = res_a.json()["access_token"]
    headers_a = {"Authorization": f"Bearer {token_a}"}

    # Register Org B user
    res_b = client.post(
        "/auth/register",
        json={"email": f"bob_{suffix_b}@org-b.com", "password": "Password123!"}
    )
    token_b = res_b.json()["access_token"]
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # Org A creates Site A
    site_res_a = client.post(
        "/sites",
        headers=headers_a,
        json={"url": "https://alice-site.example.com", "vertical": "auto"}
    )
    assert site_res_a.status_code == 201
    site_a_id = site_res_a.json()["id"]

    # Org B attempts to GET Org A's site -> MUST return 404 (not 403)
    get_res = client.get(f"/sites/{site_a_id}", headers=headers_b)
    assert get_res.status_code == 404, f"Expected 404, got {get_res.status_code}"
    assert get_res.json()["detail"] == "Site not found"

    # Org B attempts to PATCH Org A's site -> MUST return 404
    patch_res = client.patch(
        f"/sites/{site_a_id}",
        headers=headers_b,
        json={"vertical": "malicious_override"}
    )
    assert patch_res.status_code == 404

    # Org B attempts to DELETE Org A's site -> MUST return 404
    delete_res = client.delete(f"/sites/{site_a_id}", headers=headers_b)
    assert delete_res.status_code == 404

    # Org B listing sites shows 0 sites
    list_b = client.get("/sites", headers=headers_b)
    assert list_b.status_code == 200
    assert len(list_b.json()) == 0

    # Org B attempts to GET non-existent/cross-org run -> MUST return 404
    run_res = client.get("/runs/crawl_non_existent_or_org_a", headers=headers_b)
    assert run_res.status_code == 404


def test_e2e_site_run_pipeline_and_etl(client):
    """
    End-to-end test: Register user, create site (Stage-1 baseline site),
    POST /runs (synchronous execution + ETL), wait for response,
    then GET /runs/{id} and assert returned metrics match Stage 2 ETL & Phase 2 Baseline.
    """
    port = 8925
    server = SyntheticSiteServer(port=port)
    server.start()

    suffix = os.urandom(4).hex()
    email = f"e2e_{suffix}@test.com"
    crawl_id = f"crawl_e2e_api_{suffix}"

    try:
        # 1. Register User
        reg = client.post(
            "/auth/register",
            json={"email": email, "password": "Password123!", "org_name": "E2E Testing Org"}
        )
        assert reg.status_code == 201
        token = reg.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 2. Create Site
        site_res = client.post(
            "/sites",
            headers=headers,
            json={"url": f"http://127.0.0.1:{port}/", "vertical": "automotive"}
        )
        assert site_res.status_code == 201
        site_id = site_res.json()["id"]

        # 3. Synchronous POST /runs
        run_payload = {
            "site_id": site_id,
            "crawl_id": crawl_id,
            "max_pages": 50,
            "concurrency": 2,
            "fresh": True,
            "sync": True
        }
        run_res = client.post("/runs", headers=headers, json=run_payload)
        assert run_res.status_code == 201, run_res.text
        run_data = run_res.json()

        assert run_data["id"] == crawl_id
        assert run_data["status"] == "completed"
        assert run_data["progress_pct"] == 100.0
        assert run_data["urls_crawled"] >= 12
        assert run_data["total_issues"] >= 40

        # Verify ETL counts in run response
        counts = run_data["counts"]
        assert counts["templates"] == 6
        assert counts["findings"] == 48
        assert counts["opportunities"] == 48
        assert counts["work_orders"] == 48

        # 4. GET /runs/{id}
        get_run_res = client.get(f"/runs/{crawl_id}", headers=headers)
        assert get_run_res.status_code == 200
        detail = get_run_res.json()
        assert detail["id"] == crawl_id
        assert detail["status"] == "completed"
        assert detail["counts"]["findings"] == 48
        assert detail["counts"]["opportunities"] == 48
        assert detail["counts"]["work_orders"] == 48
        assert detail["counts"]["templates"] == 6

        # 5. GET /runs
        list_runs = client.get(f"/runs?site_id={site_id}", headers=headers)
        assert list_runs.status_code == 200
        runs_list = list_runs.json()
        assert len(runs_list) >= 1
        assert runs_list[0]["id"] == crawl_id

    finally:
        server.stop()
        # Clean up scratch test db and reports if created
        if os.path.exists(f"data/{crawl_id}.db"):
            try:
                os.remove(f"data/{crawl_id}.db")
            except Exception:
                pass
