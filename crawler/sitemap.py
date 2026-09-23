import re
import urllib.parse
from typing import List, Dict, Any, Set, Tuple
import httpx
from bs4 import BeautifulSoup

class SitemapParser:
    def __init__(self, normalizer):
        self.normalizer = normalizer
        self.discovered_urls: Set[str] = set()
        self.sitemap_records: List[Dict[str, Any]] = []
        self.processed_sitemaps: Set[str] = set()

    async def discover_all(self, client: httpx.AsyncClient, sitemap_seeds: List[str]) -> Tuple[List[str], List[Dict[str, Any]]]:
        """
        Recursively fetch and parse sitemap indexes and sitemaps.
        Returns list of normalized discovered URLs and detailed sitemap records.
        """
        queue = list(sitemap_seeds)
        while queue:
            sitemap_url = queue.pop(0)
            if sitemap_url in self.processed_sitemaps:
                continue
            self.processed_sitemaps.add(sitemap_url)

            record = {
                "url": sitemap_url,
                "status_code": 0,
                "is_valid": False,
                "url_count": 0,
                "type": "unknown",
                "error": ""
            }

            try:
                resp = await client.get(sitemap_url, timeout=15.0, follow_redirects=True)
                record["status_code"] = resp.status_code
                if resp.status_code != 200:
                    record["error"] = f"HTTP {resp.status_code}"
                    self.sitemap_records.append(record)
                    continue

                content = resp.text
                if "<sitemapindex" in content:
                    record["type"] = "sitemapindex"
                    record["is_valid"] = True
                    # Find nested sitemaps
                    sub_sitemaps = re.findall(r"<loc>(.*?)</loc>", content, re.IGNORECASE)
                    record["url_count"] = len(sub_sitemaps)
                    for sub in sub_sitemaps:
                        sub = sub.strip()
                        if sub and sub not in self.processed_sitemaps:
                            queue.append(sub)
                elif "<urlset" in content or "<loc>" in content:
                    record["type"] = "urlset"
                    record["is_valid"] = True
                    locs = re.findall(r"<loc>(.*?)</loc>", content, re.IGNORECASE)
                    record["url_count"] = len(locs)
                    for loc in locs:
                        loc = loc.strip()
                        norm = self.normalizer.normalize(loc)
                        if norm and self.normalizer.is_same_domain(norm) and self.normalizer.is_crawlable_page(norm):
                            self.discovered_urls.add(norm)
                else:
                    record["error"] = "Unrecognized XML/Sitemap format"

            except Exception as e:
                record["error"] = str(e)

            self.sitemap_records.append(record)

        return sorted(list(self.discovered_urls)), self.sitemap_records
