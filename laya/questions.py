def get_laya_seo_questions():
    """
    Standardized, compact question schema for Laya MLX classification.
    """
    return {
        "verdict": {
            "type": "choice",
            "instructions": "Decide whether the deterministic evidence is a real SEO issue or noise.",
            "criteria": {"real_issue": "evidence supports a search visibility or crawl problem", "noise": "no actionable SEO impact or detector false positive"}
        },
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
        "scope": {
            "type": "choice",
            "instructions": "Choose the smallest scope that explains the evidence.",
            "criteria": {"page": "one URL", "template": "shared template or repeated page pattern", "site": "site-wide configuration or architecture"}
        },
        "root_cause": {
            "type": "choice",
            "instructions": "Choose the primary root cause category.",
            "criteria": {"technical": "crawl, status, canonical, robots, or indexability", "content": "thin, duplicate, or intent mismatch content", "architecture": "template, internal linking, or site structure"}
        },
        "canonical_indexability": {
            "type": "choice",
            "instructions": "Assess canonical and indexability evidence.",
            "criteria": {"valid": "canonical and indexability are aligned", "fix": "canonical or indexability needs correction", "blocked": "indexability is intentionally or accidentally blocked"}
        },
        "content_assessment": {
            "type": "choice",
            "instructions": "Assess thin or duplicate content evidence.",
            "criteria": {"healthy": "content is sufficiently unique and useful", "thin": "content depth is insufficient", "duplicate": "content substantially repeats another page"}
        },
        "cannibalization": {
            "type": "choice",
            "instructions": "Assess whether pages compete for the same intent.",
            "criteria": {"none": "no competing intent evidence", "possible": "some overlap needs review", "confirmed": "multiple pages compete for the same intent"}
        },
        "internal_linking": {
            "type": "choice",
            "instructions": "Assess internal link coverage, orphaning, depth, and anchor signals.",
            "criteria": {"healthy": "link coverage is sufficient", "fix": "orphan, depth, or anchor evidence requires action"}
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
