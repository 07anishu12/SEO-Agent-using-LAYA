from typing import List, Dict, Any
from models.issue import SEOIssue

def find_orphan_pages(pages: List[Dict[str, Any]], node_metrics: Dict[str, Dict[str, Any]], homepage_url: str) -> List[Dict[str, Any]]:
    """Identifies orphan pages: discovered via sitemap or external source with 0 inbound links."""
    orphans = []
    for p in pages:
        u = p["url"]
        if u == homepage_url:
            continue
        metrics = node_metrics.get(u, {})
        if metrics.get("in_degree", 0) == 0:
            orphans.append({
                "url": u,
                "page_type": p.get("page_type", "other"),
                "template_id": p.get("template_id", "default"),
                "discovery_source": p.get("discovery_source", "unknown")
            })
    return orphans
