import csv
from typing import Dict, Any, List, Set, Optional

class IndexFunnelReconciler:
    """Reconciles the full URL universe across sitemaps, link discovery, crawl status, indexability, and search visibility."""
    def __init__(self):
        pass

    def build_funnel(
        self,
        sitemap_urls: Set[str],
        pages: List[Dict[str, Any]],
        gsc_page_metrics: Optional[Dict[str, Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        gsc_page_metrics = gsc_page_metrics or {}
        
        crawled_urls = {p["url"] for p in pages}
        status_200_urls = {p["url"] for p in pages if p.get("status_code") == 200}
        indexable_urls = {p["url"] for p in pages if p.get("is_indexable") == 1}

        urls_with_impressions = set()
        urls_with_clicks = set()
        for u, m in gsc_page_metrics.items():
            if m.get("impressions", 0) > 0:
                urls_with_impressions.add(u)
            if m.get("clicks", 0) > 0:
                urls_with_clicks.add(u)

        # Mismatch sets
        in_sitemap_not_linked = sitemap_urls - crawled_urls
        linked_not_in_sitemap = crawled_urls - sitemap_urls
        in_sitemap_non_indexable = {p["url"] for p in pages if p["url"] in sitemap_urls and p.get("is_indexable") == 0}
        indexable_zero_impressions = indexable_urls - urls_with_impressions

        stages = [
            {"stage": "1. In XML Sitemap", "count": len(sitemap_urls)},
            {"stage": "2. Discovered & Crawled", "count": len(crawled_urls)},
            {"stage": "3. HTTP 200 OK", "count": len(status_200_urls)},
            {"stage": "4. Technical Indexable", "count": len(indexable_urls)},
            {"stage": "5. Received GSC Impressions", "count": len(urls_with_impressions)},
            {"stage": "6. Generated Clicks", "count": len(urls_with_clicks)},
        ]

        mismatches = {
            "sitemap_count": len(sitemap_urls),
            "crawled_count": len(crawled_urls),
            "in_sitemap_not_linked_count": len(in_sitemap_not_linked),
            "linked_not_in_sitemap_count": len(linked_not_in_sitemap),
            "in_sitemap_non_indexable_count": len(in_sitemap_non_indexable),
            "indexable_zero_impressions_count": len(indexable_zero_impressions)
        }

        return {
            "funnel_stages": stages,
            "mismatches": mismatches,
            "sample_sitemap_non_indexable": list(in_sitemap_non_indexable)[:10]
        }

    def export_csv(self, funnel_data: Dict[str, Any], output_path: str = "reports/index-funnel.csv"):
        with open(output_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["Funnel Stage", "URL Count"])
            for s in funnel_data.get("funnel_stages", []):
                writer.writerow([s["stage"], s["count"]])
            
            writer.writerow([])
            writer.writerow(["Diagnostic Mismatch Dimension", "Affected URLs"])
            for k, v in funnel_data.get("mismatches", {}).items():
                writer.writerow([k.replace("_", " ").title(), v])
