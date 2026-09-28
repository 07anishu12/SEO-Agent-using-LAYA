"""One column contract shared by decision writers and SQLite migrations."""
import json

DECISION_COLUMNS = {
    "decision_id": "TEXT", "run_id": "TEXT", "cluster_id": "TEXT", "decision_type": "TEXT",
    "choice": "TEXT", "confidence": "REAL", "severity": "TEXT", "reason_codes": "TEXT",
    "recommended_action": "TEXT", "affected_scope": "TEXT", "affected_count": "INTEGER",
    "evidence_refs": "TEXT", "model_version": "TEXT", "input_hash": "TEXT", "latency_ms": "REAL",
    "created_at": "TEXT", "from_cache": "INTEGER", "raw_response": "TEXT", "gate": "TEXT",
    "prompt_version": "TEXT", "is_real_issue": "INTEGER", "scope": "TEXT", "root_cause": "TEXT",
    "canonical_indexability": "TEXT", "content_assessment": "TEXT", "cannibalization": "TEXT",
    "internal_linking": "TEXT", "head_confidences": "TEXT", "checkpoint_id": "TEXT", "verdict": "TEXT",
}
LEGACY_COLUMNS = {
    "crawl_id": "TEXT", "issue_key": "TEXT", "prompt_summary": "TEXT", "response_raw": "TEXT",
    "decision_category": "TEXT", "decision_severity": "TEXT", "decision_action": "TEXT",
}
OPPORTUNITY_COLUMNS = {
    "laya_action": "TEXT", "laya_confidence": "REAL", "laya_decision_id": "TEXT",
    "laya_validated": "INTEGER DEFAULT 0", "laya_verdict": "TEXT", "laya_scope": "TEXT",
    "laya_root_cause": "TEXT", "laya_canonical_indexability": "TEXT", "laya_content_assessment": "TEXT",
    "laya_cannibalization": "TEXT", "laya_internal_linking": "TEXT", "laya_candidate_id": "TEXT",
    "laya_gate": "TEXT", "laya_head_confidences": "TEXT", "laya_checkpoint_id": "TEXT",
}
JSON_COLUMNS = {"reason_codes", "evidence_refs", "canonical_indexability", "content_assessment", "cannibalization", "internal_linking", "head_confidences"}


def decision_row(decision):
    values = decision.to_dict()
    return {k: json.dumps(values[k], sort_keys=True) if k in JSON_COLUMNS else int(values[k]) if isinstance(values[k], bool) else values[k] for k in DECISION_COLUMNS}


def insert_decision(conn, table, decision):
    if table not in {"laya_decisions", "laya_decision_log"}:
        raise ValueError("Unknown Laya decision table")
    row = decision_row(decision)
    if table == "laya_decisions":
        row.update(crawl_id=decision.run_id, issue_key=decision.cluster_id, prompt_summary=f"Reduced candidate {decision.cluster_id}", response_raw=decision.raw_response, decision_category=decision.head_confidences["category"]["choice"], decision_severity=decision.severity, decision_action=decision.choice)
    return conn.execute(f"INSERT OR REPLACE INTO {table} ({','.join(row)}) VALUES ({','.join('?' for _ in row)})", tuple(row.values())).rowcount
