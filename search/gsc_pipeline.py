import os
import csv
import urllib.parse
from typing import Dict, Any, List, Set, Optional, Tuple

class GSCPipeline:
    """Ingests Google Search Console data, normalizes URLs, matches to crawl frontier, and aggregates performance."""
    def __init__(self, gsc_csv_path: Optional[str] = None, brand_terms: List[str] = None):
        self.gsc_csv_path = gsc_csv_path
        self.brand_terms = [b.lower() for b in (brand_terms or ["drivio"])]
        self.rows: List[Dict[str, Any]] = []
        self.has_data = False
        if gsc_csv_path and os.path.exists(gsc_csv_path):
            self.load_csv(gsc_csv_path)

    def load_csv(self, path: str):
        self.rows = []
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            reader = csv.DictReader(f)
            for r in reader:
                # Column normalization
                clean_row = self._normalize_row(r)
                if clean_row:
                    self.rows.append(clean_row)
        self.has_data = len(self.rows) > 0

    def _normalize_row(self, row: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        # Map common GSC column name variations
        q = row.get("Top queries") or row.get("query") or row.get("Query") or ""
        p = row.get("Top pages") or row.get("page") or row.get("Page") or ""
        if not q or not p:
            return None

        clicks = int(float(row.get("Clicks") or row.get("clicks") or 0))
        impr = int(float(row.get("Impressions") or row.get("impressions") or 0))
        ctr = float(str(row.get("CTR") or row.get("ctr") or "0").replace("%", ""))
        if ctr > 1.0:
            ctr = ctr / 100.0 # Convert percentage to decimal
        pos = float(row.get("Position") or row.get("position") or 0.0)
        dt = row.get("Date") or row.get("date") or ""

        # Normalize page URL
        norm_page = self.normalize_gsc_url(p)
        is_brand = any(b in q.lower() for b in self.brand_terms)

        return {
            "query": q.strip(),
            "page": norm_page,
            "raw_page": p.strip(),
            "clicks": clicks,
            "impressions": impr,
            "ctr": round(ctr, 4),
            "position": round(pos, 1),
            "date": dt,
            "is_brand": is_brand,
            "bracket": self.get_position_bracket(pos)
        }

    @staticmethod
    def normalize_gsc_url(url: str) -> str:
        parsed = urllib.parse.urlsplit(url.strip())
        scheme = parsed.scheme.lower() or "https"
        netloc = parsed.netloc.lower()
        path = parsed.path.rstrip("/")
        return f"{scheme}://{netloc}{path}"

    @staticmethod
    def get_position_bracket(pos: float) -> str:
        if pos <= 3.0: return "1-3"
        elif pos <= 10.0: return "4-10"
        elif pos <= 20.0: return "11-20"
        elif pos <= 30.0: return "21-30"
        elif pos <= 50.0: return "31-50"
        else: return "51-100"

    def match_to_crawl(self, crawled_pages: List[Dict[str, Any]]) -> Dict[str, Any]:
        crawled_url_set = {self.normalize_gsc_url(p["url"]) for p in crawled_pages}
        matched_rows = []
        unmatched_pages = set()

        for r in self.rows:
            if r["page"] in crawled_url_set:
                matched_rows.append(r)
            else:
                unmatched_pages.add(r["page"])

        return {
            "total_gsc_rows": len(self.rows),
            "matched_rows": len(matched_rows),
            "unmatched_urls_count": len(unmatched_pages),
            "unmatched_sample": list(unmatched_pages)[:10]
        }

    def compute_summary(self) -> Dict[str, Any]:
        if not self.has_data:
            return {
                "has_data": False,
                "message": "Search-performance analysis unavailable until GSC data is supplied."
            }

        total_clicks = sum(r["clicks"] for r in self.rows)
        total_impressions = sum(r["impressions"] for r in self.rows)
        weighted_pos = round(sum(r["position"] * r["impressions"] for r in self.rows) / max(total_impressions, 1), 1)

        brackets = {}
        for r in self.rows:
            b = r["bracket"]
            brackets[b] = brackets.get(b, 0) + 1

        brand_rows = [r for r in self.rows if r["is_brand"]]
        non_brand_rows = [r for r in self.rows if not r["is_brand"]]

        return {
            "has_data": True,
            "total_queries": len(self.rows),
            "total_clicks": total_clicks,
            "total_impressions": total_impressions,
            "average_weighted_position": weighted_pos,
            "position_brackets": brackets,
            "brand_queries_count": len(brand_rows),
            "non_brand_queries_count": len(non_brand_rows),
            "pos_11_20_count": brackets.get("11-20", 0),
            "pos_21_30_count": brackets.get("21-30", 0)
        }
