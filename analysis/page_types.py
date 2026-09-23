import urllib.parse
import re
from typing import List, Optional

def infer_page_type(
    url: str,
    title: str = "",
    h1: str = "",
    schema_types: Optional[List[str]] = None,
    word_count: int = 0
) -> str:
    """
    Universally infer page type using URL path, schema signals, DOM headings, and title.
    Works across e-commerce, automotive, SaaS, blogs, finance, marketplaces, and content sites.
    """
    parsed = urllib.parse.urlsplit(url)
    path = parsed.path.lower().strip("/")
    schemas = [s.lower() for s in (schema_types or [])]
    combined_text = f"{title.lower()} {h1.lower()}"

    # 1. Homepage
    if not path or path == "":
        return "homepage"

    segments = [s for s in path.split("/") if s]

    # 2. Schema-based hints
    if any(s in schemas for s in ("vehicle", "car", "motorcycle")):
        return "vehicle"
    if "product" in schemas:
        return "product"
    if any(s in schemas for s in ("article", "newsarticle", "blogposting")):
        return "article"
    if "faqpage" in schemas and len(segments) <= 2:
        return "guide"

    # 3. Path & Keyword patterns
    first_seg = segments[0] if segments else ""
    last_seg = segments[-1] if segments else ""

    # Finance / Loans / Calculators
    if any(k in path for k in ("finance", "loan", "emi", "calculator", "interest", "credit", "insurance")):
        return "finance"

    # Comparison
    if any(k in path for k in ("compare", "vs", "versus")):
        return "comparison"

    # Search / Filter
    if any(k in path for k in ("search", "find", "filter")) or parsed.query:
        if "query" in parsed.query or "q=" in parsed.query or "search" in parsed.query:
            return "search"

    # Automotive / Vehicle models
    if any(k in path for k in ("bikes", "cars", "scooters", "vehicles", "motorcycles")):
        if len(segments) >= 3:
            return "model"
        elif len(segments) == 2:
            return "brand"
        else:
            return "category"

    # General Product / Model detection
    if any(k in path for k in ("brand", "brands", "make")):
        if len(segments) >= 2:
            return "brand"
        return "category"

    if any(k in path for k in ("model", "models", "variant", "specs", "specification")):
        return "model"

    # City / Location pages
    if any(k in path for k in ("city", "cities", "location", "locations", "dealers", "showroom", "in-")):
        return "city"
    # Indian / Global major city pattern heuristics in path (e.g. /delhi, /mumbai, /bangalore, /pune, /hyderabad)
    major_cities = {"delhi", "mumbai", "bangalore", "bengaluru", "chennai", "pune", "hyderabad", "kolkata", "ahmedabad", "jaipur", "lucknow", "chandigarh", "gurgaon", "noida"}
    if any(seg in major_cities for seg in segments):
        return "city"

    # Article / Blog / News / Guide
    if any(k in first_seg for k in ("blog", "article", "story", "news", "post", "stories", "read")):
        if len(segments) > 1:
            return "article"
        return "category"

    if any(k in path for k in ("guide", "tutorial", "how-to", "tips")):
        return "guide"

    # Documentation / Help / Support
    if any(k in first_seg for k in ("docs", "doc", "documentation", "api", "support", "help", "faq")):
        return "documentation"

    # Category / Listing
    if any(k in path for k in ("category", "categories", "listing", "collection", "collections", "all", "shop")):
        return "category"

    # Text-based hints
    if "vs" in combined_text or "compare" in combined_text:
        return "comparison"
    if "loan" in combined_text or "emi" in combined_text:
        return "finance"
    if "price, specs" in combined_text or "specifications" in combined_text:
        return "model"

    # Segment depth heuristics
    if len(segments) == 1:
        return "category"
    elif len(segments) == 2:
        return "listing"
    elif len(segments) >= 3:
        return "product"

    return "other"
