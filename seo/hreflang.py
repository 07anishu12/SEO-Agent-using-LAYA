import urllib.parse
from typing import List, Dict, Tuple
from bs4 import BeautifulSoup
from models.issue import SEOIssue

def analyze_hreflang(
    soup: BeautifulSoup,
    current_url: str,
    page_type: str,
    template: str
) -> Tuple[List[Dict[str, str]], List[SEOIssue]]:
    issues: List[SEOIssue] = []
    hreflangs: List[Dict[str, str]] = []

    alternate_tags = soup.find_all("link", attrs={"rel": "alternate", "hreflang": True})
    has_self_ref = False

    for tag in alternate_tags:
        lang = tag.get("hreflang", "").strip()
        href = tag.get("href", "").strip()
        full_href = urllib.parse.urljoin(current_url, href)

        hreflangs.append({"lang": lang, "href": full_href})
        if full_href == current_url:
            has_self_ref = True

    if alternate_tags and not has_self_ref:
        issues.append(SEOIssue(
            url=current_url, page_type=page_type, template=template,
            category="technical", issue="missing_self_hreflang",
            severity="low",
            evidence=f"Page specifies {len(alternate_tags)} alternate hreflang tags but omits a self-referencing hreflang tag.",
            recommendation="Include a self-referencing alternate link for the page's canonical language/locale."
        ))

    return hreflangs, issues
