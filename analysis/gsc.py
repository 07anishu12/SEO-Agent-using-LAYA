import os
import csv
import re
from typing import Dict, Any, List, Optional, Tuple
from collections import defaultdict

class GSCAnalyzer:
    def __init__(self, gsc_csv_path: Optional[str] = None):
        self.gsc_csv_path = gsc_csv_path
        self.query_rows: List[Dict[str, Any]] = []
        self.page_to_queries: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        self.has_data = False
        if gsc_csv_path and os.path.exists(gsc_csv_path):
            self._load_csv(gsc_csv_path)

    def _normalize_url(self, url: str) -> str:
        u = url.strip()
        if len(u) > 1 and u.endswith("/"):
            u = u[:-1]
        return u.lower()

    def _load_csv(self, path: str):
        try:
            with open(path, "r", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                headers = {h.strip().lower(): h for h in (reader.fieldnames or [])}
                
                # Identify header aliases
                query_col = headers.get("query") or headers.get("top queries") or headers.get("search query")
                page_col = headers.get("page") or headers.get("landing page") or headers.get("top pages") or headers.get("url")
                clicks_col = headers.get("clicks")
                imp_col = headers.get("impressions")
                ctr_col = headers.get("ctr")
                pos_col = headers.get("position") or headers.get("average position")

                for row in reader:
                    query = row.get(query_col, "").strip() if query_col else ""
                    page = row.get(page_col, "").strip() if page_col else ""
                    if not page and not query:
                        continue

                    clicks = int(float(row.get(clicks_col, 0) or 0)) if clicks_col else 0
                    impressions = int(float(row.get(imp_col, 0) or 0)) if imp_col else 0
                    
                    # CTR parsing
                    raw_ctr = str(row.get(ctr_col, "0%")).replace("%", "").strip() if ctr_col else "0"
                    try:
                        ctr = round(float(raw_ctr), 2)
                    except Exception:
                        ctr = 0.0

                    # Position parsing
                    try:
                        pos = round(float(row.get(pos_col, 0) or 0), 1) if pos_col else 0.0
                    except Exception:
                        pos = 0.0

                    record = {
                        "query": query,
                        "page": page,
                        "clicks": clicks,
                        "impressions": impressions,
                        "ctr": ctr,
                        "position": pos,
                        "bracket": self._get_position_bracket(pos)
                    }
                    self.query_rows.append(record)
                    if page:
                        norm_page = self._normalize_url(page)
                        self.page_to_queries[norm_page].append(record)

            self.has_data = len(self.query_rows) > 0
        except Exception as e:
            self.has_data = False

    def _get_position_bracket(self, pos: float) -> str:
        if pos <= 0:
            return "Unranked"
        elif 1.0 <= pos <= 3.0:
            return "1-3"
        elif 3.0 < pos <= 10.0:
            return "4-10"
        elif 10.0 < pos <= 20.0:
            return "11-20"
        elif 20.0 < pos <= 30.0:
            return "21-30"
        elif 30.0 < pos <= 50.0:
            return "31-50"
        else:
            return "51-100"

    def get_page_ranking_data(self, url: str) -> Optional[Dict[str, Any]]:
        if not self.has_data:
            return None
        norm_url = self._normalize_url(url)
        queries = self.page_to_queries.get(norm_url, [])
        if not queries:
            return None

        # Sort queries by impressions descending
        queries_sorted = sorted(queries, key=lambda x: x["impressions"], reverse=True)
        top_query_rec = queries_sorted[0]
        
        total_impressions = sum(q["impressions"] for q in queries)
        total_clicks = sum(q["clicks"] for q in queries)
        avg_pos = round(sum(q["position"] * q["impressions"] for q in queries) / max(total_impressions, 1), 1)
        avg_ctr = round((total_clicks / max(total_impressions, 1)) * 100, 2)

        return {
            "has_data": True,
            "top_query": top_query_rec["query"],
            "top_query_position": top_query_rec["position"],
            "top_query_impressions": top_query_rec["impressions"],
            "top_query_clicks": top_query_rec["clicks"],
            "top_query_ctr": top_query_rec["ctr"],
            "total_impressions": total_impressions,
            "total_clicks": total_clicks,
            "average_position": avg_pos,
            "average_ctr": avg_ctr,
            "position_bracket": self._get_position_bracket(avg_pos),
            "all_queries": queries_sorted[:10]
        }

    def get_optimization_opportunity_set(self) -> List[Dict[str, Any]]:
        """
        Pages ranking positions 11-30 (Optimization Opportunity Set) with high impressions.
        """
        if not self.has_data:
            return []

        opps = []
        for norm_url, q_list in self.page_to_queries.items():
            total_imp = sum(q["impressions"] for q in q_list)
            avg_pos = round(sum(q["position"] * q["impressions"] for q in q_list) / max(total_imp, 1), 1)
            
            # Position 11-30 check
            if 10.5 <= avg_pos <= 30.5 and total_imp >= 20:
                top_q = sorted(q_list, key=lambda x: x["impressions"], reverse=True)[0]
                opps.append({
                    "url": q_list[0]["page"],
                    "top_query": top_q["query"],
                    "position": avg_pos,
                    "impressions": total_imp,
                    "clicks": sum(q["clicks"] for q in q_list),
                    "bracket": "11-20" if avg_pos <= 20.5 else "21-30",
                    "opportunity_type": "Position 11-30 Striking Distance"
                })

        opps.sort(key=lambda x: x["impressions"], reverse=True)
        return opps

    def get_ctr_presentation_opportunities(self) -> List[Dict[str, Any]]:
        """
        High impressions + low CTR (below expected for their position bracket).
        Search-result presentation opportunity.
        """
        if not self.has_data:
            return []

        opps = []
        for norm_url, q_list in self.page_to_queries.items():
            total_imp = sum(q["impressions"] for q in q_list)
            total_clk = sum(q["clicks"] for q in q_list)
            ctr = (total_clk / max(total_imp, 1)) * 100
            avg_pos = sum(q["position"] * q["impressions"] for q in q_list) / max(total_imp, 1)

            # High impressions with low CTR (< 2.0% in top 10, or < 0.8% in 11-20)
            if (avg_pos <= 10 and total_imp >= 100 and ctr < 2.0) or (10 < avg_pos <= 20 and total_imp >= 200 and ctr < 0.8):
                top_q = sorted(q_list, key=lambda x: x["impressions"], reverse=True)[0]
                opps.append({
                    "url": q_list[0]["page"],
                    "top_query": top_q["query"],
                    "position": round(avg_pos, 1),
                    "impressions": total_imp,
                    "clicks": total_clk,
                    "ctr": round(ctr, 2),
                    "diagnosis": "Search-result presentation opportunity: Title/Snippet alignment deficit."
                })

        opps.sort(key=lambda x: x["impressions"], reverse=True)
        return opps
