import os
import json
import csv
from typing import Dict, Any, List, Optional
from collections import Counter

class AIObservationsPipeline:
    """Ingests and analyzes real generative AI citations (Perplexity, ChatGPT, Copilot) or generates observational test queries."""
    def __init__(self, observations_path: Optional[str] = None):
        self.observations_path = observations_path
        self.has_observations = bool(observations_path and os.path.exists(observations_path))
        self.observations: List[Dict[str, Any]] = []
        if self.has_observations:
            self._load_observations()

    def _load_observations(self):
        try:
            if os.path.isdir(self.observations_path):
                files = [os.path.join(self.observations_path, f) for f in os.listdir(self.observations_path) if f.endswith((".json", ".csv"))]
            else:
                files = [self.observations_path]

            for fpath in files:
                if fpath.endswith(".json"):
                    with open(fpath, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        if isinstance(data, list):
                            self.observations.extend(data)
                        elif isinstance(data, dict):
                            self.observations.append(data)
                elif fpath.endswith(".csv"):
                    with open(fpath, "r", encoding="utf-8") as f:
                        reader = csv.DictReader(f)
                        self.observations.extend(list(reader))
        except Exception:
            self.has_observations = False

    def compute_summary(self, target_domain: str = "drivio.in") -> Dict[str, Any]:
        if not self.has_observations:
            return {
                "has_observations": False,
                "label": "STRUCTURAL GEO ANALYSIS",
                "message": "AI OBSERVATIONS REQUIRED: Connect third-party AI citation logs to measure observed citation share."
            }

        total = len(self.observations)
        target_citations = 0
        domain_counts = Counter()

        for obs in self.observations:
            citations = obs.get("citations") or []
            if isinstance(citations, str):
                citations = [c.strip() for c in citations.split(",") if c.strip()]

            for c in citations:
                domain_counts[c] += 1
                if target_domain.lower() in c.lower():
                    target_citations += 1

        share = round((target_citations / max(total, 1)) * 100, 1)

        return {
            "has_observations": True,
            "total_observed_queries": total,
            "target_domain_citations": target_citations,
            "citation_share_pct": share,
            "top_cited_domains": domain_counts.most_common(5)
        }

    def generate_observation_query_template(self, product_models: List[str]) -> List[str]:
        """Generates standard consumer queries for manual testing across AI engines."""
        queries = []
        for m in product_models[:10]:
            queries.append(f"What is the on-road price of {m} in Delhi?")
            queries.append(f"What is the real world mileage and top speed of {m}?")
            queries.append(f"What are the best finance and EMI deals for {m}?")
        return queries
