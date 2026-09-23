import re
import urllib.parse
from typing import Dict, Any, List, Tuple, Set
from collections import Counter

class TemplateMiner:
    """Discovers template families via URL pattern mining, DOM structure hashing, and section signatures."""
    def __init__(self):
        self.templates: Dict[str, Dict[str, Any]] = {}

    def extract_url_signature(self, url: str) -> str:
        """Converts URL into a generic path pattern replacing numbers, IDs, and dynamic slugs with placeholders."""
        parsed = urllib.parse.urlsplit(url)
        path = parsed.path.strip("/")
        if not path:
            return "tpl_home"

        segments = path.split("/")
        pattern_segs = []
        for seg in segments:
            # Check if pure number or ID
            if re.match(r"^\d+$", seg):
                pattern_segs.append("{id}")
            elif re.search(r"\d{4}-\d{2}-\d{2}", seg):
                pattern_segs.append("{date}")
            elif any(c.isdigit() for c in seg) and len(seg) > 8:
                pattern_segs.append("{slug_id}")
            else:
                pattern_segs.append(seg)

        # First segment determines the primary namespace
        primary = pattern_segs[0]
        depth = len(pattern_segs)
        return f"tpl_{primary}_{depth}seg"

    def compute_dom_skeleton_hash(self, html: str) -> str:
        """Computes a structural SimHash of the HTML tag skeleton, stripping text content and attributes."""
        import hashlib
        # Extract tag names in order of appearance
        tag_matches = re.findall(r"<([a-z0-9]+)[^>]*>", (html or "").lower())
        structural_tags = [t for t in tag_matches if t not in ("script", "style", "svg", "path", "meta", "link", "br", "hr")]
        tag_stream = ",".join(structural_tags[:150]) # First 150 structural tags
        return hashlib.sha256(tag_stream.encode("utf-8")).hexdigest()[:12]

    def cluster_pages(self, pages: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """Groups pages into template clusters with member counts, sample URLs, and structural confidence."""
        clusters: Dict[str, List[Dict[str, Any]]] = {}

        for p in pages:
            url = p.get("url", "")
            tpl_id = p.get("template_id") or self.extract_url_signature(url)
            clusters.setdefault(tpl_id, []).append(p)

        results = {}
        for tpl_id, members in clusters.items():
            sample_urls = [m["url"] for m in members[:5]]
            page_types = Counter(m.get("page_type", "other") for m in members)
            dominant_type = page_types.most_common(1)[0][0] if page_types else "other"

            results[tpl_id] = {
                "template_id": tpl_id,
                "member_count": len(members),
                "dominant_page_type": dominant_type,
                "sample_urls": sample_urls,
                "canonical_url_pattern": self.extract_url_signature(sample_urls[0]) if sample_urls else tpl_id,
                "confidence": round(page_types.most_common(1)[0][1] / len(members), 2) if members else 1.0
            }

        self.templates = results
        return results
