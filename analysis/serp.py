import json
import os
from typing import Dict, Any, List, Optional
from models.product import ProductPageData

class SERPAnalyzer:
    def __init__(self, serp_data_path: Optional[str] = None):
        self.serp_data_path = serp_data_path
        self.serp_cache: Dict[str, Any] = {}
        if serp_data_path and os.path.exists(serp_data_path):
            self._load_data(serp_data_path)

    def _load_data(self, path: str):
        try:
            with open(path, "r", encoding="utf-8") as f:
                self.serp_cache = json.load(f)
        except Exception:
            self.serp_cache = {}

    def analyze_product_serp_gaps(self, product_data: ProductPageData, target_query: str = "") -> Dict[str, Any]:
        """
        Analyzes SERP competitive format gaps and SERP feature opportunities.
        """
        query = target_query or f"{product_data.brand} {product_data.model} price".strip()
        
        # Check if actual external SERP data is available for query
        serp_entry = self.serp_cache.get(query)

        # Baseline competitive expectations for Indian automotive SERPs (Bikewale, BikeDekho, Zigwheels)
        competitor_features = {
            "faq_schema": True,
            "variant_comparison_table": True,
            "on_road_price_breakdown": True,
            "user_reviews": True,
            "expert_verdict": True,
            "color_galleries": True,
            "competitor_comparison": True
        }

        gaps = []
        serp_feature_opportunities = []

        # Compare target page
        has_faqs = "faqs" in product_data.present_content_sections
        has_reviews = product_data.has_reviews
        has_variants = bool(product_data.variants_list) or "variants" in product_data.present_content_sections
        has_comparison = product_data.has_comparison
        has_on_road = bool(product_data.on_road_price) or "on_road_price" in product_data.present_content_sections

        if not has_faqs:
            gaps.append("Competitor SERPs frequently earn FAQ Rich Snippets; target page lacks FAQ markup.")
            serp_feature_opportunities.append("FAQ Rich Results")

        if not has_on_road:
            gaps.append("Leading competitors provide city-wise on-road price breakdowns directly answering commercial search intent.")

        if not has_variants:
            gaps.append("Top ranking competitors feature dedicated variant selection matrices.")

        if not has_reviews:
            gaps.append("Competitors display Review and AggregateRating snippets in SERP results.")
            serp_feature_opportunities.append("Review Star Snippets (when legitimate reviews exist)")

        if not has_comparison:
            gaps.append("Competitor sites feature embedded comparison widgets for closely competing models.")

        return {
            "query": query,
            "has_external_serp_data": bool(serp_entry),
            "serp_feature_opportunities": serp_feature_opportunities,
            "competitor_gaps": gaps,
            "gap_summary": f"Identified {len(gaps)} competitive content and SERP feature opportunities."
        }
