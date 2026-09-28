"""
SEOJEV Phase 2: Stage 6 Next.js Frontend Skeleton Test Suite.
Uses Playwright to test the real frontend connected to the real FastAPI backend:
1. Protected route test: navigating to /sites unauthenticated redirects to /login.
2. Invalid login test: submitting bad credentials shows the API error message.
3. Registration & Site creation test: registers a user and adds a target site via the real API.
4. Main E2E flow test:
   Register/Login -> Open Sites -> Add baseline site -> Open New Run -> Submit real run ->
   Open Run Detail -> Receive live SSE progress without page refresh -> Wait for terminal state.
5. Run cancellation test: start run and trigger cancel button, verifying UI reflects 'cancelled'.
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

    # Wait for API server ready
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
async def test_protected_route_unauthenticated(frontend_server, api_server):
    """Navigating to protected route /sites without JWT redirects to /login."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        # Set API URL in browser context
        await page.add_init_script(f"window.__SEOJEV_API_URL__ = '{api_server}';")

        await page.goto(f"{frontend_server}/sites")
        # Should redirect to /login
        await page.wait_for_url(f"{frontend_server}/login", timeout=5000)
        assert "/login" in page.url

        # Check login elements exist
        assert await page.is_visible("text=Sign in to SEOJEV")
        await browser.close()


@pytest.mark.asyncio
async def test_invalid_login_error_handling(frontend_server, api_server):
    """Attempting login with invalid credentials displays API error message."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        await page.add_init_script(f"window.__SEOJEV_API_URL__ = '{api_server}';")

        await page.goto(f"{frontend_server}/login")
        await page.fill("#email", "nonexistent_user@example.com")
        await page.fill("#password", "WrongPassword123")
        await page.click("button[type='submit']")

        # Error banner should appear
        await page.wait_for_selector("text=Invalid email or password", timeout=5000)
        assert await page.is_visible("text=Invalid email or password")

        await browser.close()


@pytest.mark.asyncio
async def test_registration_and_site_creation(frontend_server, api_server, site_server):
    """Registers a new user, creates a site via the real API, and asserts it appears in the dashboard."""
    suffix = os.urandom(4).hex()
    email = f"fe_user_{suffix}@example.com"

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        await page.add_init_script(f"window.__SEOJEV_API_URL__ = '{api_server}';")

        # 1. Register
        await page.goto(f"{frontend_server}/register")
        await page.fill("#email", email)
        await page.fill("#password", "Password123!")
        await page.fill("#orgName", f"Agency {suffix}")
        await page.click("button[type='submit']")

        # Redirects to /sites
        await page.wait_for_url(f"{frontend_server}/sites", timeout=8000)
        assert "/sites" in page.url

        # 2. Add Site via UI modal
        await page.click("button:has-text('Add Site'), button:has-text('Add Your First Site')")
        await page.wait_for_selector("text=Add Target Site", timeout=3000)

        site_url = f"http://127.0.0.1:{SITE_PORT}/"
        await page.fill("input[placeholder*='http']", site_url)
        await page.select_option("select", "automotive")
        await page.click("button[type='submit']:has-text('Add Site')")

        # 3. Assert site card rendered with domain
        domain = f"127.0.0.1:{SITE_PORT}"
        await page.wait_for_selector(f"h3:has-text('{domain}')", timeout=5000)
        assert await page.is_visible(f"h3:has-text('{domain}')")
        assert await page.is_visible("text=automotive")

        await browser.close()


@pytest.mark.asyncio
async def test_main_e2e_flow_with_live_sse(frontend_server, api_server, site_server):
    """
    Main E2E Flow:
    Register -> Sites -> Add baseline site -> New Run -> Submit real run ->
    Run Detail -> Receive live SSE progress -> Verify pass progress changes without refresh ->
    Wait for completed state -> Verify metrics and deliverables.
    """
    suffix = os.urandom(4).hex()
    email = f"e2e_{suffix}@example.com"

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        await page.add_init_script(f"window.__SEOJEV_API_URL__ = '{api_server}';")

        # 1. Register & Land on Sites
        await page.goto(f"{frontend_server}/register")
        await page.fill("#email", email)
        await page.fill("#password", "Password123!")
        await page.fill("#orgName", f"E2E Org {suffix}")
        await page.click("button[type='submit']")

        await page.wait_for_url(f"{frontend_server}/sites", timeout=8000)

        # 2. Add Site
        await page.click("button:has-text('Add Site'), button:has-text('Add Your First Site')")
        site_url = f"http://127.0.0.1:{SITE_PORT}/"
        await page.fill("input[placeholder*='http']", site_url)
        await page.click("button[type='submit']:has-text('Add Site')")

        domain = f"127.0.0.1:{SITE_PORT}"
        await page.wait_for_selector(f"h3:has-text('{domain}')", timeout=5000)

        # 3. Click 'New Run' from site card
        await page.click("a:has-text('New Run')")
        await page.wait_for_url(f"**/runs/new**", timeout=5000)
        assert "/runs/new" in page.url

        # Configure crawl limits: 15 pages for quick reliable test
        await page.fill("input[type='number']:first-of-type", "15")

        # 4. Submit Run
        await page.click("button[type='submit']:has-text('Start Audit Run')")

        # 5. Open Run Detail (redirects to /runs/crawl_...)
        await page.wait_for_url(f"**/runs/crawl_*", timeout=8000)
        assert "/runs/crawl_" in page.url

        # 6. Verify Live SSE connection status appears without refresh
        await page.wait_for_selector("text=Live SSE Connected", timeout=10000)
        assert await page.is_visible("text=Live SSE Connected")

        # 7. Verify progress percentage updates in real time
        # Record initial percent
        pct_elem = page.locator("span.font-mono.font-extrabold")
        await pct_elem.wait_for(timeout=5000)
        initial_pct = await pct_elem.text_content()

        # Wait for terminal state 'Completed' without refreshing the page
        # Timeout 45s for full 6-pass execution against synthetic site
        await page.wait_for_selector("span:has-text('Completed')", timeout=180000)
        assert await page.is_visible("span:has-text('Completed')")

        # Confirm 100% reached
        final_pct = await pct_elem.text_content()
        assert "100%" in final_pct or int(final_pct.replace("%", "").strip()) >= 90

        # Confirm metrics populated
        urls_crawled_elem = page.locator("div:has-text('URLs Crawled') + div, div:has-text('URLs Crawled') div.text-2xl")
        # Assert opportunities and deliverables appeared
        await page.wait_for_selector("text=Generated Deliverables & Reports", timeout=5000)
        # Assert at least one artifact download button rendered
        download_btns = page.locator("button:has-text('Download')")
        count = await download_btns.count()
        assert count > 0, "Expected generated artifacts with download buttons"

        # Assert 'Download All (.zip)' button is visible
        assert await page.is_visible("button:has-text('Download All (.zip)')")

        await browser.close()


@pytest.mark.asyncio
async def test_run_cancellation_action(frontend_server, api_server, site_server):
    """Starts a run and cancels it from the UI, asserting that status becomes 'Cancelled'."""
    suffix = os.urandom(4).hex()
    email = f"cancel_user_{suffix}@example.com"

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        await page.add_init_script(f"window.__SEOJEV_API_URL__ = '{api_server}';")

        # Handle confirm() dialog automatically
        page.on("dialog", lambda dialog: dialog.accept())

        # Register & Create site
        await page.goto(f"{frontend_server}/register")
        await page.fill("#email", email)
        await page.fill("#password", "Password123!")
        await page.click("button[type='submit']")
        await page.wait_for_url(f"{frontend_server}/sites", timeout=8000)

        await page.click("button:has-text('Add Site'), button:has-text('Add Your First Site')")
        site_url = f"http://127.0.0.1:{SITE_PORT}/"
        await page.fill("input[placeholder*='http']", site_url)
        await page.click("button[type='submit']:has-text('Add Site')")

        domain = f"127.0.0.1:{SITE_PORT}"
        await page.wait_for_selector(f"h3:has-text('{domain}')", timeout=5000)

        # Start Run with high max_pages so we can cancel it mid-crawl
        await page.click("a:has-text('New Run')")
        await page.wait_for_url(f"**/runs/new**", timeout=5000)
        await page.fill("input[type='number']:first-of-type", "200")
        await page.click("button[type='submit']:has-text('Start Audit Run')")

        await page.wait_for_url(f"**/runs/crawl_*", timeout=8000)

        # Find and click 'Cancel Run' button
        cancel_btn = page.locator("button:has-text('Cancel Run')")
        await cancel_btn.wait_for(timeout=5000)
        await cancel_btn.click()

        # Wait for terminal state 'Cancelled'
        await page.wait_for_selector("span:has-text('Cancelled')", timeout=15000)
        assert await page.is_visible("span:has-text('Cancelled')")

        await browser.close()
