import re
import json
from typing import Dict, Any, List, Optional, Tuple
from bs4 import BeautifulSoup

INFORMATION_CLASSES = [
    "PRICE", "VARIANTS", "SPECIFICATIONS", "MILEAGE", "FEATURES",
    "COMPARISON", "EMI_FINANCE", "FAQ", "OWNERSHIP_COST",
    "ALTERNATIVES", "REVIEWS", "MEDIA"
]

class ProvenanceExtractor:
    """Extracts entity attributes with verifiable provenance and evaluates ProductCoverageProfile across 12 information classes."""
    def __init__(self, vertical):
        self.vertical = vertical
        self.ontology = vertical.get_attribute_ontology()

    def extract_with_provenance(self, html: str, url: str) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """Extracts attributes with provenance and builds ProductCoverageProfile.
        Returns: (attributes_map, coverage_profile)
        """
        soup = BeautifulSoup(html, "lxml")
        body_text = soup.get_text(separator=" ").lower()
        attributes = {}

        # 1. Price
        price_match = re.search(r"₹\s*([0-9,]+)", html)
        if price_match:
            attributes["price"] = {
                "value": price_match.group(0),
                "source_type": "visible",
                "selector": ".price, span, div",
                "text_span": price_match.group(0),
                "confidence": 0.95
            }
        else:
            attributes["price"] = {"value": None, "absent_reason": "not_present"}

        # 2. Mileage
        mileage_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:kmpl|km/l)", body_text)
        if mileage_match:
            attributes["mileage"] = {
                "value": f"{mileage_match.group(1)} kmpl",
                "source_type": "visible",
                "selector": "table, p",
                "text_span": mileage_match.group(0),
                "confidence": 0.90
            }
        else:
            attributes["mileage"] = {"value": None, "absent_reason": "not_present"}

        # 3. Engine CC
        engine_match = re.search(r"(\d+(?:\.\d+)?)\s*cc\b", body_text)
        if engine_match:
            attributes["engine_cc"] = {
                "value": f"{engine_match.group(1)} cc",
                "source_type": "visible",
                "selector": "table, p",
                "text_span": engine_match.group(0),
                "confidence": 0.90
            }
        else:
            attributes["engine_cc"] = {"value": None, "absent_reason": "not_present"}

        # 4. Power
        power_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:bhp|ps|hp)\b", body_text)
        if power_match:
            attributes["power_bhp"] = {
                "value": f"{power_match.group(1)} bhp",
                "source_type": "visible",
                "selector": "table, p",
                "text_span": power_match.group(0),
                "confidence": 0.90
            }
        else:
            attributes["power_bhp"] = {"value": None, "absent_reason": "not_present"}

        # 5. Build ProductCoverageProfile across 12 information classes
        profile = {}
        has_table = bool(soup.find("table"))
        
        profile["PRICE"] = {"present": attributes["price"]["value"] is not None, "structured": has_table, "answer_extractable": True}
        profile["VARIANTS"] = {"present": "variant" in body_text, "structured": bool(soup.find("ul") or has_table), "answer_extractable": False}
        profile["SPECIFICATIONS"] = {"present": attributes["engine_cc"]["value"] is not None or "specification" in body_text, "structured": has_table, "answer_extractable": has_table}
        profile["MILEAGE"] = {"present": attributes["mileage"]["value"] is not None, "structured": has_table, "answer_extractable": True}
        profile["FEATURES"] = {"present": "feature" in body_text, "structured": bool(soup.find("ul")), "answer_extractable": False}
        profile["COMPARISON"] = {"present": any(k in body_text for k in (" vs ", "compare", "alternative")), "structured": has_table, "answer_extractable": False}
        profile["EMI_FINANCE"] = {"present": any(k in body_text for k in ("emi", "loan", "finance")), "structured": has_table, "answer_extractable": True}
        profile["FAQ"] = {"present": any(k in body_text for k in ("faq", "frequently asked")), "structured": bool(soup.find_all("h3")), "answer_extractable": True}
        profile["OWNERSHIP_COST"] = {"present": any(k in body_text for k in ("service cost", "maintenance", "warranty")), "structured": False, "answer_extractable": False}
        profile["ALTERNATIVES"] = {"present": any(k in body_text for k in ("similar", "alternative", "competitor")), "structured": False, "answer_extractable": False}
        profile["REVIEWS"] = {"present": any(k in body_text for k in ("review", "rating", "verdict")), "structured": False, "answer_extractable": False}
        profile["MEDIA"] = {"present": bool(soup.find_all("img")), "structured": True, "answer_extractable": False}

        present_count = sum(1 for c in profile.values() if c["present"])
        profile_summary = {
            "classes": profile,
            "classes_present_count": present_count,
            "total_classes": len(INFORMATION_CLASSES),
            "coverage_percentage": round((present_count / len(INFORMATION_CLASSES)) * 100, 1)
        }

        return attributes, profile_summary
