from typing import Dict, Any, List

class ContentGapEngineV3:
    """Diagnoses structural content gaps against active vertical ontology and produces exact actionable specifications."""
    def __init__(self, vertical):
        self.vertical = vertical
        self.expected_sections = vertical.get_section_expectations()

    def analyze_gaps(self, product_page: Dict[str, Any], coverage_profile: Dict[str, Any]) -> List[Dict[str, Any]]:
        classes = coverage_profile.get("classes", {})
        gaps = []

        brand = product_page.get("brand") or "Vehicle"
        model = product_page.get("model") or "Model"

        # 1. Price Breakdown Gap
        if not classes.get("PRICE", {}).get("present"):
            gaps.append({
                "section_name": "On-Road Price Breakdown",
                "format": "table",
                "fields": ["Ex-Showroom Price", "RTO Registration Charges", "Insurance", "Total On-Road Estimate"],
                "questions_to_answer": [f"What is the on-road price of {brand} {model}?"],
                "entities_to_mention": [brand, model, "RTO", "Insurance"],
                "action_specification": f"Add an On-Road Price breakdown table for {brand} {model} displaying ex-showroom, RTO, and insurance costs.",
                "data_source_needed": "Automotive pricing database / OEM rate card"
            })

        # 2. Variants Matrix Gap
        if not classes.get("VARIANTS", {}).get("present"):
            gaps.append({
                "section_name": "Variant Comparison Matrix",
                "format": "table",
                "fields": ["Variant Name", "Ex-Showroom Price", "Key Feature Delta", "Brakes", "Wheels"],
                "questions_to_answer": [f"What are the differences between {brand} {model} variants?"],
                "entities_to_mention": [brand, model, "Standard", "Deluxe", "Disc", "Drum"],
                "action_specification": f"Add a Variant Comparison table below the price block; link each variant row to its dedicated detail view.",
                "data_source_needed": "Model trim specifications"
            })

        # 3. Specifications Table Gap
        if not classes.get("SPECIFICATIONS", {}).get("present"):
            gaps.append({
                "section_name": "Technical Specifications",
                "format": "table",
                "fields": ["Engine Displacement (cc)", "Max Power (bhp)", "Peak Torque (Nm)", "Mileage (kmpl)", "Fuel Tank (L)"],
                "questions_to_answer": [f"What is the engine capacity and power of {brand} {model}?"],
                "entities_to_mention": [brand, model, "Engine", "Power", "Torque"],
                "action_specification": f"Add a structured HTML technical specifications table with standardized automotive units (cc, bhp, Nm, kmpl).",
                "data_source_needed": "ARAI homologation / OEM brochure"
            })

        # 4. FAQ Accordion Gap
        if not classes.get("FAQ", {}).get("present"):
            gaps.append({
                "section_name": "Frequently Asked Questions",
                "format": "FAQ accordion + FAQPage JSON-LD",
                "fields": ["Question", "Direct Concise Answer (1-3 sentences)"],
                "questions_to_answer": [
                    f"What is the mileage of {brand} {model}?",
                    f"What is the minimum down payment for {brand} {model}?",
                    f"What are the available colors for {brand} {model}?"
                ],
                "entities_to_mention": [brand, model],
                "action_specification": f"Implement structured Q&A accordion answering top 3 customer queries with corresponding FAQPage JSON-LD schema.",
                "data_source_needed": "Consumer search query bank"
            })

        return gaps
