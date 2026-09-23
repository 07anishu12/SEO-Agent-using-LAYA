import re
import uuid
import hashlib
from typing import Optional, Dict, Any, Tuple
from bs4 import BeautifulSoup

COMMON_404_KEYWORDS = [
    "page not found", "404 not found", "oops! that page can’t be found",
    "the page you are looking for does not exist", "nothing here", "error 404",
    "page cannot be found", "we couldn't find that page"
]

class Soft404Detector:
    """Detects soft-404 responses returning HTTP 200 and thin HTML shells."""
    def __init__(self):
        self.probed: bool = False
        self.fingerprint_title: str = ""
        self.fingerprint_h1: str = ""
        self.fingerprint_text_sample: str = ""
        self.fingerprint_content_length: int = 0

    async def probe_site(self, fetcher, base_url: str):
        """Probes a random non-existent path to learn the site's custom 404 template signature."""
        probe_path = f"{base_url.rstrip('/')}/__seojev_probe_{uuid.uuid4().hex[:8]}"
        try:
            res = await fetcher.fetch(probe_path)
            html = res.text
            self.fingerprint_content_length = len(html)
            soup = BeautifulSoup(html, "lxml")
            title_tag = soup.find("title")
            h1_tag = soup.find("h1")
            self.fingerprint_title = (title_tag.get_text() if title_tag else "").strip().lower()
            self.fingerprint_h1 = (h1_tag.get_text() if h1_tag else "").strip().lower()
            self.fingerprint_text_sample = soup.get_text(separator=" ").strip()[:300].lower()
            self.probed = True
        except Exception:
            self.probed = False

    def is_soft_404(self, status_code: int, html: str, title: str = "", h1: str = "") -> Tuple[bool, Optional[str]]:
        """Determines if a 200 OK page is actually a soft-404 or empty shell.
        Returns: (is_soft_404: bool, reason: Optional[str])
        """
        if status_code != 200:
            return False, None

        clean_html = (html or "").strip()
        length = len(clean_html)

        # 1. Thin HTML Shell
        if length < 350:
            return True, f"Thin HTML shell (content length only {length} bytes)"

        # 2. Text-level 404 keywords in Title or H1
        title_lower = title.lower()
        h1_lower = h1.lower()
        for kw in COMMON_404_KEYWORDS:
            if kw in title_lower or kw in h1_lower:
                return True, f"Explicit 404 indicator '{kw}' found in Title/H1"

        # 3. Match against probed 404 fingerprint
        if self.probed and self.fingerprint_title and self.fingerprint_title == title_lower:
            # Check length similarity
            if abs(length - self.fingerprint_content_length) < 500:
                return True, f"Exact match with site 404 fingerprint title: '{self.fingerprint_title}'"

        return False, None
