import re
import urllib.parse
from typing import List, Tuple
from bs4 import BeautifulSoup
from models.issue import SEOIssue

def analyze_canonical(
    soup: BeautifulSoup,
    current_url: str,
    normalizer,
    page_type: str,
    template: str
) -> Tuple[str, str, bool, List[SEOIssue]]:
    issues: List[SEOIssue] = []

    canonical_tags = soup.find_all("link", attrs={"rel": re.compile(r"^canonical$", re.I)})
    canonical_url = ""
    canonical_status = "ok"
    is_self_canonical = True

    if not canonical_tags:
        canonical_status = "missing"
        is_self_canonical = False
        issues.append(SEOIssue(
            url=current_url, page_type=page_type, template=template,
            category="canonical", issue="missing_canonical_tag",
            severity="medium",
            evidence="Page does not declare a canonical tag.",
            recommendation="Add a self-referencing <link rel='canonical'> tag to prevent duplicate content issues."
        ))
    else:
        if len(canonical_tags) > 1:
            issues.append(SEOIssue(
                url=current_url, page_type=page_type, template=template,
                category="canonical", issue="multiple_canonical_tags",
                severity="high",
                evidence=f"Page specifies {len(canonical_tags)} conflicting canonical tags.",
                recommendation="Ensure only a single canonical link element exists in the head."
            ))

        raw_canonical = canonical_tags[0].get("href", "").strip()
        normalized_canonical = normalizer.normalize(raw_canonical, current_url)

        if not normalized_canonical:
            canonical_status = "invalid"
            is_self_canonical = False
            issues.append(SEOIssue(
                url=current_url, page_type=page_type, template=template,
                category="canonical", issue="invalid_canonical_url",
                severity="high",
                evidence=f"Canonical tag href '{raw_canonical}' is not a valid absolute URL.",
                recommendation="Provide a fully qualified absolute URL with scheme and host for canonical."
            ))
        else:
            canonical_url = normalized_canonical
            # Check domain
            if not normalizer.is_same_domain(canonical_url):
                canonical_status = "external"
                is_self_canonical = False
                issues.append(SEOIssue(
                    url=current_url, page_type=page_type, template=template,
                    category="canonical", issue="cross_domain_canonical",
                    severity="medium",
                    evidence=f"Canonical points outside the primary website domain: '{canonical_url}'.",
                    recommendation="Verify whether cross-domain canonicalization is intentional."
                ))
            elif canonical_url != current_url:
                canonical_status = "mismatch"
                is_self_canonical = False
                issues.append(SEOIssue(
                    url=current_url, page_type=page_type, template=template,
                    category="canonical", issue="canonical_mismatch",
                    severity="low",
                    evidence=f"Page points canonical to a different URL: '{canonical_url}'.",
                    recommendation="Verify that this non-self canonical is intentional consolidation."
                ))
            else:
                canonical_status = "ok"
                is_self_canonical = True

    return canonical_url, canonical_status, is_self_canonical, issues
