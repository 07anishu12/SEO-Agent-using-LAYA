from dataclasses import dataclass, field, asdict
from typing import Dict, Any, Optional

@dataclass
class CrawlRun:
    crawl_id: str
    target_url: str
    start_time: str
    end_time: Optional[str] = None
    status: str = "running"
    max_pages: int = 5000
    concurrency: int = 10
    config_json: str = "{}"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass
class CrawlStats:
    urls_discovered: int = 0
    urls_eligible: int = 0
    urls_crawled: int = 0
    urls_skipped: int = 0
    urls_failed: int = 0
    urls_blocked_robots: int = 0
    urls_redirected: int = 0
    urls_error_4xx: int = 0
    urls_error_5xx: int = 0
    indexable_urls: int = 0
    non_indexable_urls: int = 0
    average_response_time: float = 0.0
    crawl_duration_seconds: float = 0.0
    total_issues: int = 0
    critical_issues: int = 0
    high_issues: int = 0
    medium_issues: int = 0
    low_issues: int = 0
    templates_count: int = 0
    performance_sample_count: int = 0
    laya_decisions_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
