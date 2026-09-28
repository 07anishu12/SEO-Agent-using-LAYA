"""Stable reduced candidates and explicit cluster-to-opportunity membership."""
from collections import Counter
import json
from engine.id_system import IDSystem
from .decision import LayaCandidateInput


def samples(value):
    if isinstance(value, str):
        return json.loads(value) if value.startswith("[") else [v.strip() for v in value.split(",") if v.strip()]
    return list(value or [])


def candidate_key(opportunity=None, *, cluster_id=None):
    if cluster_id is not None:
        return f"cluster:{cluster_id}"
    if opportunity is None:
        raise ValueError("Candidate key requires an opportunity or cluster ID")
    # JSON encoding avoids delimiter collisions; the full action avoids truncation collisions.
    return "opportunity:" + json.dumps([opportunity.get("type") or "generic", opportunity.get("implementation_location") or "", opportunity.get("action") or ""], separators=(",", ":"))


def opportunity_candidate_key(opportunity, members):
    return members.get(opportunity["opportunity_id"], candidate_key(opportunity))


def build_candidates(clusters, pages, opportunities):
    by_url = {p["url"]: p for p in pages}
    by_template = {}
    for page in pages:
        by_template.setdefault(page.get("template_id"), []).append(page)

    def evidence(template, urls):
        cohort = [by_url[u] for u in sorted(set(urls)) if u in by_url]
        if not cohort:
            cohort = by_template.get(template, [])
        words = [int(p.get("word_count") or 0) for p in cohort]
        hashes = [p["content_hash"] for p in cohort if p.get("content_hash")]
        canonical = {"indexable": sum(bool(p.get("is_indexable")) for p in cohort), "non_indexable": sum(not bool(p.get("is_indexable")) for p in cohort), "canonical_statuses": dict(Counter(p.get("canonical_status") or "unknown" for p in cohort))}
        return {"status_distribution": dict(Counter(str(p.get("status_code") or 0) for p in cohort)), "indexability": canonical, "canonical_relationship": canonical,
                "content_metrics": {"pages": len(cohort), "min_words": min(words or [0]), "avg_words": round(sum(words)/max(len(words),1),1), "unique_content_hashes": len(set(hashes)), "duplicate_content_pages": len(hashes)-len(set(hashes))},
                "link_metrics": {"avg_internal_links": round(sum(int(p.get("internal_links_count") or 0) for p in cohort)/max(len(cohort),1),1)}}

    candidates, members, fingerprints = {}, {}, {}
    template_ids = {t for o in opportunities for t in samples(o.get("affected_templates_json"))}
    for cluster in clusters:
        cluster_id = cluster["cluster_id"]
        key = candidate_key(cluster_id=cluster_id)
        template = cluster.get("primary_affected_template") or "default"
        urls = sorted(set(samples(cluster.get("sample_urls"))))[:5]
        candidates[key] = LayaCandidateInput(cluster_id=key, template_id=template, issue_type=cluster["issue"], page_count=cluster["affected_urls_count"], sample_urls=urls,
                                             severity_hint=cluster.get("severity") or "medium", category_hint=cluster.get("category") or "technical", evidence_refs=[cluster.get("evidence_summary") or ""], **evidence(template, urls))
        fingerprints[IDSystem.generate_fingerprint(cluster_id, "site", "site-wide")] = key
        for tpl in template_ids:
            fingerprints[IDSystem.generate_fingerprint(cluster_id, tpl, "template-aggregate")] = key
    grouped = {}
    for opportunity in opportunities:
        member = fingerprints.get(opportunity.get("fingerprint"))
        if member:
            members[opportunity["opportunity_id"]] = member
        else:
            key = candidate_key(opportunity)
            grouped.setdefault(key, []).append(opportunity)
    for key, group in grouped.items():
        group.sort(key=lambda o: o["opportunity_id"])
        first = group[0]
        urls = sorted({u for o in group for u in samples(o.get("sample_urls_json"))})[:5]
        templates = samples(first.get("affected_templates_json"))
        template = templates[0] if templates else first.get("implementation_location") or "default"
        candidates[key] = LayaCandidateInput(cluster_id=key, template_id=template, issue_type=first.get("observation") or first["type"], page_count=sum(int(o.get("affected_urls_count") or 1) for o in group), sample_urls=urls,
                                             severity_hint=(first.get("opportunity_tier") or "medium").lower(), category_hint=first["type"], evidence_refs=[first.get("hypothesis") or ""], **evidence(template, urls))
    return candidates, members
