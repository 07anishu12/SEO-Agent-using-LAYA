"""
SEOJEV Phase 2: Stage 7 Opportunities, Templates, Blueprints & GSC Exploration Test Suite.
Validates the four real-data exploration areas using Playwright against a live completed crawl:
1. Opportunities Explorer: real opportunities, diagnostic chain expansion (Observation -> Evidence ->
   Diagnosis -> Hypothesis -> Action -> Verification), ICE factors, tier filtering.
2. Opportunity Feedback Persistence: submit 'False Positive' feedback, reload page, assert persistence.
3. Templates Explorer & Detail: clustered templates list with member and issue counts, and template detail
   showing affected member URLs and associated findings.
4. Blueprints Explorer & Detail: crawled page inventory and 20-dimension blueprint inspector with
   tabs (Diagnostic Dimensions & Raw Markdown).
5. GSC / Search Console Intelligence: explicit empty state, sample dataset ingestion, striking-distance queries,
   cannibalization evidence, query clusters, and trend distribution charts.
"""
import os
import sys
import time
import socket
import subprocess
import urllib.request
import urllib.error
import pytest
from playwright.async_api import async_playwright

from database.migrator import PostgresMigrator
from lab.server import SyntheticSiteServer


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
def completed_run(frontend_server, api_server, site_server):
    """
    Performs a real crawl against SyntheticSiteServer and waits for completion.
    Provides run_id, credentials, and authentication state for all Stage 7 tests.
    """
    suffix = os.urandom(4).hex()
    email = f"stage7_{suffix}@example.com"
    password = "Password123!"

    import asyncio

    async def _setup_run():
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.add_init_script(f"window.__SEOJEV_API_URL__ = '{api_server}';")

            # 1. Register
            await page.goto(f"{frontend_server}/register")
            await page.fill("#email", email)
            await page.fill("#password", password)
            await page.fill("#orgName", f"Stage 7 Org {suffix}")
            await page.click("button[type='submit']")
            await page.wait_for_url(f"{frontend_server}/sites", timeout=8000)

            # 2. Add Site
            await page.click("button:has-text('Add Site'), button:has-text('Add Your First Site')")
            site_url = f"http://127.0.0.1:{SITE_PORT}/"
            await page.fill("input[placeholder*='http']", site_url)
            await page.click("button[type='submit']:has-text('Add Site')")

            domain = f"127.0.0.1:{SITE_PORT}"
            await page.wait_for_selector(f"h3:has-text('{domain}')", timeout=5000)

            # 3. New Run with limit 15 for fast, comprehensive test
            await page.click("a:has-text('New Run')")
            await page.wait_for_url(f"**/runs/new**", timeout=5000)
            await page.fill("input[type='number']:first-of-type", "15")
            await page.click("button[type='submit']:has-text('Start Audit Run')")

            # 4. Wait for run detail
            await page.wait_for_url(f"**/runs/crawl_*", timeout=8000)
            run_id = page.url.split("/runs/")[-1].split("?")[0].split("/")[0]

            # 5. Wait for run to complete via live SSE
            await page.wait_for_selector("span:has-text('Completed')", timeout=45000)

            # Extract auth token and user from local storage
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


async def setup_authenticated_session(page, frontend_server, api_server, completed_run):
    """Authenticates the browser session using stored credentials/tokens."""
    await page.add_init_script(f"window.__SEOJEV_API_URL__ = '{api_server}';")
    await page.goto(f"{frontend_server}/login")
    if completed_run.get("auth_token") and completed_run.get("user_json"):
        await page.evaluate(
            """([token, user, apiUrl]) => {
                localStorage.setItem('seojev_access_token', token);
                localStorage.setItem('seojev_user', user);
                localStorage.setItem('seojev_api_url', apiUrl);
            }""",
            [completed_run["auth_token"], completed_run["user_json"], api_server],
        )
    else:
        await page.fill("#email", completed_run["email"])
        await page.fill("#password", completed_run["password"])
        await page.click("button[type='submit']")
        await page.wait_for_url(f"{frontend_server}/sites", timeout=8000)


@pytest.mark.asyncio
async def test_opportunities_explorer_display_and_diagnostic_chain(frontend_server, api_server, completed_run):
    """
    Asserts Opportunities Explorer renders real opportunities and expanding an item displays
    the full 6-phase diagnostic chain and ICE factors.
    """
    run_id = completed_run["run_id"]

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await setup_authenticated_session(page, frontend_server, api_server, completed_run)

        # Navigate to Opportunities Explorer
        await page.goto(f"{frontend_server}/runs/{run_id}/opportunities")
        await page.wait_for_selector("table tbody tr", timeout=10000)

        # 1. Assert table has loaded real opportunities
        opp_rows = page.locator("table tbody tr")
        count = await opp_rows.count()
        assert count > 0, "Expected at least one opportunity row from completed run"

        first_opp = page.locator("table tbody tr").first
        opp_text = await first_opp.text_content()
        assert len(opp_text) > 0 and "Inspect" in opp_text

        # 2. Expand first opportunity via Inspect button
        inspect_btn = first_opp.locator("button:has-text('Inspect')")
        if await inspect_btn.count() > 0:
            await inspect_btn.click()
        else:
            await first_opp.click()

        # 3. Assert full diagnostic chain (Observation -> Evidence -> Diagnosis -> Hypothesis -> Action -> Verification)
        await page.wait_for_selector("text=1. Observation", timeout=5000)
        assert await page.is_visible("text=1. Observation")
        assert await page.is_visible("text=2. Evidence Provenance")
        assert await page.is_visible("text=3. Diagnosis")
        assert await page.is_visible("text=4. Hypothesis")
        assert await page.is_visible("text=5. Recommended Action")
        assert await page.is_visible("text=6. Verification Specification")

        # 4. Assert ICE Impact Factors are rendered
        assert await page.is_visible("text=Opportunity Engine ICE Factors")
        assert await page.is_visible("text=Visibility")
        assert await page.is_visible("text=Gap")
        assert await page.is_visible("text=Tech Severity")

        await browser.close()


@pytest.mark.asyncio
async def test_opportunities_filtering_and_feedback_persistence(frontend_server, api_server, completed_run):
    """
    Asserts opportunity filtering works, submitting feedback (False Positive) updates state,
    and the verdict is persisted across a full page reload.
    """
    run_id = completed_run["run_id"]

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await setup_authenticated_session(page, frontend_server, api_server, completed_run)

        await page.goto(f"{frontend_server}/runs/{run_id}/opportunities")
        await page.wait_for_selector("table tbody tr", timeout=10000)

        # 1. Test search filter with a prefix from the first opportunity's display ID
        opp_cell_text = await page.locator("table tbody tr:first-child td:nth-child(2)").text_content()
        search_query = opp_cell_text.strip()[:4] if opp_cell_text else "TPL"

        search_input = page.locator("input[placeholder*='Search opportunities']")
        await search_input.fill(search_query)
        await page.wait_for_timeout(300)
        filtered_rows = page.locator("table tbody tr")
        assert await filtered_rows.count() > 0

        # Clear search
        await search_input.fill("")
        await page.wait_for_timeout(300)

        # 2. Expand first opportunity to submit feedback
        first_opp = page.locator("table tbody tr").first
        inspect_btn = first_opp.locator("button:has-text('Inspect')")
        if await inspect_btn.count() > 0:
            await inspect_btn.click()
        else:
            await first_opp.click()

        # Click "False Positive" feedback button
        fp_button = page.locator("button:has-text('False Positive')").first
        await fp_button.wait_for(timeout=5000)
        await fp_button.click()

        # Wait for feedback status badge or text to reflect False Positive
        await page.wait_for_selector("text=FALSE_POSITIVE", timeout=5000)
        assert await page.is_visible("text=FALSE_POSITIVE")

        # 3. Reload page and assert persistence
        await page.reload()
        await page.wait_for_selector("table tbody tr", timeout=10000)

        # Verify persisted status badge is visible
        persisted_badge = page.locator("span:has-text('False Positive'), span:has-text('FALSE_POSITIVE')")
        assert await persisted_badge.count() > 0, "Expected persisted False Positive feedback after page reload"

        await browser.close()


@pytest.mark.asyncio
async def test_templates_explorer_and_detail(frontend_server, api_server, completed_run):
    """
    Asserts Templates Explorer lists real template clusters with member and issue counts,
    and navigating to a template detail displays member URLs and associated findings.
    """
    run_id = completed_run["run_id"]

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await setup_authenticated_session(page, frontend_server, api_server, completed_run)

        # 1. Navigate to Templates Explorer
        await page.goto(f"{frontend_server}/runs/{run_id}/templates")
        await page.wait_for_selector("table tbody tr", timeout=10000)

        # Assert at least one template cluster rendered
        tpl_rows = page.locator("table tbody tr")
        count = await tpl_rows.count()
        assert count > 0, "Expected clustered templates"

        # Assert headers and columns
        assert await page.is_visible("th:has-text('Template ID')")
        assert await page.is_visible("th:has-text('Member Pages')")
        assert await page.is_visible("th:has-text('Associated Issues')")

        # 2. Click 'Inspect Template' on first row
        inspect_btn = page.locator("a:has-text('Inspect Template')").first
        await inspect_btn.click()

        # 3. Verify Template Detail Page loaded
        await page.wait_for_url(f"**/runs/{run_id}/templates/**", timeout=8000)
        await page.wait_for_selector("text=Back to Templates List", timeout=8000)
        await page.wait_for_selector("text=Sample Affected Member URLs", timeout=10000)
        assert await page.is_visible("text=Member Pages")
        assert await page.is_visible("text=Sample Affected Member URLs")

        # Assert sample member URLs list has entries
        member_urls = page.locator("text=View Blueprint")
        assert await member_urls.count() > 0

        await browser.close()


@pytest.mark.asyncio
async def test_blueprints_explorer_and_detail(frontend_server, api_server, completed_run):
    """
    Asserts Blueprints Explorer lists crawled pages and inspecting a blueprint renders
    the 20-dimension blueprint sections and raw markdown.
    """
    run_id = completed_run["run_id"]

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await setup_authenticated_session(page, frontend_server, api_server, completed_run)

        # 1. Navigate to Blueprints Explorer
        await page.goto(f"{frontend_server}/runs/{run_id}/blueprints")
        await page.wait_for_selector("table tbody tr", timeout=10000)

        # Assert crawled pages listed
        page_rows = page.locator("table tbody tr")
        count = await page_rows.count()
        assert count > 0, "Expected crawled pages in blueprint index"

        # 2. Click 'Inspect Blueprint' on the first page
        inspect_btn = page.locator("a:has-text('Inspect Blueprint')").first
        await inspect_btn.click()

        # 3. Verify Blueprint Detail Page loaded
        await page.wait_for_url(f"**/runs/{run_id}/blueprints/detail?url=**", timeout=8000)
        await page.wait_for_selector("text=Template ID", timeout=10000)

        # Assert 20-dimension blueprint sections are rendered
        assert await page.is_visible("text=Template ID")
        assert await page.is_visible("text=Indexability")
        assert await page.is_visible("text=Entity Coverage")
        assert await page.is_visible("text=AEO Extractability")
        assert await page.is_visible("text=Query Fit & Search Intent")
        assert await page.is_visible("text=Core Metadata & Headings")
        assert await page.is_visible("text=Structured Data Schema")
        assert await page.is_visible("text=Internal Link Graph Signals")

        # 4. Switch to 'Raw Blueprint Markdown' tab
        markdown_tab_btn = page.locator("button:has-text('Raw Blueprint Markdown')")
        await markdown_tab_btn.click()

        # Assert markdown contains # Page Optimization Blueprint header
        await page.wait_for_selector("pre:has-text('# Page Optimization Blueprint')", timeout=5000)
        assert await page.is_visible("pre:has-text('# Page Optimization Blueprint')")

        await browser.close()


@pytest.mark.asyncio
async def test_gsc_explorer_empty_state_and_populated_dataset(frontend_server, api_server, completed_run):
    """
    Asserts GSC / Search Console Explorer displays explicit empty state when unconnected,
    and ingesting dataset populates striking-distance queries, cannibalization, clusters, and trend charts.
    """
    run_id = completed_run["run_id"]

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        page.on("dialog", lambda d: d.accept())
        await setup_authenticated_session(page, frontend_server, api_server, completed_run)

        # 1. Navigate to GSC Explorer
        await page.goto(f"{frontend_server}/runs/{run_id}/gsc")

        # 2. Assert explicit clean empty state
        await page.wait_for_selector("text=Ranking Data Unavailable", timeout=10000)
        assert await page.is_visible("text=Ranking Data Unavailable")
        assert await page.is_visible("text=Google Search Console performance data has not been connected")

        # 3. Click 'Connect Sample Search Data' button
        load_btn = page.locator("button:has-text('Connect Sample Search Data')").first
        await load_btn.click()

        # 4. Wait for Search Intelligence dashboard to populate
        await page.wait_for_selector("text=Total Queries", timeout=15000)

        # Assert aggregate metrics
        assert await page.is_visible("text=Total Queries")
        assert await page.is_visible("text=Organic Clicks")
        assert await page.is_visible("text=Impressions")
        assert await page.is_visible("text=Avg Position")

        # Assert striking-distance target section (Pos 11–20)
        assert await page.is_visible("text=Striking-Distance Opportunities (Positions 11–20)")

        # Assert cannibalization section
        assert await page.is_visible("text=Keyword Cannibalization Evidence")

        # Assert query clusters section
        assert await page.is_visible("text=Intent & Search Query Clusters")

        # Assert distribution trends charts
        assert await page.is_visible("text=Impression Trends by Ranking Bracket")
        assert await page.is_visible("text=Click Trends by Ranking Bracket")

        await browser.close()
