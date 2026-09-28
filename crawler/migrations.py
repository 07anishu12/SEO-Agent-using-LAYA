import datetime
import os
import sqlite3
from typing import List
from laya.persistence import DECISION_COLUMNS, LEGACY_COLUMNS, OPPORTUNITY_COLUMNS


class MigrationRunner:
    def __init__(self, db_path="data/seo.db", migrations_dir="crawler/migrations"):
        self.db_path = db_path
        self.migrations_dir = migrations_dir

    @staticmethod
    def _ensure_columns(conn, table, columns):
        existing = {r[1] for r in conn.execute(f'PRAGMA table_info("{table}")')}
        if not existing:
            raise sqlite3.OperationalError(f"Cannot migrate missing table {table}")
        for column, definition in columns.items():
            if column not in existing:
                conn.execute(f'ALTER TABLE "{table}" ADD COLUMN "{column}" {definition}')

    def run_migrations(self) -> List[str]:
        os.makedirs(os.path.dirname(os.path.abspath(self.db_path)), exist_ok=True)
        applied = []
        with sqlite3.connect(self.db_path, timeout=30) as conn:
            conn.execute("CREATE TABLE IF NOT EXISTS schema_migrations (version INTEGER PRIMARY KEY, name TEXT NOT NULL, applied_at TEXT NOT NULL)")
            existing = {r[0] for r in conn.execute("SELECT version FROM schema_migrations")}
            for filename in sorted(os.listdir(self.migrations_dir)):
                if not filename.endswith(".sql") or not filename.split("_")[0].isdigit():
                    continue
                version = int(filename.split("_")[0])
                if version not in existing:
                    with open(os.path.join(self.migrations_dir, filename)) as source:
                        conn.executescript(source.read())
                    conn.execute("INSERT INTO schema_migrations VALUES (?, ?, ?)", (version, filename, datetime.datetime.now().isoformat()))
                    conn.commit()
                    applied.append(filename)
            self._ensure_v3_columns(conn)
            self._ensure_laya_decision_v2(conn)
            if 2 not in existing:
                # Recoverable via the required pre-migration SQLite backup. Only
                # known fabricated legacy stamps are cleared, never model output.
                assignments = [f'"{c}"=NULL' for c in OPPORTUNITY_COLUMNS if c != "laya_validated"]
                conn.execute(f"UPDATE opportunities SET {','.join(assignments)}, laya_validated=0 WHERE laya_action='optimize' OR laya_decision_id LIKE 'dec_laya_OPP-%'")
                conn.execute("UPDATE stage_checkpoints SET status='stale' WHERE stage IN ('P4_CALIBRATION','P5_WORK_ORDERS','P6_DELIVERABLES','P4_LAYA_DECISION_ENGINE','P5_VALIDATED_OPPORTUNITIES','P6_REPORTS')")
                conn.execute("INSERT INTO schema_migrations VALUES (2, 'laya_strict_mlx_provenance', ?)", (datetime.datetime.now().isoformat(),))
                applied.append("laya_strict_mlx_provenance")
        return applied

    def _ensure_v3_columns(self, conn):
        # These base crawler tables are optional when only V3 tables are created.
        additions = {
            "links": {"dom_region": "TEXT DEFAULT 'body'", "anchor_quality": "TEXT DEFAULT 'descriptive'", "link_position": "INTEGER DEFAULT 0", "is_rendered": "INTEGER DEFAULT 0"},
            "urls": {"priority_score": "REAL DEFAULT 0.0", "is_trap": "INTEGER DEFAULT 0", "trap_reason": "TEXT"},
            "pages": {"content_hash_ref": "TEXT", "rendered_hash_ref": "TEXT"},
            "work_orders": {"laya_action": "TEXT", "laya_confidence": "REAL", "laya_decision_id": "TEXT", "laya_gate": "TEXT"},
        }
        for table, columns in additions.items():
            if conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone():
                self._ensure_columns(conn, table, columns)
        conn.execute("CREATE TABLE IF NOT EXISTS stage_checkpoints (crawl_id TEXT NOT NULL, stage TEXT NOT NULL, status TEXT NOT NULL, metadata_json TEXT, completed_at TEXT, PRIMARY KEY(crawl_id, stage))")

    def _ensure_laya_decision_v2(self, conn):
        """Inspect and ALTER every evolving table; CREATE alone is insufficient."""
        conn.execute("CREATE TABLE IF NOT EXISTS laya_decisions (id INTEGER PRIMARY KEY AUTOINCREMENT)")
        conn.execute("CREATE TABLE IF NOT EXISTS laya_decision_log (decision_id TEXT PRIMARY KEY)")
        self._ensure_columns(conn, "laya_decisions", {**DECISION_COLUMNS, **LEGACY_COLUMNS})
        self._ensure_columns(conn, "laya_decision_log", DECISION_COLUMNS)
        self._ensure_columns(conn, "opportunities", OPPORTUNITY_COLUMNS)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_laya_cache_identity ON laya_decision_log(input_hash, checkpoint_id, prompt_version)")
