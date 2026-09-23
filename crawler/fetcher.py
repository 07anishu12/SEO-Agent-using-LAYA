import asyncio
import time
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
        client = await self.get_client()
        redirect_chain: List[str] = []

        retries = 0
        while retries <= self.max_retries:
            start_time = time.monotonic()
            try:
                # We can perform a manual redirect trace or let httpx trace history
                response = await client.get(url)
                duration = time.monotonic() - start_time

                # Track redirect history
                if response.history:
                    for resp in response.history:
                        redirect_chain.append(str(resp.url))

                # Handle transient 429 or 503 with backoff
                if response.status_code in (429, 502, 503, 504) and retries < self.max_retries:
                    retries += 1
                    sleep_time = self.backoff_factor ** retries
                    await asyncio.sleep(sleep_time)
                    continue

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
                if retries <= self.max_retries:
                    sleep_time = self.backoff_factor ** retries
                    await asyncio.sleep(sleep_time)
                else:
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
