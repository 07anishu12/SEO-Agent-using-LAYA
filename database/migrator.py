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


def check_migrations_applied(db_url: Optional[str] = None, migrations_dir: Optional[str] = None) -> dict:
    """Verifies whether all pending database migrations have been applied."""
    m_dir = migrations_dir or os.path.join(os.path.dirname(__file__), "migrations")
    try:
        sql_files = sorted(glob.glob(os.path.join(m_dir, "*.sql")))
        expected = [os.path.basename(f) for f in sql_files]
        with get_connection(db_url) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS schema_migrations (
                        version VARCHAR(255) PRIMARY KEY,
                        applied_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                    );
                """)
                cur.execute("SELECT version FROM schema_migrations")
                applied = {r["version"] for r in cur.fetchall()}
        pending = [v for v in expected if v not in applied]
        return {
            "status": "ok" if not pending else "pending",
            "healthy": len(pending) == 0,
            "applied_count": len(applied),
            "pending_count": len(pending),
            "pending_versions": pending
        }
    except Exception as e:
        return {"status": "error", "healthy": False, "error": str(e)}


def seed_dev_user(db_url: Optional[str] = None):
    """Idempotently seeds a default admin user for local development ONLY."""
    env = (os.environ.get("ENV") or os.environ.get("ENVIRONMENT") or "development").lower()
    if env in ("production", "prod"):
        raise RuntimeError("CRITICAL SECURITY ERROR: seed_dev_user is forbidden in production environments.")

    import bcrypt
    email = "admin@seojev.local"
    pw = "Password123!"
    pw_hash = bcrypt.hashpw(pw.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    with get_connection(db_url) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO orgs (id, name, slug)
                VALUES ('org_default', 'Default Organization', 'default-org')
                ON CONFLICT (id) DO NOTHING;
            """)
            cur.execute("""
                INSERT INTO users (id, org_id, email, password_hash, role)
                VALUES ('user_default_admin', 'org_default', %s, %s, 'admin')
                ON CONFLICT (email) DO UPDATE SET password_hash = EXCLUDED.password_hash;
            """, (email, pw_hash))
        conn.commit()


if __name__ == "__main__":
    migrator = PostgresMigrator()
    applied = migrator.run_migrations()
    if applied:
        print(f"Applied migrations: {', '.join(applied)}")
    else:
        print("Database schema is up to date.")
    env = (os.environ.get("ENV") or os.environ.get("ENVIRONMENT") or "development").lower()
    if env not in ("production", "prod"):
        seed_dev_user()



