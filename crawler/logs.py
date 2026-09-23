import os
import re
import urllib.parse
from collections import Counter
from typing import Dict, Any, List, Optional

LOG_PATTERN = re.compile(
    r'^(?P<ip>\S+)\s+\S+\s+\S+\s+\[(?P<time>[^\]]+)\]\s+"(?P<method>[A-Z]+)\s+(?P<path>\S+)\s+HTTP/[0-9.]+"\s+(?P<status>\d{3})\s+(?P<bytes>\S+)\s+"(?P<referer>[^"]*)"\s+"(?P<ua>[^"]*)"'
)

class ServerLogAnalyzer:
    """Parses server access logs to analyze Googlebot crawl behavior and crawl budget waste."""
    def __init__(self, log_path: Optional[str] = None):
        self.log_path = log_path
        self.has_logs = bool(log_path and os.path.exists(log_path))
        self.googlebot_hits: List[Dict[str, Any]] = []

    def parse_logs(self, max_lines: int = 100000) -> Dict[str, Any]:
        if not self.has_logs:
            return {"has_logs": False, "message": "No server access log provided."}

        total_lines = 0
        bot_hits = 0
        status_counts = Counter()
        path_counts = Counter()
        wasted_requests = 0

        with open(self.log_path, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                total_lines += 1
                if total_lines > max_lines:
                    break

                match = LOG_PATTERN.match(line.strip())
                if not match:
                    continue

                d = match.groupdict()
                ua = d["ua"]
                if "Googlebot" in ua:
                    bot_hits += 1
                    status = int(d["status"])
                    path = d["path"]
                    status_counts[status] += 1
                    path_counts[path] += 1

                    if status >= 400 or "?" in path:
                        wasted_requests += 1

                    self.googlebot_hits.append({
                        "ip": d["ip"],
                        "time": d["time"],
                        "path": path,
                        "status": status,
                        "ua": ua
                    })

        wasted_pct = round((wasted_requests / max(bot_hits, 1)) * 100, 1)
        return {
            "has_logs": True,
            "total_lines_analyzed": total_lines,
            "total_googlebot_hits": bot_hits,
            "status_distribution": dict(status_counts),
            "top_crawled_paths": path_counts.most_common(20),
            "wasted_googlebot_requests": wasted_requests,
            "wasted_percentage": wasted_pct
        }
