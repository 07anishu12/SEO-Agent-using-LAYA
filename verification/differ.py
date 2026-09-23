import json
import sqlite3
import hashlib
from typing import Dict, Any, List, Optional

class SnapshotDiffer:
    """
    Compares two snapshot runs (before vs after deployment) to detect:
    FIXED, REGRESSED, IMPROVED, NEW_ISSUE, STILL_FAILING, UNCHANGED.
    Writes diff records to SQLite 'snapshot_diffs' and exports 'seo-diff.json'.
    """
    def __init__(self, db_path: str = "data/seo.db"):
        self.db_path = db_path

    def diff_runs(
        self,
        before_run_id: str,
        after_run_id: str,
        export_path: Optional[str] = "seo-diff.json"
    ) -> Dict[str, Any]:
        """Compares snapshots between two runs and records findings in snapshot_diffs."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            before_rows = conn.execute("SELECT * FROM snapshots WHERE run_id = ?", (before_run_id,)).fetchall()
            after_rows = conn.execute("SELECT * FROM snapshots WHERE run_id = ?", (after_run_id,)).fetchall()

        before_map = {r["url"]: dict(r) for r in before_rows}
        after_map = {r["url"]: dict(r) for r in after_rows}

        all_urls = sorted(set(before_map.keys()) | set(after_map.keys()))

        diff_results = []
        summary_counts = {
            "FIXED": 0,
            "REGRESSED": 0,
            "IMPROVED": 0,
            "NEW_ISSUE": 0,
            "STILL_FAILING": 0,
            "UNCHANGED": 0
        }

        diff_entries_to_insert = []

        for u in all_urls:
            b = before_map.get(u)
            a = after_map.get(u)

            if b and a:
                category, details = self._compare_snapshots(b, a)
                b_id = b["snapshot_id"]
                a_id = a["snapshot_id"]
            elif a and not b:
                b_id = "NONE"
                a_id = a["snapshot_id"]
                if a.get("status_code", 200) >= 400 or "noindex" in a.get("meta_robots", "").lower():
                    category = "NEW_ISSUE"
                    details = {"event": "New page detected with technical errors", "status_code": a.get("status_code")}
                else:
                    category = "IMPROVED"
                    details = {"event": "New healthy page detected", "status_code": a.get("status_code")}
            else: # b and not a
                b_id = b["snapshot_id"]
                a_id = "NONE"
                category = "REGRESSED"
                details = {"event": "Page missing / dropped in post-deployment snapshot"}

            summary_counts[category] += 1
            fp = hashlib.sha256(f"{u}|{category}|{json.dumps(details, sort_keys=True)}".encode()).hexdigest()[:16]

            entry = {
                "before_snapshot_id": b_id,
                "after_snapshot_id": a_id,
                "url": u,
                "fingerprint": fp,
                "category": category,
                "details": details
            }
            diff_results.append(entry)
            diff_entries_to_insert.append((
                b_id, a_id, u, fp, category, json.dumps(details)
            ))

        # Save to database
        with sqlite3.connect(self.db_path) as conn:
            for item in diff_entries_to_insert:
                conn.execute("""
                INSERT INTO snapshot_diffs (
                    before_snapshot_id, after_snapshot_id, url, fingerprint, category, details_json
                ) VALUES (?, ?, ?, ?, ?, ?)
                """, item)
            conn.commit()

        diff_payload = {
            "before_run_id": before_run_id,
            "after_run_id": after_run_id,
            "total_urls_compared": len(all_urls),
            "summary": summary_counts,
            "differences": [d for d in diff_results if d["category"] != "UNCHANGED"]
        }

        if export_path:
            with open(export_path, "w", encoding="utf-8") as f:
                json.dump(diff_payload, f, indent=2)

        return diff_payload

    def _compare_snapshots(self, b: Dict[str, Any], a: Dict[str, Any]) -> tuple:
        """Determines the diff verdict for a single URL present in both snapshots."""
        regressions = []
        fixes = []
        improvements = []

        # 1. Status Code
        b_code = b.get("status_code", 200)
        a_code = a.get("status_code", 200)
        if b_code >= 400 and a_code == 200:
            fixes.append(f"HTTP status code resolved from {b_code} to {a_code}")
        elif b_code == 200 and a_code >= 400:
            regressions.append(f"HTTP status code worsened from {b_code} to {a_code}")
        elif b_code >= 400 and a_code >= 400:
            pass # still failing

        # 2. Meta Robots / Indexability
        b_noindex = "noindex" in b.get("meta_robots", "").lower()
        a_noindex = "noindex" in a.get("meta_robots", "").lower()
        if b_noindex and not a_noindex:
            fixes.append("Removed noindex directive; page is now indexable")
        elif not b_noindex and a_noindex:
            regressions.append("Page inadvertently set to noindex")

        # 3. Title Tag
        b_title = b.get("title", "").strip()
        a_title = a.get("title", "").strip()
        if not b_title and a_title:
            fixes.append(f"Title tag populated: '{a_title[:40]}...'")
        elif b_title and not a_title:
            regressions.append("Title tag was removed or missing")
        elif b_title != a_title:
            improvements.append(f"Title updated from '{b_title[:30]}...' to '{a_title[:30]}...'")

        # 4. Schema
        b_schema = b.get("schema_hash", "")
        a_schema = a.get("schema_hash", "")
        if not b_schema and a_schema:
            fixes.append("Structured data schema added")
        elif b_schema and not a_schema:
            regressions.append("Structured data schema was removed")

        # Verdict assignment
        if regressions:
            return "REGRESSED", {"regressions": regressions, "fixes": fixes}
        if fixes:
            return "FIXED", {"fixes": fixes, "improvements": improvements}
        if b_code >= 400 or b_noindex:
            return "STILL_FAILING", {"issue": f"Status {a_code}, Robots: {a.get('meta_robots')}"}
        if improvements or b.get("content_hash") != a.get("content_hash"):
            return "IMPROVED", {"improvements": improvements, "content_hash_changed": True}

        return "UNCHANGED", {}
