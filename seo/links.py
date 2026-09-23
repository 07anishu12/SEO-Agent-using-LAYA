import urllib.parse
from typing import List, Tuple, Set
from bs4 import BeautifulSoup
from models.page import LinkItem
from models.issue import SEOIssue

def analyze_links(
    soup: BeautifulSoup,
    current_url: str,
    normalizer,
    page_type: str,
    template: str
) -> Tuple[List[LinkItem], int, int, int, int, List[SEOIssue]]:
    issues: List[SEOIssue] = []
    link_items: List[LinkItem] = []

    internal_count = 0
    external_count = 0
    unique_internals: Set[str] = set()
    unique_externals: Set[str] = set()
    empty_anchors_count = 0

    anchors = soup.find_all("a", href=True)

    for a in anchors:
        raw_href = a.get("href", "").strip()
        if not raw_href or raw_href.startswith(("javascript:", "mailto:", "tel:", "#")):
            continue

        normalized_target = normalizer.normalize(raw_href, current_url)
        if not normalized_target:
            continue

        anchor_text = a.get_text(strip=True)
        # Check if anchor contains an img with alt
        if not anchor_text:
            img = a.find("img")
            if img and img.get("alt"):
                anchor_text = f"[IMG: {img.get('alt').strip()}]"
            elif not a.find("svg"):
                empty_anchors_count += 1

        rel = [r.lower() for r in a.get("rel", [])] if isinstance(a.get("rel"), list) else [str(a.get("rel", "")).lower()]
        is_nofollow = "nofollow" in rel
        is_sponsored = "sponsored" in rel
        is_ugc = "ugc" in rel

        is_internal = normalizer.is_same_domain(normalized_target)

        item = LinkItem(
            source_url=current_url,
            target_url=normalized_target,
            anchor_text=anchor_text[:100],
            is_internal=is_internal,
            is_nofollow=is_nofollow,
            is_sponsored=is_sponsored,
            is_ugc=is_ugc
        )
        link_items.append(item)

        if is_internal:
            internal_count += 1
            unique_internals.add(normalized_target)
        else:
            external_count += 1
            unique_externals.add(normalized_target)

    if empty_anchors_count > 0:
        issues.append(SEOIssue(
            url=current_url, page_type=page_type, template=template,
            category="internal_linking", issue="empty_anchor_text",
            severity="low",
            evidence=f"Found {empty_anchors_count} links with no visible anchor text or image alt.",
            recommendation="Provide meaningful, keyword-rich anchor text for all navigational links."
        ))

    if internal_count == 0:
        issues.append(SEOIssue(
            url=current_url, page_type=page_type, template=template,
            category="internal_linking", issue="zero_outbound_internal_links",
            severity="medium",
            evidence="Page has no outbound internal links pointing to other sections of the site.",
            recommendation="Add contextual internal links to related categories, models, or topics."
        ))

    return (
        link_items,
        internal_count,
        len(unique_internals),
        external_count,
        len(unique_externals),
        issues
    )
