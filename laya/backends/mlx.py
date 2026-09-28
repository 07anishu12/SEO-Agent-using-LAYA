"""
Apple Silicon MLX Backend for local inference using laya_mlx.
"""
import logging
import platform
import threading
from typing import Dict, Any, Optional
from .base import LayaBackend

logger = logging.getLogger("seojev.laya.mlx")


class MLXBackend(LayaBackend):
    def __init__(self):
        self.model_id: Optional[str] = None
        self._agent = None
        self._options: Dict[str, Any] = {}
        self._predict_lock = threading.Lock()
        self.checkpoint_id = None

    def initialize(self, model_id: str = "aac6fef/laya-mlx", options: Optional[Dict[str, Any]] = None) -> bool:
        self.model_id = model_id
        self._options = options or {}
        try:
            if platform.system() != "Darwin" or platform.machine() != "arm64":
                raise RuntimeError("MLX requires native Apple Silicon macOS, outside Docker")
            import laya_mlx
            logger.info(f"Initializing MLX backend with model '{model_id}'...")
            self._agent = laya_mlx.load(model_id)
            self.checkpoint_id = f"{model_id}@{self._agent.model_dir.name}"
            logger.info("Laya calibration temperatures raw=%s applied=%s; SEO questions use at most 8 options", self._agent.temperature_by_options_raw, self._agent.temperature_by_options)
            logger.info("MLX backend initialized successfully.")
            return True
        except Exception as e:
            self._agent = None
            raise RuntimeError("Laya MLX startup failed. Run .venv/bin/python3 on the Apple Silicon host; install pinned requirements and ensure aac6fef/laya-mlx is accessible. " + str(e)) from e

    def is_available(self) -> bool:
        return self._agent is not None

    def predict(self, prompt_state: Dict[str, Any], questions: Dict[str, Any]) -> Dict[str, Any]:
        if not self.is_available():
            raise RuntimeError("MLX backend is not available for inference.")
        with self._predict_lock:
            return self._agent.predict(prompt_state, questions)

    def health_status(self) -> Dict[str, Any]:
        return {
            "backend": "mlx",
            "available": self.is_available(),
            "model_id": self.model_id,
            "checkpoint_id": self.checkpoint_id,
            "device": "apple_silicon",
            "framework": "mlx"
        }
