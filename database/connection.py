"""
PostgreSQL Connection Factory for SEOJEV Platform.
Supports psycopg 3 connection pools and row factories.
"""
import os
import getpass
from typing import Optional
from dotenv import load_dotenv
import psycopg
from psycopg.rows import dict_row

load_dotenv()

def get_default_db_url() -> str:
    url = os.environ.get("DATABASE_URL")
    if url:
        return url
    return f"postgresql://postgres:postgres@localhost:5432/{os.environ.get('POSTGRES_DB', 'seojev_test')}"

def normalize_db_url(url: Optional[str]) -> str:
    default_url = get_default_db_url()
    if not url:
        return default_url
    if url.startswith("postgresql:///"):
        if os.environ.get("DATABASE_URL"):
            return os.environ["DATABASE_URL"]
        dbname = url.replace("postgresql:///", "") or os.environ.get('POSTGRES_DB', 'seojev_test')
        return f"postgresql://postgres:postgres@localhost:5432/{dbname}"
    return url

def get_connection(db_url: Optional[str] = None, autocommit: bool = False, max_retries: int = 3) -> psycopg.Connection:
    url = normalize_db_url(db_url)
    last_err = None
    for attempt in range(max_retries):
        try:
            conn = psycopg.connect(url, row_factory=dict_row, autocommit=autocommit)
            return conn
        except psycopg.OperationalError as e:
            last_err = e
            if attempt < max_retries - 1:
                import time
                time.sleep(0.5 * (2 ** attempt))
            else:
                raise


def check_db_health(db_url: Optional[str] = None) -> dict:
    """Verifies database connectivity by executing a lightweight query."""
    try:
        with get_connection(db_url, max_retries=1) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1 AS alive")
                row = cur.fetchone()
                if row and row.get("alive") == 1:
                    return {"status": "ok", "healthy": True}
                return {"status": "degraded", "healthy": False, "error": "Unexpected query response"}
    except Exception as e:
        return {"status": "error", "healthy": False, "error": str(e)}

