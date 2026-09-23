import os
import csv
import sqlite3
import json
from typing import Dict, Any, List, Optional

class CSVSuiteExporter:
    """
    Exports comprehensive 25+ stable CSV datasets for deep spreadsheet analysis and BI tools.
    Pulls data directly from SQLite database and in-memory evaluation results.
    """
    def __init__(self, output_dir: str = "reports/drivio/csv", db_path: str = "data/seo.db"):
        self.output_dir = output_dir
        self.db_path = db_path
        os.makedirs(output_dir, exist_ok=True)

    def export_all(self, run_id: Optional[str] = None) -> Dict[str, int]:
        """Pulls from SQLite tables and exports 25+ CSV files, returning row counts."""
        exported = {}
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row

            def dump_query(filename: str, query: str, params: tuple = ()) -> int:
                rows = [dict(r) for r in conn.execute(query, params).fetchall()]
                self._write_csv(filename, rows)
                exported[filename] = len(rows)
                return len(rows)

            # 1. Pages
            dump_query("pages.csv", "SELECT * FROM pages")

            # 2. Issues All
            dump_query("issues_all.csv", "SELECT * FROM issues")

            # 3. Issues Critical & High
            dump_query("issues_critical_high.csv", "SELECT * FROM issues WHERE severity IN ('CRITICAL', 'HIGH')")

            # 4. Issue Clusters
            dump_query("issue_clusters.csv", "SELECT * FROM findings")

            # 5. Opportunities
            dump_query("opportunities.csv", "SELECT * FROM opportunities ORDER BY priority_score DESC")

            # 6. Work Orders
            dump_query("work_orders.csv", "SELECT * FROM work_orders ORDER BY priority ASC")

            # 7. Templates
            dump_query("templates.csv", "SELECT template_id, COUNT(*) as page_count, AVG(word_count) as avg_words FROM pages GROUP BY template_id")

            # 8. Internal Links
            dump_query("internal_links.csv", "SELECT * FROM links LIMIT 100000")

            # 9. Link Recommendations
            dump_query("link_recommendations.csv", "SELECT * FROM opportunities WHERE type = 'LINK'")

            # 10. GSC Queries
            dump_query("gsc_queries.csv", "SELECT * FROM gsc_rows ORDER BY impressions DESC LIMIT 50000")

            # 11. Query Page Map
            dump_query("query_page_map.csv", "SELECT * FROM query_page_map ORDER BY impressions DESC")

            # 12. Cannibalization
            dump_query("cannibalization.csv", "SELECT * FROM query_page_map WHERE verdict = 'COMPETING_URLS'")

            # 13. Striking Distance
            dump_query("striking_distance.csv", "SELECT * FROM query_page_map WHERE position BETWEEN 11.0 AND 20.0")

            # 14. Entity Coverage
            dump_query("entity_coverage.csv", "SELECT * FROM attributes")

            # 15. Content Gaps
            dump_query("content_gaps.csv", "SELECT * FROM opportunities WHERE type = 'CONTENT'")

            # 16. Schemas
            dump_query("schemas.csv", "SELECT * FROM schema_items")

            # 17. Soft 404s
            dump_query("soft_404s.csv", "SELECT * FROM findings WHERE rule_id LIKE '%404%'")

            # 18. Traps
            dump_query("traps.csv", "SELECT * FROM findings WHERE rule_id LIKE '%TRAP%'")

            # 19. Performance
            dump_query("performance.csv", "SELECT url, load_time, word_count, internal_links_count FROM pages ORDER BY load_time DESC LIMIT 1000")

            # 20. AEO Evaluations
            dump_query("aeo_evaluations.csv", "SELECT * FROM opportunities WHERE type = 'AEO'")

            # 21. GEO Evaluations
            dump_query("geo_evaluations.csv", "SELECT * FROM opportunities WHERE type = 'GEO'")

            # 22. Freshness & YMYL
            dump_query("freshness_ymyl.csv", "SELECT * FROM findings WHERE rule_id LIKE '%FRESHNESS%' OR rule_id LIKE '%YMYL%'")

            # 23. JS SEO Diffs
            dump_query("js_seo_diffs.csv", "SELECT * FROM findings WHERE rule_id LIKE '%JS%'")

            # 24. Competitor Matrix
            dump_query("competitor_matrix.csv", "SELECT * FROM competitor_pages")

            # 25. Numeric Provenance
            dump_query("numeric_provenance.csv", "SELECT * FROM numeric_provenance")

        return exported

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
