import re
from typing import Dict, List, Tuple
from bs4 import BeautifulSoup
from models.issue import SEOIssue

def analyze_robots_meta(
    soup: BeautifulSoup,
    headers: Dict[str, str],
    url: str,
    page_type: str,
    template: str,
    discovery_source: str
) -> Tuple[str, str, bool, bool, List[SEOIssue]]:
    issues: List[SEOIssue] = []

    # Meta robots
    meta_tags = soup.find_all("meta", attrs={"name": re.compile(r"^(robots|googlebot)$", re.I)})
    meta_directives = []
    for tag in meta_tags:
        content = tag.get("content", "").strip().lower()
        if content:
            meta_directives.extend([d.strip() for d in content.split(",")])

    meta_robots_str = ", ".join(meta_directives)

    # X-Robots-Tag header
    x_robots = ""
    for k, v in headers.items():
        if k.lower() == "x-robots-tag":
            x_robots = v.lower()
            meta_directives.extend([d.strip() for d in x_robots.split(",")])

    all_directives = set(meta_directives)

    is_indexable = True
    is_follow = True

    if "noindex" in all_directives or "none" in all_directives:
        is_indexable = False
        # If URL was in sitemap, this is a conflict!
        if discovery_source == "sitemap":
            issues.append(SEOIssue(
                url=url, page_type=page_type, template=template,
                category="indexability", issue="sitemap_url_has_noindex",
                severity="critical",
                evidence=f"URL is listed in XML sitemap but returns noindex directive: '{meta_robots_str or x_robots}'.",
                recommendation="Remove noindex from this page or remove the URL from XML sitemaps to resolve conflict."
            ))
        else:
            issues.append(SEOIssue(
                url=url, page_type=page_type, template=template,
                category="indexability", issue="page_has_noindex",
                severity="medium",
                evidence=f"Page is blocked from indexing via robots directive: '{meta_robots_str or x_robots}'.",
                recommendation="Verify whether this page should be excluded from search engine indexes."
            ))

    if "nofollow" in all_directives or "none" in all_directives:
        is_follow = False
        issues.append(SEOIssue(
            url=url, page_type=page_type, template=template,
            category="internal_linking", issue="page_has_nofollow",
            severity="low",
            evidence=f"Page contains nofollow directive: '{meta_robots_str or x_robots}'.",
            recommendation="Avoid site-wide nofollow directives so search engines can discover internal links."
        ))

    return meta_robots_str, x_robots, is_indexable, is_follow, issues
