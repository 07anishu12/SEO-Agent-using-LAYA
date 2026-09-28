"""
Apple Silicon MLX Backend for local inference using laya_mlx.
"""
import logging
import gc
import os
import multiprocessing
import tempfile
import fcntl
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
        self._mx = None
        self._owner_lock = None

    def initialize(self, model_id: str = "aac6fef/laya-mlx", options: Optional[Dict[str, Any]] = None) -> bool:
        self.model_id = model_id
        self._options = options or {}
        try:
            if platform.system() != "Darwin" or platform.machine() != "arm64":
                raise RuntimeError("MLX requires native Apple Silicon macOS, outside Docker")
            if multiprocessing.current_process().name != 'MainProcess' or os.getenv('SEOJEV_CPU_WORKER') == '1':
                raise RuntimeError('CPU pool workers must never import MLX')
            # OS lock covers separate CLI/API processes; retained for model lifetime.
            lock_path = os.getenv('SEOJEV_MLX_LOCK_PATH', os.path.join(tempfile.gettempdir(), 'seojev-laya-mlx.lock'))
            self._owner_lock = open(lock_path, 'a')
            fcntl.flock(self._owner_lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            from engine.memory_guard import MemoryGuard
            self.guard = self._options.get('memory_guard') or MemoryGuard()
            self.guard.checkpoint(reserve_mb=1024)
            import mlx.core as mx
            self._mx = mx
            # Reclaim unused allocator buffers; weights, dtype, heads and model batch settings stay unchanged.
            mx.set_cache_limit(0)
            import laya_mlx
            logger.info(f"Initializing MLX backend with model '{model_id}'...")
            self._agent = laya_mlx.load(model_id)
            mx.clear_cache()  # Converted checkpoint-loading temporaries are no longer live.
            self.guard.checkpoint()
            self.checkpoint_id = f"{model_id}@{self._agent.model_dir.name}"
            logger.info("Laya calibration temperatures raw=%s applied=%s; SEO questions use at most 8 options", self._agent.temperature_by_options_raw, self._agent.temperature_by_options)
            logger.info("MLX backend initialized successfully.")
            return True
        except Exception as e:
            self.close()
            from engine.memory_guard import MemoryBudgetExceeded
            if isinstance(e, MemoryBudgetExceeded):
                raise
            raise RuntimeError("Laya MLX startup failed. Run .venv/bin/python3 on the Apple Silicon host; install pinned requirements and ensure aac6fef/laya-mlx is accessible. " + str(e)) from e

    def is_available(self) -> bool:
        return self._agent is not None

    def predict(self, prompt_state: Dict[str, Any], questions: Dict[str, Any]) -> Dict[str, Any]:
        if not self.is_available():
            raise RuntimeError("MLX backend is not available for inference.")
        with self._predict_lock:
            self.guard.checkpoint(reserve_mb=256)
            try:
                result = self._agent.predict(prompt_state, questions)
            finally:
                # Upstream predict evaluates tensors and returns only Python/NumPy-derived scalars.
                self._mx.clear_cache()
            self.guard.checkpoint()
            return result

    def close(self):
        """Release an owned model and allocator cache before relinquishing the OS lock."""
        self._agent = None
        gc.collect()
        try:
            if self._mx is not None:
                self._mx.clear_cache()
        finally:
            if self._owner_lock is not None:
                self._owner_lock.close()
                self._owner_lock = None

    def health_status(self) -> Dict[str, Any]:
        return {
            "backend": "mlx",
            "available": self.is_available(),
            "model_id": self.model_id,
            "checkpoint_id": self.checkpoint_id,
            "device": "apple_silicon",
            "framework": "mlx"
        }
