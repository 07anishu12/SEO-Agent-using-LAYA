"""
SEOJEV Scale Test Infrastructure — synthetic site generator for 10K-500K URLs.

Extends the existing lab/ infrastructure with high-volume URL generation
for benchmarking the optimized crawler at scale.
"""
import hashlib
import json
import os
import random
import string
import time
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from typing import Dict, List, Optional, Any
from threading import Thread


# Common page templates for realistic synthetic sites
_TEMPLATES = {
    "product": {
        "title": "{brand} {model} - Price, Specs & Reviews | {site}",
        "h1": "{brand} {model}",
        "template_id": "tpl_product",
        "page_type": "product",
    },
    "category": {
        "title": "{category} - Browse All {site}",
        "h1": "All {category}",
        "template_id": "tpl_category",
        "page_type": "category",
    },
    "article": {
        "title": "{topic} - {site} Blog",
        "h1": "{topic}",
        "template_id": "tpl_article",
        "page_type": "article",
    },
    "faq": {
        "title": "FAQ: {topic} | {site}",
        "h1": "Frequently Asked Questions: {topic}",
        "template_id": "tpl_faq",
        "page_type": "faq",
    },
}

# SEO defect types to inject
_DEFECTS = [
    "missing_title",
    "missing_description",
    "missing_h1",
    "duplicate_title",
    "canonical_mismatch",
    "missing_canonical",
    "thin_content",
    "noindex_indexed",
    "broken_internal_link",
    "redirect_chain",
    "soft_404",
    "missing_alt_text",
    "missing_schema",
    "duplicate_content",
    "keyword_cannibalization",
]

_BRANDS = ["Alpha", "Bravo", "Charlie", "Delta", "Echo", "Foxtrot", "Golf"]
_CATEGORIES = ["Electronics", "Clothing", "Home", "Sports", "Books", "Auto", "Garden"]
_TOPICS = ["Best Practices", "How To Guide", "Comparison", "Review", "Tutorial", "News"]
_LOREM = (
    "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor "
    "incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud "
    "exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat. Duis aute irure "
    "dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur."
)


class ScaleSiteGenerator:
    """Generates a synthetic site with N URLs for scale testing.

    Produces:
    - sitemap.xml (with all URLs)
    - robots.txt
    - HTML pages with realistic templates and planted SEO defects
    - Ground truth manifest for validation
    """

    def __init__(
        self,
        base_url: str = "http://localhost:9999",
        num_urls: int = 10000,
        seed: int = 42,
        defect_rate: float = 0.15,
    ):
        self.base_url = base_url.rstrip("/")
        self.num_urls = num_urls
        self.seed = seed
        self.defect_rate = defect_rate
        self.rng = random.Random(seed)
        self.site_name = "ScaleTest Site"

        self.pages: Dict[str, Dict[str, Any]] = {}
        self.sitemap_urls: List[str] = []
        self.ground_truth: Dict[str, List[str]] = {}
        self._internal_links: Dict[str, List[str]] = {}

    def generate(self) -> Dict[str, Any]:
        """Generate all pages, sitemap, and ground truth."""
        t0 = time.monotonic()

        # 1. Generate URLs by template type
        template_dist = {
            "product": 0.50,
            "category": 0.15,
            "article": 0.25,
            "faq": 0.10,
        }

        url_id = 0
        for tpl_type, ratio in template_dist.items():
            count = int(self.num_urls * ratio)
            for i in range(count):
                url_id += 1
                url, page = self._generate_page(url_id, tpl_type)
                self.pages[url] = page
                self.sitemap_urls.append(url)

        # Fill remaining to exact num_urls
        while len(self.pages) < self.num_urls:
            url_id += 1
            tpl_type = self.rng.choice(list(template_dist.keys()))
            url, page = self._generate_page(url_id, tpl_type)
            self.pages[url] = page
            self.sitemap_urls.append(url)

        # 2. Generate internal link graph (each page links to 3-8 others)
        all_urls = list(self.pages.keys())
        for url in all_urls:
            num_links = self.rng.randint(3, 8)
            targets = self.rng.sample(all_urls, min(num_links, len(all_urls)))
            self._internal_links[url] = [t for t in targets if t != url]

        # 3. Homepage
        home_url = f"{self.base_url}/"
        self.pages[home_url] = {
            "url": home_url,
            "status_code": 200,
            "title": f"{self.site_name} - Home",
            "h1": f"Welcome to {self.site_name}",
            "page_type": "homepage",
            "template_id": "tpl_homepage",
            "defects": [],
            "html": self._build_html(
                f"{self.site_name} - Home",
                f"Welcome to {self.site_name}",
                f"<p>{_LOREM}</p>" * 3,
                home_url,
                all_urls[:20],
            ),
        }
        self.sitemap_urls.insert(0, home_url)

        elapsed = time.monotonic() - t0
        return {
            "total_urls": len(self.pages),
            "sitemap_urls": len(self.sitemap_urls),
            "defect_count": sum(len(d) for d in self.ground_truth.values()),
            "generation_time_sec": round(elapsed, 2),
            "templates": {
                tpl: sum(1 for p in self.pages.values() if p.get("template_id") == f"tpl_{tpl}")
                for tpl in template_dist
            },
        }

    def _generate_page(self, url_id: int, tpl_type: str):
        """Generate a single page with optional defects."""
        tpl = _TEMPLATES[tpl_type]
        brand = self.rng.choice(_BRANDS)
        model = f"Model-{url_id:05d}"
        category = self.rng.choice(_CATEGORIES)
        topic = self.rng.choice(_TOPICS)

        slug = f"{tpl_type}/{brand.lower()}-{model.lower()}"
        url = f"{self.base_url}/{slug}"

        title = tpl["title"].format(brand=brand, model=model, category=category, topic=topic, site=self.site_name)
        h1 = tpl["h1"].format(brand=brand, model=model, category=category, topic=topic)

        # Decide defects
        defects = []
        if self.rng.random() < self.defect_rate:
            num_defects = self.rng.randint(1, 3)
            defects = self.rng.sample(_DEFECTS, min(num_defects, len(_DEFECTS)))
            self.ground_truth[url] = defects

        # Build HTML with defects applied
        content = f"<p>{_LOREM}</p>" * self.rng.randint(2, 8)
        if "thin_content" in defects:
            content = "<p>Short.</p>"
        if "missing_title" in defects:
            title = ""
        if "missing_h1" in defects:
            h1 = ""

        canonical = url
        if "canonical_mismatch" in defects:
            canonical = url + "-wrong"
        elif "missing_canonical" in defects:
            canonical = ""

        html = self._build_html(title, h1, content, canonical, [])

        page = {
            "url": url,
            "status_code": 200,
            "title": title,
            "h1": h1,
            "page_type": tpl["page_type"],
            "template_id": tpl["template_id"],
            "defects": defects,
            "html": html,
        }
        return url, page

    def _build_html(self, title: str, h1: str, content: str, canonical: str, links: List[str]) -> str:
        """Build a realistic HTML page."""
        title_tag = f"<title>{title}</title>" if title else ""
        h1_tag = f"<h1>{h1}</h1>" if h1 else ""
        canonical_tag = f'<link rel="canonical" href="{canonical}" />' if canonical else ""
        desc = title[:160] if title else ""
        desc_tag = f'<meta name="description" content="{desc}" />' if desc else ""

        nav_links = "\n".join(f'<a href="{u}">Link</a>' for u in links[:10])

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    {title_tag}
    {desc_tag}
    {canonical_tag}
    <meta charset="UTF-8">
</head>
<body>
    {h1_tag}
    {content}
    <nav>{nav_links}</nav>
</body>
</html>"""

    def get_sitemap_xml(self) -> str:
        """Generate sitemap XML for all URLs."""
        entries = "\n".join(
            f"  <url><loc>{url}</loc></url>" for url in self.sitemap_urls
        )
        return f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
{entries}
</urlset>"""

    def get_robots_txt(self) -> str:
        """Generate robots.txt."""
        return f"""User-agent: *
Allow: /
Sitemap: {self.base_url}/sitemap.xml
"""


class ScaleTestServer:
    """HTTP server that serves a synthetic scale test site.

    Designed to serve 10K-500K URLs with minimal latency for benchmarking.
    """

    def __init__(self, generator: ScaleSiteGenerator, port: int = 9999):
        self.generator = generator
        self.port = port
        self._server: Optional[HTTPServer] = None
        self._thread: Optional[Thread] = None

    def start(self):
        """Start the test server in a background thread."""
        pages = self.generator.pages
        sitemap_xml = self.generator.get_sitemap_xml()
        robots_txt = self.generator.get_robots_txt()
        base_url = self.generator.base_url

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                url = f"{base_url}{self.path}"

                if self.path == "/robots.txt":
                    self.send_response(200)
                    self.send_header("Content-Type", "text/plain")
                    self.end_headers()
                    self.wfile.write(robots_txt.encode())
                elif self.path == "/sitemap.xml":
                    self.send_response(200)
                    self.send_header("Content-Type", "application/xml")
                    self.end_headers()
                    self.wfile.write(sitemap_xml.encode())
                elif url in pages:
                    page = pages[url]
                    self.send_response(page.get("status_code", 200))
                    self.send_header("Content-Type", "text/html; charset=utf-8")
                    content_bytes = page["html"].encode()
                    content_hash = hashlib.sha256(content_bytes).hexdigest()[:16]
                    self.send_header("ETag", f'"{content_hash}"')
                    self.send_header("Content-Length", str(len(content_bytes)))
                    self.end_headers()
                    self.wfile.write(content_bytes)
                else:
                    self.send_response(404)
                    self.send_header("Content-Type", "text/html")
                    self.end_headers()
                    self.wfile.write(b"<html><body><h1>404 Not Found</h1></body></html>")

            def log_message(self, format, *args):
                pass  # Suppress logging for benchmark speed

        self._server = ThreadingHTTPServer(("127.0.0.1", self.port), Handler)
        self._thread = Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()
        print(f"Scale test server running on http://127.0.0.1:{self.port} ({len(pages):,} URLs)")

    def stop(self):
        """Stop the test server."""
        if self._server:
            self._server.shutdown()
            self._server = None
        print("Scale test server stopped.")
