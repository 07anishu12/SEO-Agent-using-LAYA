"""
Base abstraction for Laya inference backends.
SEOJEV uses native Apple Silicon MLX as the exclusive AI decision maker.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional


class LayaBackend(ABC):
    """Abstract interface that all Laya inference backends must implement."""

    @abstractmethod
    def initialize(self, model_id: str, options: Optional[Dict[str, Any]] = None) -> bool:
        """Initializes model weights or remote client."""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Returns True if the backend is loaded and ready for inference."""
        pass

    @abstractmethod
    def predict(self, prompt_state: Dict[str, Any], questions: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executes inference against structured questions.
        Returns dictionary containing 'answers' with choices and confidence scores.
        """
        pass

    @abstractmethod
    def health_status(self) -> Dict[str, Any]:
        """Returns backend telemetry and operational health."""
        pass
