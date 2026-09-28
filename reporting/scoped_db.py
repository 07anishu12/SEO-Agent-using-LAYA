"""Read-only per-run views keep report queries from mixing historical crawls."""
from contextlib import contextmanager
import sqlite3


@contextmanager
def report_connection(db_path, run_id=None):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        if run_id is not None:
            literal = conn.execute("SELECT quote(?)", (run_id,)).fetchone()[0]
            tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")]
            for table in tables:
                name = '"' + table.replace('"', '""') + '"'
                columns = {r[1] for r in conn.execute(f"PRAGMA table_info({name})")}
                key = "crawl_id" if "crawl_id" in columns else "run_id" if "run_id" in columns else None
                if key:
                    conn.execute(f"CREATE TEMP VIEW {name} AS SELECT * FROM main.{name} WHERE {key}={literal}")
        yield conn
    finally:
        conn.close()
