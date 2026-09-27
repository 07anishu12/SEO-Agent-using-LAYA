"""
Remote HTTP API Backend for Laya inference microservices.
"""
import logging
import os
from typing import Dict, Any, Optional
import httpx
from .base import LayaBackend

logger = logging.getLogger("seojev.laya.api")


class APIBackend(LayaBackend):
    def __init__(self, client: Optional[httpx.Client] = None):
        self.client = client or httpx.Client(timeout=5.0)
        self.endpoint_url: str = os.environ.get("LAYA_API_URL", "http://127.0.0.1:8080/v1/predict")
        self.api_key: Optional[str] = os.environ.get("LAYA_API_KEY")
        self.model_id: Optional[str] = None
        self._available: bool = False

    def initialize(self, model_id: str = "laya-remote", options: Optional[Dict[str, Any]] = None) -> bool:
        self.model_id = model_id
        opts = options or {}
        if "endpoint_url" in opts:
            self.endpoint_url = opts["endpoint_url"]
        if "api_key" in opts:
            self.api_key = opts["api_key"]

        # In testing or local environments, verify configuration
        self._available = bool(self.endpoint_url)
        return self._available

    def is_available(self) -> bool:
        return self._available

    def predict(self, prompt_state: Dict[str, Any], questions: Dict[str, Any]) -> Dict[str, Any]:
        if not self.is_available():
            raise RuntimeError("API backend is not configured or available.")

        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        payload = {
            "model": self.model_id,
            "prompt_state": prompt_state,
            "questions": questions
        }

        try:
            resp = self.client.post(self.endpoint_url, json=payload, headers=headers)
            if resp.status_code == 200:
                data = resp.json()
                if "answers" in data:
                    return data
                return {"answers": data}
            else:
                raise RuntimeError(f"Remote Laya API returned HTTP {resp.status_code}: {resp.text}")
        except Exception as e:
            logger.warning(f"Remote API prediction error at {self.endpoint_url}: {e}")
            raise

    def health_status(self) -> Dict[str, Any]:
        return {
            "backend": "api",
            "available": self.is_available(),
            "endpoint_url": self.endpoint_url,
            "model_id": self.model_id,
            "framework": "http_rest"
        }
