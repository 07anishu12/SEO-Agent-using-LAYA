import time
import json
import logging
from typing import Dict, Any, List, Optional
from .questions import get_laya_seo_questions
from .metrics import LayaMetricsTracker
from .backends import get_laya_backend, LayaBackend

logger = logging.getLogger("seojev.laya")


class LayaSEOAnalyzer:
    """
    Cloud-portable Laya SEO Classifier.
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
        self.backend: LayaBackend = get_laya_backend(
            backend_type=self.backend_type,
            model_id=self.model_id,
            options=self.options
        )

    def is_available(self) -> bool:
        return self.backend.is_available()

    def get_health(self) -> Dict[str, Any]:
        return self.backend.health_status()

    def classify_issue(self, issue_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Classifies a single structured issue using the active Laya backend.
        Expected input: compact dictionary with page_type, issue, affected_count, evidence.
        """
        if not self.is_available():
            return {
                "category": issue_data.get("category", "technical"),
                "severity": issue_data.get("severity", "medium"),
                "action": "fix_template" if issue_data.get("template") else "fix_page",
                "confidence": 0.5,
                "latency_ms": 0.0,
                "raw_response": "{}"
            }

        start = time.monotonic()
        try:
            prompt_state = {
                "message": (
                    f"SEO finding: '{issue_data.get('issue')}' on page type '{issue_data.get('page_type')}'. "
                    f"Template: {issue_data.get('template')}. Affected pages: {issue_data.get('affected_urls_count', 1)}. "
                    f"Evidence: {issue_data.get('evidence', '')[:150]}"
                )
            }

            res = self.backend.predict(prompt_state, self.questions)
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

            return {
                "category": category,
                "severity": severity,
                "action": action,
                "confidence": confidence,
                "latency_ms": round(elapsed_ms, 2),
                "raw_response": json.dumps(res)
            }

        except Exception as e:
            elapsed_ms = (time.monotonic() - start) * 1000.0
            self.metrics.record_error()
            logger.warning(f"Laya inference error ({type(self.backend).__name__}): {e}")
            return {
                "category": issue_data.get("category", "technical"),
                "severity": issue_data.get("severity", "medium"),
                "action": "investigate",
                "confidence": 0.5,
                "latency_ms": round(elapsed_ms, 2),
                "raw_response": json.dumps({"error": str(e)})
            }
