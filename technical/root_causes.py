from typing import Dict, Any, List, Set, Tuple
from collections import defaultdict

UPSTREAM_BLOCKERS = {"http_404_error", "sitemap_url_has_noindex", "redirect_loop"}
DOWNSTREAM_SYMPTOMS = {"missing_meta_description", "low_text_to_html_ratio", "missing_canonical"}

class RootCauseClusterer:
    """Consolidates granular issues into fundamental root causes and suppresses downstream symptoms."""
    def __init__(self):
        pass

    def cluster_root_causes(self, issues: List[Dict[str, Any]]) -> Dict[str, Any]:
        # Track pages that have hard upstream blockers
        blocked_urls: Set[str] = set()
        for iss in issues:
            if iss.get("issue") in UPSTREAM_BLOCKERS:
                blocked_urls.add(iss.get("url", ""))

        filtered_issues = []
        suppressed_symptoms_count = 0

        for iss in issues:
            u = iss.get("url", "")
            rule = iss.get("issue", "")
            # If page is 404 or noindexed, suppress minor downstream symptoms
            if u in blocked_urls and rule in DOWNSTREAM_SYMPTOMS:
                suppressed_symptoms_count += 1
                continue
            filtered_issues.append(iss)

        # Cluster by rule + template
        root_causes = defaultdict(list)
        for iss in filtered_issues:
            rule = iss.get("issue", "unknown")
            tpl = iss.get("template") or iss.get("template_id") or "site_wide"
            key = f"{rule}::{tpl}"
            root_causes[key].append(iss)

        clusters = []
        for key, members in root_causes.items():
            rule, tpl = key.split("::")
            sample_urls = [m.get("url") for m in members[:5]]
            clusters.append({
                "root_cause_id": key,
                "rule_id": rule,
                "template": tpl,
                "affected_pages_count": len(members),
                "severity": members[0].get("severity", "medium"),
                "category": members[0].get("category", "technical"),
                "sample_urls": sample_urls,
                "recommended_action": members[0].get("recommendation", f"Resolve {rule} at template level across {len(members)} pages.")
            })

        # Sort clusters by affected pages descending
        clusters.sort(key=lambda c: c["affected_pages_count"], reverse=True)

        return {
            "raw_issues_count": len(issues),
            "suppressed_symptoms_count": suppressed_symptoms_count,
            "retained_issues_count": len(filtered_issues),
            "root_cause_clusters_count": len(clusters),
            "clusters": clusters
        }
