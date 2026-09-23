from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Tuple

class VerticalInterface(ABC):
    """Universal interface for domain-specific verticals and overlays."""
    name: str = "generic"

    @abstractmethod
    def detect(self, profile: Any) -> float:
        """Evaluates likelihood that target website belongs to this vertical (0.0 to 1.0)."""
        pass

    @abstractmethod
    def get_attribute_ontology(self) -> Dict[str, Dict[str, Any]]:
        """Returns map of attribute names to synonyms, expected units, and validation regex."""
        pass

    @abstractmethod
    def get_question_bank(self) -> List[str]:
        """Returns standard consumer search questions for this vertical (for AEO analysis)."""
        pass

    @abstractmethod
    def get_intent_lexicon(self) -> Dict[str, List[str]]:
        """Returns mapping of search intents to characteristic keyword tokens."""
        pass

    @abstractmethod
    def get_section_expectations(self) -> List[str]:
        """Returns list of essential structural content sections expected on product/detail pages."""
        pass

    @abstractmethod
    def get_schema_expectations(self) -> List[str]:
        """Returns expected Schema.org types for pages in this vertical."""
        pass
