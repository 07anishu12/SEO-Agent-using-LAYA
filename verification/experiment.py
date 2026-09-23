import json
import sqlite3
import math
from typing import Dict, Any, List, Optional

class ExperimentEvaluator:
    """
    Evaluates SEO deployments using Difference-in-Differences (DiD) cohort analysis.
    Compares test URLs vs control URLs across pre/post time windows to isolate
    the net effect of an optimization from broader site-wide or seasonal fluctuations.
    Strictly reports observational changes without predicting future rankings.
    """
    def __init__(self, db_path: str = "data/seo.db"):
        self.db_path = db_path

    def evaluate_cohorts(
        self,
        experiment_id: str,
        annotation: str,
        template: str,
        deploy_date: str,
        test_urls: List[str],
        control_urls: List[str],
        pre_metrics: Dict[str, float],   # {"test": float, "control": float}
        post_metrics: Dict[str, float],  # {"test": float, "control": float}
        metric_name: str = "clicks",
        pre_window: str = "28d",
        post_window: str = "28d"
    ) -> Dict[str, Any]:
        """Calculates DiD lift between test and control cohorts and logs to experiments table."""
        t_pre = pre_metrics.get("test", 0.0)
        t_post = post_metrics.get("test", 0.0)
        c_pre = pre_metrics.get("control", 0.0)
        c_post = post_metrics.get("control", 0.0)

        test_delta = t_post - t_pre
        control_delta = c_post - c_pre

        # DiD = (Test_Post - Test_Pre) - (Control_Post - Control_Pre)
        did_estimate = test_delta - control_delta

        # Percentage lift relative to test pre baseline
        lift_pct = round((did_estimate / max(t_pre, 1.0)) * 100.0, 2)

        # Basic statistical confidence heuristic based on sample size and magnitude
        sample_size = len(test_urls) + len(control_urls)
        variance_proxy = abs(control_delta) * 0.5 + 1.0
        t_stat = abs(did_estimate) / math.sqrt(variance_proxy / max(sample_size, 1))
        conf_level = "High (>95%)" if t_stat >= 2.0 else ("Moderate (~80%)" if t_stat >= 1.3 else "Low (<80%)")

        result_summary = {
            "metric_name": metric_name,
            "test_pre_mean": round(t_pre, 2),
            "test_post_mean": round(t_post, 2),
            "test_delta": round(test_delta, 2),
            "control_pre_mean": round(c_pre, 2),
            "control_post_mean": round(c_post, 2),
            "control_delta": round(control_delta, 2),
            "did_net_lift": round(did_estimate, 2),
            "lift_pct": lift_pct,
            "confidence_estimate": conf_level,
            "claim_type": "OBSERVED",
            "observational_note": (
                "Observed difference in cohort trajectories following deployment. "
                "Calculated relative to the parallel control cohort; not an assurance of causal effect or ranking prediction."
            )
        }

        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
            INSERT OR REPLACE INTO experiments (
                experiment_id, annotation, template, deploy_date, pre_start,
                pre_end, post_start, post_end, test_urls_json, control_urls_json, result_summary_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                experiment_id, annotation, template, deploy_date,
                f"-{pre_window}", deploy_date, deploy_date, f"+{post_window}",
                json.dumps(test_urls), json.dumps(control_urls), json.dumps(result_summary)
            ))
            conn.commit()

        return {
            "experiment_id": experiment_id,
            "annotation": annotation,
            "template": template,
            "deploy_date": deploy_date,
            "test_urls_count": len(test_urls),
            "control_urls_count": len(control_urls),
            "result_summary": result_summary
        }
