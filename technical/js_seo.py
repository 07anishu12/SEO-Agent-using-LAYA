from typing import Dict, Any, List, Optional
from bs4 import BeautifulSoup

class JSSEOAnalyzer:
    """Compares raw HTTP response HTML against rendered DOM to detect client-side rendering dependency and SEO risks."""
    def __init__(self):
        pass

    def compare_raw_vs_rendered(self, raw_html: str, rendered_html: str, url: str) -> Dict[str, Any]:
        raw_soup = BeautifulSoup(raw_html or "", "lxml")
        rend_soup = BeautifulSoup(rendered_html or "", "lxml")

        raw_text = raw_soup.get_text(separator=" ").strip()
        rend_text = rend_soup.get_text(separator=" ").strip()

        raw_links = [a.get("href") for a in raw_soup.find_all("a", href=True)]
        rend_links = [a.get("href") for a in rend_soup.find_all("a", href=True)]

        raw_canon = raw_soup.find("link", rel=lambda r: r and "canonical" in r)
        rend_canon = rend_soup.find("link", rel=lambda r: r and "canonical" in r)

        raw_schema = bool(raw_soup.find("script", type="application/ld+json"))
        rend_schema = bool(rend_soup.find("script", type="application/ld+json"))

        raw_h1 = (raw_soup.find("h1").get_text().strip() if raw_soup.find("h1") else "")
        rend_h1 = (rend_soup.find("h1").get_text().strip() if rend_soup.find("h1") else "")

        content_ratio = round(len(raw_text) / max(len(rend_text), 1), 2)
        link_ratio = round(len(raw_links) / max(len(rend_links), 1), 2)

        risks = []
        if content_ratio < 0.35:
            risks.append("Severe content deficiency in raw HTML (under 35% of rendered text present). Search engines may index thin content before JS execution.")
        if link_ratio < 0.50:
            risks.append(f"Internal links absent from raw HTML: only {len(raw_links)} links in raw vs {len(rend_links)} in rendered DOM.")
        if not raw_canon and rend_canon:
            risks.append("Canonical tag rendered only via client-side JavaScript.")
        if not raw_schema and rend_schema:
            risks.append("Schema.org JSON-LD injected only after client-side hydration.")
        if not raw_h1 and rend_h1:
            risks.append("H1 heading tag rendered only via client-side JavaScript.")

        has_risk = len(risks) > 0

        return {
            "url": url,
            "has_js_seo_risk": has_risk,
            "content_visible_in_raw_ratio": content_ratio,
            "links_visible_in_raw_ratio": link_ratio,
            "raw_text_length": len(raw_text),
            "rendered_text_length": len(rend_text),
            "raw_links_count": len(raw_links),
            "rendered_links_count": len(rend_links),
            "identified_risks": risks,
            "verdict": "JS SEO RISK" if has_risk else "SSR / HYDRATED CLEAN"
        }
