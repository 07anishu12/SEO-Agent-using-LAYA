import json
import sqlite3
import pytest
from crawler.migrations import MigrationRunner
from crawler.storage import CrawlStorage
from engine.id_system import IDSystem
from laya.candidates import build_candidates, candidate_key, opportunity_candidate_key
from laya.decision import LayaCandidateInput, LayaDecision
from laya.worker_pool import LayaCacheError, LayaWorkerPool


def test_key_round_trip_and_cluster_membership():
    cluster = {"cluster_id": "cluster_missing_title", "issue": "missing_title", "primary_affected_template": "product", "affected_urls_count": 2, "sample_urls": ["https://example.com/a"]}
    member = {"opportunity_id": "OPP-1", "fingerprint": IDSystem.generate_fingerprint(cluster["cluster_id"], "product", "template-aggregate"), "type": "TPL", "affected_templates_json": '["product"]', "action": "fix title"}
    other = {"opportunity_id": "OPP-2", "type": "AEO", "action": "test|" + "x"*100, "observation": "Missing answer section", "sample_urls_json": "[]", "implementation_location": "product"}
    candidates, members = build_candidates([cluster], [], [member, other])
    assert opportunity_candidate_key(member, members) == candidate_key(cluster_id=cluster["cluster_id"])
    assert opportunity_candidate_key(other, members) == candidate_key(other)
    assert set(candidates) == {opportunity_candidate_key(o, members) for o in [member, other]}
    assert candidate_key(other) != candidate_key({**other, "action": other["action"]+"different"})


@pytest.mark.asyncio
@pytest.mark.mlx
async def test_real_worker_durable_cache_and_completion(tmp_path):
    db = str(tmp_path / "cache.db")
    CrawlStorage(db)
    MigrationRunner(db).run_migrations()
    candidate = LayaCandidateInput(cluster_id="fixture:missing_title", issue_type="missing title on HTTP 200 indexable page", page_count=1, status_distribution={"200": 1})
    first = LayaWorkerPool(cache_db_path=db, num_workers=1)
    await first.start()
    await first.submit_candidate(candidate, "run-first")
    decisions = await first.finish()
    await first.stop()
    assert len(decisions) == first.total_candidates == first.total_decisions == 1
    assert first.total_errors == first.persist_failures == 0
    first._analyzer.reset_metrics_for_test()  # Prove SQLite reuse without memory cache.
    second = LayaWorkerPool(cache_db_path=db, num_workers=1)
    await second.start()
    await second.submit_candidate(candidate, "run-second")
    cached = await second.finish()
    await second.stop()
    assert second.total_cache_hits == 1 and second.total_cache_misses == 0
    assert second._analyzer.inference_calls == 0
    assert cached[0].run_id == "run-second"
    assert cached[0].decision_id == decisions[0].decision_id
    with sqlite3.connect(db) as conn:
        conn.execute("UPDATE laya_decision_log SET checkpoint_id='another-checkpoint'")
    assert second._load_cached_decision(candidate.compute_hash(second._analyzer.backend.checkpoint_id)) is None
    with sqlite3.connect(db) as conn:
        conn.execute("DROP TABLE laya_decision_log")
    with pytest.raises(LayaCacheError):
        second._persist_decision(decisions[0])
    assert second.persist_failures == 1
    with pytest.raises(LayaCacheError):
        second._load_cached_decision(candidate.compute_hash(second._analyzer.backend.checkpoint_id))
    assert second.cache_read_failures == 1


@pytest.mark.asyncio
@pytest.mark.mlx
async def test_worker_error_is_counted_and_fails_pass():
    def failed_callback(decision):
        raise RuntimeError("intentional callback failure")
    pool = LayaWorkerPool(num_workers=1, decision_callback=failed_callback)
    await pool.start()
    await pool.submit_candidate(LayaCandidateInput(cluster_id="callback-test", issue_type="missing title"), "test")
    try:
        with pytest.raises(RuntimeError, match="completion/error"):
            await pool.finish()
        assert pool.total_errors == 1
        assert "intentional callback failure" in pool.recent_errors[-1]
    finally:
        await pool.stop(abort=True)
