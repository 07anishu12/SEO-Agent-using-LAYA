import csv
import sqlite3
import datetime
from typing import Dict, Any, List, Optional, Set

class FeedbackEngine:
    """Manages user feedback (false_positive / accepted / fixed / wontfix) and suppression learning."""
    def __init__(self, db_path: str = "data/seo.db"):
        self.db_path = db_path
        self._suppressed_cache: Optional[Set[str]] = None

    def record_feedback(self, fingerprint: str, rule_id: str, url: str, action: str, comment: str = ""):
        """Records user decision on finding. Allowed actions: false_positive, accepted, fixed, wontfix."""
        now_str = datetime.datetime.now().isoformat()
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
            INSERT INTO feedback (fingerprint, rule_id, url, user_action, comment, recorded_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """, (fingerprint, rule_id, url, action, comment, now_str))
            conn.commit()
        if self._suppressed_cache is not None and action in ("false_positive", "wontfix"):
            self._suppressed_cache.add(fingerprint)

    def is_suppressed(self, fingerprint: str) -> bool:
        """Checks if a finding fingerprint has been suppressed by user feedback."""
        if self._suppressed_cache is None:
            with sqlite3.connect(self.db_path) as conn:
                rows = conn.execute("SELECT fingerprint FROM feedback WHERE user_action IN ('false_positive', 'wontfix')").fetchall()
                self._suppressed_cache = {r[0] for r in rows}
        return fingerprint in self._suppressed_cache

    def export_csv(self, output_path: str = "reports/feedback.csv"):
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("SELECT * FROM feedback ORDER BY recorded_at DESC").fetchall()
            
            with open(output_path, "w", encoding="utf-8", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["id", "fingerprint", "rule_id", "url", "user_action", "comment", "recorded_at"])
                for r in rows:
                    writer.writerow([r["id"], r["fingerprint"], r["rule_id"], r["url"], r["user_action"], r["comment"], r["recorded_at"]])
