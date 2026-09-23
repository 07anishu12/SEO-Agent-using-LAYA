from typing import List, Dict, Any
from collections import defaultdict
from models.issue import SEOIssue

def analyze_duplicates(pages: List[Dict[str, Any]]) -> List[SEOIssue]:
    issues: List[SEOIssue] = []

    titles_map = defaultdict(list)
    descs_map = defaultdict(list)
    h1s_map = defaultdict(list)
    hashes_map = defaultdict(list)

    for p in pages:
        url = p["url"]
        p_type = p.get("page_type", "other")
        tpl = p.get("template_id", "default")

        title = (p.get("title") or "").strip().lower()
        if len(title) > 10:
            titles_map[title].append((url, p_type, tpl))

        desc = (p.get("description") or "").strip().lower()
        if len(desc) > 20:
            descs_map[desc].append((url, p_type, tpl))

        h1 = (p.get("h1_text") or "").strip().lower()
        if len(h1) > 5:
            h1s_map[h1].append((url, p_type, tpl))

        c_hash = p.get("content_hash")
        word_count = p.get("word_count", 0)
        # Only check content hash if word count > 100 to avoid matching empty/thin shell pages as duplicate content
        if c_hash and word_count >= 100:
            hashes_map[c_hash].append((url, p_type, tpl, word_count))

    # Duplicate Titles
    for title, url_list in titles_map.items():
        if len(url_list) > 1:
            urls = [u for u, pt, t in url_list]
            for u, pt, t in url_list[:5]:  # limit individual issues to sample
                issues.append(SEOIssue(
                    url=u, page_type=pt, template=t,
                    category="duplicates", issue="duplicate_title_tag",
                    severity="medium",
                    evidence=f"Identical title '{title[:60]}' shared across {len(url_list)} pages (e.g. {urls[0]} and {urls[1]}).",
                    recommendation="Ensure every indexable URL has a distinct, tailored title reflecting specific page content."
                ))

    # Duplicate Meta Descriptions
    for desc, url_list in descs_map.items():
        if len(url_list) > 1:
            urls = [u for u, pt, t in url_list]
            for u, pt, t in url_list[:5]:
                issues.append(SEOIssue(
                    url=u, page_type=pt, template=t,
                    category="duplicates", issue="duplicate_meta_description",
                    severity="low",
                    evidence=f"Identical meta description shared across {len(url_list)} pages.",
                    recommendation="Craft unique descriptions to provide clearer context in search engine result snippets."
                ))

    # Duplicate Exact Content
    for c_hash, url_list in hashes_map.items():
        if len(url_list) > 1:
            urls = [u for u, pt, t, wc in url_list]
            for u, pt, t, wc in url_list:
                issues.append(SEOIssue(
                    url=u, page_type=pt, template=t,
                    category="duplicates", issue="exact_duplicate_content",
                    severity="high",
                    evidence=f"Exact main-body content match across {len(url_list)} URLs (word count: {wc}).",
                    recommendation="Consolidate duplicate pages using 301 redirects or canonical tags to the master version."
                ))

    return issues
