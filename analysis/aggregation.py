from typing import List, Dict, Any
from collections import defaultdict
from models.issue import IssueCluster

def build_issue_clusters(issues: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Solves issue explosion by clustering thousands of granular issue occurrences
    into structured, decision-oriented IssueClusters:
    ISSUE -> ISSUE CLUSTER -> TEMPLATE ISSUE / SITE-WIDE ISSUE / PAGE OPPORTUNITY.
    """
    clusters_map = defaultdict(list)
    for iss in issues:
        i_name = iss.get("issue", "unknown_issue")
        clusters_map[i_name].append(iss)

    issue_clusters = []

    for i_name, iss_list in clusters_map.items():
        total_affected = len(iss_list)
        first = iss_list[0]
        cat = first.get("category", "technical")
        raw_sev = first.get("severity", "medium")

        # Template distribution
        templates_counter = defaultdict(int)
        for i in iss_list:
            templates_counter[i.get("template", "default")] += 1

        sorted_templates = sorted(templates_counter.items(), key=lambda x: x[1], reverse=True)
        primary_tpl, primary_tpl_count = sorted_templates[0] if sorted_templates else ("default", 0)
        affected_templates_count = len(sorted_templates)

        # Determine scope
        if affected_templates_count >= 5 and total_affected >= 50:
            scope = "site_wide"
            fix_location = "Global layout / site-wide metadata service"
        elif primary_tpl_count / max(total_affected, 1) >= 0.5:
            scope = "template"
            fix_location = f"Template component: '{primary_tpl}'"
        else:
            scope = "page_opportunity"
            fix_location = "Individual page content / route handlers"

        # Determine P0 - P3 priority transparently
        if i_name in ("redirect_loop", "http_500_server_error", "sitemap_url_has_noindex") or raw_sev == "critical":
            priority = "P0"
            rec_action = f"Immediate engineering blocker: resolve {i_name.replace('_', ' ')} across {total_affected} URLs."
        elif i_name in ("orphan_page", "weakly_linked_product_page", "missing_h1", "canonical_mismatch", "malformed_json_ld") or (cat == "technical" and raw_sev == "high"):
            priority = "P1"
            rec_action = f"High-impact fix: update {primary_tpl} layout to resolve {i_name.replace('_', ' ')} across {total_affected} pages."
        elif i_name in ("missing_meta_description", "missing_title", "thin_content", "duplicate_title_tag", "empty_h1"):
            priority = "P2"
            rec_action = f"Important architectural improvement: revise {fix_location} to supply unique structured content."
        else:
            priority = "P3"
            rec_action = f"Routine hygiene cleanup: review {i_name.replace('_', ' ')} on affected pages."

        # Representative URLs (up to 8)
        sample_urls = []
        for i in iss_list:
            u = i.get("url")
            if u and u not in sample_urls:
                sample_urls.append(u)
                if len(sample_urls) >= 8:
                    break

        evidence_summary = (
            f"Observed on {total_affected:,} URLs across {affected_templates_count} templates. "
            f"Primary concentration in '{primary_tpl}' ({primary_tpl_count:,} pages affected, "
            f"{round((primary_tpl_count/max(total_affected,1))*100, 1)}% of total occurrences)."
        )

        cluster = {
            "cluster_id": f"cluster_{i_name}",
            "issue": i_name,
            "category": cat,
            "priority": priority,
            "severity": raw_sev,
            "affected_urls_count": total_affected,
            "affected_templates_count": affected_templates_count,
            "primary_affected_template": primary_tpl,
            "scope": scope,
            "evidence_summary": evidence_summary,
            "recommended_action": rec_action,
            "engineering_fix_location": fix_location,
            "sample_urls": sample_urls
        }
        issue_clusters.append(cluster)

    # Sort by priority (P0 -> P1 -> P2 -> P3), then affected_urls_count descending
    priority_order = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}
    issue_clusters.sort(key=lambda x: (priority_order.get(x["priority"], 99), -x["affected_urls_count"]))
    return issue_clusters

def aggregate_issues(issues: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Legacy compatibility returning the upgraded issue clusters."""
    return build_issue_clusters(issues)
