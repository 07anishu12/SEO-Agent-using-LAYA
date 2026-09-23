from typing import Dict, Any, List

class GEOAnalyzerV3:
    """Evaluates Structural Generative Search Optimization (GEO) readiness across entity clarity and first-party structured signals."""
    def __init__(self):
        pass

    def evaluate_geo(self, page_data: Dict[str, Any], html: str = "") -> Dict[str, Any]:
        factors = []
        gaps = []
        score = 0.0

        title = page_data.get("title", "")
        h1 = page_data.get("h1_text", "")
        schema = page_data.get("schema_types", "")

        # 1. Entity Clarity
        brand = page_data.get("brand")
        model = page_data.get("model")
        if brand and model and brand.lower() in title.lower() and model.lower() in title.lower():
            factors.append("Explicit Brand + Model entity clarity in Title tag")
            score += 25.0
        else:
            gaps.append("Inconsistent entity naming between Brand/Model and Title tag")

        # 2. Structured First-Party Product Schema
        if "Product" in schema or "Vehicle" in schema:
            factors.append("Structured Product / Vehicle JSON-LD entity markup present")
            score += 25.0
        else:
            gaps.append("Missing Schema.org Product / Vehicle structured entity markup")

        # 3. Structured Data Tables
        if "<table" in (html or "").lower():
            factors.append("Machine-readable specifications table present in DOM")
            score += 25.0
        else:
            gaps.append("Missing structured HTML data tables for key specifications")

        # 4. Source Identity & Organization
        if "Organization" in schema or "ContactPoint" in schema:
            factors.append("Source identity verified via Organization schema")
            score += 25.0
        else:
            gaps.append("Missing publisher Organization schema with sameAs social profiles")

        score = min(100.0, score)
        level = "High" if score >= 75.0 else ("Medium" if score >= 50.0 else "Low")

        return {
            "label": "STRUCTURAL GEO ANALYSIS",
            "geo_readiness_score": score,
            "readiness_level": level,
            "positive_factors": factors,
            "gaps": gaps,
            "recommended_action": f"Resolve structural GEO gap: {gaps[0]}" if gaps else "Maintain high structured entity clarity."
        }
