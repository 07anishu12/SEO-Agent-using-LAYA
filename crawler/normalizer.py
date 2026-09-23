import urllib.parse
import re
from typing import Optional, Set

TRACKING_PARAMS = {
    "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
    "fbclid", "gclid", "gclsrc", "dclid", "msclkid", "mc_eid", "_ga", "_gl",
    "yclid", "zanpid", "ref", "fb_action_ids", "fb_action_types", "source"
}

MEDIA_EXTENSIONS = {
    ".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg", ".ico", ".tiff", ".bmp",
    ".mp4", ".webm", ".avi", ".mov", ".mkv", ".mp3", ".wav", ".ogg",
    ".pdf", ".zip", ".tar", ".gz", ".rar", ".7z", ".doc", ".docx", ".xls", ".xlsx",
    ".css", ".js", ".json", ".xml", ".txt"
}

class URLNormalizer:
    def __init__(self, base_url: str):
        parsed = urllib.parse.urlparse(base_url)
        self.base_scheme = parsed.scheme if parsed.scheme else "https"
        # Extract registered domain / base netloc
        self.base_netloc = parsed.netloc.lower()
        # Handle www vs non-www
        self.clean_domain = re.sub(r"^www\.", "", self.base_netloc)

    def is_same_domain(self, url: str) -> bool:
        try:
            parsed = urllib.parse.urlparse(url)
            if not parsed.netloc:
                return True  # relative url is same domain
            netloc = parsed.netloc.lower()
            clean_netloc = re.sub(r"^www\.", "", netloc)
            return clean_netloc == self.clean_domain or clean_netloc.endswith("." + self.clean_domain)
        except Exception:
            return False

    def is_crawlable_page(self, url: str) -> bool:
        """Filter out static assets, binary files, non-web protocols."""
        try:
            parsed = urllib.parse.urlparse(url)
            if parsed.scheme and parsed.scheme not in ("http", "https"):
                return False
            path = parsed.path.lower()
            for ext in MEDIA_EXTENSIONS:
                if path.endswith(ext):
                    return False
            return True
        except Exception:
            return False

    def normalize(self, url: str, current_page_url: Optional[str] = None) -> Optional[str]:
        """
        Normalize URL:
        - Resolves relative URLs
        - Strips fragments
        - Lowercases scheme and netloc
        - Cleans duplicate slashes in path
        - Strips tracking query parameters
        - Alphabetizes remaining query parameters
        - Normalizes trailing slashes consistently (strip trailing slash unless path is empty or '/')
        """
        if not url:
            return None
        url = url.strip()
        if url.startswith(("javascript:", "mailto:", "tel:", "data:", "sms:", "#")):
            return None

        # Resolve relative URL
        if current_page_url:
            url = urllib.parse.urljoin(current_page_url, url)
        elif not url.startswith(("http://", "https://")):
            url = urllib.parse.urljoin(f"{self.base_scheme}://{self.base_netloc}", url)

        try:
            parsed = urllib.parse.urlsplit(url)
        except Exception:
            return None

        if parsed.scheme not in ("http", "https"):
            return None

        scheme = parsed.scheme.lower()
        netloc = parsed.netloc.lower()

        # Path normalization: collapse multiple slashes
        path = parsed.path or "/"
        path = re.sub(r"/{2,}", "/", path)

        # Normalize trailing slash (keep root as /, but strip trailing slash for paths like /cars/ -> /cars)
        # However, for directory-like URLs, we strip trailing slash for consistency
        if len(path) > 1 and path.endswith("/"):
            path = path[:-1]

        # Query parameter normalization
        query_str = ""
        if parsed.query:
            query_pairs = urllib.parse.parse_qsl(parsed.query, keep_blank_values=True)
            filtered_pairs = [
                (k, v) for k, v in query_pairs
                if k.lower() not in TRACKING_PARAMS
            ]
            if filtered_pairs:
                # Sort query parameters for canonical consistency
                filtered_pairs.sort(key=lambda x: (x[0], x[1]))
                query_str = urllib.parse.urlencode(filtered_pairs)

        normalized = urllib.parse.urlunsplit((scheme, netloc, path, query_str, ""))
        return normalized
