"""
Apple Silicon MLX Backend for local inference using laya_mlx.
"""
import logging
from typing import Dict, Any, Optional
from .base import LayaBackend

logger = logging.getLogger("seojev.laya.mlx")


class MLXBackend(LayaBackend):
    def __init__(self):
        self.model_id: Optional[str] = None
        self._agent = None
        self._options: Dict[str, Any] = {}

    def initialize(self, model_id: str = "aac6fef/laya-mlx", options: Optional[Dict[str, Any]] = None) -> bool:
        self.model_id = model_id
        self._options = options or {}
        try:
            import laya_mlx
            logger.info(f"Initializing MLX backend with model '{model_id}'...")
            self._agent = laya_mlx.load(model_id)
            logger.info("MLX backend initialized successfully.")
            return True
        except Exception as e:
            logger.warning(f"Failed to initialize MLX backend: {e}")
            self._agent = None
            return False

    def is_available(self) -> bool:
        return self._agent is not None

    def predict(self, prompt_state: Dict[str, Any], questions: Dict[str, Any]) -> Dict[str, Any]:
        if not self.is_available():
            raise RuntimeError("MLX backend is not available for inference.")
        return self._agent.predict(prompt_state, questions)

    def health_status(self) -> Dict[str, Any]:
        return {
            "backend": "mlx",
            "available": self.is_available(),
            "model_id": self.model_id,
            "device": "apple_silicon",
            "framework": "mlx"
        }
