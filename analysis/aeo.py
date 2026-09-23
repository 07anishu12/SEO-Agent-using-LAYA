from typing import Dict, Any, List, Tuple
from models.product import ProductPageData

STANDARD_PRODUCT_QUESTIONS = [
    ("What is the price?", ["price", "on_road_price", "₹", "rs"]),
    ("What is the mileage?", ["mileage", "kmpl", "fuel economy"]),
    ("What are the variants?", ["variant", "variants", "drum", "disc"]),
    ("What is the engine capacity?", ["engine", "cc", "cylinder"]),
    ("What is the EMI / finance cost?", ["emi", "loan", "down payment"]),
    ("What are the key features?", ["features", "digital console", "abs"]),
    ("What are the alternative models?", ["vs", "compare", "alternative", "competitor"]),
    ("What is the difference between variants?", ["difference", "disc vs drum", "comparison"])
]

class AEOAnalyzer:
    def __init__(self):
        pass

    def evaluate_page(self, page_data: Dict[str, Any], product_data: Optional[ProductPageData] = None) -> Dict[str, Any]:
        """
        Evaluates Answer Engine Optimization (AEO) readiness for clear factual extraction.
        """
        url = page_data.get("url", "")
        body_sample = f"{page_data.get('title', '')} {page_data.get('h1_text', '')} {page_data.get('description', '')}".lower()
        if product_data:
            body_sample += f" {' '.join(product_data.present_content_sections)}"

        answered_questions = []
        missing_questions = []

        for q_text, keywords in STANDARD_PRODUCT_QUESTIONS:
            if any(k in body_sample for k in keywords):
                answered_questions.append(q_text)
            else:
                missing_questions.append(q_text)

        # Check structural signals
        has_faq_schema = "faqpage" in [s.lower() for s in page_data.get("schema_types", [])]
        has_faq_content = bool(product_data and product_data.faq_items) or "faqs" in (product_data.present_content_sections if product_data else [])
        has_table_specs = bool(product_data and (product_data.specs.engine_cc or product_data.specs.mileage))
        has_pricing = bool(product_data and product_data.price_str)

        # Readiness scoring (0-100)
        score = 20.0
        if has_faq_content or has_faq_schema: score += 25
        if has_table_specs: score += 25
        if has_pricing: score += 15
        if len(answered_questions) >= 5: score += 15
        score = min(round(score, 1), 100.0)

        readiness_level = "High" if score >= 75 else ("Moderate" if score >= 45 else "Low")

        # Specific actionable recommendations
        recommended_actions = []
        if not has_faq_content:
            recommended_actions.append("Add structured Q&A section answering top 5 customer questions (price, mileage, variants, EMI).")
        if not has_faq_schema and has_faq_content:
            recommended_actions.append("Add JSON-LD FAQPage structured data to markup existing Q&A content.")
        if not has_table_specs:
            recommended_actions.append("Present technical specifications in a structured HTML table with clean header rows.")
        if "What are the variants?" in missing_questions:
            recommended_actions.append("Include concise definition of variant differences and pricing tiers.")

        return {
            "url": url,
            "aeo_readiness_score": score,
            "aeo_readiness_level": readiness_level,
            "answered_questions_count": len(answered_questions),
            "missing_questions_count": len(missing_questions),
            "answered_questions": answered_questions,
            "missing_questions": missing_questions,
            "has_faq_content": has_faq_content,
            "has_faq_schema": has_faq_schema,
            "recommended_actions": recommended_actions,
            "evidence": f"AEO Readiness: {score}/100 ({readiness_level}). Covers {len(answered_questions)}/8 standard vehicle queries."
        }
