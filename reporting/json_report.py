import os
import json
import urllib.parse
from typing import Dict, Any, List, Optional
from models.crawl import CrawlStats

class JSONReportGenerator:
    def __init__(self, output_dir: str = "reports/"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    def generate_summary_json(
        self,
        website: str,
        crawl_id: str,
        crawl_date: str,
        stats: CrawlStats,
        laya_summary: Dict[str, Any],
        v2_meta: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        data = {
            "website": website,
            "crawl_date": crawl_date,
            "crawl_id": crawl_id,
            "pages": {
                "discovered": stats.urls_discovered,
                "crawled": stats.urls_crawled,
                "failed": stats.urls_failed,
                "skipped": stats.urls_skipped,
                "indexable": stats.indexable_urls,
                "non_indexable": stats.non_indexable_urls
            },
            "issues": {
                "critical": stats.critical_issues,
                "high": stats.high_issues,
                "medium": stats.medium_issues,
                "low": stats.low_issues
            },
            "templates": stats.templates_count,
            "performance_sample": stats.performance_sample_count,
            "laya": {
                "decisions": laya_summary.get("total_decisions", 0),
                "median_latency_ms": laya_summary.get("median_latency_ms", 0.0),
                "p95_latency_ms": laya_summary.get("p95_latency_ms", 0.0)
            },
            "reports": {
                "docx": os.path.join(self.output_dir, "seo-audit.docx"),
                "executive_docx": os.path.join(self.output_dir, "executive-summary.docx")
            }
        }

        if v2_meta:
            data["v2_intelligence"] = v2_meta

        path = os.path.join(self.output_dir, "summary.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

        return data

    def generate_crawl_summary_json(
        self,
        website: str,
        crawl_id: str,
        stats: CrawlStats,
        page_types_dist: Dict[str, int],
        status_dist: Dict[int, int],
        issue_cat_dist: Dict[str, int]
    ):
        data = {
            "website": website,
            "crawl_id": crawl_id,
            "stats": stats.to_dict(),
            "distributions": {
                "page_types": page_types_dist,
                "http_status": status_dist,
                "issue_categories": issue_cat_dist
            }
        }
        path = os.path.join(self.output_dir, "crawl-summary.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def generate_site_profile(
        self,
        website: str,
        total_discovered: int,
        page_types_dist: Dict[str, int],
        template_count: int,
        out_path: str = "data/site-profile.json"
    ):
        domain = urllib.parse.urlparse(website).netloc
        data = {
            "domain": domain,
            "estimated_pages": total_discovered,
            "page_types": page_types_dist,
            "templates": template_count
        }
        os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def generate_readme(self, website: str, crawl_id: str, stats: CrawlStats):
        content = f"""# SEOJEV V2 Audit Reports & Intelligence Suite

- **Website**: {website}
- **Crawl ID**: `{crawl_id}`
- **Discovered URLs**: {stats.urls_discovered:,}
- **Crawled URLs**: {stats.urls_crawled:,}
- **Indexable URLs**: {stats.indexable_urls:,}
- **Total Issues Detected**: {stats.total_issues:,}

## Deliverables in this Directory:

1. **`seo-audit.docx`**: Full 23-Section Ranking-Focused Decision Audit Report.
2. **`executive-summary.docx`**: Standalone Executive Summary answering the 14 core questions.
3. **`summary.json`**: Primary audit metrics conforming to JSON schema.
4. **`crawl-summary.json`**: Exhaustive crawl breakdown and category distributions.
5. **`ranking-opportunities.csv`**: Structured ranking diagnostics and action prioritizations.
6. **`product-pages.csv`**: Automotive product intelligence and content coverage scores.
7. **`product-page-actions.csv`**: Page-by-page specific engineering and content fixes.
8. **`gsc-query-analysis.csv`**: Search Console query positions, impressions, CTR, and opportunity sets.
9. **`issues.csv`**: Granular register of all individual issues.
10. **`issue-clusters.csv`**: High-level aggregated issue clusters (Template / Site-wide).
11. **`templates.csv`**: Template clustering analysis and systemic health percentages.
12. **`internal-link-opportunities.csv`**: Concrete `Source URL -> Anchor Text -> Target URL` link injection pairs.
13. **`content-gaps.csv`**: Detailed commercial content gaps for product pages.
14. **`aeo-analysis.csv`**: Answer Engine Optimization readiness scores and Q&A checklists.
15. **`geo-analysis.csv`**: Generative Search Optimization structural scores and entity clarity.
16. **`schema-analysis.csv`**: Schema.org JSON-LD extraction and validation audit.
17. **`performance.csv`**: Browser-measured representative Core Web Vitals sample.
18. **`laya-decisions.csv`**: Local Laya-MLX classification decisions and latency logs.
19. **`pages.csv`**: Complete crawled page inventory.
20. **`internal-links.csv`**: Link graph edge list.
"""
        with open(os.path.join(self.output_dir, "README.md"), "w", encoding="utf-8") as f:
            f.write(content)
