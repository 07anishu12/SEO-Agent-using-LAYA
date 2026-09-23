import re
import urllib.parse
from typing import Dict, Any, List, Tuple
from collections import Counter

class ProgrammaticFamilyAnalyzer:
    """Detects programmatic parameter matrices (brand x model x city, comparison, EMI) and computes uniqueness and verdicts."""
    def __init__(self):
        pass

    def detect_families(self, pages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Identifies URL patterns that represent programmatic matrices."""
        city_keywords = {"delhi", "mumbai", "bangalore", "bengaluru", "hyderabad", "chennai", "pune", "kolkata", "ahmedabad", "jaipur"}
        
        city_matrix_pages: List[Dict[str, Any]] = []
        comparison_matrix_pages: List[Dict[str, Any]] = []
        loan_matrix_pages: List[Dict[str, Any]] = []

        for p in pages:
            url = p.get("url", "").lower()
            if any(c in url for c in city_keywords):
                city_matrix_pages.append(p)
            elif " vs " in url or "-vs-" in url or "/compare/" in url:
                comparison_matrix_pages.append(p)
            elif any(k in url for k in ("/loan", "/emi", "/finance")):
                loan_matrix_pages.append(p)

        families = []
        # 1. City Matrix Family
        if len(city_matrix_pages) >= 5:
            families.append(self._analyze_matrix_family(
                name="Location / City Matrix Pages",
                pattern="/{category}/{model}/{city}",
                pages=city_matrix_pages,
                default_verdict="enrich"
            ))

        # 2. Comparison Matrix Family
        if len(comparison_matrix_pages) >= 5:
            families.append(self._analyze_matrix_family(
                name="Model Comparison Matrix Pages",
                pattern="/compare/{model-a}-vs-{model-b}",
                pages=comparison_matrix_pages,
                default_verdict="keep"
            ))

        # 3. Loan / Financing Matrix Family
        if len(loan_matrix_pages) >= 5:
            families.append(self._analyze_matrix_family(
                name="Financing / Loan Calculator Matrix",
                pattern="/{brand}/{model}/loan",
                pages=loan_matrix_pages,
                default_verdict="enrich"
            ))

        return families

    def _analyze_matrix_family(self, name: str, pattern: str, pages: List[Dict[str, Any]], default_verdict: str) -> Dict[str, Any]:
        count = len(pages)
        sample_urls = [p["url"] for p in pages[:5]]
        
        # Calculate content length / uniqueness variance
        word_counts = [p.get("word_count", 0) for p in pages if p.get("word_count")]
        avg_words = round(sum(word_counts) / max(len(word_counts), 1), 0) if word_counts else 0

        # Uniqueness estimation: if word counts are identical across 80% of pages, high boilerplate token-swap risk
        count_distribution = Counter(word_counts)
        most_common_freq = count_distribution.most_common(1)[0][1] if count_distribution else 0
        token_swap_ratio = round(most_common_freq / max(count, 1), 2)

        verdict = default_verdict
        if token_swap_ratio > 0.75 and avg_words < 400:
            verdict = "consolidate" # thin token-swap
        elif token_swap_ratio > 0.50:
            verdict = "enrich"

        return {
            "family_name": name,
            "url_pattern": pattern,
            "cells_present": count,
            "average_word_count": avg_words,
            "token_swap_similarity_ratio": token_swap_ratio,
            "verdict": verdict,
            "sample_urls": sample_urls,
            "evidence": f"{count} pages observed with {int(token_swap_ratio*100)}% structural word count uniformity. Average depth {avg_words} words.",
            "recommended_action": f"{verdict.upper()}: Provide unique localized dealer pricing and distinct attributes across sibling cells."
        }
