"""
Tests for SEOJEVPipeline library wrapper and cooperative cancellation.
"""

import asyncio
import os
import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from engine.pipeline import SEOJEVPipeline, PipelineCancelledException


def test_pipeline_initialization():
    pipe = SEOJEVPipeline(
        target_url="example.com",
        options={"max_pages": 100, "concurrency": 5}
    )
    assert pipe.target_url == "https://example.com"
    assert pipe.crawl_id.startswith("crawl_")
    assert pipe.options["max_pages"] == 100


def test_pipeline_progress_callback():
    events = []

    def mock_cb(pass_name: str, pct: float, msg: str, meta=None):
        events.append((pass_name, pct, msg))

    pipe = SEOJEVPipeline(
        target_url="https://example.com",
        progress_callback=mock_cb
    )
    pipe.emit_progress("P1_CRAWL", 10.0, "Testing progress", {"test": True})

    assert len(events) == 1
    assert events[0] == ("P1_CRAWL", 10.0, "Testing progress")


def test_pipeline_cooperative_cancellation():
    cancelled = True

    def check_cancel():
        return cancelled

    pipe = SEOJEVPipeline(
        target_url="https://example.com",
        cancel_check=check_cancel
    )

    with pytest.raises(PipelineCancelledException):
        pipe.check_cancelled()


@pytest.mark.asyncio
async def test_pipeline_run_all_cancellation():
    cancelled = False

    def check_cancel():
        return cancelled

    pipe = SEOJEVPipeline(
        target_url="https://example.com",
        cancel_check=check_cancel
    )

    # Cancel immediately on pass 1
    with patch.object(pipe, "run_pass_1_crawl", side_effect=PipelineCancelledException("Cancelled early")):
        result = await pipe.run_all()
        assert result["status"] == "cancelled"
        assert "Cancelled early" in result["reason"]
