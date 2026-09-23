import json
import sqlite3
import threading
import uuid
from dataclasses import dataclass, field, asdict
from typing import Dict, Any, List, Optional

@dataclass
class EvidenceRef:
    evidence_id: str = field(default_factory=lambda: f"ev_{uuid.uuid4().hex[:12]}")
    run_id: str = ""
    url: str = ""
    evidence_type: str = "dom_selector" # dom_selector, byte_range, gsc_row, graph_edge, sql_query, text_span
    selector: Optional[str] = None
    line_number: Optional[int] = None
    byte_range: Optional[str] = None
    gsc_row_id: Optional[int] = None
    edge_id: Optional[int] = None
    query_id: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

class EvidenceLedger:
    """Central cross-cutting ledger for verifiable evidence provenance."""
    def __init__(self, db_path: str = "data/seo.db"):
        self.db_path = db_path
        self._lock = threading.Lock()

    def record_evidence(self, ref: EvidenceRef):
        """Persists a single evidence reference."""
        self.record_batch([ref])

    def record_batch(self, refs: List[EvidenceRef]):
        """Persists a batch of evidence references to SQLite."""
        if not refs:
            return
        with self._lock, sqlite3.connect(self.db_path) as conn:
            conn.executemany("""
            INSERT OR REPLACE INTO evidence 
            (evidence_id, run_id, url, evidence_type, selector, line_number, byte_range, gsc_row_id, edge_id, query_id, details_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, [
                (
                    r.evidence_id,
                    r.run_id,
                    r.url,
                    r.evidence_type,
                    r.selector,
                    r.line_number,
                    r.byte_range,
                    r.gsc_row_id,
                    r.edge_id,
                    r.query_id,
                    json.dumps(r.details) if r.details else "{}"
                )
                for r in refs
            ])
            conn.commit()

    def get_evidence(self, evidence_id: str) -> Optional[Dict[str, Any]]:
        with self._lock, sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute("SELECT * FROM evidence WHERE evidence_id = ?", (evidence_id,)).fetchone()
            if row:
                res = dict(row)
                res["details"] = json.loads(res.get("details_json") or "{}")
                return res
            return None

    def get_evidence_for_url(self, run_id: str, url: str) -> List[Dict[str, Any]]:
        with self._lock, sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("SELECT * FROM evidence WHERE run_id = ? AND url = ?", (run_id, url)).fetchall()
            results = []
            for r in rows:
                item = dict(r)
                item["details"] = json.loads(item.get("details_json") or "{}")
                results.append(item)
            return results
