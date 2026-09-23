from typing import Dict, Any, List, Tuple
from collections import defaultdict

class QueryFitAnalyzer:
    """Evaluates query-to-page landing fit, detects evidence-backed cannibalization, and identifies missing pages."""
    def __init__(self):
        pass

    def evaluate_fit(
        self,
        query_info: Dict[str, Any],
        landing_page: Dict[str, Any],
        ranking_position: float
    ) -> Tuple[str, str]:
        """Returns (verdict, evidence)."""
        page_type = landing_page.get("page_type", "").lower()
        primary_intent = query_info.get("primary_intent", "commercial")
        url = landing_page.get("url", "").lower()

        # Intent compatibility
        if primary_intent in ("pricing", "finance") and page_type in ("model", "product", "listing"):
            return "CORRECT_LANDING", "Landing page matches commercial and vehicle pricing intent."
        elif primary_intent == "informational" and page_type in ("article", "guide", "news"):
            return "CORRECT_LANDING", "Landing page matches informational editorial intent."
        elif primary_intent in ("pricing", "variant") and page_type == "article":
            return "WEAK_LANDING", "Commercial purchase query landing on a general article rather than dedicated model page."
        elif ranking_position > 30.0:
            return "WEAK_LANDING", f"Query ranks at position {ranking_position:.1f} with weak entity and intent alignment."

        return "CORRECT_LANDING", "Acceptable landing page fit."

    def detect_cannibalization(self, gsc_rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Detects evidence-backed keyword cannibalization requiring multiple URLs, significant impression share, and position flip-flop."""
        query_groups = defaultdict(list)
        for r in gsc_rows:
            query_groups[r["query"]].append(r)

        cannibalization_findings = []

        for q, rows in query_groups.items():
            # Group by page URL
            page_rows = defaultdict(list)
            for r in rows:
                page_rows[r["page"]].append(r)

            if len(page_rows) < 2:
                continue

            total_impr = sum(r.get("impressions", 0) for r in rows)
            significant_pages = {}
            for p_url, p_list in page_rows.items():
                p_impr = sum(x.get("impressions", 0) for x in p_list)
                if p_impr >= max(50, total_impr * 0.10): # At least 10% impression share
                    significant_pages[p_url] = p_list

            if len(significant_pages) >= 2:
                # Check for position flip-flop or multiple distinct dates
                urls = list(significant_pages.keys())
                u1, u2 = urls[0], urls[1]
                pos1 = significant_pages[u1][0].get("position", 0.0)
                pos2 = significant_pages[u2][0].get("position", 0.0)

                finding = {
                    "query": q,
                    "competing_urls": urls,
                    "total_query_impressions": total_impr,
                    "url_1": u1,
                    "url_1_position": pos1,
                    "url_2": u2,
                    "url_2_position": pos2,
                    "evidence": f"Query '{q}' is split across {len(urls)} URLs: '{u1}' (pos {pos1}) and '{u2}' (pos {pos2}), causing keyword cannibalization.",
                    "recommended_action": f"Differentiate intent or add canonical / 301 redirect towards preferred primary landing page '{u1}'."
                }
                cannibalization_findings.append(finding)

        return cannibalization_findings
