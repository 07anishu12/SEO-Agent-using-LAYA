import re
import hashlib
from typing import List, Tuple
from bs4 import BeautifulSoup
from models.issue import SEOIssue

def analyze_content(soup: BeautifulSoup, raw_html: str, url: str, page_type: str, template: str) -> Tuple[int, int, float, str, List[SEOIssue]]:
    issues: List[SEOIssue] = []

    # Clone soup or remove non-content elements
    content_soup = BeautifulSoup(str(soup), "lxml")
    for el in content_soup(["script", "style", "noscript", "svg", "header", "footer", "nav"]):
        el.decompose()

    body = content_soup.body or content_soup
    visible_text = body.get_text(separator=" ", strip=True)
    words = [w for w in re.findall(r"\b\w+\b", visible_text) if len(w) > 1]
    word_count = len(words)

    # Paragraphs count
    paragraphs = soup.find_all("p")
    p_count = len([p for p in paragraphs if len(p.get_text(strip=True)) > 20])

    # Text-to-HTML ratio
    html_len = len(raw_html) if raw_html else 1
    text_len = len(visible_text)
    text_ratio = round((text_len / html_len) * 100, 2)

    # Content hash for duplicate detection (normalized lowercase alphanumeric)
    norm_content = " ".join([w.lower() for w in words[:500]])
    content_hash = hashlib.md5(norm_content.encode("utf-8")).hexdigest() if norm_content else ""

    if word_count < 50:
        issues.append(SEOIssue(
            url=url, page_type=page_type, template=template,
            category="content", issue="extremely_thin_content",
            severity="high",
            evidence=f"Page has only {word_count} words of visible textual content.",
            recommendation="Add informative, comprehensive copy relevant to the page topic or consolidate thin pages."
        ))
    elif word_count < 200:
        issues.append(SEOIssue(
            url=url, page_type=page_type, template=template,
            category="content", issue="thin_content",
            severity="medium",
            evidence=f"Page has {word_count} words (below recommended 200+ words minimum threshold).",
            recommendation="Enrich page with detailed content, FAQs, specifications, or user guides."
        ))

    if text_ratio < 3.0 and word_count < 300:
        issues.append(SEOIssue(
            url=url, page_type=page_type, template=template,
            category="content", issue="low_text_to_html_ratio",
            severity="low",
            evidence=f"Text-to-HTML ratio is {text_ratio}% with heavy markup code.",
            recommendation="Streamline inline scripts/styles and augment organic textual content."
        ))

    return word_count, p_count, text_ratio, content_hash, issues
