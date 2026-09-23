import re
from typing import List, Tuple
from bs4 import BeautifulSoup
from models.issue import SEOIssue

def analyze_headings(soup: BeautifulSoup, url: str, page_type: str, template: str) -> Tuple[int, str, int, List[str], int, List[str], List[SEOIssue]]:
    issues: List[SEOIssue] = []

    h1_tags = soup.find_all("h1")
    h2_tags = soup.find_all("h2")
    h3_tags = soup.find_all("h3")

    h1_count = len(h1_tags)
    h1_texts = [re.sub(r"\s+", " ", h.get_text()).strip() for h in h1_tags if h.get_text().strip()]
    h1_primary_text = h1_texts[0] if h1_texts else ""

    h2_count = len(h2_tags)
    h2_texts = [re.sub(r"\s+", " ", h.get_text()).strip() for h in h2_tags if h.get_text().strip()][:10]

    h3_count = len(h3_tags)
    h3_texts = [re.sub(r"\s+", " ", h.get_text()).strip() for h in h3_tags if h.get_text().strip()][:10]

    if h1_count == 0:
        issues.append(SEOIssue(
            url=url, page_type=page_type, template=template,
            category="headings", issue="missing_h1",
            severity="high",
            evidence="Page has no <h1> heading tag.",
            recommendation="Add a clear, unique <h1> tag defining the main topic of the page."
        ))
    elif h1_count > 1:
        issues.append(SEOIssue(
            url=url, page_type=page_type, template=template,
            category="headings", issue="multiple_h1",
            severity="medium",
            evidence=f"Page has {h1_count} <h1> tags: {h1_texts[:3]}",
            recommendation="Consolidate page structure to use a single primary <h1> heading tag."
        ))
    elif not h1_primary_text:
        issues.append(SEOIssue(
            url=url, page_type=page_type, template=template,
            category="headings", issue="empty_h1",
            severity="high",
            evidence="The <h1> tag exists but contains only whitespace or no visible text.",
            recommendation="Ensure the <h1> tag contains concise, human-readable keyword text."
        ))

    # Hierarchy check: h3 present with 0 h2
    if h3_count > 0 and h2_count == 0:
        issues.append(SEOIssue(
            url=url, page_type=page_type, template=template,
            category="headings", issue="heading_hierarchy_skipped_h2",
            severity="low",
            evidence=f"Document contains {h3_count} <h3> headings without any preceding <h2> tags.",
            recommendation="Maintain proper hierarchical heading structure (h1 -> h2 -> h3)."
        ))

    return h1_count, h1_primary_text, h2_count, h2_texts, h3_count, h3_texts, issues
