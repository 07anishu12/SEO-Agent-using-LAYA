def get_laya_seo_questions():
    """
    Standardized, compact question schema for Laya MLX classification.
    """
    return {
        "category": {
            "type": "choice",
            "instructions": "Classify this SEO issue into its primary technical domain.",
            "criteria": {
                "metadata": "page titles, meta descriptions, open graph, header meta",
                "technical": "HTTP status codes, canonicals, robots, sitemaps, server latency",
                "content": "thin content, word count, duplicate text, body headings",
                "internal_linking": "broken links, orphan pages, anchor text, crawl depth",
                "structured_data": "schema.org, JSON-LD, microdata validation",
                "images": "image alt tags, image dimensions, modern formats",
                "indexability": "noindex, nofollow, indexing blockage",
                "performance": "slow loading, layout shifts, rendering delays"
            }
        },
        "severity": {
            "type": "choice",
            "instructions": "Determine the impact severity of this issue on search visibility and crawling.",
            "criteria": {
                "critical": "blocks search engine indexing or crashes page rendering",
                "high": "significantly depresses rankings across multiple important pages",
                "medium": "moderate optimization deficit or template-level inconsistency",
                "low": "minor hygiene, cosmetic, or edge-case improvement"
            }
        },
        "action": {
            "type": "choice",
            "instructions": "What is the recommended engineering action to resolve this issue?",
            "criteria": {
                "fix_template": "modify reusable frontend template or CMS theme component",
                "fix_metadata": "update metadata generation or SEO tags in layout",
                "fix_content": "enrich editorial copy, headings, or body text",
                "fix_internal_links": "update navigation, breadcrumbs, or cross-linking structure",
                "fix_schema": "correct or add structured data JSON-LD scripts",
                "fix_images": "add alt attributes or adjust image sizing/formats",
                "fix_performance": "optimize backend response time or frontend assets",
                "investigate": "requires manual diagnostic or server log inspection"
            }
        }
    }
