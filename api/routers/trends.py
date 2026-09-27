"""
SEOJEV Stage 10a Trends Router:
Serves historical time-series metrics (issue_count, opportunity_count) for a site.
Strictly scoped to current_user["org_id"].
"""
from datetime import date
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status

from database.scoped_query import ScopedQuery
from services.trends import get_site_trends
from ..auth import get_current_user
from ..schemas import SiteTrendsResponse

router = APIRouter(prefix="/sites/{id}/trends", tags=["trends"])


def _verify_site_access(site_id: str, org_id: str):
    with ScopedQuery(org_id=org_id) as sq:
        site = sq.fetch_one("sites", where="id = %(id)s", params={"id": site_id})
    if not site:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Site not found")
    return site


@router.get("", response_model=SiteTrendsResponse)
def get_trends(
    id: str,
    metric: Optional[str] = Query(None, description="Filter by metric: issue_count, opportunity_count"),
    start_date: Optional[date] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="End date (YYYY-MM-DD)"),
    current_user: dict = Depends(get_current_user)
):
    org_id = current_user["org_id"]
    _verify_site_access(id, org_id)

    trends_data = get_site_trends(
        org_id=org_id,
        site_id=id,
        metric=metric,
        start_date=start_date,
        end_date=end_date
    )

    return SiteTrendsResponse(site_id=id, trends=trends_data)
