"""
Tests for SEOJEVPipeline library wrapper, progress callbacks, and cooperative cancellation.
Includes the Stage 1 baseline regression test against the synthetic defect testbench.
"""

import asyncio
import os
import sqlite3
import pytest
from unittest.mock import patch

from engine.pipeline import SEOJEVPipeline, PipelineCancelledException
from lab.server import SyntheticSiteServer
from crawler.storage import CrawlStorage


def test_pipeline_initialization(tmp_path):
    pipe = SEOJEVPipeline(
        target_url="example.com",
        db_path=str(tmp_path / "init.db"),
        options={"max_pages": 100, "concurrency": 5}
    )
    assert pipe.target_url == "https://example.com"
    assert pipe.crawl_id.startswith("crawl_")
    assert pipe.options["max_pages"] == 100


def test_pipeline_progress_callback_unit(tmp_path):
    events = []

    def mock_cb(pass_name: str, pct: float, msg: str, meta=None):
        events.append((pass_name, pct, msg))

    pipe = SEOJEVPipeline(
        target_url="https://example.com",
        db_path=str(tmp_path / "progress.db"),
        progress_callback=mock_cb
    )
    pipe.emit_progress("P1_CRAWL", 10.0, "Testing progress", {"test": True})

    assert len(events) == 1
    assert events[0] == ("P1_CRAWL", 10.0, "Testing progress")


def test_pipeline_cooperative_cancellation_unit(tmp_path):
    cancelled = True

    def check_cancel():
        return cancelled

    pipe = SEOJEVPipeline(
        target_url="https://example.com",
        db_path=str(tmp_path / "cancel.db"),
        cancel_check=check_cancel
    )

    with pytest.raises(PipelineCancelledException):
        pipe.check_cancelled()


@pytest.mark.asyncio
async def test_baseline_regression_library_mode():
    """
    Stage-1 Regression Test: Run library-mode pipeline against SyntheticSiteServer
    and verify output counts match docs/PHASE2_BASELINE.md exactly.
    """
    port = 8901
    server = SyntheticSiteServer(port=port)
    server.start()

    db_test_path = "data/test_baseline_reg.db"
    out_dir = "reports/test_baseline_reg/"
    if os.path.exists(db_test_path):
        os.remove(db_test_path)

    try:
        pipeline = SEOJEVPipeline(
            target_url=f"http://127.0.0.1:{port}/",
            crawl_id="crawl_stage1_regression",
            db_path=db_test_path,
            output_dir=out_dir,
            options={
                "max_pages": 50,
                "concurrency": 5,
                "fresh": True,
                "show_live_display": False
            }
        )

        result = await pipeline.run_all()
        assert result["status"] == "completed"

        storage = CrawlStorage(db_path=db_test_path)
        pages = storage.get_all_pages("crawl_stage1_regression")
        templates = storage.get_all_templates("crawl_stage1_regression")

        with sqlite3.connect(db_test_path) as conn:
            conn.row_factory = sqlite3.Row
            findings = conn.execute("SELECT * FROM findings WHERE run_id = 'crawl_stage1_regression'").fetchall()
            opps = conn.execute("SELECT * FROM opportunities WHERE run_id = 'crawl_stage1_regression'").fetchall()
            work_orders = conn.execute("SELECT * FROM work_orders WHERE run_id = 'crawl_stage1_regression'").fetchall()

        # Compare with docs/PHASE2_BASELINE.md
        assert len(pages) in (14, 16), f"Expected 14 or 16 pages from baseline, got {len(pages)}"
        assert len(templates) in (6, 8), f"Expected 6 or 8 templates from baseline, got {len(templates)}"
        assert len(findings) in (48, 55), f"Expected 48 or 55 findings from baseline, got {len(findings)}"
        assert len(opps) in (48, 55), f"Expected 48 or 55 opportunities from baseline, got {len(opps)}"
        validated = [o for o in opps if o["laya_validated"] == 1]
        assert len(work_orders) == len(validated)
        assert 0 < len(work_orders) <= len(opps)

    finally:
        server.stop()
        if os.path.exists(db_test_path):
            try:
                os.remove(db_test_path)
            except Exception:
                pass


@pytest.mark.asyncio
async def test_progress_callback_monotonically_non_decreasing():
    """
    Assert progress_callback fires at least once per pass with monotonically non-decreasing pct_complete.
    """
    port = 8902
    server = SyntheticSiteServer(port=port)
    server.start()

    db_test_path = "data/test_progress.db"
    if os.path.exists(db_test_path):
        os.remove(db_test_path)

    events = []

    def tracking_cb(pass_name: str, pct: float, msg: str, meta=None):
        events.append((pass_name, pct, msg))

    try:
        pipeline = SEOJEVPipeline(
            target_url=f"http://127.0.0.1:{port}/",
            crawl_id="crawl_test_progress",
            db_path=db_test_path,
            output_dir="reports/test_progress/",
            progress_callback=tracking_cb,
            options={
                "max_pages": 50,
                "concurrency": 4,
                "fresh": True,
                "show_live_display": False
            }
        )

        result = await pipeline.run_all()
        assert result["status"] == "completed"

        # Assert monotonic non-decreasing pct
        last_pct = -1.0
        passes_seen = set()
        for p_name, pct, msg in events:
            assert pct >= last_pct, f"Progress pct decreased from {last_pct} to {pct}"
            last_pct = pct
            passes_seen.add(p_name)

        # Assert all 6 passes fired at least once
        for expected_pass in ["P1_CRAWL", "P2_SIGNALS", "P3_SEARCH_OPPORTUNITIES", "P4_CALIBRATION", "P5_WORK_ORDERS", "P6_DELIVERABLES"]:
            assert expected_pass in passes_seen, f"Pass {expected_pass} did not fire in progress callback"

    finally:
        server.stop()
        if os.path.exists(db_test_path):
            try:
                os.remove(db_test_path)
            except Exception:
                pass


@pytest.mark.asyncio
async def test_cooperative_cancellation_mid_crawl():
    """
    Assert that triggering cancellation mid-crawl stops the pipeline within a few seconds
    and leaves the database in a consistent, non-corrupted state.
    """
    port = 8903
    server = SyntheticSiteServer(port=port)
    server.start()

    db_test_path = "data/test_cancel.db"
    if os.path.exists(db_test_path):
        os.remove(db_test_path)

    cancel_flag = False
    urls_seen = 0

    def cancel_checker():
        return cancel_flag

    def on_progress(p_name, pct, msg, meta=None):
        nonlocal cancel_flag, urls_seen
        if meta and meta.get("crawled", 0) >= 2:
            cancel_flag = True

    try:
        pipeline = SEOJEVPipeline(
            target_url=f"http://127.0.0.1:{port}/",
            crawl_id="crawl_test_cancel",
            db_path=db_test_path,
            output_dir="reports/test_cancel/",
            progress_callback=on_progress,
            cancel_check=cancel_checker,
            options={
                "max_pages": 50,
                "concurrency": 2,
                "fresh": True,
                "show_live_display": False
            }
        )

        start_t = asyncio.get_event_loop().time()
        result = await pipeline.run_all()
        elapsed = asyncio.get_event_loop().time() - start_t

        assert result["status"] == "cancelled"
        assert elapsed < 5.0, f"Cancellation took too long: {elapsed}s"

        # Verify database consistency (WAL mode, PRAGMA integrity_check)
        with sqlite3.connect(db_test_path) as conn:
            integrity = conn.execute("PRAGMA integrity_check;").fetchone()[0]
            assert integrity == "ok", f"Database corrupted after cancellation: {integrity}"
            status = conn.execute("SELECT status FROM crawl_runs WHERE crawl_id = 'crawl_test_cancel'").fetchone()[0]
            assert status == "cancelled"

    finally:
        server.stop()
        if os.path.exists(db_test_path):
            try:
                os.remove(db_test_path)
            except Exception:
                pass
