from typing import Dict, Any, List
from .base import VerticalInterface

class GenericVertical(VerticalInterface):
    """Universal baseline vertical for any website."""
    name: str = "generic"

    def detect(self, profile: Any) -> float:
        return 0.1 # Baseline fallback confidence

    def get_attribute_ontology(self) -> Dict[str, Dict[str, Any]]:
        return {
            "name": {"synonyms": ["title", "product name", "item"], "unit": None},
            "price": {"synonyms": ["cost", "mrp", "rate", "fee"], "unit": "currency"},
            "description": {"synonyms": ["overview", "summary", "about"], "unit": None},
            "features": {"synonyms": ["highlights", "specifications", "details"], "unit": None},
            "sku": {"synonyms": ["model number", "product id"], "unit": None}
        }

    def get_question_bank(self) -> List[str]:
        return [
            "What is the price of {product}?",
            "How does {product} work?",
            "What are the features of {product}?",
            "Is there a return policy or warranty?",
            "Where to buy {product}?"
        ]

    def get_intent_lexicon(self) -> Dict[str, List[str]]:
        return {
            "commercial": ["best", "top", "review", "comparison", "vs", "rating"],
            "transactional": ["buy", "order", "price", "cost", "discount", "deal"],
            "informational": ["how to", "what is", "guide", "tutorial", "tips"],
            "navigational": ["login", "portal", "contact", "support", "official"]
        }

    def get_section_expectations(self) -> List[str]:
        return ["price", "features", "description", "faqs", "reviews", "contact"]

    def get_schema_expectations(self) -> List[str]:
        return ["WebPage", "Product", "Organization", "BreadcrumbList"]
