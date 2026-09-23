from typing import List, Dict, Any
from collections import Counter

def calculate_depth_distribution(node_metrics: Dict[str, Dict[str, Any]]) -> Dict[int, int]:
    """Calculates the frequency count of pages at each crawl depth from homepage."""
    depth_counts = Counter()
    for metrics in node_metrics.values():
        d = metrics.get("crawl_depth", -1)
        depth_counts[d] += 1
    return dict(sorted(depth_counts.items()))
