"""
Snapshot Diff Router: Real Pre/Post Deployment Snapshot Comparisons,
Classification (Fixed, Regressed, New, Improved), and Template-Level Grouping.
"""
import json
import os
import sqlite3
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from database.connection import get_connection
from database.scoped_query import ScopedQuery
from verification.differ import SnapshotDiffer
from ..auth import get_current_user

router = APIRouter(tags=["snapshot-diff"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------
class SnapshotDiffItem(BaseModel):
    before_snapshot_id: str
    after_snapshot_id: str
    url: str
    template_id: str = "default"
    fingerprint: str
    category: str  # FIXED, REGRESSED, NEW_ISSUE, IMPROVED, STILL_FAILING, UNCHANGED
    details: Dict[str, Any] = {}


class SnapshotDiffSummary(BaseModel):
    FIXED: int = 0
    REGRESSED: int = 0
    IMPROVED: int = 0
    NEW_ISSUE: int = 0
    STILL_FAILING: int = 0
    UNCHANGED: int = 0


class CompareTarget(BaseModel):
    id: str
    site_id: str
    status: str
    created_at: Optional[datetime] = None


class SnapshotDiffResponse(BaseModel):
    before_run_id: str
    after_run_id: str
    total_urls_compared: int
    summary: SnapshotDiffSummary
    by_template: Dict[str, List[SnapshotDiffItem]] = {}
    by_category: Dict[str, List[SnapshotDiffItem]] = {}
    differences: List[SnapshotDiffItem] = []
    compare_targets: List[CompareTarget] = []


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _fetch_snapshots_for_run(run_id: str, org_id: str) -> List[Dict[str, Any]]:
    """Fetches snapshots from PostgreSQL ledger, with fallback to SQLite."""
    snapshots: List[Dict[str, Any]] = []

    # 1. Try PostgreSQL
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, url, snapshot_data
                    FROM snapshots
                    WHERE org_id = %s AND run_id = %s
                    ORDER BY url ASC
                    """,
                    (org_id, run_id)
                )
                rows = cur.fetchall()
                for r in rows:
                    data = r.get("snapshot_data")
                    d_dict = data if isinstance(data, dict) else (json.loads(data) if data else {})
                    d_dict["snapshot_id"] = r["id"]
                    d_dict["run_id"] = run_id
                    d_dict["url"] = r["url"]
                    snapshots.append(d_dict)
    except Exception:
        pass

    if snapshots:
        return snapshots

    # 2. Try SQLite
    candidate_dbs = [f"data/{run_id}.db", "data/seo.db"]
    for db_path in candidate_dbs:
        if os.path.exists(db_path):
            try:
                with sqlite3.connect(db_path) as s_conn:
                    s_conn.row_factory = sqlite3.Row
                    s_rows = s_conn.execute("SELECT * FROM snapshots WHERE run_id = ?", (run_id,)).fetchall()
                    for sr in s_rows:
                        item = dict(sr)
                        if "metrics_json" in item and item["metrics_json"]:
                            try:
                                item["metrics"] = json.loads(item["metrics_json"])
                            except Exception:
                                item["metrics"] = {}
                        snapshots.append(item)
                    if snapshots:
                        break
            except Exception:
                pass

    return snapshots


def _fetch_template_map(run_id: str, org_id: str) -> Dict[str, str]:
    """Builds a map of URL -> template_id using SQLite and Postgres."""
    t_map: Dict[str, str] = {}

    # 1. Check SQLite
    candidate_dbs = [f"data/{run_id}.db", "data/seo.db"]
    for db_path in candidate_dbs:
        if os.path.exists(db_path):
            try:
                with sqlite3.connect(db_path) as s_conn:
                    s_conn.row_factory = sqlite3.Row
                    # Try template_members
                    try:
                        tm_rows = s_conn.execute(
                            "SELECT url, template_id FROM template_members WHERE run_id = ?",
                            (run_id,)
                        ).fetchall()
                        for r in tm_rows:
                            t_map[r["url"]] = r["template_id"]
                    except Exception:
                        pass

                    # Fallback to pages
                    if not t_map:
                        try:
                            p_rows = s_conn.execute(
                                "SELECT url, template_id FROM pages WHERE crawl_id = ? AND template_id IS NOT NULL",
                                (run_id,)
                            ).fetchall()
                            for pr in p_rows:
                                t_map[pr["url"]] = pr["template_id"]
                        except Exception:
                            pass
                    if t_map:
                        break
            except Exception:
                pass

    # 2. Check findings in Postgres for any remaining URLs
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT url, template_id
                    FROM findings
                    WHERE org_id = %s AND run_id = %s AND template_id IS NOT NULL
                    """,
                    (org_id, run_id)
                )
                for r in cur.fetchall():
                    if r["url"] not in t_map:
                        t_map[r["url"]] = r["template_id"]
    except Exception:
        pass

    return t_map


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@router.get("/runs/{run_id}/compare-targets", response_model=List[CompareTarget])
def get_run_compare_targets(
    run_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Lists other completed runs for the same site available to compare with.
    """
    org_id = current_user["org_id"]
    with ScopedQuery(org_id=org_id) as sq:
        current_run = sq.fetch_one("runs", where="id = %(id)s", params={"id": run_id})
        if not current_run:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")

        site_id = current_run["site_id"]
        runs = sq.fetch_all(
            "runs",
            where="site_id = %(site_id)s AND id != %(run_id)s",
            params={"site_id": site_id, "run_id": run_id},
            order_by="created_at DESC"
        )

    return [
        CompareTarget(
            id=r["id"],
            site_id=r["site_id"],
            status=r["status"],
            created_at=r.get("created_at")
        )
        for r in runs
    ]


@router.get("/runs/{run_id}/diff", response_model=SnapshotDiffResponse)
def get_snapshot_diff(
    run_id: str,
    compare_run_id: Optional[str] = Query(None, description="Previous run ID to compare against"),
    current_user: dict = Depends(get_current_user)
):
    """
    Computes or retrieves snapshot diff between compare_run_id (before) and run_id (after).
    Uses the real SnapshotDiffer engine logic.
    Categorizes changes into FIXED, REGRESSED, NEW_ISSUE (New), IMPROVED.
    Groups changes by template.
    """
    org_id = current_user["org_id"]

    with ScopedQuery(org_id=org_id) as sq:
        current_run = sq.fetch_one("runs", where="id = %(id)s", params={"id": run_id})
        if not current_run:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")

        site_id = current_run["site_id"]

        # Find potential comparison runs for the site
        other_runs = sq.fetch_all(
            "runs",
            where="site_id = %(site_id)s AND id != %(run_id)s",
            params={"site_id": site_id, "run_id": run_id},
            order_by="created_at DESC"
        )

    compare_targets = [
        CompareTarget(
            id=r["id"],
            site_id=r["site_id"],
            status=r["status"],
            created_at=r.get("created_at")
        )
        for r in other_runs
    ]

    before_run_id = compare_run_id
    if not before_run_id:
        if other_runs:
            before_run_id = other_runs[0]["id"]
        else:
            # No baseline to compare against
            return SnapshotDiffResponse(
                before_run_id="",
                after_run_id=run_id,
                total_urls_compared=0,
                summary=SnapshotDiffSummary(),
                by_template={},
                by_category={},
                differences=[],
                compare_targets=compare_targets
            )

    # Verify compare run ownership
    with ScopedQuery(org_id=org_id) as sq:
        before_run = sq.fetch_one("runs", where="id = %(id)s", params={"id": before_run_id})
    if not before_run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Comparison run not found")

    # Fetch snapshots for both runs
    before_snapshots = _fetch_snapshots_for_run(before_run_id, org_id)
    after_snapshots = _fetch_snapshots_for_run(run_id, org_id)

    # Fetch template mapping
    template_map = _fetch_template_map(run_id, org_id)
    if not template_map:
        template_map = _fetch_template_map(before_run_id, org_id)

    # Run real engine diff
    differ = SnapshotDiffer()
    diff_data = differ.diff_runs(
        before_run_id=before_run_id,
        after_run_id=run_id,
        export_path=None,
        before_snapshots=before_snapshots,
        after_snapshots=after_snapshots,
        template_map=template_map
    )

    # Persist diff to PostgreSQL snapshot_diffs table
    diff_id = f"diff_{before_run_id[:8]}_{run_id[:8]}"
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO snapshot_diffs (
                        id, org_id, site_id, before_run_id, after_run_id, diff_summary_json
                    )
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (id) DO UPDATE SET
                        diff_summary_json = EXCLUDED.diff_summary_json;
                    """,
                    (
                        diff_id, org_id, site_id, before_run_id, run_id,
                        json.dumps(diff_data["summary"])
                    )
                )
            conn.commit()
    except Exception:
        pass

    summary_obj = SnapshotDiffSummary(**diff_data["summary"])

    by_template_obj: Dict[str, List[SnapshotDiffItem]] = {
        tpl: [SnapshotDiffItem(**item) for item in items]
        for tpl, items in diff_data.get("by_template", {}).items()
    }

    by_category_obj: Dict[str, List[SnapshotDiffItem]] = {
        cat: [SnapshotDiffItem(**item) for item in items]
        for cat, items in diff_data.get("by_category", {}).items()
    }

    diff_items = [SnapshotDiffItem(**item) for item in diff_data.get("differences", [])]

    return SnapshotDiffResponse(
        before_run_id=before_run_id,
        after_run_id=run_id,
        total_urls_compared=diff_data["total_urls_compared"],
        summary=summary_obj,
        by_template=by_template_obj,
        by_category=by_category_obj,
        differences=diff_items,
        compare_targets=compare_targets
    )
