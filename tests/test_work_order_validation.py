"""Regression tests for work-order lifecycle validation and failure accounting."""
import glob
import json
import sqlite3
import pytest
from engine.work_orders import WorkOrderManager


def test_valid_work_orders_pass_audit():
    valid_wo = {
        "work_order_id": "WO-test-1",
        "fingerprint": "fp1",
        "display_id": "SEOJEV-ENG-001",
        "run_id": "test_run",
        "order_type": "engineering",
        "priority": "P1",
        "scope": "site",
        "title": "Fix canonical tag",
        "problem": "Missing canonical tag across category pages.",
        "evidence_json": json.dumps({"opportunity_id": "OPP-1", "sample_urls": ["https://example.com/bikes"]}),
        "required_change": "Add canonical link tag in template header.",
        "acceptance_criteria": "- [ ] Verification spec evaluates to true.",
        "verify_spec": "canonical_matches_url == True",
        "file_locations_json": json.dumps(["templates/header.html"]),
        "laya_action": "fix_canonical",
        "laya_confidence": 0.85,
        "laya_decision_id": "dec_1",
        "laya_gate": "AUTO_ACCEPT"
    }

    is_valid, msg = WorkOrderManager.validate_work_order(valid_wo)
    assert is_valid is True
    assert msg == "Valid"


def test_malformed_work_orders_fail_with_reasons():
    base = {
        "work_order_id": "WO-test-bad",
        "fingerprint": "fp_bad",
        "display_id": "SEOJEV-ENG-002",
        "run_id": "test_run",
        "order_type": "engineering",
        "priority": "P2",
        "required_change": "Update title",
        "acceptance_criteria": "- [ ] Title updated",
        "evidence_json": "{}"
    }

    # 1. Missing work_order_id
    wo = {**base, "work_order_id": ""}
    valid, reason = WorkOrderManager.validate_work_order(wo)
    assert valid is False and "work_order_id" in reason

    # 2. Missing display_id
    wo = {**base, "display_id": ""}
    valid, reason = WorkOrderManager.validate_work_order(wo)
    assert valid is False and "display_id" in reason

    # 3. Invalid order_type
    wo = {**base, "order_type": "invalid_type"}
    valid, reason = WorkOrderManager.validate_work_order(wo)
    assert valid is False and "order_type" in reason

    # 4. Invalid priority
    wo = {**base, "priority": "CRITICAL"}
    valid, reason = WorkOrderManager.validate_work_order(wo)
    assert valid is False and "priority" in reason

    # 5. Missing required_change
    wo = {**base, "required_change": ""}
    valid, reason = WorkOrderManager.validate_work_order(wo)
    assert valid is False and "required_change" in reason

    # 6. Missing acceptance_criteria
    wo = {**base, "acceptance_criteria": ""}
    valid, reason = WorkOrderManager.validate_work_order(wo)
    assert valid is False and "acceptance_criteria" in reason

    # 7. Malformed evidence_json
    wo = {**base, "evidence_json": "not valid json"}
    valid, reason = WorkOrderManager.validate_work_order(wo)
    assert valid is False and "evidence_json" in reason


def test_audit_run_work_orders_accounting(tmp_path):
    db_file = tmp_path / "test_wo.db"
    mgr = WorkOrderManager(str(db_file))
    
    # Initialize schema
    with sqlite3.connect(db_file) as conn:
        conn.executescript("""
        CREATE TABLE work_orders (
            work_order_id TEXT PRIMARY KEY,
            fingerprint TEXT NOT NULL,
            display_id TEXT NOT NULL,
            run_id TEXT NOT NULL,
            order_type TEXT NOT NULL,
            priority TEXT NOT NULL,
            scope TEXT NOT NULL,
            title TEXT NOT NULL,
            problem TEXT NOT NULL,
            evidence_json TEXT,
            required_change TEXT NOT NULL,
            acceptance_criteria TEXT NOT NULL,
            verify_spec TEXT NOT NULL,
            file_locations_json TEXT,
            laya_action TEXT,
            laya_confidence REAL,
            laya_decision_id TEXT,
            laya_gate TEXT
        );
        CREATE TABLE verifications (
            verification_id TEXT PRIMARY KEY,
            run_id TEXT NOT NULL,
            work_order_id TEXT NOT NULL,
            fingerprint TEXT NOT NULL,
            status TEXT NOT NULL,
            executed_at TEXT NOT NULL,
            details_json TEXT
        );
        """)
        
        # Insert 2 valid work orders and 1 malformed work order
        conn.execute("""
        INSERT INTO work_orders VALUES 
        ('WO-1', 'fp1', 'SEOJEV-ENG-001', 'run1', 'engineering', 'P1', 'site', 'Title 1', 'Prob 1', '{}', 'Change 1', 'Crit 1', 'spec1', '[]', 'act1', 0.9, 'dec1', 'AUTO_ACCEPT'),
        ('WO-2', 'fp2', 'SEOJEV-CONTENT-001', 'run1', 'content', 'P2', 'page', 'Title 2', 'Prob 2', '{\"key\": 1}', 'Change 2', 'Crit 2', 'spec2', '[]', 'act2', 0.7, 'dec2', 'HUMAN_REVIEW'),
        ('WO-3', 'fp3', 'SEOJEV-ENG-002', 'run1', 'invalid_order_type', 'P1', 'site', 'Title 3', 'Prob 3', '{}', 'Change 3', 'Crit 3', 'spec3', '[]', 'act3', 0.9, 'dec3', 'AUTO_ACCEPT')
        """)

        # Insert verifications (1 PASSED, 2 FAILED)
        conn.execute("""
        INSERT INTO verifications VALUES
        ('V-1', 'run1', 'WO-1', 'fp1', 'PASSED', '2026-09-28', '{}'),
        ('V-2', 'run1', 'WO-2', 'fp2', 'FAILED', '2026-09-28', '{}'),
        ('V-3', 'run1', 'WO-3', 'fp3', 'FAILED', '2026-09-28', '{}')
        """)
        conn.commit()

    audit = mgr.audit_run_work_orders("run1")
    assert audit["total_work_orders"] == 3
    assert audit["valid_count"] == 2
    assert audit["failed_count"] == 1
    assert len(audit["failed_reasons"]) == 1
    assert audit["failed_reasons"][0]["work_order_id"] == "WO-3"
    assert audit["by_type"] == {"content": 1, "engineering": 1}
    assert audit["baseline_verifications"] == {"PASSED": 1, "FAILED": 2}


def test_actual_validation_db_work_orders_integrity():
    dbs = glob.glob("reports/laya_val_1000/val-sample-*.db")
    if not dbs:
        pytest.skip("No validation DB present")
    db_path = dbs[0]
    mgr = WorkOrderManager(db_path)
    audit = mgr.audit_run_work_orders("crawl_20260928_152046")

    assert audit["total_work_orders"] == 1079
    assert audit["valid_count"] == 1079
    assert audit["failed_count"] == 0
    assert audit["failed_reasons"] == []
    assert audit["by_type"] == {"content": 851, "engineering": 228}
    assert audit["by_priority"] == {"P2": 1079}
    assert audit["baseline_verifications"]["FAILED"] == 443
    assert audit["baseline_verifications"]["PASSED"] == 636
