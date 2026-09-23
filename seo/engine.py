from typing import List, Tuple, Dict, Any, Optional
from bs4 import BeautifulSoup
from models.page import PageData, LinkItem, ImageItem, SchemaItem
from models.issue import SEOIssue
from .metadata import analyze_metadata
from .headings import analyze_headings
from .content import analyze_content
from .links import analyze_links
from .images import analyze_images
from .canonical import analyze_canonical
from .robots_meta import analyze_robots_meta
from .schema import analyze_schemas
from .hreflang import analyze_hreflang
from .urls import analyze_url_quality
from .technical import analyze_technical

class SEOEngine:
    def __init__(self, normalizer):
        self.normalizer = normalizer

    def process_page(
        self,
        url: str,
        final_url: str,
        status_code: int,
        content_type: str,
        response_time: float,
        content_length: int,
        redirect_chain: List[str],
        headers: Dict[str, str],
        html: str,
        discovery_source: str = "seed",
        page_type: str = "other",
        template_id: str = "default",
        crawl_depth: int = 0,
        is_rendered: bool = False,
        error: str = ""
    ) -> Tuple[PageData, List[LinkItem], List[ImageItem], List[SchemaItem], List[SEOIssue]]:
        issues: List[SEOIssue] = []
        links: List[LinkItem] = []
        images: List[ImageItem] = []
        schemas: List[SchemaItem] = []

        # 1. Technical issues on status code and response
        tech_issues = analyze_technical(
            url=url,
            status_code=status_code,
            redirect_chain=redirect_chain,
            response_time=response_time,
            content_type=content_type,
            page_type=page_type,
            template=template_id
        )
        issues.extend(tech_issues)

        # 2. URL quality checks
        url_issues = analyze_url_quality(url, page_type, template_id)
        issues.extend(url_issues)

        # If non-200 or non-HTML, create minimal page record
        if status_code != 200 or "text/html" not in content_type:
            page = PageData(
                url=url,
                final_url=final_url,
                status_code=status_code,
                content_type=content_type,
                response_time=response_time,
                content_length=content_length,
                redirect_chain=redirect_chain,
                discovery_source=discovery_source,
                page_type=page_type,
                template_id=template_id,
                crawl_depth=crawl_depth,
                is_rendered=is_rendered,
                error=error,
                is_indexable=False if status_code >= 400 else True
            )
            return page, links, images, schemas, issues

        # Parse HTML with BeautifulSoup (using lxml for speed)
        try:
            soup = BeautifulSoup(html, "lxml")
        except Exception:
            soup = BeautifulSoup(html, "html.parser")

        # 3. Metadata
        title, t_len, t_words, desc, d_len, meta_issues = analyze_metadata(soup, url, page_type, template_id)
        issues.extend(meta_issues)

        # 4. Headings
        h1_cnt, h1_txt, h2_cnt, h2_txts, h3_cnt, h3_txts, head_issues = analyze_headings(soup, url, page_type, template_id)
        issues.extend(head_issues)

        # 5. Content
        w_cnt, p_cnt, ratio, c_hash, content_issues = analyze_content(soup, html, url, page_type, template_id)
        issues.extend(content_issues)

        # 6. Canonical
        canonical_url, can_status, is_self_can, can_issues = analyze_canonical(soup, url, self.normalizer, page_type, template_id)
        issues.extend(can_issues)

        # 7. Robots Meta
        meta_rob, x_rob, is_idx, is_fllw, rob_issues = analyze_robots_meta(soup, headers, url, page_type, template_id, discovery_source)
        issues.extend(rob_issues)

        # 8. Links
        links, in_cnt, u_in_cnt, ex_cnt, u_ex_cnt, link_issues = analyze_links(soup, url, self.normalizer, page_type, template_id)
        issues.extend(link_issues)

        # 9. Images
        images, img_total, img_missing_alt, img_issues = analyze_images(soup, url, page_type, template_id)
        issues.extend(img_issues)

        # 10. Schema
        schemas, schema_types, is_sch_valid, schema_issues = analyze_schemas(soup, url, page_type, template_id)
        issues.extend(schema_issues)

        # 11. Hreflang
        hreflangs, href_issues = analyze_hreflang(soup, url, page_type, template_id)
        issues.extend(href_issues)

        page = PageData(
            url=url,
            final_url=final_url,
            status_code=status_code,
            content_type=content_type,
            response_time=response_time,
            content_length=content_length,
            redirect_chain=redirect_chain,
            discovery_source=discovery_source,
            title=title,
            title_length=t_len,
            title_word_count=t_words,
            description=desc,
            description_length=d_len,
            h1_count=h1_cnt,
            h1_text=h1_txt,
            h2_count=h2_cnt,
            h2_text=h2_txts,
            h3_count=h3_cnt,
            h3_text=h3_txts,
            meta_robots=meta_rob,
            x_robots_tag=x_rob,
            is_indexable=is_idx,
            is_follow=is_fllw,
            canonical=canonical_url,
            canonical_status=can_status,
            is_self_canonical=is_self_can,
            word_count=w_cnt,
            paragraph_count=p_cnt,
            text_html_ratio=ratio,
            content_hash=c_hash,
            internal_links_count=in_cnt,
            unique_internal_links_count=u_in_cnt,
            external_links_count=ex_cnt,
            unique_external_links_count=u_ex_cnt,
            images_count=img_total,
            images_missing_alt=img_missing_alt,
            schema_types=schema_types,
            is_schema_valid=is_sch_valid,
            hreflangs=hreflangs,
            page_type=page_type,
            template_id=template_id,
            crawl_depth=crawl_depth,
            is_rendered=is_rendered,
            error=error
        )

        return page, links, images, schemas, issues
