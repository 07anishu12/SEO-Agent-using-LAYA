import datetime
import sqlite3
import threading
from dataclasses import dataclass, asdict
from typing import Dict, Any, List, Optional

@dataclass
class MetricProvenance:
    id: str
    run_id: str
    metric_name: str
    metric_value: float
    calculation_method: str
    source_table: str
    source_query: Optional[str] = None
    timestamp: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

class NumericProvenanceLedger:
    """Maintains verifiable computation paths for all figures displayed in reports."""
    def __init__(self, db_path: str = "data/seo.db"):
        self.db_path = db_path
        self._lock = threading.Lock()

    def record_metric(self, run_id: str, name: str, value: float, method: str, table: str, query: str = ""):
        now_str = datetime.datetime.now().isoformat()
        prov_id = f"num_{run_id}_{name}".replace(" ", "_").lower()
        with self._lock, sqlite3.connect(self.db_path) as conn:
            conn.execute("""
            INSERT OR REPLACE INTO numeric_provenance
            (id, run_id, metric_name, metric_value, calculation_method, source_table, source_query, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (prov_id, run_id, name, float(value), method, table, query, now_str))
            conn.commit()

    def verify_metric(self, run_id: str, name: str) -> Optional[Dict[str, Any]]:
        with self._lock, sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute("SELECT * FROM numeric_provenance WHERE run_id = ? AND metric_name = ?", (run_id, name)).fetchone()
            return dict(row) if row else None

    def get_all_provenance(self, run_id: str) -> List[Dict[str, Any]]:
        with self._lock, sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("SELECT * FROM numeric_provenance WHERE run_id = ?", (run_id,)).fetchall()
            return [dict(r) for r in rows]
