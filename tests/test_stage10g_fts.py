"""
SEOJEV Phase 2: Stage 10g Full-Text Search Test Suite.

Validates Section 6.10:
1. PostgreSQL tsvector and GIN index full-text search.
2. Unified search across findings/opportunities, blueprints, and queries.
3. Relevance ranking (ts_rank) and highlighted excerpts (ts_headline).
4. Multi-entity simultaneous matches for unified search terms.
5. Strict Multi-tenant isolation (Org A cannot view or search Org B's records).
6. Category and site-scoped filtering.
"""
import os
import urllib.parse
from typing import Dict, Any
import pytest
from fastapi.testclient import TestClient

from api.main import app
from database.connection import get_connection
from database.migrator import PostgresMigrator
from api.auth import create_access_token


@pytest.fixture(scope="session", autouse=True)
def prepare_db():
    migrator = PostgresMigrator(db_url="postgresql:///seojev_test")
    migrator.run_migrations()


def create_token(org_id: str, email: str = "searcher@example.com") -> str:
    return create_access_token({"sub": f"usr_{org_id}", "email": email, "org_id": org_id, "role": "admin"})


def test_fts_multi_entity_search_and_ranking():
    """
    Seeds findings, opportunities, blueprints, and queries containing unique target keywords.
    Verifies that a unified search returns all entity types, ranks them appropriately,
    and returns valid excerpts and target links.
    """
    client = TestClient(app)
    suffix = os.urandom(4).hex()
    org_id = f"org_fts_{suffix}"
    site_id = f"site_fts_{suffix}"
    run_id = f"run_fts_{suffix}"

    token = create_token(org_id)

    # 1. Seed database records
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO orgs (id, name, slug) VALUES (%s, %s, %s)", (org_id, f"FTS Org {suffix}", f"fts-{suffix}"))
            cur.execute(
                "INSERT INTO sites (id, org_id, domain, url, vertical) VALUES (%s, %s, %s, %s, 'ecommerce')",
                (site_id, org_id, "vintagebikes.test", "https://vintagebikes.test")
            )
            cur.execute(
                "INSERT INTO runs (id, org_id, site_id, status, progress_pct) VALUES (%s, %s, %s, 'completed', 100.0)",
                (run_id, org_id, site_id)
            )

            # Finding 1 (Target Match: "cruiser transmission")
            cur.execute(
                """
                INSERT INTO findings (
                    id, org_id, run_id, site_id, display_id, subject, severity,
                    url, message, recommended_action
                )
                VALUES (%s, %s, %s, %s, %s, %s, 'CRITICAL', %s, %s, %s)
                """,
                (
                    f"find_{suffix}_1", org_id, run_id, site_id, f"F-CRUISER-{suffix}",
                    "Broken cruiser transmission schema specification",
                    "https://vintagebikes.test/cruiser/transmission-guide",
                    "The cruiser transmission guide page is missing essential product metadata.",
                    "Implement valid VehicleTransmission schema markup on all cruiser pages."
                )
            )

            # Opportunity 1 (Target Match: "cruiser transmission")
            cur.execute(
                """
                INSERT INTO opportunities (
                    id, org_id, run_id, site_id, fingerprint, display_id,
                    type, tier, observation, diagnosis, hypothesis, action
                )
                VALUES (%s, %s, %s, %s, %s, %s, 'technical', 'P1', %s, %s, %s, %s)
                """,
                (
                    f"opp_{suffix}_1", org_id, run_id, site_id, f"fp_cruiser_{suffix}", f"OPP-CRUISER-{suffix}",
                    "Heavy search intent for cruiser transmission parts is landing on generic hub",
                    "Cruiser transmission cluster lacks dedicated landing architecture",
                    "Creating targeted cruiser transmission sub-hubs will capture 450+ high-intent monthly clicks",
                    "Deploy dedicated cruiser transmission category blueprint"
                )
            )

            # Blueprint 1 (Target Match: "cruiser transmission")
            cur.execute(
                """
                INSERT INTO blueprints (
                    id, org_id, run_id, site_id, url, title, page_ref, artifact_path
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    f"bp_{suffix}_1", org_id, run_id, site_id,
                    "https://vintagebikes.test/models/cruiser-transmission-v2",
                    "Cruiser Transmission 5-Speed Overhaul Blueprint",
                    "tpl_cruiser_detail",
                    f"store/{run_id}/cruiser-transmission"
                )
            )

            # Query 1 (Target Match: "cruiser transmission")
            cur.execute(
                """
                INSERT INTO queries (
                    id, org_id, run_id, site_id, query, page_url, clicks, impressions, ctr, position, intent
                )
                VALUES (%s, %s, %s, %s, %s, %s, 140, 2600, 0.0538, 3.8, 'commercial')
                """,
                (
                    f"qry_{suffix}_1", org_id, run_id, site_id,
                    "vintage cruiser transmission rebuild kit",
                    "https://vintagebikes.test/parts/transmission"
                )
            )

            # Control Record: Completely unrelated content (Electric scooter)
            cur.execute(
                """
                INSERT INTO findings (
                    id, org_id, run_id, site_id, display_id, subject, severity,
                    url, message, recommended_action
                )
                VALUES (%s, %s, %s, %s, %s, %s, 'LOW', %s, %s, %s)
                """,
                (
                    f"find_{suffix}_ctrl", org_id, run_id, site_id, f"F-SCOOTER-{suffix}",
                    "Electric scooter battery charging guidelines",
                    "https://vintagebikes.test/scooters/battery",
                    "Battery cycle life warning not highlighted.",
                    "Add lithium battery safety notices."
                )
            )
        conn.commit()

    # 2. Execute Unified Search for "cruiser transmission"
    resp = client.get("/search?q=cruiser+transmission", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()

    assert data["query"] == "cruiser transmission"
    assert data["total_matches"] >= 4

    findings = data["results"]["findings"]
    blueprints = data["results"]["blueprints"]
    queries = data["results"]["queries"]

    # Verify multiple entity types returned
    assert len(findings) >= 2, f"Expected at least 2 findings/opps, got {len(findings)}"
    assert len(blueprints) >= 1, f"Expected at least 1 blueprint, got {len(blueprints)}"
    assert len(queries) >= 1, f"Expected at least 1 query, got {len(queries)}"

    # Verify finding result attributes
    finding_match = next((f for f in findings if f["display_id"] == f"F-CRUISER-{suffix}"), None)
    assert finding_match is not None
    assert "cruiser" in finding_match["title"].lower()
    assert finding_match["score"] > 0.0
    assert "<mark>" in finding_match["excerpt"]
    assert "/runs/" in finding_match["target_url"]

    # Verify opportunity result attributes
    opp_match = next((f for f in findings if f["display_id"] == f"OPP-CRUISER-{suffix}"), None)
    assert opp_match is not None
    assert opp_match["score"] > 0.0
    assert "<mark>" in opp_match["excerpt"]

    # Verify blueprint result attributes
    bp_match = blueprints[0]
    assert bp_match["id"] == f"bp_{suffix}_1"
    assert "cruiser" in bp_match["title"].lower()
    assert bp_match["score"] > 0.0
    assert "<mark>" in bp_match["excerpt"]
    assert "cruiser-transmission" in bp_match["target_url"]

    # Verify query result attributes
    q_match = queries[0]
    assert q_match["id"] == f"qry_{suffix}_1"
    assert "cruiser transmission" in q_match["title"]
    assert q_match["metadata"]["clicks"] == 140
    assert q_match["metadata"]["impressions"] == 2600

    # Verify unrelated record is NOT returned
    assert not any(f["display_id"] == f"F-SCOOTER-{suffix}" for f in findings)


def test_fts_category_filtering_and_site_scoping():
    """
    Tests filtering search by specific category and site_id scoping.
    """
    client = TestClient(app)
    suffix = os.urandom(4).hex()
    org_id = f"org_cat_{suffix}"
    site_a = f"site_a_{suffix}"
    site_b = f"site_b_{suffix}"
    run_a = f"run_a_{suffix}"
    run_b = f"run_b_{suffix}"

    token = create_token(org_id)

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO orgs (id, name, slug) VALUES (%s, %s, %s)", (org_id, f"Cat Org {suffix}", f"cat-{suffix}"))
            cur.execute("INSERT INTO sites (id, org_id, domain, url, vertical) VALUES (%s, %s, 'site-a.test', 'https://site-a.test', 'ecommerce')", (site_a, org_id))
            cur.execute("INSERT INTO sites (id, org_id, domain, url, vertical) VALUES (%s, %s, 'site-b.test', 'https://site-b.test', 'automotive')", (site_b, org_id))
            cur.execute("INSERT INTO runs (id, org_id, site_id, status, progress_pct) VALUES (%s, %s, %s, 'completed', 100.0)", (run_a, org_id, site_a))
            cur.execute("INSERT INTO runs (id, org_id, site_id, status, progress_pct) VALUES (%s, %s, %s, 'completed', 100.0)", (run_b, org_id, site_b))

            # Site A Finding
            cur.execute(
                """
                INSERT INTO findings (id, org_id, run_id, site_id, display_id, subject, url, message, recommended_action)
                VALUES (%s, %s, %s, %s, 'FA-1', 'Canonical discrepancy on Site A vintage motorcycles', 'https://site-a.test/v', 'Missing canonical', 'Add canonical')
                """,
                (f"f_a_{suffix}", org_id, run_a, site_a)
            )

            # Site B Finding (Same keyword: "motorcycles")
            cur.execute(
                """
                INSERT INTO findings (id, org_id, run_id, site_id, display_id, subject, url, message, recommended_action)
                VALUES (%s, %s, %s, %s, 'FB-1', 'Robots noindex on Site B vintage motorcycles catalog', 'https://site-b.test/v', 'Leaked noindex', 'Remove noindex')
                """,
                (f"f_b_{suffix}", org_id, run_b, site_b)
            )

            # Site A Blueprint
            cur.execute(
                """
                INSERT INTO blueprints (id, org_id, run_id, site_id, url, title, page_ref, artifact_path)
                VALUES (%s, %s, %s, %s, 'https://site-a.test/v', 'Site A Motorcycles Blueprint', 'tpl', 'store/a')
                """,
                (f"bp_a_{suffix}", org_id, run_a, site_a)
            )
        conn.commit()

    # 1. Test category=blueprints filter
    resp_bp_only = client.get("/search?q=motorcycles&category=blueprints", headers={"Authorization": f"Bearer {token}"})
    assert resp_bp_only.status_code == 200
    data_bp = resp_bp_only.json()
    assert len(data_bp["results"]["blueprints"]) >= 1
    assert len(data_bp["results"]["findings"]) == 0
    assert len(data_bp["results"]["queries"]) == 0

    # 2. Test site-scoped search (site_a only)
    resp_site_a = client.get(f"/sites/{site_a}/search?q=motorcycles", headers={"Authorization": f"Bearer {token}"})
    assert resp_site_a.status_code == 200
    data_site_a = resp_site_a.json()
    # Should contain Site A finding, but NOT Site B finding
    findings_a = data_site_a["results"]["findings"]
    assert any(f["id"] == f"f_a_{suffix}" for f in findings_a)
    assert not any(f["id"] == f"f_b_{suffix}" for f in findings_a)


def test_fts_multi_tenant_isolation():
    """
    CRITICAL MULTI-TENANT TEST:
    Confirms Org A and Org B with identical secret tokens in their findings and queries
    CANNOT see or search each other's data under any condition.
    """
    client = TestClient(app)
    suffix = os.urandom(4).hex()
    secret_term = f"ZephyrSecretTerm{suffix}"

    org_a = f"org_iso_a_{suffix}"
    org_b = f"org_iso_b_{suffix}"
    site_a = f"site_iso_a_{suffix}"
    site_b = f"site_iso_b_{suffix}"
    run_a = f"run_iso_a_{suffix}"
    run_b = f"run_iso_b_{suffix}"

    token_a = create_token(org_a, "alpha@example.com")
    token_b = create_token(org_b, "bravo@example.com")

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO orgs (id, name, slug) VALUES (%s, %s, %s)", (org_a, "Org A", f"org-a-{suffix}"))
            cur.execute("INSERT INTO orgs (id, name, slug) VALUES (%s, %s, %s)", (org_b, "Org B", f"org-b-{suffix}"))

            cur.execute("INSERT INTO sites (id, org_id, domain, url, vertical) VALUES (%s, %s, 'alpha.test', 'https://alpha.test', 'auto')", (site_a, org_a))
            cur.execute("INSERT INTO sites (id, org_id, domain, url, vertical) VALUES (%s, %s, 'bravo.test', 'https://bravo.test', 'auto')", (site_b, org_b))

            cur.execute("INSERT INTO runs (id, org_id, site_id, status, progress_pct) VALUES (%s, %s, %s, 'completed', 100.0)", (run_a, org_a, site_a))
            cur.execute("INSERT INTO runs (id, org_id, site_id, status, progress_pct) VALUES (%s, %s, %s, 'completed', 100.0)", (run_b, org_b, site_b))

            # Org A record
            cur.execute(
                """
                INSERT INTO findings (id, org_id, run_id, site_id, display_id, subject, url, message, recommended_action)
                VALUES (%s, %s, %s, %s, 'FA-CONFIDENTIAL', %s, 'https://alpha.test/p', 'Secret Alpha message', 'Fix')
                """,
                (f"f_a_{suffix}", org_a, run_a, site_a, f"Alpha proprietary audit for {secret_term}")
            )

            # Org B record
            cur.execute(
                """
                INSERT INTO findings (id, org_id, run_id, site_id, display_id, subject, url, message, recommended_action)
                VALUES (%s, %s, %s, %s, 'FB-CONFIDENTIAL', %s, 'https://bravo.test/p', 'Secret Bravo message', 'Fix')
                """,
                (f"f_b_{suffix}", org_b, run_b, site_b, f"Bravo proprietary audit for {secret_term}")
            )
        conn.commit()

    # Org A searches for secret_term
    resp_a = client.get(f"/search?q={secret_term}", headers={"Authorization": f"Bearer {token_a}"})
    assert resp_a.status_code == 200
    res_a = resp_a.json()["results"]["findings"]
    assert len(res_a) == 1
    assert res_a[0]["id"] == f"f_a_{suffix}"
    assert res_a[0]["site_id"] == site_a

    # Org B searches for secret_term
    resp_b = client.get(f"/search?q={secret_term}", headers={"Authorization": f"Bearer {token_b}"})
    assert resp_b.status_code == 200
    res_b = resp_b.json()["results"]["findings"]
    assert len(res_b) == 1
    assert res_b[0]["id"] == f"f_b_{suffix}"
    assert res_b[0]["site_id"] == site_b

    # Org A cannot access Org B's site search
    # In ScopedQuery/API conventions, attempting to query Org B's site as Org A yields 0 results
    resp_a_on_b = client.get(f"/sites/{site_b}/search?q={secret_term}", headers={"Authorization": f"Bearer {token_a}"})
    assert resp_a_on_b.status_code == 200
    assert resp_a_on_b.json()["total_matches"] == 0
