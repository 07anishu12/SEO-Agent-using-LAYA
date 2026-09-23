import json
import os
from typing import Dict, Any, List, Optional

class SERPPipeline:
    """Ingests competitor SERP snapshots, builds attribute presence matrices, and diagnoses SERP feature opportunities."""
    def __init__(self, serp_data_path: Optional[str] = None):
        self.serp_data_path = serp_data_path
        self.has_serp_data = bool(serp_data_path and os.path.exists(serp_data_path))
        self.snapshots: Dict[str, Dict[str, Any]] = {}
        if self.has_serp_data:
            self._load_data()

    def _load_data(self):
        try:
            with open(self.serp_data_path, "r", encoding="utf-8") as f:
                self.snapshots = json.load(f)
        except Exception:
            self.has_serp_data = False

    def get_query_serp(self, query: str) -> Optional[Dict[str, Any]]:
        return self.snapshots.get(query.lower().strip())

    def analyze_serp_feature_opportunities(self, query: str, page_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        if not self.has_serp_data:
            return [{
                "status": "SERP DATA REQUIRED",
                "message": "Connect external SERP JSON or API data to diagnose competitor rich snippet features."
            }]

        serp = self.get_query_serp(query)
        if not serp:
            return []

        opportunities = []
        serp_features = serp.get("features", [])
        page_schema = page_data.get("schema_types", "")

        if "faq" in serp_features and "FAQPage" not in page_schema:
            opportunities.append({
                "feature": "FAQ Rich Snippet",
                "competitor_presence": "Competitors on SERP earn FAQ rich snippets.",
                "target_status": "Missing FAQPage schema",
                "recommended_action": "Potential SERP feature opportunity based on observed query structure: implement FAQPage JSON-LD schema."
            })

        if "product_snippets" in serp_features and "Product" not in page_schema:
            opportunities.append({
                "feature": "Product & Offer Snippet",
                "competitor_presence": "Competitors display price and rating snippets in SERP results.",
                "target_status": "Missing Product schema",
                "recommended_action": "Potential SERP feature opportunity based on observed query structure: implement Product schema with Offer and Brand."
            })

        return opportunities

    def build_attribute_presence_matrix(
        self,
        query: str,
        target_attributes: List[str],
        competitor_attributes: Dict[str, List[str]]
    ) -> Dict[str, Any]:
        """Builds presence matrix: rows = target + competitors, cols = ontology attributes."""
        all_attrs = sorted(set(target_attributes) | {a for attrs in competitor_attributes.values() for a in attrs})
        matrix = {
            "attributes": all_attrs,
            "target_coverage": {a: (a in target_attributes) for a in all_attrs},
            "competitors": {
                comp: {a: (a in attrs) for a in all_attrs}
                for comp, attrs in competitor_attributes.items()
            }
        }
        return matrix
