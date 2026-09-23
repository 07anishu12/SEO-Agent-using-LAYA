import time
import json
import logging
from typing import Dict, Any, List, Optional
from .questions import get_laya_seo_questions
from .metrics import LayaMetricsTracker

logger = logging.getLogger("seojev.laya")

class LayaSEOAnalyzer:
    _instance = None
    _agent = None

    def __init__(self, model_id: str = "aac6fef/laya-mlx"):
        self.model_id = model_id
        self.metrics = LayaMetricsTracker()
        self.questions = get_laya_seo_questions()
        self._ensure_loaded()

    def _ensure_loaded(self):
        if LayaSEOAnalyzer._agent is None:
            try:
                import laya_mlx
                logger.info(f"Loading local Laya MLX model '{self.model_id}'...")
                LayaSEOAnalyzer._agent = laya_mlx.load(self.model_id)
                logger.info("Laya MLX model loaded successfully.")
            except Exception as e:
                logger.error(f"Failed to load Laya MLX model: {e}")
                LayaSEOAnalyzer._agent = None

    def is_available(self) -> bool:
        return LayaSEOAnalyzer._agent is not None

    def classify_issue(self, issue_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Classifies a single structured issue using local Laya MLX.
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

            res = LayaSEOAnalyzer._agent.predict(prompt_state, self.questions)
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
            logger.warning(f"Laya MLX inference error: {e}")
            return {
                "category": issue_data.get("category", "technical"),
                "severity": issue_data.get("severity", "medium"),
                "action": "investigate",
                "confidence": 0.5,
                "latency_ms": round(elapsed_ms, 2),
                "raw_response": json.dumps({"error": str(e)})
            }
