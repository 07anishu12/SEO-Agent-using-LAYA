import json
import sqlite3
import os
from typing import List, Dict, Any, Optional

class WorkOrderManager:
    """
    Manages developer and content work orders (SEOJEV-ENG-###, SEOJEV-CONTENT-###).
    Provides adapters for GitHub, Jira, and Linear ticket generation.
    """
    def __init__(self, db_path: str = "data/seo.db"):
        self.db_path = db_path

    def create_work_orders_from_opportunities(
        self,
        run_id: str,
        opportunities: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Transforms synthesized opportunities into actionable engineering and content work orders."""
        work_orders = []
        eng_seq = 1
        content_seq = 1

        for opp in opportunities:
            opp_type = opp.get("type", "SITE-TECH")
            disp_id_orig = opp.get("display_id", "")
            tier = opp.get("opportunity_tier", "Medium")
            score = opp.get("priority_score", 50.0)

            # Assign P0, P1, P2, P3 priority
            if tier == "High" or score >= 75.0:
                priority = "P0" if opp_type in ("SITE-TECH", "TPL") and score >= 85.0 else "P1"
            elif tier == "Medium" or score >= 45.0:
                priority = "P2"
            else:
                priority = "P3"

            is_eng = opp_type in ("SITE-TECH", "TPL", "ENG", "LINK")
            order_type = "engineering" if is_eng else "content"

            if is_eng:
                disp_id = f"SEOJEV-ENG-{eng_seq:03d}"
                eng_seq += 1
            else:
                disp_id = f"SEOJEV-CONTENT-{content_seq:03d}"
                content_seq += 1

            scope = "site" if opp_type == "SITE-TECH" else ("template" if opp_type == "TPL" else "page")
            title = f"[{disp_id}] {opp.get('action')}"
            if len(title) > 100:
                title = title[:97] + "..."

            problem = f"{opp.get('observation')}\n\nDiagnosis: {opp.get('diagnosis')}"
            
            sample_urls = json.loads(opp.get("sample_urls_json", "[]"))
            evidence = {
                "opportunity_id": opp.get("opportunity_id"),
                "affected_urls_count": opp.get("affected_urls_count", 1),
                "sample_urls": sample_urls,
                "confidence_tier": opp.get("confidence_tier", "High"),
                "effort": opp.get("effort", "S")
            }

            required_change = (
                f"Action Required: {opp.get('action')}\n\n"
                f"Target Location: {opp.get('implementation_location')}\n"
                f"Scope: {scope.capitalize()} ({opp.get('affected_urls_count', 1)} URLs affected)\n"
                f"Observed Hypothesis: {opp.get('hypothesis')}"
            )

            acceptance_criteria = (
                f"- [ ] Implementation updated in `{opp.get('implementation_location')}`.\n"
                f"- [ ] Verification spec evaluates to true: `{opp.get('verification_spec')}`.\n"
                f"- [ ] Validated on sample URLs: {', '.join(sample_urls[:3]) if sample_urls else 'Site URL'}."
            )

            wo = {
                "work_order_id": f"WO-{disp_id}",
                "fingerprint": opp.get("fingerprint"),
                "display_id": disp_id,
                "run_id": run_id,
                "order_type": order_type,
                "priority": priority,
                "scope": scope,
                "title": title,
                "problem": problem,
                "evidence_json": json.dumps(evidence),
                "required_change": required_change,
                "acceptance_criteria": acceptance_criteria,
                "verify_spec": opp.get("verification_spec", "status_code == 200"),
                "file_locations_json": json.dumps([opp.get("implementation_location")])
            }
            work_orders.append(wo)

        return work_orders

    def persist_work_orders(self, work_orders: List[Dict[str, Any]]):
        """Saves generated work orders to SQLite database."""
        with sqlite3.connect(self.db_path) as conn:
            for wo in work_orders:
                conn.execute("""
                INSERT OR REPLACE INTO work_orders (
                    work_order_id, fingerprint, display_id, run_id, order_type,
                    priority, scope, title, problem, evidence_json, required_change,
                    acceptance_criteria, verify_spec, file_locations_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    wo["work_order_id"], wo["fingerprint"], wo["display_id"], wo["run_id"],
                    wo["order_type"], wo["priority"], wo["scope"], wo["title"],
                    wo["problem"], wo["evidence_json"], wo["required_change"],
                    wo["acceptance_criteria"], wo["verify_spec"], wo["file_locations_json"]
                ))
            conn.commit()

    def get_work_order_by_display_id(self, display_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves a single work order by its display ID (e.g. SEOJEV-ENG-001 or ENG-SEO-001)."""
        norm_id = display_id.upper().strip()
        # Support both prefixes
        alt_id = norm_id.replace("SEOJEV-", "") if "SEOJEV-" in norm_id else f"SEOJEV-{norm_id}"
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM work_orders WHERE display_id = ? OR display_id = ?",
                (norm_id, alt_id)
            ).fetchone()
            if row:
                return dict(row)
        return None

    # Ticket Exporter Adapters
    def export_markdown(self, wo: Dict[str, Any]) -> str:
        """Renders work order as clean developer markdown."""
        evidence = json.loads(wo.get("evidence_json", "{}"))
        samples = evidence.get("sample_urls", [])
        samples_md = "\n".join(f"- {u}" for u in samples[:5])

        return f"""# [{wo['display_id']}] {wo['title']}

**Type:** {wo['order_type'].capitalize()}  
**Priority:** {wo['priority']}  
**Scope:** {wo['scope'].capitalize()} ({evidence.get('affected_urls_count', 1)} URLs)  
**Effort:** {evidence.get('effort', 'S')}  

---

### Problem & Observed Evidence
{wo['problem']}

**Sample Affected URLs:**
{samples_md or "- Site-wide"}

---

### Required Implementation
{wo['required_change']}

---

### Acceptance Criteria
{wo['acceptance_criteria']}

**Automated Verification Spec:**
```
{wo['verify_spec']}
```
"""

    def export_github_issue(self, wo: Dict[str, Any]) -> Dict[str, Any]:
        """Formats work order for GitHub Issues API."""
        return {
            "title": f"[{wo['display_id']}] {wo['title']}",
            "body": self.export_markdown(wo),
            "labels": ["seo", wo['order_type'], f"priority-{wo['priority'].lower()}"],
        }

    def export_jira_issue(self, wo: Dict[str, Any]) -> Dict[str, Any]:
        """Formats work order for Jira Cloud API."""
        return {
            "fields": {
                "project": {"key": "SEO"},
                "summary": f"[{wo['display_id']}] {wo['title']}",
                "description": self.export_markdown(wo),
                "issuetype": {"name": "Task" if wo['order_type'] == "engineering" else "Story"},
                "priority": {"name": "Highest" if wo['priority'] == "P0" else ("High" if wo['priority'] == "P1" else "Medium")},
                "labels": ["seojev", wo['order_type'], wo['priority']]
            }
        }

    def export_linear_issue(self, wo: Dict[str, Any]) -> Dict[str, Any]:
        """Formats work order for Linear API."""
        p_map = {"P0": 1, "P1": 2, "P2": 3, "P3": 4}
        return {
            "title": f"[{wo['display_id']}] {wo['title']}",
            "description": self.export_markdown(wo),
            "priority": p_map.get(wo['priority'], 3),
            "labels": ["SEO", wo['order_type'].capitalize()]
        }

    def export_all_tickets(self, run_id: str, output_dir: str) -> Dict[str, int]:
        """Exports all tickets for a run into markdown files and JSON bundles."""
        os.makedirs(output_dir, exist_ok=True)
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("SELECT * FROM work_orders WHERE run_id = ?", (run_id,)).fetchall()
            work_orders = [dict(r) for r in rows]

        eng_dir = os.path.join(output_dir, "engineering")
        content_dir = os.path.join(output_dir, "content")
        os.makedirs(eng_dir, exist_ok=True)
        os.makedirs(content_dir, exist_ok=True)

        gh_issues = []
        jira_issues = []
        linear_issues = []

        for wo in work_orders:
            target_dir = eng_dir if wo["order_type"] == "engineering" else content_dir
            file_path = os.path.join(target_dir, f"{wo['display_id']}.md")
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(self.export_markdown(wo))

            gh_issues.append(self.export_github_issue(wo))
            jira_issues.append(self.export_jira_issue(wo))
            linear_issues.append(self.export_linear_issue(wo))

        # Save bundle files
        with open(os.path.join(output_dir, "github_issues.json"), "w", encoding="utf-8") as f:
            json.dump(gh_issues, f, indent=2)

        with open(os.path.join(output_dir, "jira_import.json"), "w", encoding="utf-8") as f:
            json.dump(jira_issues, f, indent=2)

        with open(os.path.join(output_dir, "linear_import.json"), "w", encoding="utf-8") as f:
            json.dump(linear_issues, f, indent=2)

        return {
            "total_tickets": len(work_orders),
            "engineering_tickets": sum(1 for w in work_orders if w["order_type"] == "engineering"),
            "content_tickets": sum(1 for w in work_orders if w["order_type"] == "content")
        }
