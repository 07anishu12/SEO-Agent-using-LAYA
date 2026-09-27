"""
Laya Inference Backends Package.
Provides unified factory for MLX (Apple Silicon), llama.cpp (CPU/CUDA), and Remote API.
"""
import os
import sys
import logging
from typing import Optional, Dict, Any

from .base import LayaBackend
from .mlx import MLXBackend
from .llama_cpp import LlamaCppBackend
from .api import APIBackend

logger = logging.getLogger("seojev.laya.backends")

_cached_backend: Optional[LayaBackend] = None
_cached_backend_type: Optional[str] = None


def resolve_default_backend_type() -> str:
    """Detects available backend based on environment."""
    env_backend = os.environ.get("LAYA_BACKEND", "").lower().strip()
    if env_backend in ("mlx", "llama_cpp", "api"):
        return env_backend

    if sys.platform == "darwin":
        try:
            import laya_mlx
            return "mlx"
        except ImportError:
            pass

    return "llama_cpp"


def get_laya_backend(
    backend_type: Optional[str] = None,
    model_id: Optional[str] = None,
    options: Optional[Dict[str, Any]] = None,
    force_new: bool = False
) -> LayaBackend:
    """
    Factory creating or returning the configured Laya inference backend.
    """
    global _cached_backend, _cached_backend_type

    target_type = (backend_type or os.environ.get("LAYA_BACKEND") or resolve_default_backend_type()).lower().strip()

    if not force_new and _cached_backend is not None and _cached_backend_type == target_type:
        return _cached_backend

    logger.info(f"Instantiating Laya backend '{target_type}'...")
    if target_type == "mlx":
        backend = MLXBackend()
        backend.initialize(model_id=model_id or "aac6fef/laya-mlx", options=options)
    elif target_type in ("llama_cpp", "llamacpp"):
        backend = LlamaCppBackend()
        backend.initialize(model_id=model_id or "laya-v1-q4.gguf", options=options)
    elif target_type == "api":
        backend = APIBackend()
        backend.initialize(model_id=model_id or "laya-remote", options=options)
    else:
        raise ValueError(f"Unsupported LAYA_BACKEND '{target_type}'. Expected 'mlx', 'llama_cpp', or 'api'.")

    _cached_backend = backend
    _cached_backend_type = target_type
    return backend


__all__ = ["LayaBackend", "MLXBackend", "LlamaCppBackend", "APIBackend", "get_laya_backend"]
