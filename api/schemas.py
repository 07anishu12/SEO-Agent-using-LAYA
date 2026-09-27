"""
Pydantic Schemas for SEOJEV Platform API.
"""
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Auth Schemas
# ---------------------------------------------------------------------------
class UserRegisterRequest(BaseModel):
    email: str
    password: str
    org_name: Optional[str] = None
    org_slug: Optional[str] = None


class UserLoginRequest(BaseModel):
    email: str
    password: str


class UserCreateRequest(BaseModel):
    email: str
    password: str
    role: str = "viewer"  # viewer, editor, admin


class UserRoleUpdateRequest(BaseModel):
    role: str  # viewer, editor, admin


class UserInfo(BaseModel):
    id: str
    email: str
    org_id: str
    role: str = "member"


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserInfo


class ApiKeyCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)


class ApiKeyResponse(BaseModel):
    id: str
    name: str
    api_key: str
    created_at: Optional[datetime] = None


# ---------------------------------------------------------------------------
# Site Schemas
# ---------------------------------------------------------------------------
class SiteCreateRequest(BaseModel):
    url: str
    domain: Optional[str] = None
    vertical: Optional[str] = "generic"
    config_json: Optional[Dict[str, Any]] = None


class SiteUpdateRequest(BaseModel):
    url: Optional[str] = None
    vertical: Optional[str] = None
    config_json: Optional[Dict[str, Any]] = None


class SiteResponse(BaseModel):
    id: str
    org_id: str
    domain: str
    url: str
    vertical: str = "generic"
    config_json: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None


# ---------------------------------------------------------------------------
# Run Schemas
# ---------------------------------------------------------------------------
class RunCreateRequest(BaseModel):
    site_id: str
    crawl_id: Optional[str] = None
    max_pages: Optional[int] = 50
    concurrency: Optional[int] = 2
    render: Optional[bool] = False
    fresh: Optional[bool] = True
    sync: Optional[bool] = False
    options: Optional[Dict[str, Any]] = None


class RunResponse(BaseModel):
    id: str
    org_id: str
    site_id: str
    status: str
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    progress_pct: float = 0.0
    current_pass: Optional[str] = None
    urls_discovered: int = 0
    urls_crawled: int = 0
    urls_failed: int = 0
    total_issues: int = 0
    counts: Optional[Dict[str, int]] = None
    deliverables: Optional[Dict[str, Any]] = None


# ---------------------------------------------------------------------------
# Artifact Schemas
# ---------------------------------------------------------------------------
class ArtifactResponse(BaseModel):
    id: str
    org_id: str
    site_id: str
    run_id: str
    filename: str
    artifact_type: str
    size_bytes: int
    checksum_sha256: Optional[str] = None
    content_type: Optional[str] = None
    created_at: Optional[datetime] = None


class SignedDownloadResponse(BaseModel):
    artifact_id: Optional[str] = None
    filename: str
    download_url: str
    expires_in: int
    size_bytes: Optional[int] = None
    checksum_sha256: Optional[str] = None


# ---------------------------------------------------------------------------
# Watch & Alert Schemas
# ---------------------------------------------------------------------------
class WatchConfigRequest(BaseModel):
    cron_expression: Optional[str] = "0 0 * * *"
    is_active: Optional[bool] = True
    timezone: Optional[str] = "UTC"
    checks: Optional[List[str]] = ["robots_txt", "sitemap", "top_pages", "template_drift"]
    top_pages: Optional[List[str]] = []
    notification_channels: Optional[List[Dict[str, Any]]] = []


class WatchConfigResponse(BaseModel):
    id: str
    org_id: str
    site_id: str
    cron_expression: str = "0 0 * * *"
    is_active: bool = True
    timezone: str = "UTC"
    checks: List[str] = []
    top_pages: List[str] = []
    notification_channels: List[Dict[str, Any]] = []
    last_run_at: Optional[datetime] = None
    next_run_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class AlertResponse(BaseModel):
    id: str
    org_id: str
    site_id: str
    run_id: Optional[str] = None
    alert_type: str
    severity: str
    title: Optional[str] = None
    message: str
    source: Optional[str] = "watch"
    fingerprint: Optional[str] = None
    affected_urls: Optional[List[str]] = []
    previous_value: Optional[str] = None
    current_value: Optional[str] = None
    status: str = "open"
    is_resolved: bool = False
    dispatched: bool = False
    dispatch_status: Optional[str] = "pending"
    dispatch_error: Optional[str] = None
    payload_json: Optional[Dict[str, Any]] = None
    detected_at: Optional[datetime] = None
    created_at: Optional[datetime] = None


class AlertListResponse(BaseModel):
    alerts: List[AlertResponse]
    total: int


class AlertUpdateRequest(BaseModel):
    status: str = "resolved"


# ---------------------------------------------------------------------------
# Stage 10a: Historical Trends Schemas
# ---------------------------------------------------------------------------
class TrendPoint(BaseModel):
    id: str
    run_id: Optional[str] = None
    date: str
    value: float
    created_at: Optional[str] = None


class SiteTrendsResponse(BaseModel):
    site_id: str
    trends: Dict[str, List[TrendPoint]]


