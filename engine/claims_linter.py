import re
import csv
import json
import os
from typing import Dict, Any, List, Optional

FORBIDDEN_GUARANTEE_PATTERNS = [
    re.compile(r"\bwill\s+(?:rank|boost|outrank|skyrocket|guarantee)\b", re.I),
    re.compile(r"\bguaranteed?\b", re.I),
    re.compile(r"\bguarantees?\b", re.I),
    re.compile(r"\bpromises?\b", re.I),
    re.compile(r"\bwill\s+increase\s+traffic\b", re.I),
    re.compile(r"\brank\s+(?:#?1|first|page\s+one)\s+guaranteed\b", re.I),
    re.compile(r"\bguaranteed\s+rankings?\b", re.I),
    re.compile(r"\bwill\s+achieve\s+position\b", re.I),
    re.compile(r"\bcertain\s+to\s+rank\b", re.I),
]

VALID_CLAIM_TYPES = {"OBSERVED", "DERIVED", "INFERRED", "HYPOTHESIS"}

class ClaimsLinter:
    """Final quality gate: ensures no ranking guarantees, validates claim typing, and verifies evidence linkage."""
    def __init__(self):
        self.violations: List[Dict[str, str]] = []

    def lint_text(self, text: str, context: str = "") -> List[str]:
        """Scans arbitrary text for forbidden guarantee language."""
        if not text:
            return []
        errors = []
        cleaned_text = re.sub(r"https?://\S+", "", text)
        for pat in FORBIDDEN_GUARANTEE_PATTERNS:
            match = pat.search(cleaned_text)
            if match:
                err = f"Forbidden guarantee language '{match.group(0)}' found in {context or 'text'}: '{text[:100]}...'"
                errors.append(err)
                self.violations.append({"type": "guarantee_language", "context": context, "match": match.group(0), "error": err})
        return errors

    def lint_finding(self, finding: Dict[str, Any]) -> List[str]:
        """Validates that a finding adheres to claim typing and evidence requirements."""
        errors = []
        fid = finding.get("display_id") or finding.get("fingerprint") or "finding"
        
        # 1. Claim Typing
        claim_type = finding.get("claim_type")
        if not claim_type or claim_type not in VALID_CLAIM_TYPES:
            err = f"Finding {fid} has invalid or missing claim_type: '{claim_type}'. Must be one of {VALID_CLAIM_TYPES}."
            errors.append(err)
            self.violations.append({"type": "invalid_claim_type", "context": fid, "error": err})

        # 2. Evidence linkage
        evidence_refs = finding.get("evidence_refs") or finding.get("evidence_refs_json")
        if not evidence_refs:
            err = f"Finding {fid} is missing evidence_refs. Findings cannot be emitted without concrete evidence."
            errors.append(err)
            self.violations.append({"type": "missing_evidence", "context": fid, "error": err})

        # 3. Language check
        msg = finding.get("message") or ""
        rec = finding.get("recommended_action") or ""
        errors.extend(self.lint_text(msg, f"{fid} message"))
        errors.extend(self.lint_text(rec, f"{fid} recommended_action"))
        return errors

    def lint_work_order(self, order: Dict[str, Any]) -> List[str]:
        """Validates that a work order has executable verification and evidence."""
        errors = []
        wid = order.get("display_id") or order.get("work_order_id") or "work_order"
        
        verify_spec = order.get("verify_spec")
        if not verify_spec:
            err = f"Work order {wid} missing executable verify_spec."
            errors.append(err)
            self.violations.append({"type": "missing_verify_spec", "context": wid, "error": err})

        errors.extend(self.lint_text(order.get("title", ""), f"{wid} title"))
        errors.extend(self.lint_text(order.get("problem", ""), f"{wid} problem"))
        errors.extend(self.lint_text(order.get("required_change", ""), f"{wid} change"))
        return errors

    def lint_csv_file(self, csv_path: str) -> List[str]:
        """Scans all cells in a CSV file for guarantee language."""
        errors = []
        try:
            with open(csv_path, "r", encoding="utf-8", errors="replace") as f:
                reader = csv.reader(f)
                for row_idx, row in enumerate(reader):
                    for col_idx, cell in enumerate(row):
                        errs = self.lint_text(cell, f"{csv_path} R{row_idx+1}:C{col_idx+1}")
                        errors.extend(errs)
        except Exception as e:
            errors.append(f"Failed to read CSV for linting {csv_path}: {e}")
        return errors

    def export_report(self, output_path_or_violations: Any = "reports/lint-report.json", maybe_path: Optional[str] = None):
        if maybe_path:
            output_path = maybe_path
            if isinstance(output_path_or_violations, list):
                for v in output_path_or_violations:
                    if isinstance(v, dict) and v not in self.violations:
                        self.violations.append(v)
                    elif isinstance(v, str) and not any(v == item.get("error") for item in self.violations):
                        self.violations.append({"error": v})
        else:
            output_path = output_path_or_violations if isinstance(output_path_or_violations, str) else "reports/lint-report.json"

        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        report = {
            "passed": len(self.violations) == 0,
            "total_violations": len(self.violations),
            "violations": self.violations
        }
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)
        return report
