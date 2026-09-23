from typing import List
from models.issue import SEOIssue

def analyze_technical(
    url: str,
    status_code: int,
    redirect_chain: List[str],
    response_time: float,
    content_type: str,
    page_type: str,
    template: str
) -> List[SEOIssue]:
    issues: List[SEOIssue] = []

    # 1. HTTP 4xx Client Errors
    if 400 <= status_code < 500:
        issues.append(SEOIssue(
            url=url, page_type=page_type, template=template,
            category="technical", issue=f"http_{status_code}_error",
            severity="high" if status_code == 404 else "critical",
            evidence=f"Server returned HTTP {status_code} client error.",
            recommendation="Fix broken URL, update internal references, or configure a 301 permanent redirect."
        ))

    # 2. HTTP 5xx Server Errors
    elif status_code >= 500:
        issues.append(SEOIssue(
            url=url, page_type=page_type, template=template,
            category="technical", issue=f"http_{status_code}_server_error",
            severity="critical",
            evidence=f"Server responded with internal error HTTP {status_code}.",
            recommendation="Investigate server-side logs, unhandled backend exceptions, or database timeouts."
        ))

    # 3. Redirect chains and loops
    if len(redirect_chain) > 1:
        if len(redirect_chain) > 3:
            issues.append(SEOIssue(
                url=url, page_type=page_type, template=template,
                category="technical", issue="long_redirect_chain",
                severity="medium",
                evidence=f"Encountered redirect chain with {len(redirect_chain)} hops: {' -> '.join(redirect_chain[:4])}...",
                recommendation="Shorten redirect chains directly to the final destination to conserve crawl budget and latency."
            ))
        # Loop detection
        if len(redirect_chain) != len(set(redirect_chain)):
            issues.append(SEOIssue(
                url=url, page_type=page_type, template=template,
                category="technical", issue="redirect_loop",
                severity="critical",
                evidence=f"Detected circular redirect loop in chain: {' -> '.join(redirect_chain)}",
                recommendation="Break circular redirect configurations immediately."
            ))

    # 4. Latency
    if response_time > 2.0 and status_code == 200:
        issues.append(SEOIssue(
            url=url, page_type=page_type, template=template,
            category="performance", issue="slow_server_response",
            severity="medium",
            evidence=f"Initial server response took {response_time}s (recommended TTFB is < 0.8s).",
            recommendation="Improve backend database indexing, caching layers, or CDN edge caching."
        ))

    return issues
