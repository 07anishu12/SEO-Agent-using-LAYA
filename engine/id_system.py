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
        self._cache: Dict[str, str] = {}
        self._next_seq: Dict[str, int] = {}
        self._init_db()

    def _init_db(self):
        with self._lock, sqlite3.connect(self.db_path) as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("""
            CREATE TABLE IF NOT EXISTS display_id_map (
                fingerprint TEXT PRIMARY KEY,
                id_type TEXT NOT NULL,
                display_id TEXT NOT NULL,
                sequence_number INTEGER NOT NULL,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            );
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_disp_id_type ON display_id_map (id_type, sequence_number);")
            conn.commit()

            # Pre-load cache
            try:
                for row in conn.execute("SELECT fingerprint, display_id FROM display_id_map"):
                    self._cache[row[0]] = row[1]
                for row in conn.execute("SELECT id_type, MAX(sequence_number) FROM display_id_map GROUP BY id_type"):
                    self._next_seq[row[0]] = row[1] or 0
            except Exception:
                pass

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
        with self._lock:
            if fingerprint in self._cache:
                return self._cache[fingerprint]

            prefix = PREFIX_MAP.get(id_type, PREFIX_MAP["default"])
            next_seq = self._next_seq.get(id_type, 0) + 1
            self._next_seq[id_type] = next_seq
            display_id = f"{prefix}-{next_seq:03d}"
            self._cache[fingerprint] = display_id

            try:
                with sqlite3.connect(self.db_path) as conn:
                    conn.execute("PRAGMA journal_mode=WAL")
                    conn.execute("""
                    INSERT OR REPLACE INTO display_id_map (fingerprint, id_type, display_id, sequence_number)
                    VALUES (?, ?, ?, ?)
                    """, (fingerprint, id_type, display_id, next_seq))
                    conn.commit()
            except Exception:
                pass
            return display_id
