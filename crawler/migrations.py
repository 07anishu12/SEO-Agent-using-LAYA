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
            self._ensure_laya_decision_v2(conn)

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

        # 4. opportunities table: laya_action, laya_confidence, laya_decision_id
        try:
            cur = conn.execute("PRAGMA table_info(opportunities);")
            opp_cols = {row[1] for row in cur.fetchall()}
            new_opp_cols = {
                "laya_action": "TEXT",
                "laya_confidence": "REAL",
                "laya_decision_id": "TEXT",
                "laya_validated": "INTEGER DEFAULT 0",
                "laya_verdict": "TEXT",
                "laya_scope": "TEXT",
                "laya_root_cause": "TEXT",
                "laya_canonical_indexability": "TEXT",
                "laya_content_assessment": "TEXT",
                "laya_cannibalization": "TEXT",
                "laya_internal_linking": "TEXT",
                "laya_candidate_id": "TEXT"
            }
            for col, col_type in new_opp_cols.items():
                if col not in opp_cols:
                    conn.execute(f"ALTER TABLE opportunities ADD COLUMN {col} {col_type};")
        except Exception:
            pass

        # 5. work_orders table: laya_action, laya_confidence, laya_decision_id
        try:
            cur = conn.execute("PRAGMA table_info(work_orders);")
            wo_cols = {row[1] for row in cur.fetchall()}
            new_wo_cols = {
                "laya_action": "TEXT",
                "laya_confidence": "REAL",
                "laya_decision_id": "TEXT"
            }
            for col, col_type in new_wo_cols.items():
                if col not in wo_cols:
                    conn.execute(f"ALTER TABLE work_orders ADD COLUMN {col} {col_type};")
        except Exception:
            pass

        # 6. stage_checkpoints table
        try:
            conn.execute("""
            CREATE TABLE IF NOT EXISTS stage_checkpoints (
                crawl_id TEXT NOT NULL,
                stage TEXT NOT NULL,
                status TEXT NOT NULL,
                metadata_json TEXT,
                completed_at TEXT,
                PRIMARY KEY (crawl_id, stage)
            );
            """)
        except Exception:
            pass

        conn.commit()

    def _ensure_laya_decision_v2(self, conn: sqlite3.Connection):
        """Add enhanced laya_decisions columns and create laya_decision_log."""
        # 1. Add columns to laya_decisions table if not present
        try:
            cur = conn.execute("PRAGMA table_info(laya_decisions);")
            cols = {row[1] for row in cur.fetchall()}
            new_cols = {
                "decision_type": "TEXT",
                "choice": "TEXT",
                "gate": "TEXT",
                "input_hash": "TEXT",
                "model_version": "TEXT",
                "affected_scope": "TEXT",
                "affected_count": "INTEGER",
                "cluster_id": "TEXT",
                "prompt_version": "TEXT",
                "is_real_issue": "INTEGER DEFAULT 1",
                "scope": "TEXT",
                "root_cause": "TEXT",
                "canonical_indexability": "TEXT",
                "content_assessment": "TEXT",
                "cannibalization": "TEXT",
                "internal_linking": "TEXT"
            }
            if cols: # Table exists
                for col, col_type in new_cols.items():
                    if col not in cols:
                        try:
                            conn.execute(f"ALTER TABLE laya_decisions ADD COLUMN {col} {col_type};")
                        except Exception:
                            pass
        except Exception:
            pass

        # 2. Create laya_decision_log table
        try:
            conn.execute("""
            CREATE TABLE IF NOT EXISTS laya_decision_log (
                decision_id TEXT PRIMARY KEY,
                run_id TEXT,
                cluster_id TEXT,
                decision_type TEXT,
                choice TEXT,
                confidence REAL,
                severity TEXT,
                reason_codes TEXT,
                recommended_action TEXT,
                affected_scope TEXT,
                affected_count INTEGER,
                evidence_refs TEXT,
                model_version TEXT,
                input_hash TEXT,
                latency_ms REAL,
                created_at TEXT,
                from_cache INTEGER,
                raw_response TEXT,
                gate TEXT,
                prompt_version TEXT,
                is_real_issue INTEGER DEFAULT 1,
                scope TEXT,
                root_cause TEXT,
                canonical_indexability TEXT,
                content_assessment TEXT,
                cannibalization TEXT,
                internal_linking TEXT
            );
            """)
        except Exception:
            pass
        conn.commit()
