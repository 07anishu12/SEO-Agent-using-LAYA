"""
Opportunities Router: Real-data Exploration, ICE Factors, and Feedback Persistence.
"""
from uuid import uuid4
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from database.connection import get_connection
from database.scoped_query import ScopedQuery
from ..auth import get_current_user, require_editor_or_admin

router = APIRouter(tags=["opportunities"])


class FeedbackRequest(BaseModel):
    verdict: str  # "fixed", "false_positive", "accepted", "wont_fix"
    note: Optional[str] = None


class OpportunityResponse(BaseModel):
    id: str
    org_id: str
    run_id: str
    site_id: str
    fingerprint: str
    display_id: str
    type: Optional[str] = None
    tier: Optional[str] = None
    confidence: Optional[str] = None
    effort: Optional[str] = None
    priority_score: Optional[float] = None
    factors_json: Optional[Dict[str, Any]] = None
    evidence_refs: Optional[List[Any]] = None
    observation: Optional[str] = None
    diagnosis: Optional[str] = None
    hypothesis: Optional[str] = None
    action: Optional[str] = None
    implementation_location: Optional[str] = None
    affected_templates: Optional[List[Any]] = None
    affected_urls_count: int = 0
    sample_urls: Optional[List[str]] = None
    verification_spec: Optional[str] = None
    feedback: Optional[str] = None
    created_at: Optional[datetime] = None


@router.get("/runs/{run_id}/opportunities", response_model=List[OpportunityResponse])
def list_run_opportunities(
    run_id: str,
    tier: Optional[str] = Query(None, description="Filter by tier (e.g. tier1, tier2, tier3)"),
    confidence: Optional[str] = Query(None, description="Filter by confidence (e.g. high, medium, low)"),
    type: Optional[str] = Query(None, description="Filter by defect type"),
    search: Optional[str] = Query(None, description="Search by title/action/display_id"),
    sort_by: str = Query("priority_score", description="Sort field: priority_score, tier, effort"),
    order: str = Query("desc", description="Sort direction: asc or desc"),
    current_user: dict = Depends(get_current_user)
):
    """
    Lists opportunities for a specific run, strictly scoped by org_id,
    with attached latest user feedback and ICE factor metadata.
    """
    org_id = current_user["org_id"]

    # Verify run exists and belongs to org
    with ScopedQuery(org_id=org_id) as sq:
        run = sq.fetch_one("runs", where="id = %(id)s", params={"id": run_id})
    if not run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")

    # Allowed sorting fields
    allowed_sorts = {
        "priority_score": "o.priority_score",
        "tier": "o.tier",
        "effort": "o.effort",
        "display_id": "o.display_id"
    }
    sort_column = allowed_sorts.get(sort_by, "o.priority_score")
    sort_dir = "ASC" if order.lower() == "asc" else "DESC"

    query = f"""
        SELECT 
            o.id, o.org_id, o.run_id, o.site_id, o.fingerprint, o.display_id,
            o.type, o.tier, o.confidence, o.effort, o.priority_score,
            o.factors_json, o.evidence_refs, o.observation, o.diagnosis,
            o.hypothesis, o.action, o.implementation_location,
            o.affected_templates, o.affected_urls_count, o.sample_urls,
            o.verification_spec, o.created_at,
            (
                SELECT f.verdict 
                FROM feedback f 
                WHERE f.finding_fingerprint = o.fingerprint 
                  AND f.org_id = o.org_id 
                ORDER BY f.created_at DESC 
                LIMIT 1
            ) as feedback
        FROM opportunities o
        WHERE o.org_id = %(org_id)s AND o.run_id = %(run_id)s
    """
    params: Dict[str, Any] = {"org_id": org_id, "run_id": run_id}

    if tier:
        query += " AND LOWER(o.tier) = LOWER(%(tier)s)"
        params["tier"] = tier
    if confidence:
        query += " AND LOWER(o.confidence) = LOWER(%(confidence)s)"
        params["confidence"] = confidence
    if type:
        query += " AND LOWER(o.type) = LOWER(%(type)s)"
        params["type"] = type
    if search:
        query += """ AND (
            o.display_id ILIKE %(search)s 
            OR o.action ILIKE %(search)s 
            OR o.diagnosis ILIKE %(search)s
            OR o.observation ILIKE %(search)s
        )"""
        params["search"] = f"%{search}%"

    query += f" ORDER BY {sort_column} {sort_dir} NULLS LAST, o.display_id ASC"

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, params)
            rows = cur.fetchall()

    return [OpportunityResponse(**r) for r in rows]


@router.get("/opportunities/{id}", response_model=OpportunityResponse)
def get_opportunity(
    id: str,
    current_user: dict = Depends(get_current_user)
):
    """Fetches a single opportunity by ID or display_id, scoped to org_id."""
    org_id = current_user["org_id"]
    query = """
        SELECT 
            o.id, o.org_id, o.run_id, o.site_id, o.fingerprint, o.display_id,
            o.type, o.tier, o.confidence, o.effort, o.priority_score,
            o.factors_json, o.evidence_refs, o.observation, o.diagnosis,
            o.hypothesis, o.action, o.implementation_location,
            o.affected_templates, o.affected_urls_count, o.sample_urls,
            o.verification_spec, o.created_at,
            (
                SELECT f.verdict 
                FROM feedback f 
                WHERE f.finding_fingerprint = o.fingerprint 
                  AND f.org_id = o.org_id 
                ORDER BY f.created_at DESC 
                LIMIT 1
            ) as feedback
        FROM opportunities o
        WHERE o.org_id = %(org_id)s AND (o.id = %(id)s OR o.display_id = %(id)s)
        LIMIT 1
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, {"org_id": org_id, "id": id})
            row = cur.fetchone()

    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Opportunity not found")

    return OpportunityResponse(**row)


@router.post("/opportunities/{id}/feedback")
def submit_opportunity_feedback(
    id: str,
    req: FeedbackRequest,
    current_user: dict = Depends(require_editor_or_admin)
):
    """
    Persists feedback (fixed, false_positive, accepted, wont_fix) for an opportunity.
    Ties the feedback to the opportunity's fingerprint and org_id.
    """
    org_id = current_user["org_id"]
    user_id = current_user.get("user_id")

    valid_verdicts = {"fixed", "false_positive", "accepted", "wont_fix"}
    verdict = req.verdict.strip().lower()
    if verdict not in valid_verdicts:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid verdict. Must be one of: {', '.join(sorted(valid_verdicts))}"
        )

    # Fetch opportunity fingerprint
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, fingerprint, display_id 
                FROM opportunities 
                WHERE org_id = %s AND (id = %s OR display_id = %s)
                LIMIT 1
                """,
                (org_id, id, id)
            )
            opp = cur.fetchone()
            if not opp:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Opportunity not found")

            fingerprint = opp["fingerprint"]
            feedback_id = f"fb_{uuid4().hex[:16]}"

            cur.execute(
                """
                INSERT INTO feedback (id, org_id, finding_fingerprint, verdict, user_id, note)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (feedback_id, org_id, fingerprint, verdict, user_id, req.note)
            )
        conn.commit()

    return {
        "success": True,
        "opportunity_id": opp["id"],
        "display_id": opp["display_id"],
        "fingerprint": opp["fingerprint"],
        "verdict": verdict,
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
