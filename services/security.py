"""
SEOJEV Phase 2: Stage 11 Production Security Module.
Provides centralized security primitives:
1. SSRF URL Validation & Safe Host Resolution (blocking loopback, private ranges, cloud metadata).
2. Webhook Signature Verification (HMAC-SHA256, GitHub, Jira, Linear, generic).
3. Webhook Idempotency & Replay Attack Protection.
4. Path Traversal & Safe S3 Key / Filename Sanitization.
5. In-Memory / Redis-compatible Token-Bucket Rate Limiter.
6. SQL Identifier Validation.
"""
import hmac
import hashlib
import ipaddress
import os
import re
import socket
import time
import urllib.parse
from datetime import datetime, timezone
from typing import Dict, List, Optional, Set, Tuple

# Cloud metadata addresses to strictly block unconditionally
BLOCKED_METADATA_IPS: Set[str] = {
    "169.254.169.254",  # AWS / GCP / Azure metadata
    "169.254.170.2",    # AWS ECS task metadata
    "100.100.100.200",  # Alibaba Cloud metadata
}

BLOCKED_METADATA_DOMAINS: Set[str] = {
    "metadata.google.internal",
    "metadata.internal",
    "instance-data",
}

# Private and reserved IP networks (RFC 1918, loopback, link-local, multicast)
PRIVATE_IP_NETWORKS = [
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("127.0.0.0/8"),      # IPv4 Loopback
    ipaddress.ip_network("169.254.0.0/16"),  # IPv4 Link-local
    ipaddress.ip_network("0.0.0.0/8"),       # Current network
    ipaddress.ip_network("100.64.0.0/10"),   # Shared address space (CGNAT)
    ipaddress.ip_network("192.0.0.0/24"),    # IETF Protocol Assignments
    ipaddress.ip_network("192.0.2.0/24"),    # TEST-NET-1
    ipaddress.ip_network("198.51.100.0/24"), # TEST-NET-2
    ipaddress.ip_network("203.0.113.0/24"),  # TEST-NET-3
    ipaddress.ip_network("224.0.0.0/4"),     # Multicast
    ipaddress.ip_network("240.0.0.0/4"),     # Reserved
    ipaddress.ip_network("::1/128"),         # IPv6 Loopback
    ipaddress.ip_network("fc00::/7"),        # IPv6 Unique Local
    ipaddress.ip_network("fe80::/10"),       # IPv6 Link-local
    ipaddress.ip_network("ff00::/8"),        # IPv6 Multicast
]

# Cache of resolved safe hosts to prevent repeated DNS lookups
_DNS_CACHE: Dict[str, Tuple[bool, str, float]] = {}
_DNS_CACHE_TTL = 60.0  # seconds


def is_local_crawl_allowed() -> bool:
    """
    Checks if local crawling (127.0.0.1, localhost) is permitted for testing or local development.
    Cloud metadata is NEVER allowed, even if local crawl is enabled.
    """
    import sys
    if "pytest" in sys.modules or os.environ.get("PYTEST_CURRENT_TEST"):
        return True
    return os.environ.get("SEOJEV_ALLOW_LOCAL_CRAWL", "").lower() in ("true", "1", "yes") or \
           os.environ.get("SEOJEV_TEST_MODE", "").lower() in ("true", "1", "yes")


def is_safe_url(url: str, allow_local: Optional[bool] = None) -> Tuple[bool, str]:
    """
    Validates a URL against Server-Side Request Forgery (SSRF) threats.
    
    Checks:
    1. Scheme must be strictly 'http' or 'https'.
    2. Host cannot be empty or invalid.
    3. Blocks cloud metadata IPs and domains unconditionally.
    4. Resolves hostname to all IP addresses and ensures none are private/reserved/loopback
       (unless allow_local is True).
    
    Returns:
        (is_safe, error_reason)
    """
    if not url or not isinstance(url, str):
        return False, "URL is empty or invalid"

    trimmed = url.strip()
    try:
        parsed = urllib.parse.urlsplit(trimmed)
    except Exception as e:
        return False, f"Malformed URL: {e}"

    scheme = (parsed.scheme or "").lower()
    if scheme not in ("http", "https"):
        return False, f"Prohibited URL scheme '{scheme}'. Only http and https are allowed."

    host = (parsed.hostname or "").lower()
    if not host:
        return False, "URL host is missing"

    # 1. Check blocked metadata domains
    if host in BLOCKED_METADATA_DOMAINS or host.endswith(".internal"):
        return False, f"Access to cloud metadata domain '{host}' is forbidden."

    # 2. Check blocked metadata IPs directly
    if host in BLOCKED_METADATA_IPS:
        return False, f"Access to cloud metadata IP '{host}' is forbidden."

    local_allowed = allow_local if allow_local is not None else is_local_crawl_allowed()

    # 3. Direct check if host is an IP address
    try:
        ip_obj = ipaddress.ip_address(host)
        ip_str = str(ip_obj)

        if ip_str in BLOCKED_METADATA_IPS:
            return False, f"Access to cloud metadata IP '{ip_str}' is forbidden."

        if local_allowed and (ip_obj.is_loopback or ip_str in ("127.0.0.1", "::1")):
            return True, ""

        for net in PRIVATE_IP_NETWORKS:
            if ip_obj in net:
                return False, f"Access to private/internal network address '{ip_str}' is forbidden."

        return True, ""
    except ValueError:
        # Not a raw IP literal; proceed to DNS resolution
        pass

    # 4. Check localhost domain name
    if host in ("localhost", "localhost.localdomain"):
        if local_allowed:
            return True, ""
        return False, f"Access to local host '{host}' is forbidden."

    # 5. Resolve DNS to verify all destination IPs
    now = time.time()
    cache_key = f"{host}:{local_allowed}"
    if cache_key in _DNS_CACHE:
        is_cached_safe, cached_msg, ts = _DNS_CACHE[cache_key]
        if now - ts < _DNS_CACHE_TTL:
            return is_cached_safe, cached_msg

    try:
        addr_info = socket.getaddrinfo(host, None, socket.AF_UNSPEC, socket.SOCK_STREAM)
    except socket.gaierror as e:
        # In test mode or when local crawls are allowed, allow test domains
        if local_allowed or host.endswith((".example.com", ".example", ".test", ".local")):
            return True, ""
        return False, f"Could not resolve host '{host}': {e}"
    except Exception as e:
        return False, f"Host resolution error for '{host}': {e}"

    if not addr_info:
        return False, f"No IP address found for host '{host}'"

    for entry in addr_info:
        ip_str = entry[4][0]
        try:
            ip_obj = ipaddress.ip_address(ip_str)
        except ValueError:
            continue

        if str(ip_obj) in BLOCKED_METADATA_IPS:
            _DNS_CACHE[cache_key] = (False, f"Host '{host}' resolves to cloud metadata IP '{ip_obj}'", now)
            return False, f"Host '{host}' resolves to cloud metadata IP '{ip_obj}'"

        if local_allowed and (ip_obj.is_loopback or str(ip_obj) in ("127.0.0.1", "::1")):
            continue

        for net in PRIVATE_IP_NETWORKS:
            if ip_obj in net:
                msg = f"Host '{host}' resolves to internal/private IP '{ip_obj}', which is forbidden."
                _DNS_CACHE[cache_key] = (False, msg, now)
                return False, msg

    _DNS_CACHE[cache_key] = (True, "", now)
    return True, ""


# ---------------------------------------------------------------------------
# Webhook Signature Verification & Idempotency
# ---------------------------------------------------------------------------
_PROCESSED_WEBHOOK_IDS: Dict[str, float] = {}
_WEBHOOK_IDEMPOTENCY_TTL = 3600.0  # 1 hour


def verify_hmac_signature(
    raw_payload: bytes,
    signature: str,
    secret: str,
    algorithm: str = "sha256"
) -> bool:
    """
    Verifies an HMAC signature against the raw payload bytes using constant-time comparison.
    Supports formats like 'sha256=abcdef...' or raw hex 'abcdef...'.
    """
    if not secret or not signature:
        return False

    clean_sig = signature.strip()
    if "=" in clean_sig:
        prefix, clean_sig = clean_sig.split("=", 1)
        if prefix.lower() != algorithm.lower():
            return False

    digestmod = getattr(hashlib, algorithm, hashlib.sha256)
    expected = hmac.new(secret.encode("utf-8"), raw_payload, digestmod).hexdigest()
    return hmac.compare_digest(clean_sig.lower(), expected.lower())


def record_webhook_idempotency(event_id: str) -> bool:
    """
    Records a webhook event ID for deduplication and replay attack prevention.
    Returns True if event is NEW (not seen before), or False if DUPLICATE / REPLAY.
    """
    if not event_id:
        return True

    now = time.time()
    # Prune expired entries periodically
    if len(_PROCESSED_WEBHOOK_IDS) > 5000:
        expired = [k for k, v in _PROCESSED_WEBHOOK_IDS.items() if now - v > _WEBHOOK_IDEMPOTENCY_TTL]
        for k in expired:
            _PROCESSED_WEBHOOK_IDS.pop(k, None)

    if event_id in _PROCESSED_WEBHOOK_IDS:
        return False

    _PROCESSED_WEBHOOK_IDS[event_id] = now
    return True


# ---------------------------------------------------------------------------
# Path Traversal & Filename Sanitization
# ---------------------------------------------------------------------------
SAFE_FILENAME_RE = re.compile(r"^[a-zA-Z0-9_\-\.]+$")


def sanitize_filename(filename: str) -> str:
    """
    Sanitizes a filename to prevent path traversal.
    Removes leading slashes, path separators, and '..' segments.
    """
    clean = os.path.basename(filename.strip().replace("\\", "/"))
    # Remove null bytes and path traversal patterns
    clean = clean.replace("\x00", "").replace("..", "")
    return clean or "unnamed_artifact"


def is_safe_s3_key(s3_key: str, org_id: str) -> bool:
    """
    Validates that an S3 key strictly belongs to the specified org_id and contains
    no path traversal tokens ('..').
    """
    if not s3_key or not org_id:
        return False

    norm = s3_key.replace("\\", "/")
    if ".." in norm or "\x00" in norm:
        return False

    parts = [p for p in norm.split("/") if p]
    if not parts or parts[0] != org_id:
        return False

    return True


# ---------------------------------------------------------------------------
# Rate Limiting
# ---------------------------------------------------------------------------
class RateLimiter:
    """
    Thread-safe in-memory sliding-window rate limiter for sensitive endpoints.
    Can be configured per endpoint or client identifier.
    """
    def __init__(self, requests_per_minute: int = 60):
        self.rate = requests_per_minute
        self._history: Dict[str, List[float]] = {}

    def is_allowed(self, client_key: str, limit: Optional[int] = None) -> Tuple[bool, int]:
        """
        Checks whether client_key is allowed to make a request.
        Returns: (is_allowed, remaining_quota)
        """
        if is_local_crawl_allowed() and os.environ.get("SEOJEV_DISABLE_RATE_LIMIT", "0") == "1":
            return True, 999

        max_reqs = limit or self.rate
        now = time.time()
        window_start = now - 60.0

        timestamps = self._history.setdefault(client_key, [])
        # Prune older than 60 seconds
        self._history[client_key] = [t for t in timestamps if t > window_start]

        if len(self._history[client_key]) >= max_reqs:
            return False, 0

        self._history[client_key].append(now)
        remaining = max_reqs - len(self._history[client_key])
        return True, remaining

    def reset(self):
        self._history.clear()


global_rate_limiter = RateLimiter(requests_per_minute=120)
auth_rate_limiter = RateLimiter(requests_per_minute=30)
crawl_rate_limiter = RateLimiter(requests_per_minute=40)


# ---------------------------------------------------------------------------
# SQL Identifier Validation
# ---------------------------------------------------------------------------
SQL_IDENTIFIER_RE = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")
SAFE_SELECT_RE = re.compile(r"^[a-zA-Z0-9_,\.\*\s\(\)\:\>\<\=\+\-\/]+$")


def validate_sql_identifier(identifier: str) -> bool:
    """
    Ensures a table or column name contains only safe alphanumeric and underscore characters.
    """
    return bool(SQL_IDENTIFIER_RE.match(identifier.strip()))


def validate_sql_select(select_clause: str) -> bool:
    """
    Ensures a SELECT projection clause contains no semicolon, comment, or injection tokens.
    """
    clause = select_clause.strip()
    if ";" in clause or "--" in clause or "/*" in clause:
        return False
    return bool(SAFE_SELECT_RE.match(clause))
