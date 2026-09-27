"""
SEOJEV Phase 2: Stage 10c Scheduled Recurring Audits E2E Test Suite.

Validates:
1. Autonomous Scheduler Audit Trigger:
   - Configures a recurring audit schedule for a site.
   - Background WatchScheduler discovers due job, verifies overlap, creates new run in PostgreSQL.
2. Full Engine Execution:
   - Engine executes full crawl and ETL without manual invocation.
   - Run completes and creates snapshots.
3. Snapshot Diff & Regression Detection:
   - Compares newly generated snapshot with seeded baseline snapshot.
   - Detects planted regression (accidental noindex leak).
4. Alert & Notification Dispatch:
   - Writes regression alert row to PostgreSQL `alerts` table.
   - Emits regression.detected event to notification sink.
"""
import asyncio
import hashlib
import json
import os
import socket
import sys
import threading
import time
from datetime import datetime, timezone, timedelta
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Dict, Any, List

import pytest
from psycopg.types.json import Jsonb

from database.connection import get_connection
from database.migrator import PostgresMigrator
from jobs.scheduler import WatchScheduler
from services.notifications import NotificationDispatcher, InMemoryEmailSink
from verification.snapshot import SnapshotRecorder


def find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        return s.getsockname()[1]


TEST_SITE_PORT = find_free_port()


class ScheduledSiteHandler(BaseHTTPRequestHandler):
    mode: str = "regressed"  # "baseline", "regressed"

    def log_message(self, format, *args):
        pass

    def do_GET(self):
        target = f"http://127.0.0.1:{TEST_SITE_PORT}/"
        if self.path in ("/", "/index.html"):
            if ScheduledSiteHandler.mode == "regressed":
                # Planted regression: noindex leak
                html = (
                    "<!DOCTYPE html><html><head><title>Regressed Home</title>"
                    '<meta name="robots" content="noindex, nofollow" />'
                    f'<link rel="canonical" href="{target}" />'
                    "</head><body><h1>Landing with noindex</h1>"
                    "<p>Welcome to our company website where we provide premium auditing services and enterprise tools.</p></body></html>"
                )
            else:
                html = (
                    "<!DOCTYPE html><html><head><title>Healthy Home</title>"
                    '<meta name="robots" content="index, follow" />'
                    f'<link rel="canonical" href="{target}" />'
                    "</head><body><h1>Healthy Landing</h1>"
                    "<p>Welcome to our company website where we provide premium auditing services and enterprise tools.</p></body></html>"
                )
            data = html.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return

        if self.path == "/robots.txt":
            content = "User-agent: *\nAllow: /\n"
            data = content.encode("utf-8")
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
def scheduled_site_server():
    server = HTTPServer(("127.0.0.1", TEST_SITE_PORT), ScheduledSiteHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{TEST_SITE_PORT}"
    server.shutdown()


def test_scheduled_recurring_audits_full_cycle(scheduled_site_server):
    """
    Stage 10c E2E Test:
    Seeds Run 1 (baseline snapshot: indexable).
    Plants a regression (mode="regressed": accidental noindex).
    Starts WatchScheduler.
    Scheduler autonomously:
      - Creates Run 2
      - Executes crawl
      - Takes snapshot
      - Diffs with Run 1
      - Detects NOINDEX_LEAK
      - Persists alert in PostgreSQL
      - Emits notification to email sink
    """
    suffix = os.urandom(4).hex()
    org_id = f"org_rec_{suffix}"
    site_id = f"site_rec_{suffix}"
    base_url = f"http://127.0.0.1:{TEST_SITE_PORT}/"
    run1_id = f"crawl_base_{suffix}"

    email_sink = InMemoryEmailSink()
    dispatcher = NotificationDispatcher(email_sink=email_sink)

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO orgs (id, name, slug) VALUES (%s, %s, %s)", (org_id, f"Recurring Org {suffix}", f"rec-{suffix}"))
            cur.execute(
                "INSERT INTO sites (id, org_id, domain, url, vertical) VALUES (%s, %s, %s, %s, 'generic')",
                (site_id, org_id, f"127.0.0.1:{TEST_SITE_PORT}", base_url)
            )
            # 1. Seed completed baseline Run 1
            cur.execute(
                """
                INSERT INTO runs (id, org_id, site_id, status, progress_pct, total_issues, finished_at)
                VALUES (%s, %s, %s, 'completed', 100.0, 0, %s)
                """,
                (run1_id, org_id, site_id, datetime.now(timezone.utc) - timedelta(hours=1))
            )
            # Seed baseline snapshot for Run 1 (clean, indexable)
            baseline_snap = {
                "url": base_url,
                "title": "Healthy Home",
                "canonical": base_url,
                "meta_robots": "index, follow",
                "status_code": 200,
                "content_hash": hashlib.sha256(b"healthy").hexdigest(),
                "schema_hash": ""
            }
            cur.execute(
                """
                INSERT INTO snapshots (id, org_id, site_id, run_id, url, snapshot_data)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (f"snap1_{suffix}", org_id, site_id, run1_id, base_url, Jsonb(baseline_snap))
            )
            # Also save to SQLite data/{run1_id}.db so SnapshotDiffer finds it in both stores
            os.makedirs("data", exist_ok=True)
            recorder = SnapshotRecorder(db_path=f"data/{run1_id}.db")
            recorder.take_snapshot_for_url(run1_id, base_url, baseline_snap)

            # Deactivate previous leftover watch configs to prevent worker queue congestion
            cur.execute("UPDATE watch_configs SET is_active = FALSE WHERE is_active = TRUE")

            # 2. Configure recurring audit schedule due immediately
            cur.execute(
                """
                INSERT INTO watch_configs (
                    id, org_id, site_id, cron_expression, is_active, checks_json,
                    notification_channels_json, audit_config_json, next_run_at
                )
                VALUES (%s, %s, %s, '* * * * *', TRUE, '["full_audit"]', %s, %s, %s)
                """,
                (
                    f"watch_rec_{suffix}",
                    org_id,
                    site_id,
                    Jsonb([{"type": "email", "recipients": ["recurring-audit@example.com"]}]),
                    Jsonb({"max_pages": 5, "fresh": True}),
                    datetime.now(timezone.utc) - timedelta(seconds=10)
                )
            )
        conn.commit()

    # Set site server to regressed mode (noindex)
    ScheduledSiteHandler.mode = "regressed"

    # Start the scheduler
    scheduler = WatchScheduler(poll_interval_sec=0.2, dispatcher=dispatcher)
    scheduler.start()
    assert scheduler.is_running()

    # Wait up to 35 seconds for the scheduler to trigger full audit, execute run, and write regression alert
    completed_run = None
    regression_alert = None

    for _ in range(70):
        time.sleep(0.5)
        with get_connection() as conn:
            with conn.cursor() as cur:
                # Check for completed scheduled run
                cur.execute(
                    "SELECT id, status, progress_pct FROM runs WHERE org_id = %s AND site_id = %s AND id != %s",
                    (org_id, site_id, run1_id)
                )
                runs = cur.fetchall()
                if runs and runs[0]["status"] == "completed":
                    completed_run = runs[0]

                # Check for regression alert
                cur.execute(
                    "SELECT id, alert_type, severity, title, status FROM alerts WHERE org_id = %s AND site_id = %s",
                    (org_id, site_id)
                )
                alerts = cur.fetchall()
                if alerts:
                    regression_alert = alerts[0]

        if completed_run and regression_alert:
            break

    scheduler.stop()

    # VERIFY EXPECTED OUTCOMES
    # 1. Scheduler created and executed run to completion
    assert completed_run is not None, "Scheduler failed to create and execute scheduled audit run"
    assert completed_run["status"] == "completed"

    # 2. Regression was detected and alert persisted
    assert regression_alert is not None, "Scheduler failed to detect regression and persist alert"
    assert regression_alert["alert_type"] == "NOINDEX_LEAK"
    assert regression_alert["severity"] == "critical"
    assert regression_alert["status"] == "open"

    # 3. Notification was delivered to email sink
    emails = email_sink.get_messages()
    assert len(emails) >= 1
    assert "recurring-audit@example.com" in emails[0]["recipients"]
    assert "NOINDEX_LEAK" in emails[0]["subject"] or "Noindex" in emails[0]["subject"]
