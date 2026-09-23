from typing import Dict, Any, List, Tuple

class PriorityModel:
    """Calculates transparent Opportunity tier, Confidence tier, Effort, and weight sensitivity analysis."""
    def __init__(self):
        # Weights from Section 21:
        # Opportunity = 0.28·Visibility + 0.18·Gap + 0.14·PageImportance + 0.14·TemplateScope + 0.10·TechnicalSeverity + 0.10·CTRHeadroom + 0.06·LinkGap
        self.weights = {
            "visibility": 0.28,
            "gap": 0.18,
            "page_importance": 0.14,
            "template_scope": 0.14,
            "technical_severity": 0.10,
            "ctr_headroom": 0.10,
            "link_gap": 0.06
        }

    def calculate_opportunity_score(self, factors: Dict[str, float]) -> Tuple[float, str]:
        """Calculates normalized score (0.0 to 100.0) and assigns Opportunity Tier (High/Medium/Low)."""
        score = 0.0
        for k, w in self.weights.items():
            val = factors.get(k, 50.0) # Default to 50/100 if unspecified
            score += w * val

        score = round(score, 1)
        if score >= 70.0:
            tier = "High"
        elif score >= 40.0:
            tier = "Medium"
        else:
            tier = "Low"

        return score, tier

    def calculate_confidence_tier(self, evidence_grade: str, sample_size: int, detector_precision: float) -> str:
        """Assigns Confidence Tier (High/Medium/Low) based on evidence grade and detector metrics."""
        # Evidence grades: E4 (directly measured + corroborated), E3 (directly measured), E2 (inferred), E1 (heuristic), E0 (hypothesis)
        if evidence_grade in ("E4", "E3") and detector_precision >= 0.90:
            return "High"
        elif evidence_grade in ("E3", "E2") and detector_precision >= 0.75:
            return "Medium"
        return "Low"

    def calculate_effort(self, change_type: str, affected_pages: int) -> str:
        """Assigns Effort (S/M/L) based on change type and scope."""
        if change_type in ("config", "robots_txt") or affected_pages == 1:
            return "S"
        elif change_type in ("metadata_template", "schema_component") and affected_pages <= 500:
            return "M"
        return "L"

    def sensitivity_check(self, items: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Perturbs formula weights by +/-20% and evaluates stability of the Top-25 ranked items."""
        if not items:
            return {"top_25_stability_pct": 100.0, "unstable_items": []}

        # Baseline Top 25
        baseline_sorted = sorted(items, key=lambda x: x.get("priority_score", 0.0), reverse=True)[:25]
        baseline_fps = {x.get("fingerprint") for x in baseline_sorted}

        # Perturbed weights (+20% on visibility, -20% on gap)
        perturbed_scores = []
        for x in items:
            f = x.get("priority_factors", {})
            p_score = (
                0.336 * f.get("visibility", 50.0) +
                0.144 * f.get("gap", 50.0) +
                0.140 * f.get("page_importance", 50.0) +
                0.140 * f.get("template_scope", 50.0) +
                0.100 * f.get("technical_severity", 50.0) +
                0.080 * f.get("ctr_headroom", 50.0) +
                0.060 * f.get("link_gap", 50.0)
            )
            perturbed_scores.append((x.get("fingerprint"), p_score))

        perturbed_sorted = sorted(perturbed_scores, key=lambda x: x[1], reverse=True)[:25]
        perturbed_fps = {x[0] for x in perturbed_sorted}

        overlap = len(baseline_fps & perturbed_fps)
        stability_pct = round((overlap / max(len(baseline_fps), 1)) * 100, 1)

        unstable = list(baseline_fps - perturbed_fps)

        return {
            "top_25_stability_pct": stability_pct,
            "unstable_items_count": len(unstable),
            "unstable_fingerprints": unstable
        }
