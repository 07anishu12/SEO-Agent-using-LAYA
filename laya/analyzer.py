import time
import json
import logging
import hashlib
import threading
from typing import Dict, Any, List, Optional
from .questions import get_laya_seo_questions
from .metrics import LayaMetricsTracker
from .backends import get_laya_backend, LayaBackend

logger = logging.getLogger("seojev.laya")

# Process-level singleton analyzer and decision cache
_global_analyzer: Optional["LayaSEOAnalyzer"] = None
_global_analyzer_lock = threading.Lock()
_global_decision_cache: Dict[str, Dict[str, Any]] = {}
_global_cache_lock = threading.Lock()


class LayaSEOAnalyzer:
    """
    Cloud-portable Laya SEO Classifier with process-local singleton backend,
    lazy model initialization, and stable feature-hash decision caching.
    Routes inference to configured backend (MLX on Apple Silicon, llama.cpp on CPU/CUDA, or remote API).
    """

    def __init__(
        self,
        model_id: str = "aac6fef/laya-mlx",
        backend_type: Optional[str] = None,
        options: Optional[Dict[str, Any]] = None
    ):
        self.model_id = model_id
        self.backend_type = backend_type
        self.options = options or {}
        self.metrics = LayaMetricsTracker()
        self.questions = get_laya_seo_questions()
        self._backend: Optional[LayaBackend] = None
        self._backend_lock = threading.Lock()
        
        # Telemetry counters
        self.initialization_count = 0
        self.inference_calls = 0
        self.cache_hits = 0
        self.decisions_count = 0

    @classmethod
    def get_singleton(
        cls,
        model_id: str = "aac6fef/laya-mlx",
        backend_type: Optional[str] = None,
        options: Optional[Dict[str, Any]] = None
    ) -> "LayaSEOAnalyzer":
        """Returns the process-local singleton analyzer instance."""
        global _global_analyzer
        with _global_analyzer_lock:
            if _global_analyzer is None:
                _global_analyzer = cls(
                    model_id=model_id,
                    backend_type=backend_type,
                    options=options
                )
            return _global_analyzer

    def get_backend(self) -> LayaBackend:
        """Lazily initializes and returns the process-level backend singleton."""
        if self._backend is None:
            with self._backend_lock:
                if self._backend is None:
                    self.initialization_count += 1
                    logger.info(
                        f"Initializing Laya backend '{self.backend_type or 'default'}' "
                        f"(model_id={self.model_id}, init_count={self.initialization_count})..."
                    )
                    self._backend = get_laya_backend(
                        backend_type=self.backend_type,
                        model_id=self.model_id,
                        options=self.options
                    )
        return self._backend

    @property
    def backend(self) -> LayaBackend:
        """Exposes the active backend instance."""
        return self.get_backend()

    def is_available(self) -> bool:
        try:
            return self.get_backend().is_available()
        except Exception:
            return False

    def get_health(self) -> Dict[str, Any]:
        try:
            return self.get_backend().health_status()
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}

    def compute_feature_hash(self, issue_data: Dict[str, Any]) -> str:
        """
        Computes a stable, normalized SHA-256 feature hash representing
        the structural SEO problem regardless of superficial variation.
        """
        norm_issue = str(issue_data.get("issue") or issue_data.get("rule_id") or "").strip().lower()
        norm_template = str(issue_data.get("template") or issue_data.get("template_id") or "default").strip().lower()
        norm_evidence = str(issue_data.get("evidence") or "")[:150].strip().lower()
        model_ver = str(self.model_id).strip()

        raw_payload = f"{norm_issue}::{norm_template}::{norm_evidence}::{model_ver}"
        return hashlib.sha256(raw_payload.encode("utf-8")).hexdigest()

    def classify_issue(
        self,
        issue_data: Dict[str, Any],
        run_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Classifies a single structured issue/cluster using the active Laya backend.
        Reuses cached decisions if identical feature hash is encountered.
        Logs telemetry without dumping raw HTML.
        """
        feature_hash = self.compute_feature_hash(issue_data)
        cluster_id = issue_data.get("cluster_id") or issue_data.get("id") or issue_data.get("issue") or "generic"
        run_tag = run_id or "run_unknown"

        # Check in-memory decision cache
        with _global_cache_lock:
            if feature_hash in _global_decision_cache:
                self.cache_hits += 1
                self.decisions_count += 1
                cached = dict(_global_decision_cache[feature_hash])
                cached["from_cache"] = True
                cached["feature_hash"] = feature_hash
                logger.debug(
                    f"[LAYA] run_id={run_tag} cluster_id={cluster_id} "
                    f"cache_hit=True feature_hash={feature_hash[:12]}"
                )
                return cached

        # Check backend availability
        if not self.is_available():
            decision = {
                "category": issue_data.get("category", "technical"),
                "severity": issue_data.get("severity", "medium"),
                "action": "fix_template" if issue_data.get("template") else "fix_page",
                "confidence": 0.5,
                "latency_ms": 0.0,
                "raw_response": "{}",
                "feature_hash": feature_hash,
                "from_cache": False
            }
            with _global_cache_lock:
                _global_decision_cache[feature_hash] = decision
            self.decisions_count += 1
            return decision

        backend = self.get_backend()
        self.inference_calls += 1
        self.decisions_count += 1
        start = time.monotonic()

        try:
            prompt_state = {
                "message": (
                    f"SEO finding: '{issue_data.get('issue')}' on page type '{issue_data.get('page_type', 'generic')}'. "
                    f"Template: {issue_data.get('template', 'default')}. Affected pages: {issue_data.get('affected_urls_count', 1)}. "
                    f"Evidence: {str(issue_data.get('evidence', ''))[:150]}"
                )
            }

            res = backend.predict(prompt_state, self.questions)
            elapsed_ms = (time.monotonic() - start) * 1000.0
            self.metrics.record_decision(elapsed_ms)

            answers = res.get("answers", {})
            cat_ans = answers.get("category", {})
            sev_ans = answers.get("severity", {})
            act_ans = answers.get("action", {})

            category = cat_ans.get("choice", issue_data.get("category", "technical"))
            severity = sev_ans.get("choice", issue_data.get("severity", "medium"))
            action = act_ans.get("choice", "fix_template")
            confidence = round(float(cat_ans.get("confidence", 0.8)), 3)

            decision_id = f"dec_{feature_hash[:12]}"

            # Structured logging without raw HTML
            logger.info(
                f"[LAYA] run_id={run_tag} decision_id={decision_id} "
                f"feature_hash={feature_hash[:12]} cluster_id={cluster_id} "
                f"latency_ms={elapsed_ms:.1f} category={category} "
                f"severity={severity} action={action} confidence={confidence:.3f}"
            )

            decision = {
                "decision_id": decision_id,
                "category": category,
                "severity": severity,
                "action": action,
                "confidence": confidence,
                "latency_ms": round(elapsed_ms, 2),
                "raw_response": json.dumps(res),
                "feature_hash": feature_hash,
                "from_cache": False
            }

            with _global_cache_lock:
                _global_decision_cache[feature_hash] = decision

            return decision

        except Exception as e:
            elapsed_ms = (time.monotonic() - start) * 1000.0
            self.metrics.record_error()
            logger.warning(f"Laya inference error ({type(backend).__name__}): {e}")
            decision = {
                "decision_id": f"dec_{feature_hash[:12]}",
                "category": issue_data.get("category", "technical"),
                "severity": issue_data.get("severity", "medium"),
                "action": "investigate",
                "confidence": 0.5,
                "latency_ms": round(elapsed_ms, 2),
                "raw_response": json.dumps({"error": str(e)}),
                "feature_hash": feature_hash,
                "from_cache": False
            }
            with _global_cache_lock:
                _global_decision_cache[feature_hash] = decision
            return decision

    def reset_metrics_for_test(self):
        """Helper for test assertions."""
        self.initialization_count = 0
        self.inference_calls = 0
        self.cache_hits = 0
        self.decisions_count = 0
        with _global_cache_lock:
            _global_decision_cache.clear()
