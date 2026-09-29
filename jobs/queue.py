"""
Redis Queue Manager for SEOJEV Asynchronous Crawl Execution.
Manages job enqueuing, cooperative cancellation flags, and pub/sub progress dispatch.
"""
import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, Optional
import redis

from api.config import REDIS_URL

QUEUE_KEY = "seojev:queue:runs"
DEFAULT_MAX_QUEUE_SIZE = int(os.environ.get("SEOJEV_MAX_QUEUE_SIZE", "10000"))


def get_redis_client(url: Optional[str] = None) -> redis.Redis:
    r_url = url or REDIS_URL
    return redis.Redis.from_url(r_url, decode_responses=True)


def check_redis_health(url: Optional[str] = None) -> dict:
    """Verifies Redis connectivity and returns current queue depth."""
    try:
        r = get_redis_client(url)
        r.ping()
        depth = r.llen(QUEUE_KEY)
        return {"status": "ok", "healthy": True, "queue_depth": depth}
    except Exception as e:
        return {"status": "error", "healthy": False, "error": str(e)}


class RunQueue:
    def __init__(self, redis_url: Optional[str] = None, max_queue_size: Optional[int] = None):
        self.redis_url = redis_url or REDIS_URL
        self.max_queue_size = max_queue_size or DEFAULT_MAX_QUEUE_SIZE
        self._client: Optional[redis.Redis] = None

    @property
    def client(self) -> redis.Redis:
        if self._client is None:
            self._client = get_redis_client(self.redis_url)
        return self._client

    def enqueue_run(
        self,
        run_id: str,
        org_id: str,
        site_id: str,
        target_url: str,
        options: Optional[Dict[str, Any]] = None
    ) -> str:
        current_len = self.client.llen(QUEUE_KEY)
        if current_len >= self.max_queue_size:
            raise RuntimeError(f"Queue capacity exceeded ({current_len}/{self.max_queue_size}). Backpressure engaged.")

        payload = {
            "run_id": run_id,
            "org_id": org_id,
            "site_id": site_id,
            "target_url": target_url,
            "options": options or {},
            "enqueued_at": datetime.now(timezone.utc).isoformat()
        }
        self.client.rpush(QUEUE_KEY, json.dumps(payload))
        self.client.set(f"run:{run_id}:status", "queued")
        # Ensure cancel flag is cleared for fresh/resumed enqueue
        self.client.delete(f"run:{run_id}:cancel")
        return run_id

    def dequeue_run(self, timeout: int = 1) -> Optional[Dict[str, Any]]:
        item = self.client.blpop(QUEUE_KEY, timeout=timeout)
        if item and len(item) == 2:
            try:
                return json.loads(item[1])
            except Exception:
                return None
        return None

    def request_cancellation(self, run_id: str):
        self.client.set(f"run:{run_id}:cancel", "1")
        self.client.publish(f"run:{run_id}:cancel_signal", "CANCEL")

    def is_cancelled(self, run_id: str) -> bool:
        return bool(self.client.get(f"run:{run_id}:cancel"))

    def clear_cancellation(self, run_id: str):
        self.client.delete(f"run:{run_id}:cancel")

    def publish_progress(self, run_id: str, event_data: Dict[str, Any]):
        raw = json.dumps(event_data)
        self.client.publish(f"run:{run_id}:progress", raw)
        self.client.set(f"run:{run_id}:last_progress", raw, ex=86400)

    def get_retry_count(self, run_id: str) -> int:
        val = self.client.get(f"run:{run_id}:retries")
        return int(val) if val else 0

    def increment_retry_count(self, run_id: str) -> int:
        return int(self.client.incr(f"run:{run_id}:retries"))

    def reset_retry_count(self, run_id: str):
        self.client.delete(f"run:{run_id}:retries")
