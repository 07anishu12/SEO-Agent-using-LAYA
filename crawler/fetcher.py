import asyncio
import time
import random
import urllib.parse
from typing import List, Dict, Any, Optional
import httpx
from collections import deque

class FetchResult:
    def __init__(
        self,
        url: str,
        final_url: str = "",
        status_code: int = 0,
        content_type: str = "",
        response_time: float = 0.0,
        content_length: int = 0,
        redirect_chain: Optional[List[str]] = None,
        headers: Optional[Dict[str, str]] = None,
        text: str = "",
        error: str = "",
        not_modified: bool = False
    ):
        self.url = url
        self.final_url = final_url or url
        self.status_code = status_code
        self.content_type = content_type
        self.response_time = response_time
        self.content_length = content_length
        self.redirect_chain = redirect_chain or []
        self.headers = headers or {}
        self.text = text
        self.error = error
        self.not_modified = not_modified

    @property
    def is_success(self) -> bool:
        return 200 <= self.status_code < 300

    @property
    def is_redirect(self) -> bool:
        return 300 <= self.status_code < 400

    @property
    def is_client_error(self) -> bool:
        return 400 <= self.status_code < 500

    @property
    def is_server_error(self) -> bool:
        return self.status_code >= 500


class CircuitBreaker:
    """Per-host circuit breaker: trips after consecutive failures, auto-recovers after cooldown."""
    def __init__(self, failure_threshold: int = 5, cooldown_seconds: float = 15.0):
        self.failure_threshold = failure_threshold
        self.cooldown_seconds = cooldown_seconds
        self.failure_counts: Dict[str, int] = {}
        self.tripped_until: Dict[str, float] = {}

    def is_available(self, host: str) -> bool:
        now = time.monotonic()
        if host in self.tripped_until:
            if now < self.tripped_until[host]:
                return False
            else:
                # Reset after cooldown
                del self.tripped_until[host]
                self.failure_counts[host] = 0
        return True

    def record_success(self, host: str):
        self.failure_counts[host] = 0

    def record_failure(self, host: str):
        count = self.failure_counts.get(host, 0) + 1
        self.failure_counts[host] = count
        if count >= self.failure_threshold:
            self.tripped_until[host] = time.monotonic() + self.cooldown_seconds


class AsyncFetcher:
    def __init__(
        self,
        user_agent: str = "SEOJEV-Bot/1.0",
        timeout: float = 15.0,
        max_retries: int = 3,
        backoff_factor: float = 1.5,
        verify_ssl: bool = True,
        max_connections: int = 100,
        max_keepalive_connections: int = 80
    ):
        self.user_agent = user_agent
        self.timeout = timeout
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self.verify_ssl = verify_ssl
        self.limits = httpx.Limits(
            max_connections=max_connections,
            max_keepalive_connections=max_keepalive_connections
        )
        self._client: Optional[httpx.AsyncClient] = None
        self.circuit_breaker = CircuitBreaker()
        self.adaptive_delay_multiplier = 1.0

        self._host_latencies: Dict[str, deque] = {}
        self._host_concurrency: Dict[str, int] = {}
        self._host_max_concurrency: Dict[str, int] = {}
        self._etag_cache: Dict[str, str] = {}
        self._last_modified_cache: Dict[str, str] = {}

    def adjust_host_concurrency(self, host: str, latency_ms: float, status_code: int):
        if host not in self._host_latencies:
            self._host_latencies[host] = deque(maxlen=20)
        self._host_latencies[host].append((latency_ms, status_code))
        
        if host not in self._host_max_concurrency:
            self._host_max_concurrency[host] = min(self.limits.max_connections or 50, 30)
            
        if status_code == 429:
            self._host_max_concurrency[host] = 1
            return
            
        latencies = self._host_latencies[host]
        if len(latencies) >= 5:
            avg_latency = sum(l[0] for l in latencies) / len(latencies)
            error_rate = sum(1 for l in latencies if l[1] >= 400) / len(latencies)
            
            if avg_latency < 200.0 and error_rate == 0:
                self._host_max_concurrency[host] = min(self.limits.max_connections or 50, self._host_max_concurrency[host] + 2)
            elif avg_latency > 1000.0 or error_rate > 0.2:
                self._host_max_concurrency[host] = max(2, self._host_max_concurrency[host] - 2)

    async def get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            headers = {
                "User-Agent": self.user_agent,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
                "Accept-Encoding": "gzip, deflate, br",
            }
            self._client = httpx.AsyncClient(
                headers=headers,
                timeout=httpx.Timeout(self.timeout, connect=10.0),
                limits=self.limits,
                verify=self.verify_ssl,
                follow_redirects=True,
                http2=True
            )
        return self._client

    async def fetch(self, url: str) -> FetchResult:
        from services.security import is_safe_url
        safe, reason = is_safe_url(url)
        if not safe:
            return FetchResult(url=url, error=f"SSRF Protection: Blocked unsafe URL: {reason}")

        host = urllib.parse.urlsplit(url).netloc
        if not self.circuit_breaker.is_available(host):
            return FetchResult(url=url, error="Circuit breaker tripped: host temporarily paused due to consecutive errors")

        client = await self.get_client()
        redirect_chain: List[str] = []

        req_headers = {}
        if url in self._etag_cache:
            req_headers["If-None-Match"] = self._etag_cache[url]
        if url in self._last_modified_cache:
            req_headers["If-Modified-Since"] = self._last_modified_cache[url]

        retries = 0
        while retries <= self.max_retries:
            start_time = time.monotonic()
            try:
                response = await client.get(url, headers=req_headers)
                duration = time.monotonic() - start_time
                self.adjust_host_concurrency(host, duration * 1000, response.status_code)
                
                if response.status_code == 304:
                    return FetchResult(
                        url=url,
                        final_url=url,
                        status_code=304,
                        response_time=round(duration, 3),
                        not_modified=True
                    )

                if response.history:
                    for resp in response.history:
                        r_url = str(resp.url)
                        redirect_chain.append(r_url)
                        # Validate each intermediate redirect against SSRF
                        r_safe, r_reason = is_safe_url(r_url)
                        if not r_safe:
                            return FetchResult(url=url, error=f"SSRF Protection: Blocked unsafe redirect to {r_url}: {r_reason}")

                # Also validate final destination URL against SSRF
                final_safe, final_reason = is_safe_url(str(response.url))
                if not final_safe:
                    return FetchResult(url=url, error=f"SSRF Protection: Blocked unsafe final redirect to {response.url}: {final_reason}")

                # Handle Rate Limiting (429) & Server Overload (502, 503, 504)
                if response.status_code in (429, 502, 503, 504):
                    self.adaptive_delay_multiplier = min(self.adaptive_delay_multiplier * 1.5, 5.0)
                    retry_after_hdr = response.headers.get("Retry-After")
                    if retry_after_hdr and retry_after_hdr.isdigit():
                        sleep_time = float(retry_after_hdr)
                    else:
                        jitter = random.uniform(0.1, 0.5)
                        sleep_time = (self.backoff_factor ** (retries + 1)) + jitter

                    retries += 1
                    if retries <= self.max_retries:
                        await asyncio.sleep(sleep_time)
                        continue
                    else:
                        self.circuit_breaker.record_failure(host)
                elif response.status_code >= 500:
                    self.circuit_breaker.record_failure(host)
                else:
                    self.circuit_breaker.record_success(host)
                    # Decay adaptive delay back down on normal responses
                    self.adaptive_delay_multiplier = max(1.0, self.adaptive_delay_multiplier * 0.95)

                content_type = response.headers.get("content-type", "").lower()
                content_len = len(response.content) if response.content else 0

                if response.status_code == 200:
                    if "etag" in response.headers:
                        self._etag_cache[url] = response.headers["etag"]
                    if "last-modified" in response.headers:
                        self._last_modified_cache[url] = response.headers["last-modified"]

                return FetchResult(
                    url=url,
                    final_url=str(response.url),
                    status_code=response.status_code,
                    content_type=content_type,
                    response_time=round(duration, 3),
                    content_length=content_len,
                    redirect_chain=redirect_chain,
                    headers=dict(response.headers),
                    text=response.text
                )

            except (httpx.TimeoutException, httpx.NetworkError) as e:
                retries += 1
                self.adaptive_delay_multiplier = min(self.adaptive_delay_multiplier * 1.5, 5.0)
                if retries <= self.max_retries:
                    jitter = random.uniform(0.1, 0.5)
                    sleep_time = (self.backoff_factor ** retries) + jitter
                    await asyncio.sleep(sleep_time)
                else:
                    self.circuit_breaker.record_failure(host)
                    duration = time.monotonic() - start_time
                    return FetchResult(
                        url=url,
                        final_url=url,
                        status_code=0,
                        response_time=round(duration, 3),
                        error=f"Connection/Timeout Error: {str(e)[:100]}"
                    )
            except Exception as e:
                duration = time.monotonic() - start_time
                return FetchResult(
                    url=url,
                    final_url=url,
                    status_code=0,
                    response_time=round(duration, 3),
                    error=f"Unexpected error: {str(e)[:100]}"
                )

        return FetchResult(url=url, error="Max retries exceeded")

    async def close(self):
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None
