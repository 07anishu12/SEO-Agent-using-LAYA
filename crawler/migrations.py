import os
import sqlite3
import datetime
from typing import List

class MigrationRunner:
    def __init__(self, db_path: str = "data/seo.db", migrations_dir: str = "crawler/migrations"):
        self.db_path = db_path
        self.migrations_dir = migrations_dir

    def run_migrations(self) -> List[str]:
        """Applies all unapplied numbered SQL migrations in ascending order."""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        applied = []
        try:
            # Ensure migration table exists
            conn.execute("""
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                applied_at TEXT NOT NULL
            );
            """)
            conn.commit()

            # Query existing versions
            cursor = conn.execute("SELECT version FROM schema_migrations")
            existing_versions = {row[0] for row in cursor.fetchall()}

            # Discover migration files
            if not os.path.exists(self.migrations_dir):
                return applied

            files = sorted(f for f in os.listdir(self.migrations_dir) if f.endswith(".sql"))
            for fname in files:
                try:
                    version_prefix = fname.split("_")[0]
                    version = int(version_prefix)
                except ValueError:
                    continue

                if version not in existing_versions:
                    fpath = os.path.join(self.migrations_dir, fname)
                    with open(fpath, "r", encoding="utf-8") as f:
                        sql_script = f.read()

                    # Execute migration
                    conn.executescript(sql_script)
                    now_str = datetime.datetime.now().isoformat()
                    conn.execute(
                        "INSERT INTO schema_migrations (version, name, applied_at) VALUES (?, ?, ?)",
                        (version, fname, now_str)
                    )
                    conn.commit()
                    applied.append(fname)

            # Apply idempotent column additions for existing V2 tables
            self._ensure_v3_columns(conn)

            return applied
        finally:
            conn.close()

    def _ensure_v3_columns(self, conn: sqlite3.Connection):
        """Safely ensure V3 columns exist on legacy V2 tables."""
        # 1. links table: dom_region, anchor_quality, position, is_rendered
        cur = conn.execute("PRAGMA table_info(links);")
        link_cols = {row[1] for row in cur.fetchall()}
        new_link_cols = {
            "dom_region": "TEXT DEFAULT 'body'",
            "anchor_quality": "TEXT DEFAULT 'descriptive'",
            "link_position": "INTEGER DEFAULT 0",
            "is_rendered": "INTEGER DEFAULT 0"
        }
        for col, col_type in new_link_cols.items():
            if col not in link_cols:
                try:
                    conn.execute(f"ALTER TABLE links ADD COLUMN {col} {col_type};")
                except Exception:
                    pass

        # 2. urls table: priority_score, is_trap, trap_reason
        cur = conn.execute("PRAGMA table_info(urls);")
        url_cols = {row[1] for row in cur.fetchall()}
        new_url_cols = {
            "priority_score": "REAL DEFAULT 0.0",
            "is_trap": "INTEGER DEFAULT 0",
            "trap_reason": "TEXT"
        }
        for col, col_type in new_url_cols.items():
            if col not in url_cols:
                try:
                    conn.execute(f"ALTER TABLE urls ADD COLUMN {col} {col_type};")
                except Exception:
                    pass

        # 3. pages table: content_hash_ref, rendered_hash_ref
        cur = conn.execute("PRAGMA table_info(pages);")
        page_cols = {row[1] for row in cur.fetchall()}
        new_page_cols = {
            "content_hash_ref": "TEXT",
            "rendered_hash_ref": "TEXT"
        }
        for col, col_type in new_page_cols.items():
            if col not in page_cols:
                try:
                    conn.execute(f"ALTER TABLE pages ADD COLUMN {col} {col_type};")
                except Exception:
                    pass

        conn.commit()
