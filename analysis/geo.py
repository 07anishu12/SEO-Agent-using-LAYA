from typing import Dict, Any, List, Optional
from models.product import ProductPageData

class GEOAnalyzer:
    def __init__(self):
        pass

    def evaluate_page(self, page_data: Dict[str, Any], product_data: Optional[ProductPageData] = None) -> Dict[str, Any]:
        """
        Structural GEO (Generative Search Optimization) evaluation.
        Assesses factual density, entity clarity, and citation readiness for generative search engines.
        """
        url = page_data.get("url", "")
        title = page_data.get("title", "")
        h1 = page_data.get("h1_text", "")
        schemas = [s.lower() for s in page_data.get("schema_types", [])]

        strengths = []
        gaps = []
        recommended_actions = []

        # 1. Clear Entity Identity
        has_entity = bool(product_data and product_data.brand and product_data.model)
        if has_entity:
            strengths.append(f"Clear primary entity identified: {product_data.brand} {product_data.model}.")
        else:
            gaps.append("Unclear or generic primary entity identification.")
            recommended_actions.append("Ensure explicit Brand + Model naming throughout H1, Title, and main copy.")

        # 2. Entity Consistency
        if product_data and product_data.entity_consistency_ok:
            strengths.append("Consistent entity references across Title, H1, and URL.")
        elif product_data and not product_data.entity_consistency_ok:
            gaps.extend(product_data.entity_contradictions)
            recommended_actions.append("Resolve entity naming discrepancies between page Title, H1, and structured data.")

        # 3. Structured Data
        has_product_schema = any(s in schemas for s in ("product", "vehicle", "car", "motorcycle"))
        if has_product_schema:
            strengths.append("Entity-specific structured data (Product/Vehicle) present.")
        else:
            gaps.append("Missing Product or Vehicle Schema.org structured data.")
            recommended_actions.append("Implement Schema.org Product markup with Offer, Brand, and Model properties.")

        # 4. Structured Facts & Numerical Density
        has_specs = bool(product_data and (product_data.specs.mileage or product_data.specs.engine_cc))
        if has_specs:
            strengths.append("Dense numerical specification facts present with standardized units.")
        else:
            gaps.append("Low density of extractable numerical specifications.")
            recommended_actions.append("Add structured specification highlights with standardized units (kmpl, cc, bhp, Nm).")

        # 5. First-Party Utility Content (Pricing & EMI)
        has_first_party_utility = bool(product_data and (product_data.price_str or product_data.emi_str))
        if has_first_party_utility:
            strengths.append("First-party commercial utility signals present (pricing and loan/EMI calculator data).")
        else:
            gaps.append("Missing distinct commercial utility figures (ex-showroom/on-road breakdown).")
            recommended_actions.append("Provide clear localized on-road pricing estimates and financing calculators.")

        # 6. Comparison Signals
        has_comparison = bool(product_data and product_data.has_comparison)
        if has_comparison:
            strengths.append("Topical comparison and alternative context present.")
        else:
            gaps.append("Lacks comparative context against competing market alternatives.")
            recommended_actions.append("Add a 'Direct Competitors & Alternatives' comparison section.")

        score = 25.0
        if has_entity: score += 15
        if product_data and product_data.entity_consistency_ok: score += 15
        if has_product_schema: score += 15
        if has_specs: score += 15
        if has_first_party_utility: score += 10
        if has_comparison: score += 5
        score = min(round(score, 1), 100.0)

        readiness_level = "High" if score >= 75 else ("Moderate" if score >= 50 else "Low")

        return {
            "url": url,
            "geo_readiness_score": score,
            "geo_readiness_level": readiness_level,
            "strengths": strengths,
            "gaps": gaps,
            "recommended_actions": recommended_actions,
            "evidence": f"Structural GEO Score: {score}/100 ({readiness_level}). Analysis based on entity clarity, numerical facts, and schema completeness."
        }
