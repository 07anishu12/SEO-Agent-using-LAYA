import asyncio
import time
import random
import urllib.parse
from typing import List, Dict, Any, Optional
import httpx

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
        error: str = ""
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
        max_connections: int = 20,
        max_keepalive_connections: int = 15
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
                follow_redirects=True
            )
        return self._client

    async def fetch(self, url: str) -> FetchResult:
        host = urllib.parse.urlsplit(url).netloc
        if not self.circuit_breaker.is_available(host):
            return FetchResult(url=url, error="Circuit breaker tripped: host temporarily paused due to consecutive errors")

        client = await self.get_client()
        redirect_chain: List[str] = []

        retries = 0
        while retries <= self.max_retries:
            start_time = time.monotonic()
            try:
                response = await client.get(url)
                duration = time.monotonic() - start_time

                if response.history:
                    for resp in response.history:
                        redirect_chain.append(str(resp.url))

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
