"""
SEOJEV Phase 2: PostgreSQL Migrations & ETL Test Suite.
Tests:
1. Migration test: Schema applies cleanly to a fresh Postgres instance.
2. ETL correctness test: Baseline crawl ETL row counts match source SQLite counts.
3. Idempotency test: Running ETL twice on the same run_id does not duplicate rows.
4. Isolation test: Two orgs' data inserted; querying as org A returns 0 rows from org B.
"""
import os
import sqlite3
import pytest
import psycopg

from database.migrator import PostgresMigrator
from database.etl import run_etl
from database.scoped_query import ScopedQuery, IsolationViolationError
from lab.server import SyntheticSiteServer
from engine.pipeline import SEOJEVPipeline


TEST_DB_NAME = "seojev_test"
TEST_DB_URL = os.environ.get("DATABASE_URL") or f"postgresql://postgres:postgres@localhost:5432/{TEST_DB_NAME}"
ADMIN_DB_URL = os.environ.get("ADMIN_DB_URL") or "postgresql://postgres:postgres@localhost:5432/postgres"



@pytest.fixture(scope="session", autouse=True)
def ensure_test_database():
    """Ensure the main test database exists and has latest migrations applied."""
    try:
        with psycopg.connect(ADMIN_DB_URL, autocommit=True) as conn:
            with conn.cursor() as cur:
                cur.execute(f"SELECT 1 FROM pg_database WHERE datname = '{TEST_DB_NAME}'")
                if not cur.fetchone():
                    cur.execute(f"CREATE DATABASE {TEST_DB_NAME}")
    except Exception:
        pass

    migrator = PostgresMigrator(db_url=TEST_DB_URL)
    migrator.run_migrations()
    yield


def test_migration_fresh_postgres_instance():
    """
    Migration test: Schema applies cleanly to a completely fresh Postgres instance/database.
    Asserts all 18 tables and org_id isolation columns exist.
    """
    fresh_db = "seojev_fresh_mig_temp"
    fresh_url = f"postgresql://postgres:postgres@localhost:5432/{fresh_db}"

    # Create fresh database
    with psycopg.connect(ADMIN_DB_URL, autocommit=True) as admin_conn:
        with admin_conn.cursor() as cur:
            cur.execute(f"DROP DATABASE IF EXISTS {fresh_db}")
            cur.execute(f"CREATE DATABASE {fresh_db}")

    try:
        # Run migrations on fresh database
        migrator = PostgresMigrator(db_url=fresh_url)
        applied = migrator.run_migrations()
        assert len(applied) >= 1, "Expected at least one migration script to apply."

        # Verify all 18 required tables exist and possess org_id
        expected_tables = [
            "orgs", "users", "api_keys", "sites", "crawl_configs", "runs",
            "findings", "opportunities", "work_orders", "blueprints",
            "templates", "gsc_summary", "snapshots", "snapshot_diffs",
            "watch_configs", "alerts", "feedback", "audit_log"
        ]

        with psycopg.connect(fresh_url) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT table_name
                    FROM information_schema.tables
                    WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
                """)
                tables = {row[0] for row in cur.fetchall()}

                for t in expected_tables:
                    assert t in tables, f"Expected table '{t}' missing from migrated fresh schema."

                # Verify org_id column on every single table
                for t in expected_tables:
                    cur.execute("""
                        SELECT column_name
                        FROM information_schema.columns
                        WHERE table_schema = 'public' AND table_name = %s AND column_name = 'org_id'
                    """, (t,))
                    if t == "orgs":
                        # orgs table primary key is id
                        continue
                    assert cur.fetchone() is not None, f"Table '{t}' is missing required 'org_id' column."

    finally:
        with psycopg.connect(ADMIN_DB_URL, autocommit=True) as admin_conn:
            with admin_conn.cursor() as cur:
                cur.execute(f"DROP DATABASE IF EXISTS {fresh_db}")


@pytest.mark.asyncio
async def test_etl_correctness_against_baseline():
    """
    ETL correctness test: Run baseline site through pipeline, run ETL,
    and assert Postgres row counts match source SQLite counts for findings,
    opportunities, work_orders, and templates.
    """
    port = 8911
    server = SyntheticSiteServer(port=port)
    server.start()

    db_path = "data/test_etl_baseline.db"
    crawl_id = "crawl_etl_baseline_test"
    org_id = "org_test_correctness"

    if os.path.exists(db_path):
        os.remove(db_path)

    try:
        pipeline = SEOJEVPipeline(
            target_url=f"http://127.0.0.1:{port}/",
            crawl_id=crawl_id,
            db_path=db_path,
            output_dir="reports/test_etl/",
            options={
                "max_pages": 50,
                "concurrency": 2,
                "fresh": True,
                "show_live_display": False
            }
        )
        res = await pipeline.run_all()
        assert res["status"] == "completed"

        # Read exact counts from source SQLite database
        with sqlite3.connect(db_path) as s_conn:
            s_conn.row_factory = sqlite3.Row
            s_cur = s_conn.cursor()
            sqlite_findings = s_cur.execute("SELECT count(*) FROM findings WHERE run_id = ?", (crawl_id,)).fetchone()[0]
            sqlite_opps = s_cur.execute("SELECT count(*) FROM opportunities WHERE run_id = ?", (crawl_id,)).fetchone()[0]
            sqlite_wos = s_cur.execute("SELECT count(*) FROM work_orders WHERE run_id = ?", (crawl_id,)).fetchone()[0]
            sqlite_tpls = s_cur.execute("SELECT count(*) FROM templates WHERE crawl_id = ?", (crawl_id,)).fetchone()[0]

        # Execute ETL into PostgreSQL
        etl_res = run_etl(
            sqlite_db_path=db_path,
            crawl_id=crawl_id,
            org_id=org_id,
            db_url=TEST_DB_URL
        )
        assert etl_res["status"] == "success"

        # Query PostgreSQL via ScopedQuery and assert row counts match
        with ScopedQuery(org_id=org_id, db_url=TEST_DB_URL) as sq:
            pg_findings = sq.count("findings", where="run_id = %(r)s", params={"r": crawl_id})
            pg_opps = sq.count("opportunities", where="run_id = %(r)s", params={"r": crawl_id})
            pg_wos = sq.count("work_orders", where="run_id = %(r)s", params={"r": crawl_id})
            pg_tpls = sq.count("templates", where="run_id = %(r)s", params={"r": crawl_id})

            assert pg_findings == sqlite_findings, f"Findings mismatch: PG {pg_findings} != SQLite {sqlite_findings}"
            assert pg_opps == sqlite_opps, f"Opportunities mismatch: PG {pg_opps} != SQLite {sqlite_opps}"
            assert pg_wos == sqlite_wos, f"Work orders mismatch: PG {pg_wos} != SQLite {sqlite_wos}"
            assert pg_tpls == sqlite_tpls, f"Templates mismatch: PG {pg_tpls} != SQLite {sqlite_tpls}"

            # Verify structured opportunity fields
            sample_opp = sq.fetch_one("opportunities", where="run_id = %(r)s", params={"r": crawl_id})
            assert sample_opp is not None
            assert sample_opp["fingerprint"]
            assert sample_opp["display_id"]
            assert sample_opp["tier"]
            assert sample_opp["confidence"]
            assert sample_opp["effort"]
            assert sample_opp["priority_score"] is not None
            assert sample_opp["factors_json"] is not None

    finally:
        server.stop()
        if os.path.exists(db_path):
            try:
                os.remove(db_path)
            except Exception:
                pass


def resolve_populated_crawl(sqlite_db_path="data/seo.db") -> tuple[str, str]:
    """
    Resolves a crawl_id with populated work_orders, findings, opportunities, and templates.
    Fails fast with a clear setup-time precondition assertion (Option 6b) rather than
    failing deep inside tests. If static file lacks populated data, dynamically generates
    a self-contained test fixture (Option 6a).
    """
    if os.path.exists(sqlite_db_path):
        with sqlite3.connect(sqlite_db_path) as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT w.run_id
                FROM work_orders w
                WHERE w.run_id IN (SELECT DISTINCT run_id FROM findings)
                GROUP BY w.run_id
                HAVING count(*) > 0
                ORDER BY count(*) ASC
                LIMIT 1
            """)
            row = cur.fetchone()
            if row:
                crawl_id = row[0]
                cur.execute("SELECT count(*) FROM work_orders WHERE run_id = ?", (crawl_id,))
                w_count = cur.fetchone()[0]
                assert w_count > 0, (
                    f"Fixture missing expected data: crawl_id '{crawl_id}' in '{sqlite_db_path}' has {w_count} work_orders. "
                    "Precondition requires populated work_orders."
                )
                return sqlite_db_path, crawl_id

    # Option 6a: Generate self-contained populated fixture
    fixture_db = "data/test_fixture_populated.db"
    fixture_crawl = "crawl_fixture_auto"
    import asyncio
    port = 8913
    server = SyntheticSiteServer(port=port)
    server.start()
    try:
        pipeline = SEOJEVPipeline(
            target_url=f"http://127.0.0.1:{port}/",
            crawl_id=fixture_crawl,
            db_path=fixture_db,
            output_dir="reports/fixture_auto/",
            options={"max_pages": 30, "concurrency": 2, "fresh": True, "show_live_display": False}
        )
        asyncio.run(pipeline.run_all())
    finally:
        server.stop()
    return fixture_db, fixture_crawl


def test_etl_idempotency():
    """
    Idempotency test: Run ETL twice on the same run_id; assert row counts
    are unchanged the second time.
    """
    sqlite_db_path, crawl_id = resolve_populated_crawl()
    org_id = "org_test_idempotency"

    # Precondition assertion (Option 6b)
    with sqlite3.connect(sqlite_db_path) as s_conn:
        pre_wos = s_conn.execute("SELECT count(*) FROM work_orders WHERE run_id = ?", (crawl_id,)).fetchone()[0]
        assert pre_wos > 0, (
            f"Fixture missing expected data: '{crawl_id}' in '{sqlite_db_path}' has 0 work_orders. "
            "Precondition requires populated work_orders table."
        )

    # First ETL run
    res1 = run_etl(
        sqlite_db_path=sqlite_db_path,
        crawl_id=crawl_id,
        org_id=org_id,
        db_url=TEST_DB_URL
    )
    assert res1["status"] == "success"

    with ScopedQuery(org_id=org_id, db_url=TEST_DB_URL) as sq:
        findings_1 = sq.count("findings", where="run_id = %(r)s", params={"r": crawl_id})
        opps_1 = sq.count("opportunities", where="run_id = %(r)s", params={"r": crawl_id})
        wos_1 = sq.count("work_orders", where="run_id = %(r)s", params={"r": crawl_id})
        tpls_1 = sq.count("templates", where="run_id = %(r)s", params={"r": crawl_id})

    # Second ETL run on same crawl_id
    res2 = run_etl(
        sqlite_db_path=sqlite_db_path,
        crawl_id=crawl_id,
        org_id=org_id,
        db_url=TEST_DB_URL
    )
    assert res2["status"] == "success"

    with ScopedQuery(org_id=org_id, db_url=TEST_DB_URL) as sq:
        findings_2 = sq.count("findings", where="run_id = %(r)s", params={"r": crawl_id})
        opps_2 = sq.count("opportunities", where="run_id = %(r)s", params={"r": crawl_id})
        wos_2 = sq.count("work_orders", where="run_id = %(r)s", params={"r": crawl_id})
        tpls_2 = sq.count("templates", where="run_id = %(r)s", params={"r": crawl_id})

    assert findings_1 == findings_2 > 0, f"Findings row count changed after second ETL: {findings_1} vs {findings_2}"
    assert opps_1 == opps_2 > 0, f"Opportunities count changed after second ETL: {opps_1} vs {opps_2}"
    assert wos_1 == wos_2 > 0, f"Work orders count changed after second ETL: {wos_1} vs {wos_2}"
    assert tpls_1 == tpls_2 > 0, f"Templates count changed after second ETL: {tpls_1} vs {tpls_2}"


def test_multi_tenant_isolation():
    """
    Isolation test: Insert two orgs' data, query as org A,
    assert zero rows from org B ever appear.
    """
    sqlite_db_path, crawl_id_a = resolve_populated_crawl()
    crawl_id_b = "crawl_20260923_234236"
    org_a = "org_alpha_tenant"
    org_b = "org_beta_tenant"

    # Precondition assertion
    with sqlite3.connect(sqlite_db_path) as s_conn:
        pre_wos = s_conn.execute("SELECT count(*) FROM work_orders WHERE run_id = ?", (crawl_id_a,)).fetchone()[0]
        assert pre_wos > 0, (
            f"Fixture missing expected data: '{crawl_id_a}' in '{sqlite_db_path}' has 0 work_orders."
        )

    # Ingest distinct dataset runs for each org under their isolated tenant namespaces
    run_etl(sqlite_db_path=sqlite_db_path, crawl_id=crawl_id_a, org_id=org_a, db_url=TEST_DB_URL)
    run_etl(sqlite_db_path=sqlite_db_path, crawl_id=crawl_id_b, org_id=org_b, db_url=TEST_DB_URL)

    with ScopedQuery(org_id=org_a, db_url=TEST_DB_URL) as sq_a:
        # Querying as org A
        findings_a = sq_a.fetch_all("findings")
        opps_a = sq_a.fetch_all("opportunities")
        wos_a = sq_a.fetch_all("work_orders")
        tpls_a = sq_a.fetch_all("templates")
        runs_a = sq_a.fetch_all("runs")

        assert len(findings_a) > 0
        assert len(opps_a) > 0
        assert len(wos_a) > 0
        assert len(tpls_a) > 0
        assert len(runs_a) > 0

        # Assert every single row belongs strictly to org_a
        for row in findings_a:
            assert row["org_id"] == org_a, f"Leak detected! Found row with org_id '{row['org_id']}' in org A query."
        for row in opps_a:
            assert row["org_id"] == org_a
        for row in wos_a:
            assert row["org_id"] == org_a
        for row in tpls_a:
            assert row["org_id"] == org_a
        for row in runs_a:
            assert row["org_id"] == org_a

    with ScopedQuery(org_id=org_b, db_url=TEST_DB_URL) as sq_b:
        # Querying as org B
        findings_b = sq_b.fetch_all("findings")
        opps_b = sq_b.fetch_all("opportunities")
        wos_b = sq_b.fetch_all("work_orders")

        assert len(findings_b) > 0
        assert len(opps_b) > 0
        assert len(wos_b) > 0
        for row in findings_b:
            assert row["org_id"] == org_b, f"Leak detected! Found row with org_id '{row['org_id']}' in org B query."
        for row in opps_b:
            assert row["org_id"] == org_b
        for row in wos_b:
            assert row["org_id"] == org_b

    # Verify query without org_id raises IsolationViolationError
    with pytest.raises(IsolationViolationError):
        ScopedQuery(org_id="")

    with ScopedQuery(org_id=org_a, db_url=TEST_DB_URL) as sq_a:
        # Attempting raw cross-tenant query with mismatching parameter
        with pytest.raises(IsolationViolationError):
            sq_a.execute_scoped_raw(
                "SELECT * FROM findings WHERE org_id = %(org_id)s",
                params={"org_id": org_b}
            )
