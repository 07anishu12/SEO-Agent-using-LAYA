from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional

@dataclass
class LinkItem:
    source_url: str
    target_url: str
    anchor_text: str = ""
    is_internal: bool = True
    is_nofollow: bool = False
    is_sponsored: bool = False
    is_ugc: bool = False
    status_code: Optional[int] = None

@dataclass
class ImageItem:
    page_url: str
    image_url: str
    alt_text: str = ""
    has_alt: bool = False
    width: Optional[int] = None
    height: Optional[int] = None
    is_lazy: bool = False
    image_format: str = ""

@dataclass
class SchemaItem:
    page_url: str
    schema_type: str
    is_valid: bool = True
    raw_json: str = ""
    error_message: str = ""

@dataclass
class PageData:
    url: str
    final_url: str = ""
    status_code: int = 0
    content_type: str = ""
    response_time: float = 0.0
    content_length: int = 0
    redirect_chain: List[str] = field(default_factory=list)
    crawl_timestamp: str = ""
    discovery_source: str = "seed"
    
    # Metadata
    title: str = ""
    title_length: int = 0
    title_word_count: int = 0
    description: str = ""
    description_length: int = 0
    
    # Headings
    h1_count: int = 0
    h1_text: str = ""
    h2_count: int = 0
    h2_text: List[str] = field(default_factory=list)
    h3_count: int = 0
    h3_text: List[str] = field(default_factory=list)
    
    # Robots & Indexing
    meta_robots: str = ""
    x_robots_tag: str = ""
    is_indexable: bool = True
    is_follow: bool = True
    
    # Canonical
    canonical: str = ""
    canonical_status: str = "ok"  # ok, missing, mismatch, external, self
    is_self_canonical: bool = True
    
    # Content
    word_count: int = 0
    paragraph_count: int = 0
    text_html_ratio: float = 0.0
    content_hash: str = ""
    
    # Links
    internal_links_count: int = 0
    unique_internal_links_count: int = 0
    external_links_count: int = 0
    unique_external_links_count: int = 0
    
    # Images
    images_count: int = 0
    images_missing_alt: int = 0
    
    # Structured Data & Hreflang
    schema_types: List[str] = field(default_factory=list)
    is_schema_valid: bool = True
    hreflangs: List[Dict[str, str]] = field(default_factory=list)
    
    # Inferred
    page_type: str = "other"
    template_id: str = "default"
    crawl_depth: int = 0
    is_rendered: bool = False
    error: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
