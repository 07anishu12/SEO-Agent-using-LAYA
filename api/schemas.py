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
