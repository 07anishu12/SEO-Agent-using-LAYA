"""One canonical prompt, byte-for-byte compatible with the established worker input."""
import hashlib
import json


def issue_data(candidate):
    return {'cluster_id': candidate.cluster_id, 'issue': candidate.issue_type,
            'category': candidate.category_hint, 'severity': candidate.severity_hint,
            'template': candidate.template_id, 'affected_urls_count': candidate.page_count,
            'status_distribution': candidate.status_distribution,
            'canonical_indexability': candidate.canonical_relationship or candidate.indexability,
            'content_metrics': candidate.content_metrics, 'link_metrics': candidate.link_metrics,
            'query_metrics': candidate.query_metrics, 'schema_metrics': candidate.schema_metrics,
            'evidence_refs': candidate.evidence_refs, 'root_cause': candidate.issue_type}


def normalized_prompt(data):
    return json.dumps(data, sort_keys=True, default=str)


def prompt_hash(data, prompt_version, checkpoint_id):
    return hashlib.sha256(json.dumps([normalized_prompt(data), prompt_version, checkpoint_id], separators=(',', ':')).encode()).hexdigest()
