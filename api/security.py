"""
SEOJEV API Security Layer.
Enforces:
1. Rate limiting dependency helpers.
2. Global exception sanitization and internal detail masking.
3. Production security configuration checks.
"""
import logging
from typing import Optional
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse

from services.security import (
    global_rate_limiter,
    auth_rate_limiter,
    crawl_rate_limiter,
    is_local_crawl_allowed
)

logger = logging.getLogger("seojev.api.security")


def get_client_ip(request: Request) -> str:
    """Extracts client IP, respecting X-Forwarded-For if behind a reverse proxy."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "127.0.0.1"


async def rate_limit_auth(request: Request):
    """Rate limit for authentication endpoints (login, register)."""
    ip = get_client_ip(request)
    allowed, remaining = auth_rate_limiter.is_allowed(f"auth:{ip}")
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many authentication attempts. Please try again later.",
            headers={"Retry-After": "60"}
        )


async def rate_limit_runs(request: Request):
    """Rate limit for triggering crawler runs."""
    ip = get_client_ip(request)
    allowed, remaining = crawl_rate_limiter.is_allowed(f"crawl:{ip}")
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded for crawl run execution. Please try again later.",
            headers={"Retry-After": "60"}
        )


async def rate_limit_search(request: Request):
    """Rate limit for full-text search."""
    ip = get_client_ip(request)
    allowed, remaining = global_rate_limiter.is_allowed(f"search:{ip}", limit=80)
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded for search queries.",
            headers={"Retry-After": "60"}
        )


async def global_exception_handler(request: Request, exc: Exception):
    """
    Sanitizes unhandled 500 exceptions so internal credentials,
    file paths, and stack traces are never exposed to API clients.
    Preserves deliberate HTTPException instances.
    """
    if isinstance(exc, HTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail},
            headers=getattr(exc, "headers", None)
        )

    logger.exception(f"Unhandled exception during request {request.method} {request.url.path}: {exc}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "An internal server error occurred.",
            "error_code": "INTERNAL_SERVER_ERROR"
        }
    )
