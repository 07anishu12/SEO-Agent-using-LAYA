import re
from typing import Dict, Any, List
from bs4 import BeautifulSoup

class AEOAnalyzerV3:
    """Evaluates page readiness for Answer Engines (Perplexity, ChatGPT, AI Overviews) via answer extractability and question coverage."""
    def __init__(self, vertical):
        self.vertical = vertical
        self.question_bank = vertical.get_question_bank()

    def evaluate_aeo(self, html: str, page_data: Dict[str, Any]) -> Dict[str, Any]:
        soup = BeautifulSoup(html or "", "lxml")
        body_text = soup.get_text(separator=" ").lower()

        # 1. Answer Extractability
        # Check if headings (h2, h3) are immediately followed by concise paragraphs (< 300 chars) or structured tables
        headings = soup.find_all(["h2", "h3"])
        extractable_blocks = 0
        for h in headings:
            nxt = h.find_next_sibling()
            if nxt:
                if nxt.name == "p" and len(nxt.get_text().strip()) <= 300:
                    extractable_blocks += 1
                elif nxt.name in ("table", "ul", "dl"):
                    extractable_blocks += 1

        # 2. Question Coverage
        answered_questions = []
        missing_questions = []

        model_name = page_data.get("model") or "vehicle"
        for q_template in self.question_bank:
            q_concrete = q_template.replace("{model}", model_name).replace("{city}", "Delhi").replace("{product}", model_name)
            # Check if key tokens from the question appear in text
            q_tokens = [w for w in re.findall(r"\w+", q_concrete.lower()) if len(w) > 3 and w not in ("what", "where", "which", "available")]
            matched = sum(1 for t in q_tokens if t in body_text)
            if matched >= len(q_tokens) * 0.70:
                answered_questions.append(q_concrete)
            else:
                missing_questions.append(q_concrete)

        # 3. FAQ Schema & Accordion
        has_faq_schema = "FAQPage" in page_data.get("schema_types", "")
        has_faq_content = bool(soup.find_all(string=re.compile(r"frequently asked|faq", re.I)))

        # Score calculation (0 to 100)
        score = 0.0
        if extractable_blocks >= 3: score += 30.0
        elif extractable_blocks >= 1: score += 15.0

        q_ratio = len(answered_questions) / max(len(self.question_bank), 1)
        score += round(q_ratio * 40.0, 1)

        if has_faq_content: score += 15.0
        if has_faq_schema: score += 15.0

        score = min(100.0, score)
        level = "High" if score >= 70.0 else ("Medium" if score >= 40.0 else "Low")

        return {
            "aeo_readiness_score": score,
            "readiness_level": level,
            "extractable_answer_blocks_count": extractable_blocks,
            "answered_questions": answered_questions,
            "missing_questions": missing_questions,
            "has_faq_content": has_faq_content,
            "has_faq_schema": has_faq_schema,
            "recommended_action": f"Add concise 1-2 sentence definition answers and FAQPage JSON-LD schema for: '{missing_questions[0]}'" if missing_questions else "Maintain current answer extractability structure."
        }
