import re
import urllib.parse
from typing import Dict, Any, List, Optional, Tuple, Set

class EntityGraphEngine:
    """Site-learned gazetteer with alias resolution, cross-source consistency, and fact verification."""
    def __init__(self):
        self.gazetteer: Dict[str, str] = {} # alias -> canonical_id
        self.entities: Dict[str, Dict[str, Any]] = {} # canonical_id -> details

    def register_entity(self, canonical_id: str, name: str, entity_type: str, aliases: List[str] = None):
        """Registers a canonical entity and its alias mappings."""
        self.entities[canonical_id] = {
            "canonical_id": canonical_id,
            "name": name,
            "type": entity_type
        }
        # Normalize and map aliases
        norm_name = self._normalize_token(name)
        self.gazetteer[norm_name] = canonical_id
        if aliases:
            for al in aliases:
                self.gazetteer[self._normalize_token(al)] = canonical_id

    def _normalize_token(self, text: str) -> str:
        return re.sub(r"[^a-z0-9]", "", (text or "").lower())

    def are_aliases(self, term1: str, term2: str) -> bool:
        """Determines if two entity terms refer to the same canonical entity, accounting for brand prefixes."""
        t1_norm = self._normalize_token(term1)
        t2_norm = self._normalize_token(term2)

        if t1_norm == t2_norm:
            return True

        # Check registered gazetteer
        id1 = self.gazetteer.get(t1_norm)
        id2 = self.gazetteer.get(t2_norm)
        if id1 and id2 and id1 == id2:
            return True

        # Benign prefix check: e.g. "Bajaj Pulsar 125" vs "Pulsar 125"
        if t1_norm.endswith(t2_norm) or t2_norm.endswith(t1_norm):
            return True

        return False

    def evaluate_page_consistency(
        self,
        url: str,
        title: str,
        h1: str,
        schema_entities: List[str] = None,
        visible_price: Optional[str] = None,
        schema_price: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Compares Title, H1, Schema, and Visible facts for contradictions."""
        issues = []

        # 1. Title vs H1 entity check
        if title and h1:
            # Extract main capitalized model phrases
            t_clean = re.sub(r"(price|specs|mileage|on road|drivio|india|features).*", "", title, flags=re.I).strip()
            h_clean = re.sub(r"(price|specs|mileage|on road|drivio|india|features).*", "", h1, flags=re.I).strip()

            if t_clean and h_clean and not self.are_aliases(t_clean, h_clean):
                # Check token overlap
                t_tokens = set(re.findall(r"\w+", t_clean.lower()))
                h_tokens = set(re.findall(r"\w+", h_clean.lower()))
                if not (t_tokens & h_tokens):
                    issues.append({
                        "issue_type": "entity_conflict_title_h1",
                        "severity": "high",
                        "claim_type": "OBSERVED",
                        "title_value": title,
                        "h1_value": h1,
                        "message": f"Entity contradiction between Title ('{t_clean}') and H1 ('{h_clean}').",
                        "evidence": f"Title tag has '{title}' while H1 heading displays '{h1}' with 0 common model tokens."
                    })

        # 2. Fact Consistency: Visible Price vs Schema.org Price
        if visible_price and schema_price:
            v_num = re.sub(r"[^\d]", "", visible_price)
            s_num = re.sub(r"[^\d]", "", schema_price)
            if v_num and s_num and v_num != s_num:
                # If price differs by more than 10%
                try:
                    vn = float(v_num)
                    sn = float(s_num)
                    if abs(vn - sn) > (min(vn, sn) * 0.05): # >5% variance
                        issues.append({
                            "issue_type": "cross_source_price_mismatch",
                            "severity": "critical",
                            "claim_type": "OBSERVED",
                            "visible_price": visible_price,
                            "schema_price": schema_price,
                            "message": f"Price contradiction: on-page text shows ₹{vn:,.0f} but Schema.org Offer outputs ₹{sn:,.0f}.",
                            "evidence": f"Selector visible text: '{visible_price}' vs JSON-LD Offer.price: '{schema_price}'."
                        })
                except ValueError:
                    pass

        return issues
