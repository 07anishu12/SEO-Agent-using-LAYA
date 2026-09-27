"""
Sites CRUD Router: Scoped strictly to current_user's org_id.
"""
import hashlib
import urllib.parse
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from psycopg.types.json import Jsonb

from database.connection import get_connection
from database.scoped_query import ScopedQuery
from ..auth import get_current_user, require_admin, require_editor_or_admin
from ..schemas import SiteCreateRequest, SiteUpdateRequest, SiteResponse, SitePortfolioItem, PortfolioResponse

router = APIRouter(prefix="/sites", tags=["sites"])


@router.post("", response_model=SiteResponse, status_code=status.HTTP_201_CREATED)
def create_site(
    req: SiteCreateRequest,
    current_user: dict = Depends(require_editor_or_admin)
):
    org_id = current_user["org_id"]
    target_url = req.url.strip()
    if not target_url.startswith(("http://", "https://")):
        target_url = "https://" + target_url

    parsed = urllib.parse.urlsplit(target_url)
    domain = (req.domain or parsed.netloc or parsed.path or "unknown.domain").lower()
    site_id = f"site_{hashlib.sha256(f'{org_id}:{domain}'.encode('utf-8')).hexdigest()[:16]}"

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO sites (id, org_id, domain, url, vertical, config_json)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (org_id, domain) DO UPDATE SET
                    url = EXCLUDED.url,
                    vertical = EXCLUDED.vertical,
                    config_json = EXCLUDED.config_json
                RETURNING id, org_id, domain, url, vertical, config_json, created_at;
                """,
                (
                    site_id,
                    org_id,
                    domain,
                    target_url,
                    req.vertical or "generic",
                    Jsonb(req.config_json or {})
                )
            )
            row = cur.fetchone()
        conn.commit()

    return SiteResponse(**row)


@router.get("", response_model=List[SiteResponse])
def list_sites(current_user: dict = Depends(get_current_user)):
    with ScopedQuery(org_id=current_user["org_id"]) as sq:
        rows = sq.fetch_all("sites", order_by="created_at DESC")
    return [SiteResponse(**r) for r in rows]


@router.get("/portfolio", response_model=PortfolioResponse)
def get_portfolio_overview(current_user: dict = Depends(get_current_user)):
    """
    Stage 10i.1: Multi-Site Portfolio View (Section 6.6)
    Aggregates health, trends, runs, and alerts across all sites belonging to the tenant.
    """
    org_id = current_user["org_id"]
    with get_connection() as conn:
        with conn.cursor() as cur:
            # 1. Fetch all sites for org
            cur.execute(
                """
                SELECT id, domain, url, vertical, created_at
                FROM sites
                WHERE org_id = %s
                ORDER BY created_at DESC
                """,
                (org_id,)
            )
            site_rows = cur.fetchall()
            if not site_rows:
                return PortfolioResponse(
                    total_sites=0,
                    total_issues=0,
                    total_opportunities=0,
                    total_open_alerts=0,
                    healthy_sites=0,
                    sites=[]
                )

            site_ids = [r["id"] for r in site_rows]

            # 2. Latest runs for each site
            cur.execute(
                """
                SELECT DISTINCT ON (site_id) site_id, id, status, finished_at, created_at
                FROM runs
                WHERE org_id = %s AND site_id = ANY(%s)
                ORDER BY site_id, created_at DESC
                """,
                (org_id, site_ids)
            )
            latest_runs = {r["site_id"]: r for r in cur.fetchall()}

            # 3. Latest trends for each site (issue_count & opportunity_count)
            cur.execute(
                """
                SELECT DISTINCT ON (site_id, metric) site_id, metric, value
                FROM site_trends
                WHERE org_id = %s AND site_id = ANY(%s)
                ORDER BY site_id, metric, date DESC, created_at DESC
                """,
                (org_id, site_ids)
            )
            trends_map: Dict[str, Dict[str, int]] = {}
            for row in cur.fetchall():
                trends_map.setdefault(row["site_id"], {})[row["metric"]] = int(row["value"])

            # 4. Open alerts count and critical alerts count per site
            cur.execute(
                """
                SELECT site_id,
                       COUNT(*) FILTER (WHERE status = 'open') AS open_count,
                       COUNT(*) FILTER (WHERE status = 'open' AND severity = 'critical') AS crit_count
                FROM alerts
                WHERE org_id = %s AND site_id = ANY(%s)
                GROUP BY site_id
                """,
                (org_id, site_ids)
            )
            alerts_map = {r["site_id"]: r for r in cur.fetchall()}

    items = []
    total_issues = 0
    total_opps = 0
    total_alerts = 0
    healthy_sites = 0

    for s in site_rows:
        sid = s["id"]
        run = latest_runs.get(sid)
        t_data = trends_map.get(sid, {})
        a_data = alerts_map.get(sid, {})

        issues = t_data.get("issue_count", 0)
        opps = t_data.get("opportunity_count", 0)
        open_alerts = a_data.get("open_count", 0) if a_data else 0
        crit_alerts = a_data.get("crit_count", 0) if a_data else 0

        total_issues += issues
        total_opps += opps
        total_alerts += open_alerts

        # Health status determination
        if crit_alerts > 0:
            health = "critical"
        elif open_alerts > 0 or issues > 15:
            health = "warning"
        else:
            health = "healthy"
            healthy_sites += 1

        run_date_str = None
        if run:
            dt = run.get("finished_at") or run.get("created_at")
            if dt:
                run_date_str = dt.isoformat() if hasattr(dt, "isoformat") else str(dt)

        items.append(
            SitePortfolioItem(
                id=s["id"],
                domain=s["domain"],
                url=s["url"],
                vertical=s["vertical"] or "generic",
                created_at=s["created_at"],
                latest_run_id=run["id"] if run else None,
                latest_run_status=run["status"] if run else None,
                latest_run_date=run_date_str,
                issue_count=issues,
                opportunity_count=opps,
                open_alerts_count=open_alerts,
                critical_alerts_count=crit_alerts,
                health_status=health
            )
        )

    return PortfolioResponse(
        total_sites=len(site_rows),
        total_issues=total_issues,
        total_opportunities=total_opps,
        total_open_alerts=total_alerts,
        healthy_sites=healthy_sites,
        sites=items
    )



@router.get("/{id}", response_model=SiteResponse)
def get_site(id: str, current_user: dict = Depends(get_current_user)):
    with ScopedQuery(org_id=current_user["org_id"]) as sq:
        site = sq.fetch_one("sites", where="id = %(id)s", params={"id": id})
    if not site:
        # Return 404 to avoid leaking existence of cross-org resources
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Site not found")
    return SiteResponse(**site)


@router.patch("/{id}", response_model=SiteResponse)
def update_site(
    id: str,
    req: SiteUpdateRequest,
    current_user: dict = Depends(require_editor_or_admin)
):
    org_id = current_user["org_id"]
    with ScopedQuery(org_id=org_id) as sq:
        existing = sq.fetch_one("sites", where="id = %(id)s", params={"id": id})
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Site not found")

    new_url = req.url.strip() if req.url else None
    if new_url and not new_url.startswith(("http://", "https://")):
        new_url = "https://" + new_url

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE sites
                SET url = COALESCE(%s, url),
                    vertical = COALESCE(%s, vertical),
                    config_json = COALESCE(%s::jsonb, config_json)
                WHERE id = %s AND org_id = %s
                RETURNING id, org_id, domain, url, vertical, config_json, created_at;
                """,
                (
                    new_url,
                    req.vertical,
                    Jsonb(req.config_json) if req.config_json is not None else None,
                    id,
                    org_id
                )
            )
            updated = cur.fetchone()
        conn.commit()

    return SiteResponse(**updated)


@router.delete("/{id}")
def delete_site(id: str, current_user: dict = Depends(require_admin)):
    org_id = current_user["org_id"]
    with ScopedQuery(org_id=org_id) as sq:
        existing = sq.fetch_one("sites", where="id = %(id)s", params={"id": id})
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Site not found")

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM sites WHERE id = %s AND org_id = %s", (id, org_id))
        conn.commit()

    return {"deleted": True, "id": id}


@router.post("/{site_id}/deploy-webhook")
def cicd_deploy_webhook(
    site_id: str,
    payload: Dict[str, Any],
    sync: bool = False,
    current_user: dict = Depends(get_current_user)
):
    """
    CI/CD Deployment Webhook (Section 6.2):
    Triggers scoped re-crawl, snapshot differ, regression classification, and multi-channel results delivery.
    Strictly enforces tenant isolation via JWT org_id.
    """
    import time
    org_id = current_user["org_id"]
    with ScopedQuery(org_id=org_id) as sq:
        site = sq.fetch_one("sites", where="id = %(id)s", params={"id": site_id})
    if not site:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Site {site_id} not found in org")

    from services.cicd import execute_cicd_deploy_check

    if sync:
        try:
            result = execute_cicd_deploy_check(site_id, org_id, payload)
            return result
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    else:
        import threading
        deployment_id = str(payload.get("deployment_id") or payload.get("deploy_id") or f"dep_{int(time.time())}")
        run_id = f"crawl_dep_{hashlib.sha256(f'{site_id}:{deployment_id}:{time.time()}'.encode()).hexdigest()[:12]}"

        threading.Thread(
            target=execute_cicd_deploy_check,
            args=(site_id, org_id, payload),
            daemon=True
        ).start()

        return {
            "status": "queued",
            "run_id": run_id,
            "deployment_id": deployment_id,
            "message": "Deployment regression check queued successfully."
        }

