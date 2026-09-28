"""Strict local Laya inference and process-local reuse of validated answers."""
import hashlib
import json
import logging
import threading
import time
from .backends import MODEL_ID, get_laya_backend
from .decision import LAYA_PROMPT_VERSION
from .heads import LayaHeadMissingError, validate_heads
from .metrics import LayaMetricsTracker
from .questions import get_laya_seo_questions

logger = logging.getLogger("seojev.laya")
_global_analyzer = None
_global_analyzer_lock = threading.Lock()


class LayaSEOAnalyzer:
    def __init__(self, model_id=MODEL_ID, backend_type=None, options=None):
        self.model_id = model_id
        self.backend_type = backend_type
        self.options = options or {}
        self.questions = get_laya_seo_questions()
        self.metrics = LayaMetricsTracker()
        self._backend = None
        self._backend_lock = threading.Lock()
        self._cache = {}
        self._cache_lock = threading.Lock()
        self._preflight = None
        self.reset_metrics_for_test()

    @classmethod
    def get_singleton(cls, model_id=MODEL_ID, backend_type=None, options=None):
        global _global_analyzer
        if model_id != MODEL_ID or backend_type not in (None, "mlx"):
            raise ValueError("Laya decisions require aac6fef/laya-mlx on the native MLX backend")
        with _global_analyzer_lock:
            if _global_analyzer is None:
                _global_analyzer = cls(model_id, backend_type, options)
            return _global_analyzer

    def get_backend(self):
        if self._backend is None:
            with self._backend_lock:
                if self._backend is None:
                    self.initialization_count += 1
                    self._backend = get_laya_backend(self.backend_type, self.model_id, self.options)
        return self._backend

    @property
    def backend(self):
        return self.get_backend()

    def is_available(self):
        return self.get_backend().is_available()

    def get_health(self):
        return self.get_backend().health_status()

    def preflight(self):
        """Load the exact checkpoint and verify all ten outputs using real inference."""
        if self._preflight is not None:
            return self._preflight
        backend = self.get_backend()
        response = backend.predict({"message": "Crawl evidence: HTTP 200 page, missing title tag, indexable, self canonical.", "prompt_version": LAYA_PROMPT_VERSION}, self.questions)
        heads = validate_heads(response)
        self._preflight = {"checkpoint_id": backend.checkpoint_id, "heads": list(heads), "canary_predictions": 1}
        logger.info("Laya preflight passed: %s", self._preflight)
        return self._preflight

    def compute_feature_hash(self, issue_data):
        payload = {"evidence": {k: v for k, v in issue_data.items() if k != "run_id"}, "checkpoint_id": self.get_backend().checkpoint_id, "prompt_version": LAYA_PROMPT_VERSION}
        return hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode()).hexdigest()

    def classify_issue(self, issue_data, run_id=None):
        feature_hash = self.compute_feature_hash(issue_data)
        with self._cache_lock:
            if feature_hash in self._cache:
                self.cache_hits += 1
                self.decisions_count += 1
                return {**self._cache[feature_hash], "from_cache": True}
        self.cache_misses += 1
        start = time.monotonic()
        self.inference_calls += 1
        try:
            response = self.get_backend().predict({"message": json.dumps(issue_data, sort_keys=True, default=str), "prompt_version": LAYA_PROMPT_VERSION}, self.questions)
            heads = validate_heads(response)
            elapsed = (time.monotonic() - start) * 1000
            # Selected probabilities, not entropy confidence. See LAYA_CONFIDENCE.md.
            confidence = min(heads[n]["chosen_probability"] for n in ("verdict", "action"))
            decision = {"decision_id": f"dec_{feature_hash}", "feature_hash": feature_hash, "checkpoint_id": self.get_backend().checkpoint_id, "confidence": confidence, "head_confidences": heads, "is_real_issue": heads["verdict"]["choice"] == "real_issue", "latency_ms": elapsed, "raw_response": json.dumps(response), "from_cache": False}
            for name in ("verdict", "category", "severity", "action", "scope", "root_cause"):
                decision[name] = heads[name]["choice"]
            for name in ("canonical_indexability", "content_assessment", "cannibalization", "internal_linking"):
                decision[name] = heads[name]
            self.metrics.record_decision(elapsed)
            self.decisions_count += 1
            with self._cache_lock:
                self._cache[feature_hash] = decision
            logger.info("Laya decision run=%s candidate=%s verdict=%s action=%s confidence=%.4f", run_id, issue_data.get("cluster_id"), decision["verdict"], decision["action"], confidence)
            return decision
        except Exception:
            self.metrics.record_error()
            logger.exception("Laya inference failed for candidate %s", issue_data.get("cluster_id"))
            raise

    def reset_metrics_for_test(self):
        self.initialization_count = self.inference_calls = self.cache_hits = self.cache_misses = self.decisions_count = 0
        with self._cache_lock:
            self._cache.clear()
