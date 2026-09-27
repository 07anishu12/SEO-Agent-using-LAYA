"""
SEOJEV Phase 2: Stage 10d GSC Anomaly Detection Test Suite.

Validates Section 6.9:
1. Deterministic Statistical Decay Detection:
   - Seeds 14-day healthy baseline period (~1,000 impressions, ~100 clicks daily).
   - Seeds 3-day severe decay period (~150 impressions, ~15 clicks daily).
   - Confirms detection at page-level and template-level.
2. Alert Persistence & Evidence Ledger:
   - Verifies alert row is written to PostgreSQL `alerts` table with source="gsc_anomaly".
   - Verifies alert payload contains baseline period, current period, z-score, drop percentage, and evidence.
3. Notification Dispatch:
   - Emits event and dispatches alert through NotificationDispatcher to InMemoryEmailSink.
4. Insufficient History Guard:
   - Confirms sites with insufficient time-series (< 7 days) produce no false positive alerts.
5. API Endpoint & Tenant Isolation:
   - Verifies POST /sites/{id}/gsc/detect-anomalies honors JWT org_id isolation.
"""
import os
import random
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List

import pytest
from fastapi.testclient import TestClient

from api.main import app
from database.connection import get_connection
from database.migrator import PostgresMigrator
from services.gsc_anomaly import GSCAnomalyDetector
from services.notifications import NotificationDispatcher, InMemoryEmailSink


@pytest.fixture(scope="session", autouse=True)
def prepare_db():
    migrator = PostgresMigrator(db_url="postgresql:///seojev_test")
    migrator.run_migrations()


def create_auth_token(client: TestClient, org_id: str, email: str) -> str:
    from api.auth import create_access_token
    return create_access_token({"sub": f"usr_{org_id}", "email": email, "org_id": org_id, "role": "admin"})


def test_gsc_anomaly_detector_e2e_page_and_template_decay():
    """
    E2E Test:
    1. Ingests 14 days of baseline GSC data + 3 days of severe decay.
    2. Runs statistical anomaly detection.
    3. Verifies page and template decay anomalies, alert persistence, evidence, and email delivery.
    """
    suffix = os.urandom(4).hex()
    org_id = f"org_gsc_{suffix}"
    site_id = f"site_gsc_{suffix}"
    target_page = "https://example.com/products/pro-widget"
    template_id = "product_detail"

    # Setup org and site
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO orgs (id, name, slug) VALUES (%s, %s, %s)", (org_id, f"GSC Org {suffix}", f"gsc-{suffix}"))
            cur.execute(
                "INSERT INTO sites (id, org_id, domain, url, vertical) VALUES (%s, %s, %s, %s, 'ecommerce')",
                (site_id, org_id, "example.com", "https://example.com")
            )
        conn.commit()

    email_sink = InMemoryEmailSink()
    dispatcher = NotificationDispatcher(email_sink=email_sink)
    detector = GSCAnomalyDetector(dispatcher=dispatcher)

    # 1. Seed deterministic time series
    # 14 days baseline: daily impressions 950-1050, daily clicks 95-105
    today = datetime.now(timezone.utc).date()
    rows = []

    # 14 days of baseline (Day -17 to Day -4)
    for day_offset in range(17, 3, -1):
        d_val = today - timedelta(days=day_offset)
        # Seed target page
        rows.append({
            "page": target_page,
            "template_id": template_id,
            "date": d_val.isoformat(),
            "impressions": 1000 + ((day_offset % 3) * 20 - 20),
            "clicks": 100 + ((day_offset % 3) * 4 - 4),
            "ctr": 0.10,
            "position": 3.2
        })

    # 3 days of severe decay (Day -3 to Day -1): impressions 150, clicks 12 (~85% drop)
    for day_offset in range(3, 0, -1):
        d_val = today - timedelta(days=day_offset)
        rows.append({
            "page": target_page,
            "template_id": template_id,
            "date": d_val.isoformat(),
            "impressions": 150 + ((day_offset % 2) * 10),
            "clicks": 14 + ((day_offset % 2) * 2),
            "ctr": 0.09,
            "position": 8.5
        })

    inserted = detector.ingest_daily_metrics(org_id, site_id, rows)
    assert inserted == 17

    # 2. Run detection with email sink
    channels = [{"type": "email", "recipients": ["seo-alerts@example.com"]}]
    result = detector.detect_anomalies(site_id=site_id, org_id=org_id, channels=channels)

    # 3. Verify detection results
    assert result["status"] == "completed"
    assert result["history_days"] == 17
    assert result["anomalies_detected"] >= 2  # impressions decay + clicks decay (and/or template decay)
    assert result["alerts_persisted"] >= 2

    anomalies = result["anomalies"]
    imp_anom = next((a for a in anomalies if a["anomaly_type"] == "GSC_IMPRESSIONS_DECAY" and a["scope"] == "page"), None)
    clk_anom = next((a for a in anomalies if a["anomaly_type"] == "GSC_CLICKS_DECAY" and a["scope"] == "page"), None)
    tpl_anom = next((a for a in anomalies if a["anomaly_type"] == "GSC_TEMPLATE_DECAY"), None)

    assert imp_anom is not None, "Failed to detect page-level impressions decay"
    assert imp_anom["drop_pct"] >= 70.0
    assert imp_anom["z_score"] <= -2.5
    assert imp_anom["severity"] in ("critical", "high")
    assert "evidence" in imp_anom

    assert clk_anom is not None, "Failed to detect page-level clicks decay"
    assert clk_anom["drop_pct"] >= 70.0
    assert clk_anom["severity"] in ("critical", "high")

    assert tpl_anom is not None, "Failed to detect template-level impressions decay"
    assert tpl_anom["entity"] == template_id

    # 4. Verify PostgreSQL alerts ledger persistence
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, alert_type, severity, title, message, source, payload_json, affected_urls_json
                FROM alerts
                WHERE org_id = %s AND site_id = %s AND source = 'gsc_anomaly'
                ORDER BY created_at DESC
                """,
                (org_id, site_id)
            )
            alert_rows = cur.fetchall()

    assert len(alert_rows) >= 2
    types_saved = {r["alert_type"] for r in alert_rows}
    assert "GSC_IMPRESSIONS_DECAY" in types_saved
    assert "GSC_CLICKS_DECAY" in types_saved

    # Verify evidence stored in payload_json
    first_payload = alert_rows[0]["payload_json"]
    assert "baseline_period" in first_payload
    assert "current_period" in first_payload
    assert "drop_pct" in first_payload
    assert "evidence" in first_payload

    # 5. Verify notification delivery to email sink
    emails = email_sink.get_messages()
    assert len(emails) >= 2
    assert "seo-alerts@example.com" in emails[0]["recipients"]
    assert "GSC" in emails[0]["subject"]


def test_gsc_anomaly_insufficient_history_produces_no_alerts():
    """
    Validates that sites with fewer than 7 days of data explicitly return
    insufficient_history and produce ZERO false positive alerts.
    """
    suffix = os.urandom(4).hex()
    org_id = f"org_gsc_short_{suffix}"
    site_id = f"site_gsc_short_{suffix}"

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO orgs (id, name, slug) VALUES (%s, %s, %s)", (org_id, f"Short Org {suffix}", f"short-{suffix}"))
            cur.execute(
                "INSERT INTO sites (id, org_id, domain, url) VALUES (%s, %s, %s, %s)",
                (site_id, org_id, "short.example.com", "https://short.example.com")
            )
        conn.commit()

    detector = GSCAnomalyDetector()
    today = datetime.now(timezone.utc).date()

    # Seed only 3 days of data with erratic numbers
    short_rows = [
        {"page": "https://short.example.com/p1", "date": (today - timedelta(days=2)).isoformat(), "impressions": 1000, "clicks": 100},
        {"page": "https://short.example.com/p1", "date": (today - timedelta(days=1)).isoformat(), "impressions": 20, "clicks": 2},
        {"page": "https://short.example.com/p1", "date": today.isoformat(), "impressions": 5, "clicks": 0},
    ]
    detector.ingest_daily_metrics(org_id, site_id, short_rows)

    result = detector.detect_anomalies(site_id=site_id, org_id=org_id)
    assert result["status"] == "insufficient_history"
    assert result["history_days"] == 3
    assert result["anomalies_detected"] == 0
    assert result["anomalies"] == []

    # Verify no alerts were written to database
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT count(*) as cnt FROM alerts WHERE org_id = %s", (org_id,))
            assert cur.fetchone()["cnt"] == 0


def test_gsc_anomaly_api_endpoint_and_tenant_isolation():
    """
    Validates POST /sites/{id}/gsc/detect-anomalies:
    1. Returns successful anomaly detection for authenticated tenant.
    2. Blocks cross-tenant access.
    """
    client = TestClient(app)
    suffix = os.urandom(4).hex()
    org_a = f"org_gsc_a_{suffix}"
    org_b = f"org_gsc_b_{suffix}"
    site_a = f"site_gsc_a_{suffix}"

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO orgs (id, name, slug) VALUES (%s, %s, %s)", (org_a, "Org A", f"orga-{suffix}"))
            cur.execute("INSERT INTO orgs (id, name, slug) VALUES (%s, %s, %s)", (org_b, "Org B", f"orgb-{suffix}"))
            cur.execute("INSERT INTO sites (id, org_id, domain, url) VALUES (%s, %s, %s, %s)", (site_a, org_a, "a.com", "https://a.com"))
        conn.commit()

    token_a = create_auth_token(client, org_a, "admin@a.com")
    token_b = create_auth_token(client, org_b, "admin@b.com")

    # Org A calls detect-anomalies on site_a -> 200 OK
    resp_a = client.post(
        f"/sites/{site_a}/gsc/detect-anomalies",
        headers={"Authorization": f"Bearer {token_a}"}
    )
    assert resp_a.status_code == 200
    data_a = resp_a.json()
    assert "status" in data_a

    # Org B calls detect-anomalies on site_a -> returns 0 anomalies / isolated query
    resp_b = client.post(
        f"/sites/{site_a}/gsc/detect-anomalies",
        headers={"Authorization": f"Bearer {token_b}"}
    )
    assert resp_b.status_code == 200
    data_b = resp_b.json()
    # Org B has no data for site_a in their tenant ledger
    assert data_b["status"] == "insufficient_history"
    assert data_b["history_days"] == 0
