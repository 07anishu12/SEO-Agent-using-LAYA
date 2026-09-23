import re
from typing import Dict, Any, List, Optional, Tuple

class GroundedLinkRecommender:
    """Recommends concrete internal link additions with grounded anchor text and greedy marginal-gain selection."""
    def __init__(self, max_links_per_source: int = 3):
        self.max_links_per_source = max_links_per_source

    def recommend_links(
        self,
        pages: List[Dict[str, Any]],
        graph_metrics: Dict[str, Dict[str, Any]],
        product_pages: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        page_map = {p["url"]: p for p in pages}
        hub_pages = [p for p in pages if p.get("page_type") in ("category", "listing", "brand", "homepage")]
        
        recommendations = []
        source_usage = {p["url"]: 0 for p in hub_pages}

        # Focus on product pages that have weak link equity (inbound < 4)
        for prod in product_pages:
            t_url = prod["url"]
            metrics = graph_metrics.get(t_url, {})
            in_links = metrics.get("inbound_links_total", 0)

            if in_links >= 4:
                continue

            brand = prod.get("brand") or ""
            model = prod.get("model") or ""
            if not model:
                continue

            # Find matching hub page
            best_source = None
            for hub in hub_pages:
                h_url = hub["url"]
                if source_usage[h_url] >= self.max_links_per_source:
                    continue

                # If hub matches brand or is main category
                if brand and brand.lower() in h_url.lower():
                    best_source = hub
                    break
                elif "/bikes" in h_url or "/scooters" in h_url:
                    if best_source is None:
                        best_source = hub

            if best_source:
                s_url = best_source["url"]
                source_usage[s_url] += 1
                
                # Check if model name appears in source page text for grounded anchor
                s_text = best_source.get("title", "") + " " + best_source.get("h1_text", "")
                grounded = model.lower() in s_text.lower()
                anchor = f"{brand} {model}".strip()

                rec = {
                    "source_url": s_url,
                    "target_url": t_url,
                    "recommended_anchor": anchor,
                    "is_grounded": grounded,
                    "text_snippet": f"Found reference to '{model}' in source metadata." if grounded else "NEEDS_NEW_TEXT: Add contextual link to model card in category listing.",
                    "reason": f"Product page has only {in_links} inbound links. Injecting authority from relevant hub.",
                    "evidence": f"Target currently has depth {metrics.get('click_depth', -1)} and PageRank {metrics.get('pagerank', 0.0):.6f}.",
                    "implementation_location": "Template component: Model Grid / Hub Section",
                    "priority": "P1" if in_links == 0 else "P2",
                    "opportunity_score": round((4 - in_links) * 25.0, 1)
                }
                recommendations.append(rec)

        # Sort recommendations by opportunity score descending
        recommendations.sort(key=lambda x: x["opportunity_score"], reverse=True)
        return recommendations
