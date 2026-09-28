import sqlite3
from pathlib import Path
from crawler.migrations import MigrationRunner
from crawler.storage import CrawlStorage
from laya.persistence import DECISION_COLUMNS, LEGACY_COLUMNS, OPPORTUNITY_COLUMNS


def assert_schema(path):
    with sqlite3.connect(path) as conn:
        for table, expected in (("laya_decisions", {**DECISION_COLUMNS, **LEGACY_COLUMNS}), ("laya_decision_log", DECISION_COLUMNS), ("opportunities", OPPORTUNITY_COLUMNS)):
            assert set(expected) <= {r[1] for r in conn.execute(f"PRAGMA table_info({table})")}
        assert conn.execute("SELECT COUNT(*) FROM schema_migrations WHERE version=2").fetchone()[0] == 1


def test_fresh_migration_idempotent(tmp_path):
    db = str(tmp_path / "fresh.db")
    CrawlStorage(db)
    migrator = MigrationRunner(db)
    migrator.run_migrations()
    assert_schema(db)
    assert migrator.run_migrations() == []
    assert_schema(db)


def test_legacy_19_column_schema(tmp_path):
    # Never copy an unbounded private site DB into a development test.
    db = str(tmp_path / "legacy.db")
    CrawlStorage(db)
    with sqlite3.connect(db) as conn:
        definitions = list(DECISION_COLUMNS.items())[:19]
        conn.execute("CREATE TABLE laya_decision_log ("+",".join(f"{k} {v}" for k,v in definitions)+")")
    migrator = MigrationRunner(db)
    migrator.run_migrations()
    migrator.run_migrations()
    assert_schema(db)
    with sqlite3.connect(db) as conn:
        assert conn.execute("SELECT COUNT(*) FROM opportunities WHERE laya_action='optimize' OR laya_decision_id LIKE 'dec_laya_OPP-%'").fetchone()[0] == 0
