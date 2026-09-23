import random
from typing import List, Dict, Any, Set
from collections import defaultdict

def select_performance_sample(pages: List[Dict[str, Any]], sample_size: int = 100, homepage_url: str = "") -> List[Dict[str, Any]]:
    """
    Selects a stratified representative sample of pages:
    - Homepage (always included)
    - Top pages from each page type and template
    - Top slowest response time pages
    - Top largest content size pages
    """
    if len(pages) <= sample_size:
        return pages

    selected_urls: Set[str] = set()
    sample: List[Dict[str, Any]] = []

    # 1. Homepage
    for p in pages:
        if p["url"] == homepage_url or p.get("page_type") == "homepage":
            selected_urls.add(p["url"])
            sample.append(p)
            break

    # 2. Slowest pages (top 10%)
    sorted_by_resp = sorted(pages, key=lambda x: x.get("response_time", 0.0), reverse=True)
    slow_count = max(2, int(sample_size * 0.15))
    for p in sorted_by_resp:
        if p["url"] not in selected_urls and p.get("status_code") == 200:
            selected_urls.add(p["url"])
            sample.append(p)
            if len(sample) >= slow_count + 1:
                break

    # 3. Largest pages (top 10%)
    sorted_by_size = sorted(pages, key=lambda x: x.get("content_length", 0), reverse=True)
    large_count = max(2, int(sample_size * 0.15))
    for p in sorted_by_size:
        if p["url"] not in selected_urls and p.get("status_code") == 200:
            selected_urls.add(p["url"])
            sample.append(p)
            if len(sample) >= slow_count + large_count + 1:
                break

    # 4. Stratified selection across page_type and template
    by_type = defaultdict(list)
    for p in pages:
        if p.get("status_code") == 200:
            by_type[p.get("page_type", "other")].append(p)

    remaining_slots = sample_size - len(sample)
    if remaining_slots > 0 and by_type:
        slots_per_type = max(2, remaining_slots // len(by_type))
        for p_type, t_pages in by_type.items():
            for p in t_pages:
                if p["url"] not in selected_urls:
                    selected_urls.add(p["url"])
                    sample.append(p)
                    if len(sample) >= sample_size:
                        break
            if len(sample) >= sample_size:
                break

    # 5. Fill remaining with random sample if still under limit
    if len(sample) < sample_size:
        available = [p for p in pages if p["url"] not in selected_urls and p.get("status_code") == 200]
        random.shuffle(available)
        sample.extend(available[: sample_size - len(sample)])

    return sample
