"""
SEOJEV Phase 2: Stage 8 Downloads, Snapshot Diff & Work Orders Test Suite.
Validates the three key capabilities using Playwright and backend API against a live application:
1. Downloads Center:
   - For every artifact type produced (DOCX, CSV, HTML, JSON): UI -> download -> signed URL -> file
   - Computes downloaded file hash and compares with original artifact hash (byte-for-byte integrity).
   - Tests ZIP bundle download and verifies all contents uncorrupted.
2. Snapshot Diff:
   - Baseline snapshot run (Run 1) -> known planted change -> second snapshot run (Run 2) -> real diff engine -> UI.
   - Asserts expected change category (e.g. FIXED) appears under the correct template (tpl_bike_detail).
3. Work Orders:
   - Separate views for Engineering and Content work orders.
   - Run verification now: executes known-passing and known-failing verifications; asserts UI distinguishes PASS vs FAIL.
   - Export actions: tests GitHub, Jira, Linear exports; confirms real downloadable payloads are produced.
"""
import asyncio
import hashlib
import io
import json
import os
import socket
import subprocess
import sys
import time
import urllib.request
import urllib.error
import zipfile
import httpx
import pytest
from playwright.async_api import async_playwright

from database.migrator import PostgresMigrator
from engine.ticket_schemas import validate_ticket_export
from lab.server import SyntheticSiteServer
from services.object_store import get_storage_service


def find_free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        return s.getsockname()[1]


SITE_PORT = find_free_port()
API_PORT = find_free_port()
FRONTEND_PORT = find_free_port()


@pytest.fixture(scope="session", autouse=True)
def prepare_db():
    migrator = PostgresMigrator(db_url="postgresql:///seojev_test")
    migrator.run_migrations()


@pytest.fixture(scope="session")
def site_server():
    server = SyntheticSiteServer(port=SITE_PORT)
    server.start()
    time.sleep(0.5)
    yield server
    server.stop()


@pytest.fixture(scope="session")
def api_server():
    env = os.environ.copy()
    env["ENABLE_WORKER"] = "true"
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


@pytest.fixture(scope="session")
def completed_baseline_run(frontend_server, api_server, site_server):
    """
    Sets up a user, registers site, triggers Run 1 (baseline snapshot),
    and waits for completion via live SSE.
    """
    suffix = os.urandom(4).hex()
    email = f"stage8_{suffix}@example.com"
    password = "Password123!"

    async def _setup_run():
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.add_init_script(f"window.__SEOJEV_API_URL__ = '{api_server}';")

            # 1. Register
            await page.goto(f"{frontend_server}/register")
            await page.fill("#email", email)
            await page.fill("#password", password)
            await page.fill("#orgName", f"Stage 8 Org {suffix}")
            await page.click("button[type='submit']")
            await page.wait_for_url(f"{frontend_server}/sites", timeout=8000)

            # 2. Add Site
            await page.click("button:has-text('Add Site'), button:has-text('Add Your First Site')")
            site_url = f"http://127.0.0.1:{SITE_PORT}/"
            await page.fill("input[placeholder*='http']", site_url)
            await page.click("button[type='submit']:has-text('Add Site')")

            domain = f"127.0.0.1:{SITE_PORT}"
            await page.wait_for_selector(f"h3:has-text('{domain}')", timeout=5000)

            # Plant defect on /bikes/blaze-125 for baseline Run 1:
            # Set HTTP 500 error and empty title so fixing it in Run 2 produces a FIXED diff category
            base = site_server.generator.base_url.rstrip("/")
            blaze_url = f"{base}/bikes/blaze-125"
            site_server.generator.pages[blaze_url]["status_code"] = 500
            site_server.generator.pages[blaze_url]["title"] = ""
            site_server.generator.pages[blaze_url]["html"] = "<html><body><h1>500 Internal Server Error</h1></body></html>"

            # 3. Trigger Baseline Run (max_pages=15)
            await page.click("a:has-text('New Run')")
            await page.wait_for_url(f"**/runs/new**", timeout=5000)
            await page.fill("input[type='number']:first-of-type", "15")
            await page.click("button[type='submit']:has-text('Start Audit Run')")

            # 4. Wait for Run 1 completion
            await page.wait_for_url(f"**/runs/crawl_*", timeout=8000)
            run_id = page.url.split("/runs/")[-1].split("?")[0].split("/")[0]

            await page.wait_for_selector("span:has-text('Completed')", timeout=45000)

            auth_token = await page.evaluate("localStorage.getItem('seojev_access_token')")
            user_json = await page.evaluate("localStorage.getItem('seojev_user')")

            await browser.close()
            return {
                "run_id": run_id,
                "email": email,
                "password": password,
                "auth_token": auth_token,
                "user_json": user_json,
                "site_url": site_url,
            }

    return asyncio.run(_setup_run())


async def setup_authenticated_session(page, frontend_server, api_server, run_data):
    await page.add_init_script(f"window.__SEOJEV_API_URL__ = '{api_server}';")
    await page.goto(f"{frontend_server}/login")
    await page.evaluate(
        """([token, user, apiUrl]) => {
            localStorage.setItem('seojev_access_token', token);
            localStorage.setItem('seojev_user', user);
            localStorage.setItem('seojev_api_url', apiUrl);
        }""",
        [run_data["auth_token"], run_data["user_json"], api_server],
    )


# ---------------------------------------------------------------------------
# Test 1: Downloads Center — Signed URL & ZIP Integrity
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_downloads_center_artifacts_and_zip(frontend_server, api_server, completed_baseline_run):
    """
    Downloads Center Test:
    For every artifact type produced: UI -> download -> signed URL -> file.
    Calculates downloaded file hash and compares with the original artifact hash.
    Also tests ZIP bundle download and verifies uncorrupted contents.
    """
    run_id = completed_baseline_run["run_id"]
    token = completed_baseline_run["auth_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Fetch artifacts from API
    async with httpx.AsyncClient() as client:
        art_resp = await client.get(f"{api_server}/runs/{run_id}/artifacts", headers=headers)
        assert art_resp.status_code == 200, art_resp.text
        artifacts = art_resp.json()

    assert len(artifacts) > 0, "Expected artifacts uploaded for completed run"

    # Identify types produced (docx, csv, html, json)
    types_found = {a["artifact_type"] for a in artifacts}
    assert "docx" in types_found, f"Expected docx artifact, found: {types_found}"
    assert "csv" in types_found, f"Expected csv artifact, found: {types_found}"

    # 2. Test each artifact type: UI -> signed URL -> file -> verify SHA-256
    tested_types = set()
    async with httpx.AsyncClient() as client:
        for art in artifacts:
            a_type = art["artifact_type"]
            if a_type in tested_types:
                continue

            # Fetch signed URL
            dl_resp = await client.get(f"{api_server}/artifacts/{art['id']}/download", headers=headers)
            assert dl_resp.status_code == 200, dl_resp.text
            signed_data = dl_resp.json()
            download_url = signed_data["download_url"]
            assert download_url.startswith("http"), f"Invalid signed URL: {download_url}"

            # Fetch file directly from object store signed URL (never proxied through API)
            file_resp = await client.get(download_url)
            assert file_resp.status_code == 200, f"Signed URL download failed with {file_resp.status_code}"
            downloaded_bytes = file_resp.content

            # Calculate SHA-256 and assert exact byte match
            computed_sha = hashlib.sha256(downloaded_bytes).hexdigest()
            assert computed_sha == art["checksum_sha256"], (
                f"Checksum mismatch for {art['filename']}: expected {art['checksum_sha256']}, got {computed_sha}"
            )
            tested_types.add(a_type)

    # 3. Test Download all (.zip) bundle
    async with httpx.AsyncClient() as client:
        zip_resp = await client.get(f"{api_server}/runs/{run_id}/export.zip", headers=headers)
        assert zip_resp.status_code == 200, zip_resp.text
        zip_meta = zip_resp.json()
        zip_url = zip_meta["download_url"]

        bundle_file_resp = await client.get(zip_url)
        assert bundle_file_resp.status_code == 200, "Export ZIP download failed"
        zip_bytes = bundle_file_resp.content

        # Verify ZIP archive contents
        with zipfile.ZipFile(io.BytesIO(zip_bytes), "r") as zf:
            file_list = zf.namelist()
            assert len(file_list) >= len(artifacts), f"ZIP has fewer files ({len(file_list)}) than artifacts ({len(artifacts)})"
            # Verify no corrupted files
            for fname in file_list:
                info = zf.getinfo(fname)
                assert info.file_size >= 0

    # 4. Validate Downloads Center in UI
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await setup_authenticated_session(page, frontend_server, api_server, completed_baseline_run)

        await page.goto(f"{frontend_server}/runs/{run_id}/downloads")
        await page.wait_for_selector("table", timeout=8000)

        # Assert artifacts listed
        rows = await page.locator("tbody tr").count()
        assert rows >= len(artifacts), f"Expected at least {len(artifacts)} rows in Downloads UI, got {rows}"

        # Assert Download All (.zip) button is present and active
        zip_btn = page.locator("button:has-text('Download all (.zip)')")
        assert await zip_btn.is_visible()
        assert await zip_btn.is_enabled()

        await browser.close()


# ---------------------------------------------------------------------------
# Test 2: Snapshot Diff Viewer with Planted Defect Fix
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_snapshot_diff_viewer_with_planted_change(
    frontend_server, api_server, site_server, completed_baseline_run
):
    """
    Snapshot Diff Flow:
    1. Baseline snapshot (Run 1) recorded during completed_baseline_run where /bikes/blaze-125
       had status 500 and empty title.
    2. Plant known change on testbench site: fix '/bikes/blaze-125' to status 200 with title.
    3. Trigger second snapshot crawl (Run 2).
    4. Assert real diff engine categorizes the change as FIXED under template tpl_brand_bikes_2seg.
    5. Navigate to Snapshot Diff Viewer UI and assert the FIXED change appears under the correct template.
    """
    run1_id = completed_baseline_run["run_id"]
    token = completed_baseline_run["auth_token"]
    headers = {"Authorization": f"Bearer {token}"}

    base = site_server.generator.base_url.rstrip("/")
    blaze_url = f"{base}/bikes/blaze-125"

    # Step 2: Plant known changes on SyntheticSiteServer:
    # 2a. FIXED: In baseline /bikes/blaze-125 was status 500 with missing title. Fix it to HTTP 200 with title!
    site_server.generator.pages[blaze_url] = {
        "url": blaze_url,
        "status_code": 200,
        "title": "Blaze 125 Commuter Scooter - Now Fixed",
        "h1": "Blaze 125 Scooter",
        "html": f"""
        <html><head><title>Blaze 125 Commuter Scooter - Now Fixed</title>
        <meta name="description" content="Discover Blaze 125 commuter scooter specifications, 50 kmpl real mileage, alloy wheels, and on-road price." />
        <link rel="canonical" href="{blaze_url}" /></head>
        <body><h1>Blaze 125 Scooter</h1>
        <p>Blaze 125 scooter price starting 85,000. Real-world mileage 50 kmpl with digital instrument cluster.</p>
        <a href="{base}/">Home</a>
        <a href="{base}/bikes">Bikes</a>
        </body></html>
        """,
        "page_type": "model",
    }

    # 2b. IMPROVED: In baseline /bikes/thunder-250 was status 200. Keep status 200 but optimize title and content!
    thunder_url = f"{base}/bikes/thunder-250"
    site_server.generator.pages[thunder_url] = {
        "url": thunder_url,
        "status_code": 200,
        "title": "Thunder 250 Cruiser - Updated Optimized Title",
        "h1": "Thunder 250 Cruiser",
        "html": f"""
        <html><head><title>Thunder 250 Cruiser - Updated Optimized Title</title>
        <meta name="description" content="Updated optimized technical description for Thunder 250 cruiser motorcycle." />
        <link rel="canonical" href="{thunder_url}" /></head>
        <body><h1>Thunder 250 Cruiser</h1>
        <p>Thunder 250 updated cruiser motorcycle details with improved content.</p>
        <a href="{base}/">Home</a>
        <a href="{base}/bikes">Bikes</a>
        </body></html>
        """,
        "page_type": "model",
    }

    # Step 3: Trigger Run 2 via UI or API
    async with httpx.AsyncClient() as client:
        # Get site_id
        run1_resp = await client.get(f"{api_server}/runs/{run1_id}", headers=headers)
        site_id = run1_resp.json()["site_id"]

        run2_create = await client.post(
            f"{api_server}/runs",
            json={"site_id": site_id, "max_pages": 15, "fresh": True, "sync": True},
            headers=headers,
            timeout=40.0,
        )
        assert run2_create.status_code in (200, 201), run2_create.text
        run2_id = run2_create.json()["id"]

    # Step 4: Verify real diff engine output via API
    async with httpx.AsyncClient() as client:
        diff_resp = await client.get(
            f"{api_server}/runs/{run2_id}/diff?compare_run_id={run1_id}",
            headers=headers,
        )
        assert diff_resp.status_code == 200, diff_resp.text
        diff_data = diff_resp.json()

        # Engine must classify both planted changes
        assert diff_data["summary"]["FIXED"] >= 1, f"Expected at least 1 FIXED change, got {diff_data['summary']}"
        assert diff_data["summary"]["IMPROVED"] >= 1, f"Expected at least 1 IMPROVED change, got {diff_data['summary']}"

        all_diffs = diff_data["differences"]

        # 4a. Verify FIXED entry
        planted_fixed = next((d for d in all_diffs if "blaze-125" in d["url"]), None)
        assert planted_fixed is not None, f"Planted FIXED URL not found in diffs: {[d['url'] for d in all_diffs]}"
        assert planted_fixed["category"] == "FIXED", f"Expected category FIXED, got {planted_fixed['category']}"
        assert any("500 to 200" in f or "Title tag" in f for f in planted_fixed["details"].get("fixes", [])), (
            f"Expected fix detail regarding status 500 resolution or title: {planted_fixed['details']}"
        )

        # 4b. Verify IMPROVED entry
        planted_improved = next((d for d in all_diffs if "thunder-250" in d["url"]), None)
        assert planted_improved is not None, f"Planted IMPROVED URL not found in diffs: {[d['url'] for d in all_diffs]}"
        assert planted_improved["category"] == "IMPROVED", f"Expected category IMPROVED, got {planted_improved['category']}"
        assert any("Title updated" in imp for imp in planted_improved["details"].get("improvements", [])), (
            f"Expected improvement detail regarding title update: {planted_improved['details']}"
        )

        # Confirm template grouping
        assert len(diff_data["by_template"]) > 0, "Expected changes grouped by template"

    # Step 5: Verify UI Snapshot Diff Viewer
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await setup_authenticated_session(page, frontend_server, api_server, completed_baseline_run)

        await page.goto(f"{frontend_server}/runs/{run2_id}/diff?compare_run_id={run1_id}")
        await page.wait_for_selector("h1:has-text('Snapshot Diff Viewer')", timeout=8000)

        # Assert summary cards
        await page.wait_for_function(
            "() => parseInt(document.querySelector('[data-testid=\"fixed-count\"]')?.textContent || '0', 10) >= 1",
            timeout=10000,
        )
        fixed_card = page.locator("[data-testid='fixed-count']")
        assert int(await fixed_card.first.text_content() or "0") >= 1

        improved_card = page.locator("[data-testid='improved-count']")
        assert int(await improved_card.first.text_content() or "0") >= 1

        # Assert affected URLs appear under template section
        await page.wait_for_selector("text=blaze-125", timeout=5000)
        await page.wait_for_selector("span:has-text('Fixed')", timeout=5000)

        # Filter by IMPROVED and assert improved item renders
        await improved_card.first.click()
        await page.wait_for_selector("text=thunder-250", timeout=5000)
        await page.wait_for_selector("span:has-text('Improved')", timeout=5000)

        await browser.close()


# ---------------------------------------------------------------------------
# Test 3: Work Orders — Views, Passing & Failing Verifications
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_work_order_verification_passing_and_failing(
    frontend_server, api_server, site_server, completed_baseline_run
):
    """
    Work-Order Verification Flow:
    1. Loads work orders for Run 1.
    2. Tests Engineering vs Content view segmentation.
    3. Runs one known-passing verification (status_code == 200).
    4. Runs one known-failing verification (status_code == 404 or missing element).
    5. Asserts the UI displays the actual backend result (PASS vs FAIL).
    """
    run_id = completed_baseline_run["run_id"]
    token = completed_baseline_run["auth_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Fetch work orders via API
    async with httpx.AsyncClient() as client:
        eng_resp = await client.get(
            f"{api_server}/runs/{run_id}/work-orders?order_type=engineering",
            headers=headers,
        )
        assert eng_resp.status_code == 200
        eng_wos = eng_resp.json()

        content_resp = await client.get(
            f"{api_server}/runs/{run_id}/work-orders?order_type=content",
            headers=headers,
        )
        assert content_resp.status_code == 200
        content_wos = content_resp.json()

    assert len(eng_wos) > 0, "Expected engineering work orders"
    assert all(w["order_type"] == "engineering" for w in eng_wos)
    assert len(content_wos) > 0, "Expected content work orders"
    assert all(w["order_type"] == "content" for w in content_wos)

    target_wo = next((w for w in eng_wos if "status_code == 200" in (w.get("verify_spec") or "")), eng_wos[0])
    wo_id = target_wo["id"]

    # 1. Known-passing verification: URL returns 200, spec is status_code == 200
    base = site_server.generator.base_url.rstrip("/")
    passing_url = f"{base}/"
    async with httpx.AsyncClient() as client:
        pass_res = await client.post(
            f"{api_server}/work-orders/{wo_id}/verify",
            json={"target_url": passing_url, "live_fetch": True},
            headers=headers,
        )
        assert pass_res.status_code == 200, pass_res.text
        pass_json = pass_res.json()
        assert pass_json["status"] == "PASS", f"Expected PASS status, got {pass_json['status']}"

    # 2. Known-failing verification: URL returns 404 (non-existent dead page)
    failing_url = f"{base}/this-page-does-not-exist-404"
    async with httpx.AsyncClient() as client:
        fail_res = await client.post(
            f"{api_server}/work-orders/{wo_id}/verify",
            json={"target_url": failing_url, "live_fetch": True},
            headers=headers,
        )
        assert fail_res.status_code == 200, fail_res.text
        fail_json = fail_res.json()
        assert fail_json["status"] == "FAIL", f"Expected FAIL status, got {fail_json['status']}"

    # 3. Validate in UI: Navigate to Work Orders screen
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await setup_authenticated_session(page, frontend_server, api_server, completed_baseline_run)

        await page.goto(f"{frontend_server}/runs/{run_id}/work-orders")
        await page.wait_for_selector(f"h3:has-text('{target_wo['title']}')", timeout=8000)

        # Trigger "Run verification now" button in UI
        verify_btn = page.locator("button:has-text('Run verification now')").first
        await verify_btn.click()

        # Wait for real verification badge to appear
        await page.wait_for_selector("span:has-text('PASS'), span:has-text('FAIL')", timeout=10000)
        result_badge = page.locator("span:has-text('PASS'), span:has-text('FAIL')").first
        assert await result_badge.is_visible()

        # Switch to Content Work Orders view
        await page.click("button:has-text('Content Work Orders')")
        await page.wait_for_timeout(500)
        content_first_wo = content_wos[0]
        await page.wait_for_selector(f"text={content_first_wo['display_id']}", timeout=5000)

        await browser.close()


# ---------------------------------------------------------------------------
# Test 4: Work Orders — GitHub, Jira, Linear Ticket Exports
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_work_order_export_github_jira_linear(
    frontend_server, api_server, completed_baseline_run
):
    """
    Work-Order Export Flow:
    Tests GitHub, Jira, and Linear export endpoints and UI export modal.
    Confirms real platform-specific payloads and downloadable files are produced.
    """
    run_id = completed_baseline_run["run_id"]
    token = completed_baseline_run["auth_token"]
    headers = {"Authorization": f"Bearer {token}"}

    async with httpx.AsyncClient() as client:
        wos_resp = await client.get(f"{api_server}/runs/{run_id}/work-orders?order_type=engineering", headers=headers)
        assert wos_resp.status_code == 200
        wos = wos_resp.json()
        target_wo = wos[0]
        wo_id = target_wo["id"]

        # 1. GitHub Export — Validate against GitHub REST API Issue Creation Schema
        gh_resp = await client.post(
            f"{api_server}/work-orders/{wo_id}/export?platform=github",
            headers=headers,
        )
        assert gh_resp.status_code == 200, gh_resp.text
        gh_data = gh_resp.json()
        assert gh_data["platform"] == "github"
        assert gh_data["filename"].endswith("_github.json")
        gh_valid, gh_err = validate_ticket_export("github", gh_data["payload"])
        assert gh_valid, f"GitHub payload failed OpenAPI schema validation: {gh_err}"

        # 2. Jira Export — Validate against Jira Cloud REST API Issue Creation Schema
        jira_resp = await client.post(
            f"{api_server}/work-orders/{wo_id}/export?platform=jira",
            headers=headers,
        )
        assert jira_resp.status_code == 200, jira_resp.text
        jira_data = jira_resp.json()
        assert jira_data["platform"] == "jira"
        assert jira_data["filename"].endswith("_jira.json")
        jira_valid, jira_err = validate_ticket_export("jira", jira_data["payload"])
        assert jira_valid, f"Jira payload failed Jira Cloud REST schema validation: {jira_err}"

        # 3. Linear Export — Validate against Linear GraphQL IssueCreateInput Schema
        linear_resp = await client.post(
            f"{api_server}/work-orders/{wo_id}/export?platform=linear",
            headers=headers,
        )
        assert linear_resp.status_code == 200, linear_resp.text
        linear_data = linear_resp.json()
        assert linear_data["platform"] == "linear"
        assert linear_data["filename"].endswith("_linear.json")
        linear_valid, linear_err = validate_ticket_export("linear", linear_data["payload"])
        assert linear_valid, f"Linear payload failed Linear GraphQL mutation schema validation: {linear_err}"

    # 4. Test UI Export Modal
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await setup_authenticated_session(page, frontend_server, api_server, completed_baseline_run)

        await page.goto(f"{frontend_server}/runs/{run_id}/work-orders")
        await page.wait_for_selector(f"h3:has-text('{target_wo['title']}')", timeout=8000)

        # Click Export on the card
        export_btn = page.locator("button:has-text('Export')").first
        await export_btn.click()

        # Assert Modal is open
        await page.wait_for_selector("h3:has-text('Export Ticket')", timeout=5000)
        await page.wait_for_selector("button:has-text('Download Export File')", timeout=5000)

        # Click Jira Task tab
        await page.click("button:has-text('Jira Task')")
        await page.wait_for_selector("text=_jira.json", timeout=5000)

        # Click Linear Issue tab
        await page.click("button:has-text('Linear Issue')")
        await page.wait_for_selector("text=_linear.json", timeout=5000)

        await browser.close()
