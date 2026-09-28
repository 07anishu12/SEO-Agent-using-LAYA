"""The decision engine supports only the specified local MLX checkpoint."""
import os
import threading
from .base import LayaBackend
from .mlx import MLXBackend

MODEL_ID = "aac6fef/laya-mlx"
_cached_backend = None
_lock = threading.Lock()


def resolve_default_backend_type():
    backend = os.environ.get("LAYA_BACKEND", "mlx").strip().lower()
    if backend != "mlx":
        raise ValueError(f"LAYA_BACKEND={backend!r} is forbidden: Pass 4 requires local aac6fef/laya-mlx")
    return backend


def get_laya_backend(backend_type=None, model_id=None, options=None, force_new=False):
    global _cached_backend
    configured = resolve_default_backend_type()
    if (backend_type or configured) != "mlx" or (model_id or MODEL_ID) != MODEL_ID:
        raise ValueError("Pass 4 requires backend='mlx', model_id='aac6fef/laya-mlx'; no alternatives are supported")
    with _lock:
        if force_new or _cached_backend is None:
            backend = MLXBackend()
            backend.initialize(MODEL_ID, options)
            _cached_backend = backend
        return _cached_backend


__all__ = ["LayaBackend", "MLXBackend", "get_laya_backend"]
