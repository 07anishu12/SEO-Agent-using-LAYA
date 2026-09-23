import urllib.parse
import re
from typing import List, Dict, Any, Tuple
from collections import defaultdict
from models.issue import SEOIssue

def derive_template_id(url: str, page_type: str) -> str:
    """
    Derives a canonical template identifier based on page type and path structural pattern.
    E.g. https://www.drivio.in/bikes/tvs/raider-125 -> 'tpl_model_3seg'
    """
    if page_type == "homepage":
        return "tpl_homepage"

    parsed = urllib.parse.urlsplit(url)
    segments = [s for s in parsed.path.strip("/").split("/") if s]
    seg_count = len(segments)

    first_seg = segments[0] if segments else "root"
    # Simplify first_seg if it's dynamic
    first_seg = re.sub(r"\d+", "N", first_seg)

    return f"tpl_{page_type}_{first_seg}_{seg_count}seg"

def analyze_templates(pages: List[Dict[str, Any]], issues: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[SEOIssue]]:
    """
    Clusters pages into structural templates and calculates template-level health metrics.
    Detects systemic template-level issues.
    """
    template_groups = defaultdict(list)
    for p in pages:
        t_id = p.get("template_id") or derive_template_id(p["url"], p.get("page_type", "other"))
        template_groups[t_id].append(p)

    # Map issues to (template, issue_name)
    issues_by_template = defaultdict(lambda: defaultdict(list))
    for iss in issues:
        t_id = iss.get("template") or "default"
        i_name = iss.get("issue") or ""
        issues_by_template[t_id][i_name].append(iss)

    template_summaries = []
    template_issues = []

    for t_id, t_pages in template_groups.items():
        total_p = len(t_pages)
        if total_p == 0:
            continue

        sample_urls = [p["url"] for p in t_pages[:5]]
        dominant_type = t_pages[0].get("page_type", "other")

        titles = [p.get("title", "") for p in t_pages if p.get("title")]
        descs = [p.get("description", "") for p in t_pages if p.get("description")]
        h1s = [p.get("h1_text", "") for p in t_pages if p.get("h1_text")]

        unique_titles_pct = round((len(set(titles)) / max(total_p, 1)) * 100, 1)
        unique_descs_pct = round((len(set(descs)) / max(total_p, 1)) * 100, 1)
        unique_h1_pct = round((len(set(h1s)) / max(total_p, 1)) * 100, 1)

        avg_words = round(sum(p.get("word_count", 0) for p in t_pages) / max(total_p, 1), 1)
        avg_links = round(sum(p.get("internal_links_count", 0) for p in t_pages) / max(total_p, 1), 1)

        indexable_count = sum(1 for p in t_pages if p.get("is_indexable"))
        indexability_pct = round((indexable_count / max(total_p, 1)) * 100, 1)

        self_can_count = sum(1 for p in t_pages if p.get("is_self_canonical"))
        canonical_consistency = round((self_can_count / max(total_p, 1)) * 100, 1)

        # Status distribution
        status_dist = defaultdict(int)
        for p in t_pages:
            status_dist[p.get("status_code", 0)] += 1

        summary = {
            "template_id": t_id,
            "page_count": total_p,
            "sample_urls": sample_urls,
            "dominant_page_type": dominant_type,
            "characteristics": {
                "unique_title_percentage": unique_titles_pct,
                "unique_description_percentage": unique_descs_pct,
                "unique_h1_percentage": unique_h1_pct,
                "average_word_count": avg_words,
                "canonical_consistency": canonical_consistency,
                "internal_link_density": avg_links,
                "indexability": indexability_pct,
                "status_distribution": dict(status_dist)
            }
        }
        template_summaries.append(summary)

        # Check for systemic template-level issues (if >= 40% of pages in template have the issue and total >= 3)
        for issue_name, affected_issue_list in issues_by_template[t_id].items():
            affected_count = len(affected_issue_list)
            pct = (affected_count / total_p) * 100
            if (pct >= 40.0 and affected_count >= 3) or affected_count >= 50:
                first_iss = affected_issue_list[0]
                template_issues.append(SEOIssue(
                    url=sample_urls[0],
                    page_type=dominant_type,
                    template=t_id,
                    category=first_iss.get("category", "technical"),
                    issue=f"template_{issue_name}",
                    severity="high" if first_iss.get("severity") in ("critical", "high") else "medium",
                    evidence=f"Systemic template defect: {affected_count}/{total_p} pages ({round(pct, 1)}%) in template '{t_id}' have issue '{issue_name}'.",
                    recommendation=f"Update page template/layout for '{t_id}' to fix '{issue_name}' across all {affected_count} affected URLs simultaneously.",
                    source="template_aggregation"
                ))

    return template_summaries, template_issues
