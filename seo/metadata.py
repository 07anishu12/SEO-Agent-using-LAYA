import re
from typing import List, Tuple
from bs4 import BeautifulSoup
from models.issue import SEOIssue

def analyze_metadata(soup: BeautifulSoup, url: str, page_type: str, template: str) -> Tuple[str, int, int, str, int, List[SEOIssue]]:
    issues: List[SEOIssue] = []
    
    # Title analysis
    title_tags = soup.find_all("title")
    title_text = ""
    title_length = 0
    title_words = 0

    if not title_tags:
        issues.append(SEOIssue(
            url=url, page_type=page_type, template=template,
            category="metadata", issue="missing_title",
            severity="critical",
            evidence="Page has no <title> tag.",
            recommendation="Add a descriptive, unique <title> tag between 30 and 60 characters."
        ))
    else:
        if len(title_tags) > 1:
            issues.append(SEOIssue(
                url=url, page_type=page_type, template=template,
                category="metadata", issue="multiple_title_tags",
                severity="medium",
                evidence=f"Found {len(title_tags)} <title> tags in document.",
                recommendation="Ensure only a single <title> tag exists in the <head>."
            ))
        
        raw_title = title_tags[0].get_text().strip()
        title_text = re.sub(r"\s+", " ", raw_title)
        title_length = len(title_text)
        title_words = len(title_text.split())

        if title_length == 0:
            issues.append(SEOIssue(
                url=url, page_type=page_type, template=template,
                category="metadata", issue="empty_title",
                severity="critical",
                evidence="<title> tag is completely empty.",
                recommendation="Specify a unique and descriptive title representing the page content."
            ))
        elif title_length < 30:
            issues.append(SEOIssue(
                url=url, page_type=page_type, template=template,
                category="metadata", issue="short_title",
                severity="low",
                evidence=f"Title length is only {title_length} characters: '{title_text}'.",
                recommendation="Expand title to at least 30-60 characters including primary topic keywords and branding."
            ))
        elif title_length > 65:
            issues.append(SEOIssue(
                url=url, page_type=page_type, template=template,
                category="metadata", issue="long_title_truncated",
                severity="low",
                evidence=f"Title is {title_length} characters (exceeds typical 60-character SERP display limit).",
                recommendation="Shorten title to 50-60 characters to prevent truncation in search result snippets."
            ))

    # Meta Description analysis
    desc_tags = soup.find_all("meta", attrs={"name": re.compile(r"^description$", re.I)})
    desc_text = ""
    desc_length = 0

    if not desc_tags:
        issues.append(SEOIssue(
            url=url, page_type=page_type, template=template,
            category="metadata", issue="missing_meta_description",
            severity="medium",
            evidence="No meta description tag was found on the page.",
            recommendation="Add a compelling meta description tag (70-160 characters) summarizing page value."
        ))
    else:
        if len(desc_tags) > 1:
            issues.append(SEOIssue(
                url=url, page_type=page_type, template=template,
                category="metadata", issue="multiple_meta_descriptions",
                severity="medium",
                evidence=f"Found {len(desc_tags)} meta description tags.",
                recommendation="Keep exactly one meta description tag per page."
            ))
        
        raw_desc = desc_tags[0].get("content", "").strip()
        desc_text = re.sub(r"\s+", " ", raw_desc)
        desc_length = len(desc_text)

        if desc_length == 0:
            issues.append(SEOIssue(
                url=url, page_type=page_type, template=template,
                category="metadata", issue="empty_meta_description",
                severity="medium",
                evidence="Meta description content attribute is empty.",
                recommendation="Provide an engaging description between 70 and 160 characters."
            ))
        elif desc_length < 70:
            issues.append(SEOIssue(
                url=url, page_type=page_type, template=template,
                category="metadata", issue="short_meta_description",
                severity="low",
                evidence=f"Meta description is only {desc_length} characters: '{desc_text}'.",
                recommendation="Elaborate description to 70-160 characters to improve click-through rates."
            ))
        elif desc_length > 165:
            issues.append(SEOIssue(
                url=url, page_type=page_type, template=template,
                category="metadata", issue="long_meta_description",
                severity="low",
                evidence=f"Meta description is {desc_length} characters (likely truncated by search engines).",
                recommendation="Trim meta description to under 160 characters to fit standard SERP viewports."
            ))

    return title_text, title_length, title_words, desc_text, desc_length, issues
