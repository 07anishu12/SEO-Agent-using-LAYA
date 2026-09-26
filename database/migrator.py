"""
PostgreSQL Schema Migrator for SEOJEV.
Tracks and applies versioned migration scripts idempotently.
"""
import os
import glob
from typing import List, Optional
from .connection import get_connection

class PostgresMigrator:
    def __init__(self, db_url: Optional[str] = None):
        self.db_url = db_url

    def run_migrations(self, migrations_dir: Optional[str] = None) -> List[str]:
        m_dir = migrations_dir or os.path.join(os.path.dirname(__file__), "migrations")
        applied = []
        with get_connection(self.db_url) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS schema_migrations (
                        version VARCHAR(255) PRIMARY KEY,
                        applied_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                    );
                """)
                cur.execute("SELECT version FROM schema_migrations")
                existing = {r["version"] for r in cur.fetchall()}

                sql_files = sorted(glob.glob(os.path.join(m_dir, "*.sql")))
                for file_path in sql_files:
                    version = os.path.basename(file_path)
                    if version not in existing:
                        with open(file_path, "r", encoding="utf-8") as f:
                            sql = f.read()
                        cur.execute(sql)
                        cur.execute(
                            "INSERT INTO schema_migrations (version) VALUES (%s)",
                            (version,)
                        )
                        applied.append(version)
            conn.commit()
        return applied
