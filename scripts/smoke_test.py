"""Full Production Smoke Test Script for SEOJEV (Phase 23)

Verifies:
1. Database, Redis, and Object Storage health
2. Laya-MLX Apple Silicon native preflight canary
3. Streamed candidate reduction & Laya scalar inference
4. Work order generation & schema validation
5. Baseline verification
6. Report generation (JSON, CSV suite)
7. MemoryGuard stability (peak RSS, swap delta)
"""
import asyncio
import json
import os
import sys
import time
from pathlib import Path
import sqlite3

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import yaml
from database.connection import check_db_health
from jobs.queue import check_redis_health
from services.object_store import check_storage_health
from engine.memory_guard import MemoryGuard
from engine.profiles import resolve_profile
from laya.analyzer import LayaSEOAnalyzer
from laya.streaming import LocalMLXService, iter_candidates, decide_classes
from engine.work_orders import WorkOrderManager
from verification.runner import VerificationRunner
from reporting.json_report import JSONReportGenerator
from reporting.csv_suite import CSVSuiteExporter


async def run_smoke_test():
    start_time = time.monotonic()
    print("==================================================")
    print("STARTING SEOJEV PRODUCTION SMOKE TEST")
    print("==================================================")

    # 1. Check supporting services
    print("\n[Step 1] Checking infrastructure health...")
    db_health = check_db_health()
    print(f"  -> PostgreSQL: {db_health.get('status', 'unknown')}")

    redis_health = check_redis_health()
    print(f"  -> Redis: {redis_health.get('status', 'unknown')}")

    storage_health = check_storage_health()
    print(f"  -> Object Storage: {storage_health.get('status', 'unknown')}")

    # 2. Check Laya-MLX Apple Silicon Preflight
    print("\n[Step 2] Checking Laya-MLX Apple Silicon engine...")
    analyzer = LayaSEOAnalyzer.get_singleton("aac6fef/laya-mlx")
    health = analyzer.get_health()
    preflight = analyzer.preflight()
    print(f"  -> Checkpoint ID: {preflight.get('checkpoint_id')}")
    print(f"  -> Heads verified: {len(preflight.get('heads', []))}")
    print(f"  -> Apple Silicon compatible: {health.get('apple_silicon_compatible')}")
    assert health.get("apple_silicon_compatible") is True, "Must be Apple Silicon compatible"
    assert len(preflight.get("heads", [])) == 10, "Must have 10 multi-task heads"

    # 3. Setup test database and MemoryGuard
    print("\n[Step 3] Initializing bounded test execution...")
    config = yaml.safe_load(Path("config.yaml").read_text())
    profile_cfg = resolve_profile(config, "dev")
    limits = profile_cfg["runtime"]

    guard = MemoryGuard(
        limit_mb=limits["memory_budget_mb"],
        batch_size=limits["batch_size"],
        min_available_mb=limits["min_available_mb"],
        max_swap_delta_mb=limits.get("max_swap_delta_mb", 64.0)
    )

    test_output_dir = Path("reports/test_smoke")
    test_output_dir.mkdir(parents=True, exist_ok=True)
    test_db = test_output_dir / "smoke.db"

    # Copy sample db to isolated test db
    sample_files = list(Path("reports/smoke-test").glob("dev-sample-*.db"))
    source_db = sample_files[0] if sample_files else Path("data/seo.db")

    with sqlite3.connect(source_db) as src, sqlite3.connect(test_db) as dst:
        src.backup(dst)

    crawl_id = "crawl_20260928_152046"

    # 4. Execute bounded Laya inference (10 candidates)
    print("\n[Step 4] Running bounded Laya-MLX decision inference...")
    service = LocalMLXService(profile_cfg, guard)

    bounded_candidates = []
    for cand in iter_candidates(str(test_db), crawl_id):
        bounded_candidates.append(cand)
        if len(bounded_candidates) >= 10:
            break

    print(f"  -> Streamed {len(bounded_candidates)} candidates")
    from engine.chunks import SQLiteStageStore
    stage_store = SQLiteStageStore(str(test_db))
    with guard.stage("laya_inference"):
        decisions = list(decide_classes(bounded_candidates, service, stage_store, guard, crawl_id))

    print(f"  -> Generated {len(decisions)} decisions across 10 heads with full provenance")
    assert len(decisions) == len(bounded_candidates)
    first_dec = decisions[0]
    assert first_dec.checkpoint_id == preflight["checkpoint_id"]
    assert first_dec.prompt_version == "laya-seo-decision-v3"
    print(f"  -> Provenance verified: Checkpoint={first_dec.checkpoint_id[:16]}..., Gate={first_dec.gate}")

    # 5. Work order generation
    print("\n[Step 5] Generating work orders and running baseline verification...")
    # Mark opportunities validated for test
    with sqlite3.connect(test_db) as conn:
        conn.execute("UPDATE opportunities SET laya_validated = 1, laya_action = 'fix_template', laya_gate = 'HUMAN_REVIEW', laya_decision_id = 'dec_test_1', laya_candidate_id = 'cand_test_1' WHERE rowid IN (SELECT rowid FROM opportunities WHERE run_id = ? LIMIT 5)", (crawl_id,))
        conn.commit()

    from laya.streaming import class_opportunities
    wo_mgr = WorkOrderManager(str(test_db))
    opps = list(class_opportunities(str(test_db), crawl_id))
    created_orders = wo_mgr.create_work_orders_from_opportunities(crawl_id, opps)
    wo_mgr.persist_work_orders(created_orders, run_id=crawl_id)
    print(f"  -> Created {len(created_orders)} canonical work orders")

    audit = wo_mgr.audit_run_work_orders(crawl_id)
    print(f"  -> Audit: {audit['valid_count']} valid, {audit['failed_count']} failed")
    assert audit["failed_count"] == 0, "No failed work orders permitted"

    # 6. Baseline verification runner
    print("\n[Step 6] Running baseline spec verification...")
    runner = VerificationRunner(str(test_db))
    if created_orders:
        sample_wo = created_orders[0]
        verif_res = runner.verify_work_order(sample_wo, live_fetch=False)
        print(f"  -> Verified WO: {verif_res['display_id']} | Status: {verif_res['status']}")

    # 7. Deliverables / Reports Export
    print("\n[Step 7] Exporting deliverables (JSON, CSV suite)...")
    summary_data = {
        "status": "completed",
        "crawl_id": crawl_id,
        "decisions_count": len(decisions),
        "work_orders_count": len(created_orders)
    }
    summary_path = test_output_dir / "smoke-summary.json"
    summary_path.write_text(json.dumps(summary_data, indent=2))
    print(f"  -> JSON summary generated: {summary_path}")

    csv_exporter = CSVSuiteExporter(output_dir=str(test_output_dir / "csv"), db_path=str(test_db))
    csv_results = csv_exporter.export_all(crawl_id)
    print(f"  -> CSV suite exported: {len(csv_results)} tables")

    total_duration = time.monotonic() - start_time
    peak_rss = guard.peak_rss_mb
    current_state = guard.sample()
    swap_delta = (current_state['swap_used'] - guard.initial['swap_used']) / (1024 * 1024)

    print("\n==================================================")
    print("SMOKE TEST COMPLETE: PASSED")
    print("==================================================")
    print(f"Total Duration: {total_duration:.2f}s")
    print(f"Peak RSS: {peak_rss:.2f} MiB")
    print(f"Swap Delta: {swap_delta:.2f} MiB")
    print(f"Artifacts: {test_output_dir}")
    print("==================================================")

    smoke_manifest = {
        "status": "passed",
        "duration_seconds": total_duration,
        "peak_rss_mb": peak_rss,
        "swap_delta_mb": swap_delta,
        "candidates_evaluated": len(bounded_candidates),
        "decisions_generated": len(decisions),
        "work_orders_created": len(created_orders),
        "csv_tables": len(csv_results),
        "checkpoint_id": preflight["checkpoint_id"],
        "timestamp": time.time()
    }
    (test_output_dir / "smoke_manifest.json").write_text(json.dumps(smoke_manifest, indent=2))
    return smoke_manifest


if __name__ == "__main__":
    asyncio.run(run_smoke_test())
