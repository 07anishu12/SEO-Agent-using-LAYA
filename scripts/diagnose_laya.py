"""Read-only Laya provenance, schema, checkpoint, and downstream diagnostics."""
import argparse
import json
import sqlite3
from pathlib import Path


def diagnose(db_path, run_id=None):
    with sqlite3.connect(Path(db_path).resolve().as_uri() + "?mode=ro", uri=True) as conn:
        conn.row_factory = sqlite3.Row
        tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        result = {"database": str(Path(db_path).resolve()), "tables": {}}
        for table in ("laya_decisions", "laya_decision_log", "opportunities", "stage_checkpoints", "work_orders", "verifications"):
            if table not in tables:
                result["tables"][table] = {"missing": True}
                continue
            columns = [r[1] for r in conn.execute(f'PRAGMA table_info("{table}")')]
            item = {"rows": conn.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0], "columns": columns}
            if table == "opportunities":
                item["laya_columns"] = [c for c in columns if c.startswith("laya_")]
                item["distributions"] = {}
                for col in ("laya_validated", "laya_gate", "laya_action"):
                    item["distributions"][col] = [dict(r) for r in conn.execute(f'SELECT "{col}" AS value, COUNT(*) AS count FROM opportunities GROUP BY "{col}"')] if col in columns else "MISSING COLUMN"
                item["legacy_stamps"] = conn.execute("SELECT COUNT(*) FROM opportunities WHERE laya_action='optimize' OR laya_decision_id LIKE 'dec_laya_OPP-%'").fetchone()[0]
            result["tables"][table] = item
        latest = (run_id,) if run_id else conn.execute("SELECT crawl_id FROM crawl_runs ORDER BY start_time DESC LIMIT 1").fetchone()
        if latest:
            run = latest[0]
            result["latest_run"] = run
            result["latest_counts"] = {}
            for table, key in (("pages", "crawl_id"), ("laya_decisions", "crawl_id"), ("opportunities", "run_id"), ("work_orders", "run_id"), ("verifications", "run_id")):
                if table in tables:
                    result["latest_counts"][table] = conn.execute(f'SELECT COUNT(*) FROM "{table}" WHERE "{key}"=?', (run,)).fetchone()[0]
            result["checkpoints"] = [dict(r) for r in conn.execute("SELECT * FROM stage_checkpoints WHERE crawl_id=? ORDER BY completed_at", (run,))]
            result["decisions_by_run"] = [dict(r) for r in conn.execute("SELECT crawl_id, COUNT(*) AS count, SUM(cluster_id IS NULL OR choice IS NULL OR gate IS NULL OR prompt_version IS NULL) AS incomplete FROM laya_decisions GROUP BY crawl_id")]
        return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", default="data/seo.db")
    parser.add_argument("--run-id")
    args = parser.parse_args()
    print(json.dumps(diagnose(args.db, args.run_id), indent=2))
