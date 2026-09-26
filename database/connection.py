"""
PostgreSQL Connection Factory for SEOJEV Platform.
Supports psycopg 3 connection pools and row factories.
"""
import os
import getpass
from typing import Optional
import psycopg
from psycopg.rows import dict_row

def get_default_db_url() -> str:
    url = os.environ.get("DATABASE_URL")
    if url:
        return url
    user = getpass.getuser()
    return f"postgresql:///{os.environ.get('POSTGRES_DB', 'seojev_test')}"

def get_connection(db_url: Optional[str] = None, autocommit: bool = False) -> psycopg.Connection:
    url = db_url or get_default_db_url()
    conn = psycopg.connect(url, row_factory=dict_row, autocommit=autocommit)
    return conn
