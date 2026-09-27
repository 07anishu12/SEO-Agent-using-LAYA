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
from ..auth import get_current_user
from ..schemas import SiteCreateRequest, SiteUpdateRequest, SiteResponse

router = APIRouter(prefix="/sites", tags=["sites"])


@router.post("", response_model=SiteResponse, status_code=status.HTTP_201_CREATED)
def create_site(
    req: SiteCreateRequest,
    current_user: dict = Depends(get_current_user)
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
    current_user: dict = Depends(get_current_user)
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
                    config_json = CASE WHEN %s IS NOT NULL THEN %s ELSE config_json END
                WHERE id = %s AND org_id = %s
                RETURNING id, org_id, domain, url, vertical, config_json, created_at;
                """,
                (
                    new_url,
                    req.vertical,
                    Jsonb(req.config_json) if req.config_json is not None else None,
                    Jsonb(req.config_json) if req.config_json is not None else None,
                    id,
                    org_id
                )
            )
            updated = cur.fetchone()
        conn.commit()

    return SiteResponse(**updated)


@router.delete("/{id}")
def delete_site(id: str, current_user: dict = Depends(get_current_user)):
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

