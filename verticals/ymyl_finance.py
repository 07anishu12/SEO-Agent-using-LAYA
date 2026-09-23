from typing import Dict, Any, List
from .base import VerticalInterface

class YMYLFinanceOverlay(VerticalInterface):
    """Overlay vertical for consumer loan, EMI financing, and financial compliance analysis."""
    name: str = "ymyl_finance"

    def detect(self, profile: Any) -> float:
        domain = getattr(profile, "domain", "").lower()
        if "loan" in domain or "finance" in domain or "credit" in domain:
            return 0.90
        page_types = getattr(profile, "page_types", {})
        if "finance" in page_types or any("loan" in str(k) for k in page_types):
            return 0.85
        return 0.40 # Enabled as overlay when financing terms appear

    def get_attribute_ontology(self) -> Dict[str, Dict[str, Any]]:
        return {
            "interest_rate": {"synonyms": ["roi", "interest percentage", "rate of interest"], "unit": "%"},
            "loan_tenure": {"synonyms": ["tenure", "duration", "repayment period"], "unit": "months"},
            "down_payment": {"synonyms": ["initial payment", "margin money"], "unit": "₹"},
            "processing_fee": {"synonyms": ["fee", "documentation charges"], "unit": "₹"},
            "nbfc_partner": {"synonyms": ["lender", "bank partner", "financier"], "unit": None}
        }

    def get_question_bank(self) -> List[str]:
        return [
            "What is the interest rate for {product} loan?",
            "What documents are required for two-wheeler finance?",
            "Can I get 100% financing for {product}?",
            "What is the maximum tenure for {product} EMI?"
        ]

    def get_intent_lexicon(self) -> Dict[str, List[str]]:
        return {
            "finance": ["apply loan", "calculate emi", "low interest", "instant approval", "cibil score", "zero down payment"]
        }

    def get_section_expectations(self) -> List[str]:
        return ["emi_calculator", "interest_rates", "eligibility_criteria", "disclaimer", "lender_disclosure"]

    def get_schema_expectations(self) -> List[str]:
        return ["FinancialProduct", "LoanOrCredit"]
