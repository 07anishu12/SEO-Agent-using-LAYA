"""
SEOJEV Phase 2: Stage 5 Object Storage (S3 / MinIO) Test Suite.
Tests:
1. Upload test: after a completed run, assert every expected artifact type
   (DOCX, CSVs, HTML explorer, ticket JSON/CSVs) exists in storage and database ledger.
2. Signed URL test: fetch a signed URL and confirm the downloaded file's hash matches
   the original file the engine wrote to disk (byte-for-byte integrity).
3. Expiry test: confirm a signed URL stops working after its expiry window (HTTP 403 Request has expired).
4. export.zip test: download the bundle and confirm every individual artifact is present inside, uncorrupted.
5. Cross-tenant isolation test: Org B cannot list or download Org A's artifacts (HTTP 404).
"""
import hashlib
import io
import json
import os
import time
import zipfile
import httpx
import pytest
from fastapi.testclient import TestClient

from api.config import S3_BUCKET, S3_ENDPOINT_URL
from api.main import app
from database.connection import get_connection
from database.migrator import PostgresMigrator
from lab.server import SyntheticSiteServer
from services.object_store import get_storage_service, compute_sha256


TEST_DB_NAME = "seojev_test"
TEST_DB_URL = f"postgresql:///{TEST_DB_NAME}"


@pytest.fixture(scope="session", autouse=True)
def prepare_test_db():
    migrator = PostgresMigrator(db_url=TEST_DB_URL)
    migrator.run_migrations()
    storage = get_storage_service()
    storage.ensure_bucket_exists()
    yield


@pytest.fixture
def client():
    os.environ["ENABLE_WORKER"] = "false"
    return TestClient(app)


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


@pytest.fixture(scope="module")
def completed_run_data():
    """Module-level fixture running one crawl to produce artifacts for the tests."""
    port = 8951
    server = SyntheticSiteServer(port=port)
    server.start()

    client = TestClient(app)
    headers, org_id, site_id, suffix = _register_and_create_site(client, "s5_run", port)
    crawl_id = f"crawl_s5_{suffix}"

    try:
        # Run synchronously to ensure completion and upload
        run_payload = {
            "site_id": site_id,
            "crawl_id": crawl_id,
            "max_pages": 50,
            "concurrency": 2,
            "fresh": True,
            "sync": True
        }
        res = client.post("/runs", headers=headers, json=run_payload)
        assert res.status_code == 201, res.text

        # Yield context for tests
        yield {
            "client": client,
            "headers": headers,
            "org_id": org_id,
            "site_id": site_id,
            "crawl_id": crawl_id
        }
    finally:
        server.stop()
        if os.path.exists(f"data/{crawl_id}.db"):
            try:
                os.remove(f"data/{crawl_id}.db")
            except Exception:
                pass


def test_upload_artifacts_completeness(completed_run_data):
    """
    Upload test: after a completed run, assert every expected artifact type
    (DOCX, CSVs, HTML explorer, ticket JSON/CSVs) exists in storage and database ledger.
    """
    client = completed_run_data["client"]
    headers = completed_run_data["headers"]
    crawl_id = completed_run_data["crawl_id"]
    org_id = completed_run_data["org_id"]

    # 1. Fetch artifacts via API
    res = client.get(f"/runs/{crawl_id}/artifacts", headers=headers)
    assert res.status_code == 200, res.text
    artifacts = res.json()
    assert len(artifacts) > 0, "No artifacts returned for run"

    types_found = {a["artifact_type"] for a in artifacts}
    assert "docx" in types_found, f"Missing docx artifacts: {types_found}"
    assert "csv" in types_found, f"Missing csv artifacts: {types_found}"
    assert "html" in types_found, f"Missing html artifacts: {types_found}"
    assert "json" in types_found, f"Missing json artifacts: {types_found}"

    # 2. Assert specific key deliverables exist
    filenames = {a["filename"] for a in artifacts}
    assert any("AUDIT_REPORT.docx" in f or "EXECUTIVE_SUMMARY.docx" in f for f in filenames)
    assert "explorer.html" in filenames
    assert any("issues_all.csv" in f for f in filenames)
    assert any("github_issues.json" in f for f in filenames)

    # 3. Assert S3 head_object succeeds for each artifact
    storage = get_storage_service()
    for art in artifacts:
        assert art["size_bytes"] >= 0
        assert art["checksum_sha256"]
        s3_key = f"{org_id}/{art['site_id']}/{crawl_id}/{art['filename']}"
        head = storage.client.head_object(Bucket=S3_BUCKET, Key=s3_key)
        assert head["ContentLength"] == art["size_bytes"]


def test_signed_url_integrity(completed_run_data):
    """
    Signed URL test: fetch a signed URL and confirm the downloaded file's hash matches
    the original file the engine wrote to disk (integrity, not just 'a file exists').
    """
    client = completed_run_data["client"]
    headers = completed_run_data["headers"]
    crawl_id = completed_run_data["crawl_id"]

    # Find the HTML explorer or master report artifact
    res = client.get(f"/runs/{crawl_id}/artifacts", headers=headers)
    assert res.status_code == 200
    artifacts = res.json()

    chosen_art = next(a for a in artifacts if a["filename"] == "explorer.html")
    art_id = chosen_art["id"]

    # 1. Fetch presigned URL
    download_res = client.get(f"/artifacts/{art_id}/download", headers=headers)
    assert download_res.status_code == 200, download_res.text
    dl_data = download_res.json()
    download_url = dl_data["download_url"]

    # Verify download_url points directly to S3 / MinIO
    assert S3_ENDPOINT_URL in download_url or "9000" in download_url
    assert "X-Amz-Signature=" in download_url

    # 2. Download directly from S3 using presigned URL
    http_resp = httpx.get(download_url)
    assert http_resp.status_code == 200
    downloaded_bytes = http_resp.content

    # 3. Verify SHA-256 against original file on disk
    original_disk_path = f"reports/{crawl_id}/explorer.html"
    assert os.path.exists(original_disk_path)
    expected_sha256 = compute_sha256(original_disk_path)

    actual_sha256 = hashlib.sha256(downloaded_bytes).hexdigest()
    assert actual_sha256 == expected_sha256, "Downloaded file hash does not match original disk file"
    assert actual_sha256 == chosen_art["checksum_sha256"]


def test_signed_url_expiry(completed_run_data):
    """
    Expiry test: confirm a signed URL stops working after its expiry window (returns 403 Forbidden).
    """
    client = completed_run_data["client"]
    headers = completed_run_data["headers"]
    crawl_id = completed_run_data["crawl_id"]

    res = client.get(f"/runs/{crawl_id}/artifacts", headers=headers)
    art_id = res.json()[0]["id"]

    # 1. Request presigned URL with 1-second expiry
    download_res = client.get(f"/artifacts/{art_id}/download?expires_in=1", headers=headers)
    assert download_res.status_code == 200
    short_url = download_res.json()["download_url"]

    # 2. Immediately verify it works
    immediate_res = httpx.get(short_url)
    assert immediate_res.status_code == 200, f"Expected 200 immediately, got {immediate_res.status_code}"

    # 3. Wait for expiry window to elapse
    time.sleep(2.5)

    # 4. Assert S3 / MinIO rejects the expired request
    expired_res = httpx.get(short_url)
    assert expired_res.status_code == 403, f"Expected 403 for expired URL, got {expired_res.status_code}"
    assert "Request has expired" in expired_res.text or "ExpiredToken" in expired_res.text or "SignatureDoesNotMatch" in expired_res.text


def test_export_zip_bundle(completed_run_data):
    """
    export.zip test: download it and confirm every individual artifact is present inside, uncorrupted.
    """
    client = completed_run_data["client"]
    headers = completed_run_data["headers"]
    crawl_id = completed_run_data["crawl_id"]

    # 1. Request export.zip
    res = client.get(f"/runs/{crawl_id}/export.zip", headers=headers)
    assert res.status_code == 200, res.text
    zip_meta = res.json()
    assert zip_meta["filename"] == "export.zip"
    download_url = zip_meta["download_url"]

    # 2. Download zip directly from S3
    dl_res = httpx.get(download_url)
    assert dl_res.status_code == 200
    zip_bytes = dl_res.content

    # 3. Inspect zip contents and verify integrity
    with zipfile.ZipFile(io.BytesIO(zip_bytes), "r") as zf:
        # testzip returns None on valid archives
        assert zf.testzip() is None, "Corrupted archive entries detected"
        namelist = zf.namelist()

        # Confirm key artifacts exist inside archive
        assert any("explorer.html" in name for name in namelist)
        assert any("issues_all.csv" in name for name in namelist)
        assert any(".docx" in name for name in namelist)
        assert any("github_issues.json" in name for name in namelist)

        # 4. Verify uncorrupted extraction of a file
        explorer_data = zf.read("explorer.html")
        expected_explorer_sha256 = compute_sha256(f"reports/{crawl_id}/explorer.html")
        assert hashlib.sha256(explorer_data).hexdigest() == expected_explorer_sha256


def test_cross_tenant_artifact_isolation(completed_run_data):
    """
    Isolation test: Org B cannot list Org A's artifacts, fetch download URLs,
    or generate export.zip for Org A's run (returns 404).
    """
    client = completed_run_data["client"]
    run_a_id = completed_run_data["crawl_id"]

    # Register Org B user
    suffix_b = os.urandom(4).hex()
    reg_b = client.post(
        "/auth/register",
        json={"email": f"hacker_{suffix_b}@org-b.com", "password": "Password123!", "org_name": "Org B"}
    )
    token_b = reg_b.json()["access_token"]
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # 1. Org B cannot list Org A's artifacts -> 404
    list_res = client.get(f"/runs/{run_a_id}/artifacts", headers=headers_b)
    assert list_res.status_code == 404

    # 2. Org B cannot request export.zip for Org A's run -> 404
    zip_res = client.get(f"/runs/{run_a_id}/export.zip", headers=headers_b)
    assert zip_res.status_code == 404

    # 3. Org B cannot fetch signed URL for Org A's artifact -> 404
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM artifacts WHERE run_id = %s LIMIT 1", (run_a_id,))
            art_a_id = cur.fetchone()["id"]

    dl_res = client.get(f"/artifacts/{art_a_id}/download", headers=headers_b)
    assert dl_res.status_code == 404
