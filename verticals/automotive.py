import re
from typing import Dict, Any, List
from .base import VerticalInterface

class AutomotiveVertical(VerticalInterface):
    """Domain intelligence for automotive, two-wheelers, and commercial vehicles."""
    name: str = "automotive"

    KNOWN_BRANDS = [
        "hero", "honda", "bajaj", "tvs", "royal enfield", "yamaha", "suzuki",
        "ktm", "ather", "ola", "revolt", "tork", "matter", "ultraviolette",
        "kawasaki", "bmw", "triumph", "harley-davidson", "ducati", "aprilia",
        "vespa", "jawa", "yezdi", "husqvarna", "benelli"
    ]

    def detect(self, profile: Any) -> float:
        domain = getattr(profile, "domain", "").lower()
        if any(b in domain for b in ("bike", "drivio", "moto", "auto", "car", "wheel", "scooter")):
            return 0.95
        # Check URL paths
        page_types = getattr(profile, "page_types", {})
        if "model" in page_types or any(b in str(page_types) for b in self.KNOWN_BRANDS):
            return 0.90
        return 0.0

    def get_attribute_ontology(self) -> Dict[str, Dict[str, Any]]:
        return {
            "brand": {"synonyms": ["manufacturer", "make"], "unit": None},
            "model": {"synonyms": ["bike name", "vehicle"], "unit": None},
            "variant": {"synonyms": ["trim", "edition", "version"], "unit": None},
            "ex_showroom_price": {"synonyms": ["ex showroom", "starting price", "base price"], "unit": "₹"},
            "on_road_price": {"synonyms": ["on road", "rto price", "delhi price"], "unit": "₹"},
            "emi": {"synonyms": ["monthly installment", "loan emi", "financing starting"], "unit": "₹/mo"},
            "mileage": {"synonyms": ["fuel economy", "arai mileage", "average"], "unit": "kmpl"},
            "engine_cc": {"synonyms": ["displacement", "engine capacity", "cubic capacity"], "unit": "cc"},
            "power_bhp": {"synonyms": ["max power", "bhp", "horsepower", "ps"], "unit": "bhp"},
            "torque_nm": {"synonyms": ["max torque", "peak torque"], "unit": "Nm"},
            "top_speed": {"synonyms": ["maximum speed", "speed"], "unit": "km/h"},
            "curb_weight_kg": {"synonyms": ["weight", "kerb weight"], "unit": "kg"},
            "seat_height_mm": {"synonyms": ["saddle height"], "unit": "mm"},
            "ground_clearance_mm": {"synonyms": ["clearance"], "unit": "mm"},
            "tank_capacity_l": {"synonyms": ["fuel tank", "tank capacity"], "unit": "litres"},
            "colors": {"synonyms": ["colour options", "paint schemes"], "unit": None},
            "ev_range_km": {"synonyms": ["battery range", "riding range"], "unit": "km/charge"},
            "battery_kwh": {"synonyms": ["battery capacity", "pack size"], "unit": "kWh"},
            "charging_time_hrs": {"synonyms": ["charge time", "fast charging"], "unit": "hours"}
        }

    def get_question_bank(self) -> List[str]:
        return [
            "What is the on-road price of {model} in {city}?",
            "What is the real-world mileage of {model}?",
            "What are the available variants and prices of {model}?",
            "What is the engine capacity and power output of {model}?",
            "What is the monthly EMI and down payment for {model}?",
            "What are the top competitors and alternatives for {model}?",
            "What colors are available for {model}?",
            "Is {model} suitable for daily commuting?"
        ]

    def get_intent_lexicon(self) -> Dict[str, List[str]]:
        return {
            "pricing": ["price", "on road", "cost", "quotation", "rate", "ex showroom"],
            "finance": ["emi", "loan", "down payment", "interest rate", "tenure", "financing"],
            "mileage": ["mileage", "kmpl", "fuel economy", "average", "efficiency"],
            "specification": ["specs", "engine", "cc", "bhp", "power", "torque", "dimensions", "weight"],
            "comparison": ["vs", "compare", "comparison", "better", "alternative", "against"],
            "variant": ["variant", "variants", "base model", "top model", "split seat", "disc"]
        }

    def get_section_expectations(self) -> List[str]:
        return [
            "price", "on_road_price", "variants", "specifications", "mileage",
            "engine", "power", "torque", "features", "colors", "pros", "cons",
            "comparison", "emi", "faqs", "images", "reviews"
        ]

    def get_schema_expectations(self) -> List[str]:
        return ["Product", "Vehicle", "Offer", "Brand", "FAQPage", "BreadcrumbList"]
