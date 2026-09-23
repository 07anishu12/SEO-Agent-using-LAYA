import os
import csv
from typing import List, Dict, Any

class CSVReportGenerator:
    def __init__(self, output_dir: str = "reports/"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    def export_v2(
        self,
        pages: List[Dict[str, Any]],
        issues: List[Dict[str, Any]],
        issue_clusters: List[Dict[str, Any]],
        ranking_opportunities: List[Dict[str, Any]],
        product_pages: List[Dict[str, Any]],
        product_page_actions: List[Dict[str, Any]],
        gsc_queries: List[Dict[str, Any]],
        templates: List[Dict[str, Any]],
        internal_link_opportunities: List[Dict[str, Any]],
        content_gaps: List[Dict[str, Any]],
        aeo_analysis: List[Dict[str, Any]],
        geo_analysis: List[Dict[str, Any]],
        schema_analysis: List[Dict[str, Any]],
        performance: List[Dict[str, Any]],
        laya_decisions: List[Dict[str, Any]],
        links: List[Dict[str, Any]]
    ):
        self._write_csv("pages.csv", pages)
        self._write_csv("issues.csv", issues)
        self._write_csv("issue-clusters.csv", issue_clusters)
        self._write_csv("ranking-opportunities.csv", ranking_opportunities)
        self._write_csv("product-pages.csv", product_pages)
        self._write_csv("product-page-actions.csv", product_page_actions)
        self._write_csv("gsc-query-analysis.csv", gsc_queries)
        self._write_csv("templates.csv", templates)
        self._write_csv("internal-link-opportunities.csv", internal_link_opportunities)
        self._write_csv("content-gaps.csv", content_gaps)
        self._write_csv("aeo-analysis.csv", aeo_analysis)
        self._write_csv("geo-analysis.csv", geo_analysis)
        self._write_csv("schema-analysis.csv", schema_analysis)
        self._write_csv("performance.csv", performance)
        self._write_csv("laya-decisions.csv", laya_decisions)
        self._write_csv("internal-links.csv", links)

    def _write_csv(self, filename: str, rows: List[Dict[str, Any]]):
        filepath = os.path.join(self.output_dir, filename)
        if not rows:
            with open(filepath, "w", newline="", encoding="utf-8") as f:
                f.write("")
            return

        headers = list(rows[0].keys())
        with open(filepath, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=headers, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(rows)
