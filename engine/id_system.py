import hashlib
import sqlite3
import threading
from typing import Dict, Optional

PREFIX_MAP = {
    "site_tech": "SITE-TECH",
    "template": "TPL-SEO",
    "page": "PAGE-SEO",
    "query": "QUERY-SEO",
    "engineering": "ENG-SEO",
    "content": "CONTENT-SEO",
    "link": "LINK-SEO",
    "aeo": "AEO-SEO",
    "geo": "GEO-SEO",
    "default": "FINDING-SEO"
}

class IDSystem:
    """Manages permanent deterministic fingerprints and stable display IDs."""
    def __init__(self, db_path: str = "data/seo.db"):
        self.db_path = db_path
        self._lock = threading.Lock()
        self._init_db()

    def _init_db(self):
        with self._lock, sqlite3.connect(self.db_path) as conn:
            conn.execute("""
            CREATE TABLE IF NOT EXISTS display_id_map (
                fingerprint TEXT PRIMARY KEY,
                id_type TEXT NOT NULL,
                display_id TEXT NOT NULL,
                sequence_number INTEGER NOT NULL,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            );
            """)
            conn.commit()

    @staticmethod
    def generate_fingerprint(rule_id: str, scope_key: str, subject: str) -> str:
        """Computes permanent SHA-256 fingerprint for rule + scope + normalized subject."""
        norm_rule = (rule_id or "").strip().lower()
        norm_scope = (scope_key or "").strip().lower()
        norm_subj = (subject or "").strip().lower()
        raw = f"{norm_rule}|{norm_scope}|{norm_subj}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]

    def get_or_create_display_id(self, fingerprint: str, id_type: str = "default") -> str:
        """Returns existing display ID for fingerprint or allocates the next sequential ID."""
        prefix = PREFIX_MAP.get(id_type, PREFIX_MAP["default"])
        with self._lock, sqlite3.connect(self.db_path) as conn:
            row = conn.execute("SELECT display_id FROM display_id_map WHERE fingerprint = ?", (fingerprint,)).fetchone()
            if row:
                return row[0]

            # Allocate next sequence number for this prefix
            seq_row = conn.execute("SELECT MAX(sequence_number) FROM display_id_map WHERE id_type = ?", (id_type,)).fetchone()
            next_seq = (seq_row[0] or 0) + 1
            display_id = f"{prefix}-{next_seq:03d}"

            conn.execute("""
            INSERT OR REPLACE INTO display_id_map (fingerprint, id_type, display_id, sequence_number)
            VALUES (?, ?, ?, ?)
            """, (fingerprint, id_type, display_id, next_seq))
            conn.commit()
            return display_id
