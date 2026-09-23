import re
import urllib.parse
from typing import List, Tuple
from bs4 import BeautifulSoup
from models.page import ImageItem
from models.issue import SEOIssue

def analyze_images(
    soup: BeautifulSoup,
    current_url: str,
    page_type: str,
    template: str
) -> Tuple[List[ImageItem], int, int, List[SEOIssue]]:
    issues: List[SEOIssue] = []
    image_items: List[ImageItem] = []

    img_tags = soup.find_all("img")
    total_images = len(img_tags)
    missing_alt_count = 0
    missing_dimensions_count = 0

    for img in img_tags:
        src = img.get("src") or img.get("data-src") or ""
        src = src.strip()
        if not src or src.startswith("data:"):
            continue

        full_src = urllib.parse.urljoin(current_url, src)
        alt = img.get("alt")
        has_alt = alt is not None and len(alt.strip()) > 0
        alt_text = alt.strip() if alt else ""

        if not has_alt:
            missing_alt_count += 1

        width = None
        height = None
        try:
            if img.get("width"):
                width = int(re.sub(r"\D", "", img.get("width")))
            if img.get("height"):
                height = int(re.sub(r"\D", "", img.get("height")))
        except Exception:
            pass

        if not width or not height:
            missing_dimensions_count += 1

        is_lazy = img.get("loading", "").lower() == "lazy"

        # Determine extension/format
        img_format = ""
        path = urllib.parse.urlparse(full_src).path.lower()
        for ext in (".webp", ".avif", ".png", ".jpg", ".jpeg", ".svg", ".gif"):
            if path.endswith(ext):
                img_format = ext[1:]
                break

        image_items.append(ImageItem(
            page_url=current_url,
            image_url=full_src,
            alt_text=alt_text[:120],
            has_alt=has_alt,
            width=width,
            height=height,
            is_lazy=is_lazy,
            image_format=img_format
        ))

    if missing_alt_count > 0:
        issues.append(SEOIssue(
            url=current_url, page_type=page_type, template=template,
            category="images", issue="missing_image_alt",
            severity="medium" if missing_alt_count > 3 else "low",
            evidence=f"Found {missing_alt_count} out of {total_images} images missing alt text.",
            recommendation="Add descriptive, keyword-relevant alt attributes to all informational images."
        ))

    if missing_dimensions_count > 3:
        issues.append(SEOIssue(
            url=current_url, page_type=page_type, template=template,
            category="images", issue="missing_image_dimensions",
            severity="low",
            evidence=f"Found {missing_dimensions_count} images without explicit width/height attributes (potential CLS impact).",
            recommendation="Specify explicit width and height attributes on <img> tags to reduce Cumulative Layout Shift."
        ))

    return image_items, total_images, missing_alt_count, issues
