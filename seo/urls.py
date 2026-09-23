import urllib.parse
import re
from typing import List
from models.issue import SEOIssue

def analyze_url_quality(url: str, page_type: str, template: str) -> List[SEOIssue]:
    issues: List[SEOIssue] = []
    parsed = urllib.parse.urlsplit(url)

    # 1. URL Length
    if len(url) > 100:
        issues.append(SEOIssue(
            url=url, page_type=page_type, template=template,
            category="url", issue="long_url",
            severity="low",
            evidence=f"URL length is {len(url)} characters (exceeds recommended 100-character limit).",
            recommendation="Shorten URL slugs for better usability and social sharing readability."
        ))

    # 2. Path Depth
    path_segments = [s for s in parsed.path.split("/") if s]
    if len(path_segments) > 4:
        issues.append(SEOIssue(
            url=url, page_type=page_type, template=template,
            category="url", issue="deep_url_path",
            severity="low",
            evidence=f"URL path depth is {len(path_segments)} segments: '{parsed.path}'.",
            recommendation="Flatten URL path hierarchy to keep important pages closer to domain root."
        ))

    # 3. Uppercase in path
    if re.search(r"[A-Z]", parsed.path):
        issues.append(SEOIssue(
            url=url, page_type=page_type, template=template,
            category="url", issue="uppercase_in_url",
            severity="low",
            evidence=f"URL path contains uppercase characters: '{parsed.path}'.",
            recommendation="Use lowercase characters throughout URLs to avoid duplicate content on case-sensitive servers."
        ))

    # 4. Duplicate slashes
    if "//" in parsed.path:
        issues.append(SEOIssue(
            url=url, page_type=page_type, template=template,
            category="url", issue="duplicate_slashes_in_path",
            severity="medium",
            evidence=f"URL path contains duplicate consecutive slashes: '{parsed.path}'.",
            recommendation="Normalize URLs to eliminate double slashes."
        ))

    # 5. Dangerous / unencoded characters
    if any(c in url for c in [" ", "<", ">", '"', "{", "}", "|", "\\", "^", "`"]):
        issues.append(SEOIssue(
            url=url, page_type=page_type, template=template,
            category="url", issue="unsafe_characters_in_url",
            severity="medium",
            evidence="URL contains unescaped special characters or spaces.",
            recommendation="Properly percent-encode or remove non-standard characters from URLs."
        ))

    return issues
