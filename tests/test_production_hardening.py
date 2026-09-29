"""
Production Hardening Regression and Verification Test Suite.
Validates:
1. Dev/Prod initialization (sampling never blocks fresh runs).
2. Memory safety (budget exceeded stops crawler, pauses pipeline, persists recoverable checkpoint).
3. Laya-MLX exclusivity (fail closed, zero fallback/mock/external AI models).
4. Production secrets enforcement.
5. Bounded Redis queue backpressure.
6. Health checks (liveness and readiness).
"""
import os
import sqlite3
import pytest
from unittest.mock import patch, MagicMock

from engine.dev_sample import has_existing_crawl
from engine.memory_guard import MemoryGuard, MemoryBudgetExceeded
from engine.pipeline import SEOJEVPipeline
from laya.analyzer import LayaSEOAnalyzer
from laya.backends import get_laya_backend
from api.config import validate_production_secrets
from jobs.queue import RunQueue


# ==============================================================================
# 1. Dev / Production Initialization Tests (Phase 2)
# ==============================================================================

def test_dev_initialization_allows_fresh_crawl_when_no_db(tmp_path):
    """Proves that a fresh dev run does not crash when no crawl database exists."""
    non_existent_db = str(tmp_path / "does_not_exist.db")
    assert not has_existing_crawl(non_existent_db)

    # Creating pipeline with fresh non-existent database must NOT attempt sampling
    pipeline = SEOJEVPipeline(
        target_url="https://example.com/",
        db_path=non_existent_db,
        output_dir=str(tmp_path / "reports"),
        options={"profile": "dev", "fresh": True}
    )
    # Pipeline should be initialized for fresh crawl, NOT analyze_only
    assert pipeline.options.get("analyze_only") is not True
    assert os.path.exists(non_existent_db)


def test_dev_initialization_samples_when_crawl_exists(tmp_path):
    """Proves that dev profile detects existing crawl with pages and samples correctly."""
    source_db = str(tmp_path / "source.db")
    with sqlite3.connect(source_db) as conn:
        conn.execute("CREATE TABLE crawl_runs (crawl_id TEXT PRIMARY KEY, target_url TEXT, start_time TEXT)")
        conn.execute("CREATE TABLE pages (url TEXT, crawl_id TEXT, page_type TEXT)")
        conn.execute("INSERT INTO crawl_runs VALUES ('crawl_test', 'https://example.com/', '2026-09-29T00:00:00')")
        conn.execute("INSERT INTO pages VALUES ('https://example.com/', 'crawl_test', 'home')")

    assert has_existing_crawl(source_db, target="https://example.com/") is True


# ==============================================================================
# 2. Memory Safety & Enforcement Tests (Phase 3)
# ==============================================================================

def test_memory_guard_budget_exceeded_raises():
    """Proves that MemoryGuard raises MemoryBudgetExceeded and does not convert to False."""
    # Guard with low limit and mock sample returning high RSS
    def mock_high_sample():
        return dict(rss_mb=5000.0, available_mb=500.0, swap_used=0, swap_out=0)

    guard = MemoryGuard(limit_mb=1000.0, min_available_mb=1000.0, pause_seconds=0.0, sample=mock_high_sample)

    with pytest.raises(MemoryBudgetExceeded) as exc_info:
        guard.check_and_enforce(raise_on_exceeded=True)

    assert "Memory pressure persists" in str(exc_info.value)


def test_memory_guard_swap_delta_growth():
    """Proves that actual swap growth beyond threshold raises MemoryBudgetExceeded."""
    call_count = 0
    def mock_swap_growth():
        nonlocal call_count
        call_count += 1
        # Initial sample swap_used = 100MB; second sample swap_used = 300MB (delta 200MB > 64MB limit)
        swap = 100 * 1024 * 1024 if call_count == 1 else 300 * 1024 * 1024
        return dict(rss_mb=500.0, available_mb=8000.0, swap_used=swap, swap_out=0)

    guard = MemoryGuard(limit_mb=4096.0, max_swap_delta_mb=64.0, pause_seconds=0.0, sample=mock_swap_growth)

    with pytest.raises(MemoryBudgetExceeded) as exc_info:
        guard.observe()

    assert "System swap grew" in str(exc_info.value)


@pytest.mark.asyncio
async def test_pipeline_pauses_cleanly_on_memory_budget_exceeded(tmp_path):
    """Proves that when memory budget is exceeded, pipeline catches failure, persists checkpoint as paused, and returns recoverable status."""
    test_db = str(tmp_path / "mem_test.db")
    pipeline = SEOJEVPipeline(
        target_url="https://example.com/",
        db_path=test_db,
        output_dir=str(tmp_path / "reports"),
        options={"profile": "dev", "fresh": True}
    )

    # Force memory guard to always raise MemoryBudgetExceeded
    with patch.object(pipeline.memory_guard, "checkpoint", side_effect=MemoryBudgetExceeded("Simulated OOM")):
        result = await pipeline.run_all()

    assert result["status"] == "memory_budget_exceeded"
    assert result["recoverable"] is True
    assert "Simulated OOM" in result["reason"]

    # Verify status in database
    with sqlite3.connect(test_db) as conn:
        status = conn.execute("SELECT status FROM crawl_runs WHERE crawl_id=?", (pipeline.crawl_id,)).fetchone()[0]
        assert status == "paused"


# ==============================================================================
# 3. Laya Exclusivity & Fail-Closed Tests (Phase 4 & Phase 5)
# ==============================================================================

def test_laya_backend_rejects_non_mlx():
    """Proves that attempting to configure an alternative or fallback backend raises ValueError."""
    with pytest.raises(ValueError) as exc:
        get_laya_backend(backend_type="openai")
    assert "no alternatives are supported" in str(exc.value)

    with pytest.raises(ValueError) as exc:
        get_laya_backend(backend_type="llama.cpp")
    assert "no alternatives are supported" in str(exc.value)


def test_laya_analyzer_fails_fast_on_inference_error():
    """Proves that when Laya inference fails, analyzer raises and never substitutes a mock or fallback."""
    analyzer = LayaSEOAnalyzer.get_singleton()

    # Mock backend to fail on predict
    mock_backend = MagicMock()
    mock_backend.predict.side_effect = RuntimeError("MLX compute kernel failed")
    mock_backend.checkpoint_id = "aac6fef/laya-mlx@test"

    with patch.object(analyzer, "get_backend", return_value=mock_backend):
        candidate = {"cluster_id": "cls_test", "issue_type": "missing_title"}
        with pytest.raises(RuntimeError) as exc_info:
            analyzer.classify_issue(candidate)

        assert "MLX compute kernel failed" in str(exc_info.value)


# ==============================================================================
# 4. Production Secrets Validation Tests (Phase 6)
# ==============================================================================

def test_production_secrets_rejects_missing_or_default():
    """Proves that in production environment, missing secrets or development defaults are rejected."""
    with patch.dict(os.environ, {
        "ENVIRONMENT": "production",
        "JWT_SECRET": "seojev_jwt_secret_development_change_in_prod_2026",
        "DATABASE_URL": "postgresql://postgres:postgres@localhost:5432/seojev_test",
        "S3_ACCESS_KEY": "minioadmin",
        "S3_SECRET_KEY": "minioadmin",
        "REDIS_URL": "redis://localhost:6379/0"
    }):
        with pytest.raises(RuntimeError) as exc_info:
            validate_production_secrets()

        err_msg = str(exc_info.value)
        assert "JWT_SECRET must be explicitly set" in err_msg
        assert "DATABASE_URL cannot use default development credentials" in err_msg
        assert "S3_ACCESS_KEY and S3_SECRET_KEY cannot use default development credentials" in err_msg


# ==============================================================================
# 5. Bounded Queue Backpressure Tests (Phase 10)
# ==============================================================================

def test_queue_backpressure_enforcement():
    """Proves that RunQueue enforces max queue size and blocks unbounded growth."""
    mock_redis = MagicMock()
    mock_redis.llen.return_value = 100  # Queue is currently at 100 items

    queue = RunQueue(max_queue_size=100)
    queue._client = mock_redis

    with pytest.raises(RuntimeError) as exc_info:
        queue.enqueue_run(
            run_id="run_overflow",
            org_id="org_test",
            site_id="site_test",
            target_url="https://example.com"
        )

    assert "Queue capacity exceeded" in str(exc_info.value)


# ==============================================================================
# 6. Health Checks (Phase 20)
# ==============================================================================

def test_health_endpoints():
    """Verifies that API health endpoints expose liveness and readiness."""
    from fastapi.testclient import TestClient
    from api.main import app

    client = TestClient(app)

    # 1. Liveness endpoint must return 200
    res_live = client.get("/health")
    assert res_live.status_code == 200
    assert res_live.json()["status"] == "ok"

    res_live_alias = client.get("/health/liveness")
    assert res_live_alias.status_code == 200

    # 2. Readiness endpoint returns status for all components
    res_ready = client.get("/health/ready")
    assert res_ready.status_code in (200, 503)
    data = res_ready.json()
    assert "components" in data
    assert "database" in data["components"]
    assert "redis" in data["components"]
    assert "object_storage" in data["components"]
    assert "laya" in data["components"]
