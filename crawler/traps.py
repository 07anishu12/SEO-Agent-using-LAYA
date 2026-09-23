import re
import urllib.parse
from typing import Tuple, Optional, Dict, Any

SESSION_PARAM_PATTERNS = [
    re.compile(r"jsessionid=[a-z0-9]+", re.I),
    re.compile(r"phpsessid=[a-z0-9]+", re.I),
    re.compile(r"sid=[a-z0-9]+", re.I),
    re.compile(r"session_id=[a-z0-9]+", re.I),
    re.compile(r"cfid=[0-9]+&cftoken=[0-9]+", re.I),
]

CALENDAR_PATTERNS = [
    re.compile(r"/(?:events|calendar|archive)/\d{4}/\d{2}/\d{2}", re.I),
    re.compile(r"[?&](?:date|cal_date|day)=\d{4}-\d{2}-\d{2}", re.I),
]

FACET_PARAM_KEYS = {
    "filter", "filter_", "facet", "sort", "order", "dir", "limit", "view",
    "color", "colour", "size", "brand", "price_min", "price_max", "tag"
}

class TrapDetector:
    """Detects infinite crawl traps, parameter explosions, session IDs, and loop cycles."""
    def __init__(self, max_facet_params: int = 3, max_pagination_depth: int = 50):
        self.max_facet_params = max_facet_params
        self.max_pagination_depth = max_pagination_depth
        self.quarantined_families: Dict[str, Dict[str, Any]] = {}

    def is_trap(self, url: str) -> Tuple[bool, Optional[str], Optional[str]]:
        """Evaluates whether a URL represents an infinite trap or parameter explosion.
        Returns: (is_trap: bool, trap_type: Optional[str], reason: Optional[str])
        """
        parsed = urllib.parse.urlsplit(url)
        path = parsed.path.lower()
        query = parsed.query.lower()

        # 1. Session ID Traps
        for pat in SESSION_PARAM_PATTERNS:
            if pat.search(url):
                return True, "session_id", f"Contains session identifier token: {pat.pattern}"

        # 2. Calendar / Infinite Date Traps
        for pat in CALENDAR_PATTERNS:
            if pat.search(url):
                return True, "calendar_trap", "Infinite date/calendar matrix URL pattern"

        # 3. Repeated Path Segments (Loop / recursion trap)
        segments = [s for s in path.strip("/").split("/") if s]
        if len(segments) >= 4:
            # Check for immediate repetition e.g. /a/b/a/b or /bike/pulsar/bike/pulsar
            for i in range(len(segments) - 1):
                if segments.count(segments[i]) >= 3:
                    return True, "repeating_path", f"Path segment '{segments[i]}' repeated 3+ times in path"

        # 4. Faceted Parameter Explosion
        if query:
            q_dict = urllib.parse.parse_qs(query)
            facet_count = sum(1 for k in q_dict if any(fk in k.lower() for fk in FACET_PARAM_KEYS))
            if facet_count > self.max_facet_params:
                return True, "parameter_explosion", f"Faceted parameter count ({facet_count}) exceeds safety limit ({self.max_facet_params})"

            # 5. Excessive Pagination
            page_val = q_dict.get("page") or q_dict.get("p") or q_dict.get("pg")
            if page_val:
                try:
                    p_num = int(page_val[0])
                    if p_num > self.max_pagination_depth:
                        return True, "infinite_pagination", f"Pagination depth {p_num} exceeds limit {self.max_pagination_depth}"
                except ValueError:
                    pass

        return False, None, None

    def record_quarantine(self, url: str, trap_type: str, reason: str):
        parsed = urllib.parse.urlsplit(url)
        family = f"{parsed.netloc}{parsed.path}"
        if family not in self.quarantined_families:
            self.quarantined_families[family] = {
                "sample_url": url,
                "trap_type": trap_type,
                "reason": reason,
                "quarantined_count": 0
            }
        self.quarantined_families[family]["quarantined_count"] += 1
