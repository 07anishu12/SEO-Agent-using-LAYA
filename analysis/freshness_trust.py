import re
from typing import Dict, Any, List

class FreshnessTrustAnalyzer:
    """Evaluates content freshness consistency and YMYL financial trust transparency."""
    def __init__(self):
        pass

    def evaluate(self, page_data: Dict[str, Any], html: str = "") -> Dict[str, Any]:
        text = f"{page_data.get('title', '')} {page_data.get('h1_text', '')} {html}".lower()
        findings = []

        # 1. Stale year detection (e.g., 2022, 2023 on new vehicle pricing pages)
        stale_years = re.findall(r"\b(202[0-3])\b", text)
        if stale_years and "news" not in page_data.get("url", ""):
            findings.append({
                "type": "stale_content_signal",
                "severity": "medium",
                "message": f"Time-sensitive vehicle content references past year '{stale_years[0]}'. Review pricing and specifications for 2026 accuracy."
            })

        # 2. YMYL Finance: Loan & EMI transparency
        if any(k in text for k in ("emi", "loan", "down payment")):
            has_disclaimer = any(k in text for k in ("terms and conditions", "t&c apply", "subject to credit approval", "disclaimer"))
            has_rate_stated = bool(re.search(r"\d+(?:\.\d+)?\s*%\s*(?:interest|p\.a\.)", text))

            if not has_disclaimer:
                findings.append({
                    "type": "ymyl_missing_disclaimer",
                    "severity": "high",
                    "message": "Page promotes vehicle financing/EMI offers without mandatory legal disclaimer or terms of credit."
                })
            if not has_rate_stated:
                findings.append({
                    "type": "ymyl_unstated_interest_rate",
                    "severity": "medium",
                    "message": "EMI calculation presented without explicitly disclosing interest rate assumptions or tenure parameters."
                })

        return {
            "has_trust_findings": len(findings) > 0,
            "findings": findings
        }
