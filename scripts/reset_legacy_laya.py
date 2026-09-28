#!/usr/bin/env python3
"""One-time idempotent script to reset legacy fake Laya stamps and unblock revalidation."""
import argparse
import datetime
import shutil
import sqlite3
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from laya.persistence import OPPORTUNITY_COLUMNS


def reset_legacy(db_path: str = "data/seo.db", backup: bool = True):
    db_file = Path(db_path).resolve()
    if not db_file.exists():
        raise FileNotFoundError(f"Database not found: {db_file}")

    if backup:
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        bak_file = db_file.parent / f"{db_file.name}.bak-reset-{timestamp}"
        print(f"Creating pre-reset backup at: {bak_file}")
        # Perform clean SQLite online backup
        with sqlite3.connect(db_file) as src, sqlite3.connect(bak_file) as dst:
            src.backup(dst)
        print("Backup complete.")

    with sqlite3.connect(db_file) as conn:
        conn.execute("PRAGMA journal_mode=WAL")
        # 1. Count existing legacy fake stamps
        fake_stamps = conn.execute("""
            SELECT COUNT(*) FROM opportunities
            WHERE laya_action = 'optimize' OR laya_decision_id LIKE 'dec_laya_OPP-%'
        """).fetchone()[0]
        print(f"Found {fake_stamps} legacy fake stamps in opportunities.")

        # 2. Reset legacy fake stamps
        assignments = [f'"{c}"=NULL' for c in OPPORTUNITY_COLUMNS if c != "laya_validated"]
        cur = conn.execute(f"""
            UPDATE opportunities
            SET {','.join(assignments)}, laya_validated=0
            WHERE laya_action = 'optimize' OR laya_decision_id LIKE 'dec_laya_OPP-%'
        """)
        print(f"Cleared {cur.rowcount} fake stamps.")

        # 3. Mark old stages stale so Pass 4 will re-run
        cp_cur = conn.execute("""
            UPDATE stage_checkpoints
            SET status = 'stale'
            WHERE stage IN (
                'P4_CALIBRATION', 'P5_WORK_ORDERS', 'P6_DELIVERABLES',
                'P4_LAYA_DECISION_ENGINE', 'P5_VALIDATED_OPPORTUNITIES', 'P6_REPORTS'
            )
        """)
        print(f"Marked {cp_cur.rowcount} stage_checkpoints as stale.")
        conn.commit()

    print("Legacy reset finished successfully.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", default="data/seo.db", help="Path to SQLite database")
    parser.add_argument("--no-backup", action="store_true", help="Skip database backup")
    args = parser.parse_args()
    reset_legacy(args.db, backup=not args.no_backup)
