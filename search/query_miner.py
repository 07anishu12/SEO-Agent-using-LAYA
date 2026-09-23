import re
from typing import Dict, Any, List, Tuple
from collections import Counter

class QueryMiner:
    """Parses search query entities, classifies multi-label intent, and computes demand-weighted attribute priorities."""
    def __init__(self, vertical=None):
        self.vertical = vertical
        self.intent_lexicon = vertical.get_intent_lexicon() if vertical else {}

    def parse_query(self, query_text: str) -> Dict[str, Any]:
        """Extracts brand, model, intent, location, and structural query template."""
        q_lower = query_text.lower().strip()
        tokens = re.findall(r"\w+", q_lower)

        # 1. Location detection
        cities = ["delhi", "mumbai", "bangalore", "bengaluru", "hyderabad", "chennai", "pune", "kolkata", "jaipur"]
        location = next((c for c in cities if c in tokens), None)

        # 2. Multi-label intent classification
        intents = []
        for intent_name, keywords in self.intent_lexicon.items():
            if any(k in q_lower for k in keywords):
                intents.append(intent_name)

        if not intents:
            if any(k in q_lower for k in ("what", "how", "why", "when", "guide")):
                intents.append("informational")
            else:
                intents.append("commercial")

        primary_intent = intents[0]

        # 3. Query template abstraction
        template_str = q_lower
        if location:
            template_str = template_str.replace(location, "{city}")
        for k in ("price", "on road", "cost"):
            if k in template_str:
                template_str = template_str.replace(k, "{price}")
        for k in ("mileage", "average", "kmpl"):
            if k in template_str:
                template_str = template_str.replace(k, "{mileage}")
        for k in ("emi", "loan", "down payment"):
            if k in template_str:
                template_str = template_str.replace(k, "{emi}")

        return {
            "query": query_text,
            "primary_intent": primary_intent,
            "intents": intents,
            "location": location,
            "query_template": template_str
        }

    def compute_demand_weighted_attribute_priority(self, gsc_rows: List[Dict[str, Any]]) -> Dict[str, float]:
        """Computes share of total impression demand driven by each attribute/intent."""
        intent_impressions = Counter()
        total_impr = 0

        for r in gsc_rows:
            parsed = self.parse_query(r["query"])
            impr = r.get("impressions", 1)
            total_impr += impr
            intent_impressions[parsed["primary_intent"]] += impr

        priorities = {}
        for intent, count in intent_impressions.items():
            priorities[intent] = round((count / max(total_impr, 1)) * 100, 1)

        return priorities
