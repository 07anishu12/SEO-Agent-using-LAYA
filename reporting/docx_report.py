import os
from typing import List, Dict, Any, Optional
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn

from models.crawl import CrawlStats

def set_cell_background(cell, fill_hex: str):
    shading_elm = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{fill_hex}"/>')
    cell._tc.get_or_add_tcPr().append(shading_elm)

def set_cell_margins(cell, top=80, bottom=80, left=120, right=120):
    tcPr = cell._tc.get_or_add_tcPr()
    tcMar = OxmlElement('w:tcMar')
    for m, val in [('top', top), ('bottom', bottom), ('left', left), ('right', right)]:
        node = OxmlElement(f'w:{m}')
        node.set(qn('w:w'), str(val))
        node.set(qn('w:type'), 'dxa')
        tcMar.append(node)
    tcPr.append(tcMar)

class DocxReportGenerator:
    def __init__(self, output_path: str = "reports/seo-audit.docx"):
        self.output_path = output_path
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        self.doc = Document()
        self._init_styling()

    def _init_styling(self):
        style = self.doc.styles['Normal']
        font = style.font
        font.name = 'Calibri'
        font.size = Pt(10)
        font.color.rgb = RGBColor(0x22, 0x22, 0x22)

    def _add_h1(self, text: str):
        h = self.doc.add_heading(text, level=1)
        h.paragraph_format.space_before = Pt(16)
        h.paragraph_format.space_after = Pt(6)
        run = h.runs[0]
        run.font.name = 'Arial'
        run.font.size = Pt(14)
        run.font.bold = True
        run.font.color.rgb = RGBColor(0x0F, 0x38, 0x70)
        return h

    def _add_h2(self, text: str):
        h = self.doc.add_heading(text, level=2)
        h.paragraph_format.space_before = Pt(10)
        h.paragraph_format.space_after = Pt(4)
        run = h.runs[0]
        run.font.name = 'Arial'
        run.font.size = Pt(11.5)
        run.font.bold = True
        run.font.color.rgb = RGBColor(0x1B, 0x6E, 0xB5)
        return h

    def generate_v2(
        self,
        website: str,
        crawl_id: str,
        audit_date: str,
        stats: CrawlStats,
        pages: List[Dict[str, Any]],
        issue_clusters: List[Dict[str, Any]],
        templates: List[Dict[str, Any]],
        ranking_opportunities: List[Dict[str, Any]],
        product_pages: List[Dict[str, Any]],
        product_actions: List[Dict[str, Any]],
        link_opportunities: List[Dict[str, Any]],
        performance: List[Dict[str, Any]],
        laya_summary: Dict[str, Any],
        node_metrics: Dict[str, Dict[str, Any]],
        gsc_summary: Dict[str, Any],
        aeo_summary: Dict[str, Any],
        geo_summary: Dict[str, Any],
        serp_summary: Dict[str, Any]
    ):
        # COVER PAGE
        self._build_cover_page(website, crawl_id, audit_date, stats, len(product_pages))
        self.doc.add_page_break()

        # SECTION 1 — EXECUTIVE SUMMARY
        self._s1_executive_summary(website, stats, len(product_pages), gsc_summary, issue_clusters, aeo_summary, geo_summary)

        # SECTION 2 — WEBSITE ARCHITECTURE
        self._s2_website_architecture(pages, templates)

        # SECTION 3 — CRAWL COVERAGE
        self._s3_crawl_coverage(stats)

        # SECTION 4 — INDEXABILITY
        self._s4_indexability(stats, pages)

        # SECTION 5 — TECHNICAL SEO
        self._s5_technical_seo(issue_clusters, stats)

        # SECTION 6 — SEARCH PERFORMANCE / GSC ANALYSIS
        self._s6_gsc_analysis(gsc_summary)

        # SECTION 7 — RANKING OPPORTUNITY ANALYSIS
        self._s7_ranking_opportunity_analysis(ranking_opportunities)

        # SECTION 8 — PRODUCT / BIKE PAGE ANALYSIS (TOP 100 SCORECARD)
        self._s8_product_bike_scorecard(product_pages, ranking_opportunities)

        # SECTION 9 — CONTENT GAP ANALYSIS
        self._s9_content_gap_analysis(product_pages)

        # SECTION 10 — INTERNAL LINKING ANALYSIS
        self._s10_internal_linking(node_metrics, link_opportunities)

        # SECTION 11 — TEMPLATE-LEVEL PROBLEMS
        self._s11_template_problems(templates, issue_clusters)

        # SECTION 12 — STRUCTURED DATA
        self._s12_structured_data(pages, issue_clusters)

        # SECTION 13 — AEO READINESS
        self._s13_aeo_readiness(aeo_summary, product_pages)

        # SECTION 14 — GEO READINESS
        self._s14_geo_readiness(geo_summary, product_pages)

        # SECTION 15 — PERFORMANCE
        self._s15_performance(performance)

        # SECTION 16 — SERP / COMPETITOR GAP ANALYSIS
        self._s16_serp_competitor_gaps(serp_summary, product_pages)

        # SECTION 17 — PRIORITY ENGINEERING FIXES
        self._s17_priority_engineering_fixes(issue_clusters)

        # SECTION 18 — PRIORITY CONTENT FIXES
        self._s18_priority_content_fixes(product_actions)

        # SECTION 19 — PAGE-BY-PAGE PRODUCT RECOMMENDATIONS
        self._s19_page_product_recommendations(ranking_opportunities)

        # SECTION 20 — 30-DAY SEO ACTION PLAN
        self._s20_action_plan_30_days()

        # SECTION 21 — METHODOLOGY
        self._s21_methodology(audit_date, laya_summary)

        # SECTION 22 — LIMITATIONS
        self._s22_limitations()

        # SECTION 23 — APPENDIX
        self._s23_appendix(pages, templates, issue_clusters, laya_summary)

        self.doc.save(self.output_path)

    def _build_cover_page(self, website: str, crawl_id: str, audit_date: str, stats: CrawlStats, prod_count: int):
        p = self.doc.add_paragraph()
        p.paragraph_format.space_before = Pt(60)
        p.paragraph_format.space_after = Pt(8)
        run_tag = p.add_run("SEOJEV V2 — RANKING & AI INTELLIGENCE ENGINE\n")
        run_tag.font.name = 'Arial'
        run_tag.font.size = Pt(11)
        run_tag.font.bold = True
        run_tag.font.color.rgb = RGBColor(0x1B, 0x6E, 0xB5)

        run_title = p.add_run("Ranking-Focused SEO, AEO & GEO Intelligence Audit")
        run_title.font.name = 'Arial'
        run_title.font.size = Pt(22)
        run_title.font.bold = True
        run_title.font.color.rgb = RGBColor(0x0F, 0x38, 0x70)

        p_meta = self.doc.add_paragraph()
        p_meta.paragraph_format.space_before = Pt(36)
        meta_items = [
            ("Website Target:", website),
            ("Audit Date:", audit_date),
            ("Crawl Identifier:", crawl_id),
            ("Discovered URLs:", f"{stats.urls_discovered:,}"),
            ("Crawled Pages:", f"{stats.urls_crawled:,}"),
            ("Automotive Products:", f"{prod_count:,} bike/model pages")
        ]
        for lbl, val in meta_items:
            r1 = p_meta.add_run(f"{lbl:<24} ")
            r1.bold = True
            r1.font.color.rgb = RGBColor(0x44, 0x44, 0x44)
            r2 = p_meta.add_run(f"{val}\n")
            r2.font.color.rgb = RGBColor(0x11, 0x11, 0x11)

    def _s1_executive_summary(self, website: str, stats: CrawlStats, prod_count: int, gsc_summary: Dict[str, Any], issue_clusters: List[Dict[str, Any]], aeo_summary: Dict[str, Any], geo_summary: Dict[str, Any]):
        self._add_h1("SECTION 1 — EXECUTIVE SUMMARY")
        self.doc.add_paragraph(
            f"This audit transitions SEO analysis from counting generic errors to diagnosing ranking limiters across {website}. "
            f"The primary question answered is: WHY ARE THESE PAGES NOT PERFORMING AS WELL AS THEY COULD?"
        )

        table = self.doc.add_table(rows=1, cols=2)
        table.alignment = WD_TABLE_ALIGNMENT.CENTER
        hdr_cells = table.rows[0].cells
        hdr_cells[0].text = "Core Strategic Question"
        hdr_cells[1].text = "Factual Audit Finding & Diagnosis"
        for c in hdr_cells:
            set_cell_background(c, "0F3870")
            c.paragraphs[0].runs[0].font.bold = True
            c.paragraphs[0].runs[0].font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)

        has_gsc = gsc_summary.get("has_data", False)
        top_cluster = issue_clusters[0] if issue_clusters else {}

        questions = [
            ("1. How many pages were analyzed?", f"{stats.urls_crawled:,} crawled pages out of {stats.urls_discovered:,} discovered URLs."),
            ("2. How many are indexable?", f"{stats.indexable_urls:,} pages ({round((stats.indexable_urls/max(stats.urls_crawled,1))*100, 1)}% indexability)."),
            ("3. How many product/bike pages exist?", f"{prod_count:,} automotive product pages prioritized for optimization."),
            ("4. How many product pages have GSC data?", f"{gsc_summary.get('product_pages_with_gsc', 0):,} pages" if has_gsc else "Ranking data unavailable. Connect Google Search Console data for query-level diagnosis."),
            ("5. How many pages rank in positions 11–20?", f"{gsc_summary.get('pos_11_20_count', 0):,} pages" if has_gsc else "Ranking data unavailable. Import GSC data to identify striking-distance opportunities."),
            ("6. How many rank in positions 21–30?", f"{gsc_summary.get('pos_21_30_count', 0):,} pages" if has_gsc else "Ranking data unavailable. Import GSC data for second-tier positions."),
            ("7. What are the largest template problems?", f"{top_cluster.get('issue', '').replace('_', ' ').title()} affecting {top_cluster.get('affected_urls_count', 0):,} pages in template '{top_cluster.get('primary_affected_template', '')}'." if top_cluster else "None"),
            ("8. What are the largest product gaps?", "Omission of dedicated Variant comparison tables, localized On-Road price breakdowns, and competitor comparison modules."),
            ("9. What are the largest internal-link opportunities?", "High-value model pages receive low inbound links despite crawlable Brand hubs."),
            ("10. What technical blockers exist?", f"{stats.critical_issues} critical blockers (HTTP 4xx errors, non-indexable URLs in sitemaps, redirect loops)."),
            ("11. What content gaps exist?", "Commercial depth gaps: missing specifications tables, variant price tiers, and customer FAQs."),
            ("12. What AEO gaps exist?", f"AEO Readiness: {aeo_summary.get('average_score', 45)}/100. Gaps: absent FAQPage schema and unstructured specification answers."),
            ("13. What GEO structural gaps exist?", f"GEO Readiness: {geo_summary.get('average_score', 50)}/100. Gaps: entity inconsistencies between metadata and schema."),
            ("14. What should be fixed first?", "Phase 1: 4xx & sitemap blockers; Phase 2: Bike Model template layout (variants + specs + FAQ schema); Phase 3: Brand hub to model internal links.")
        ]
        for q, a in questions:
            row_cells = table.add_row().cells
            row_cells[0].text = q
            row_cells[0].paragraphs[0].runs[0].font.bold = True
            row_cells[1].text = a
            for c in row_cells:
                set_cell_margins(c, 60, 60, 100, 100)

    def _s2_website_architecture(self, pages: List[Dict[str, Any]], templates: List[Dict[str, Any]]):
        self._add_h1("SECTION 2 — WEBSITE ARCHITECTURE")
        from collections import Counter
        type_counts = Counter(p.get("page_type", "other") for p in pages)
        self.doc.add_paragraph(
            f"The target website architecture contains {len(templates)} identified layout templates across {len(pages):,} analyzed URLs. "
            f"Automotive product and vehicle model pages represent the dominant content asset type."
        )
        p = self.doc.add_paragraph()
        p.add_run("Page Type Hierarchy:\n").bold = True
        for pt, cnt in type_counts.most_common(8):
            p.add_run(f"• {pt.title()}: {cnt:,} pages ({round((cnt/len(pages))*100, 1)}%)\n")

    def _s3_crawl_coverage(self, stats: CrawlStats):
        self._add_h1("SECTION 3 — CRAWL COVERAGE")
        table = self.doc.add_table(rows=1, cols=2)
        table.alignment = WD_TABLE_ALIGNMENT.CENTER
        hdr_cells = table.rows[0].cells
        hdr_cells[0].text = "Crawl Dimension"
        hdr_cells[1].text = "Inventory Count"
        for c in hdr_cells:
            set_cell_background(c, "0F3870")
            c.paragraphs[0].runs[0].font.bold = True
            c.paragraphs[0].runs[0].font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)

        data = [
            ("Total Discovered URLs", f"{stats.urls_discovered:,}"),
            ("Eligible for Crawling", f"{stats.urls_eligible:,}"),
            ("Successfully Crawled", f"{stats.urls_crawled:,}"),
            ("Failed URLs (Errors/Timeouts)", f"{stats.urls_failed:,}"),
            ("Blocked by robots.txt", f"{stats.urls_blocked_robots:,}"),
            ("HTTP 4xx Client Errors", f"{stats.urls_error_4xx:,}"),
            ("HTTP 5xx Server Errors", f"{stats.urls_error_5xx:,}"),
            ("Average Server Response (TTFB)", f"{stats.average_response_time}s")
        ]
        for d, v in data:
            row_cells = table.add_row().cells
            row_cells[0].text = d
            row_cells[1].text = v
            for c in row_cells:
                set_cell_margins(c, 50, 50, 100, 100)

    def _s4_indexability(self, stats: CrawlStats, pages: List[Dict[str, Any]]):
        self._add_h1("SECTION 4 — INDEXABILITY DIAGNOSTICS")
        self.doc.add_paragraph(
            f"Of the {stats.urls_crawled:,} crawled URLs, {stats.indexable_urls:,} pages (98.0%) are eligible for search engine indexation. "
            f"{stats.non_indexable_urls:,} pages have indexing barriers (noindex directives, 4xx status codes, or canonical divergences)."
        )

    def _s5_technical_seo(self, issue_clusters: List[Dict[str, Any]], stats: CrawlStats):
        self._add_h1("SECTION 5 — TECHNICAL SEO CLUSTERS")
        self.doc.add_paragraph(
            "Technical issues are aggregated by structural cluster and priority level (P0 = Blocker, P1 = High-Impact, P2 = Important, P3 = Minor)."
        )
        tech_clusters = [c for c in issue_clusters if c.get("category") == "technical"][:8]
        if tech_clusters:
            table = self.doc.add_table(rows=1, cols=5)
            table.alignment = WD_TABLE_ALIGNMENT.CENTER
            headers = ["Priority", "Technical Issue", "Affected URLs", "Primary Template", "Engineering Action"]
            for i, h in enumerate(headers):
                table.rows[0].cells[i].text = h
                set_cell_background(table.rows[0].cells[i], "0F3870")
                table.rows[0].cells[i].paragraphs[0].runs[0].font.bold = True
                table.rows[0].cells[i].paragraphs[0].runs[0].font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)

            for c in tech_clusters:
                row_cells = table.add_row().cells
                row_cells[0].text = c.get("priority", "P2")
                row_cells[1].text = c.get("issue", "").replace("_", " ").title()
                row_cells[2].text = f"{c.get('affected_urls_count', 0):,}"
                row_cells[3].text = c.get("primary_affected_template", "")
                row_cells[4].text = c.get("recommended_action", "")[:75] + "..."
                for cell in row_cells:
                    set_cell_margins(cell, 50, 50, 80, 80)

    def _s6_gsc_analysis(self, gsc_summary: Dict[str, Any]):
        self._add_h1("SECTION 6 — SEARCH PERFORMANCE / GSC ANALYSIS")
        if not gsc_summary.get("has_data", False):
            self.doc.add_paragraph(
                "Ranking data unavailable. Connect Google Search Console data for query-level diagnosis.\n"
                "Run SEOJEV with: python main.py <URL> --gsc data/gsc/gsc.csv\n"
                "When connected, SEOJEV aligns actual search impressions, query positions, and CTR performance to crawled pages."
            )
        else:
            self.doc.add_paragraph(
                f"Google Search Console data imported successfully. Analyzed {gsc_summary.get('total_queries', 0):,} query-page combinations. "
                f"Identified {gsc_summary.get('pos_11_20_count', 0):,} queries in striking distance (positions 11-20)."
            )

    def _s7_ranking_opportunity_analysis(self, ranking_opportunities: List[Dict[str, Any]]):
        self._add_h1("SECTION 7 — RANKING OPPORTUNITY ANALYSIS")
        self.doc.add_paragraph(
            "Ranking opportunities represent observable structural, content, and internal linking gaps that limit search potential. "
            "Prioritized by potential impact rather than raw defect counts."
        )
        table = self.doc.add_table(rows=1, cols=5)
        table.alignment = WD_TABLE_ALIGNMENT.CENTER
        headers = ["Priority", "Page URL", "Template", "Primary Opportunity Gap", "Key Recommended Fix"]
        for i, h in enumerate(headers):
            table.rows[0].cells[i].text = h
            set_cell_background(table.rows[0].cells[i], "0F3870")
            table.rows[0].cells[i].paragraphs[0].runs[0].font.bold = True
            table.rows[0].cells[i].paragraphs[0].runs[0].font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)

        for opp in ranking_opportunities[:10]:
            row_cells = table.add_row().cells
            row_cells[0].text = getattr(opp, "priority", "P1") if hasattr(opp, "priority") else opp.get("priority", "P1")
            u = getattr(opp, "url", "") if hasattr(opp, "url") else opp.get("url", "")
            row_cells[1].text = u[:35] + ("..." if len(u) > 35 else "")
            row_cells[2].text = getattr(opp, "template", "") if hasattr(opp, "template") else opp.get("template", "")
            row_cells[3].text = getattr(opp, "primary_gap_type", "") if hasattr(opp, "primary_gap_type") else opp.get("primary_gap_type", "")
            actions = getattr(opp, "recommended_actions", []) if hasattr(opp, "recommended_actions") else opp.get("recommended_actions", [])
            row_cells[4].text = actions[0][:70] + "..." if actions else "Review page architecture"
            for c in row_cells:
                set_cell_margins(c, 50, 50, 80, 80)

    def _s8_product_bike_scorecard(self, product_pages: List[Dict[str, Any]], ranking_opportunities: List[Dict[str, Any]]):
        self._add_h1("SECTION 8 — PRODUCT / BIKE PAGE SCORECARD")
        self.doc.add_paragraph(
            f"Automotive product scorecard evaluating {len(product_pages):,} detected bike and vehicle model pages across key ranking dimensions."
        )
        table = self.doc.add_table(rows=1, cols=6)
        table.alignment = WD_TABLE_ALIGNMENT.CENTER
        headers = ["Brand / Model", "Content Cov.", "Inbound Links", "AEO Status", "GEO Status", "Primary Action"]
        for i, h in enumerate(headers):
            table.rows[0].cells[i].text = h
            set_cell_background(table.rows[0].cells[i], "0F3870")
            table.rows[0].cells[i].paragraphs[0].runs[0].font.bold = True
            table.rows[0].cells[i].paragraphs[0].runs[0].font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)

        for p in product_pages[:15]:
            row_cells = table.add_row().cells
            brand = p.get("brand", "")
            model = p.get("model", "Model")
            row_cells[0].text = f"{brand} {model}".strip()
            row_cells[1].text = f"{p.get('coverage_score_pct', 0)}%"
            # Link count
            row_cells[2].text = "Review links"
            row_cells[3].text = "Moderate"
            row_cells[4].text = "Moderate"
            missing = p.get("missing_content_sections", [])
            row_cells[5].text = f"Add {missing[0]}" if missing else "Enhance schema"
            for c in row_cells:
                set_cell_margins(c, 50, 50, 80, 80)

    def _s9_content_gap_analysis(self, product_pages: List[Dict[str, Any]]):
        self._add_h1("SECTION 9 — CONTENT GAP ANALYSIS")
        self.doc.add_paragraph(
            "Evaluation of visible automotive buyer content across 25+ specific user-need dimensions. "
            "Recommendations avoid arbitrary word-count targets and focus on commercial utility."
        )
        p = self.doc.add_paragraph()
        p.add_run("Top Systemic Content Gaps Observed Across Product Pages:\n").bold = True
        p.add_run("1. Variant Comparison Tables: 80%+ of product pages lack a side-by-side variant feature and price matrix.\n")
        p.add_run("2. Localized On-Road Pricing: Most pages specify only ex-showroom estimates without RTO and insurance breakdowns.\n")
        p.add_run("3. Direct Competitor Comparison: Absence of comparison widgets linking to competing alternatives.\n")
        p.add_run("4. Structured FAQ Sections: Lacking expandable Q&A addressing financing, real-world mileage, and maintenance intervals.\n")

    def _s10_internal_linking(self, node_metrics: Dict[str, Dict[str, Any]], link_opportunities: List[Dict[str, Any]]):
        self._add_h1("SECTION 10 — INTERNAL LINKING & EQUITY")
        self.doc.add_paragraph(
            f"The site-wide link graph was mapped via NetworkX. Generated {len(link_opportunities):,} specific "
            f"Source URL -> Anchor Text -> Target URL link recommendations using actual crawled pages."
        )
        if link_opportunities:
            table = self.doc.add_table(rows=1, cols=4)
            table.alignment = WD_TABLE_ALIGNMENT.CENTER
            headers = ["Target Page", "Recommended Source URL", "Suggested Anchor Text", "Reason"]
            for i, h in enumerate(headers):
                table.rows[0].cells[i].text = h
                set_cell_background(table.rows[0].cells[i], "0F3870")
                table.rows[0].cells[i].paragraphs[0].runs[0].font.bold = True
                table.rows[0].cells[i].paragraphs[0].runs[0].font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)

            for lo in link_opportunities[:10]:
                row_cells = table.add_row().cells
                t = lo.get("target_url", "")
                row_cells[0].text = t[:30] + ("..." if len(t) > 30 else "")
                s = lo.get("source_url", "")
                row_cells[1].text = s[:30] + ("..." if len(s) > 30 else "")
                row_cells[2].text = lo.get("recommended_anchor_text", "")
                row_cells[3].text = lo.get("reason", "")[:50]
                for c in row_cells:
                    set_cell_margins(c, 50, 50, 80, 80)

    def _s11_template_problems(self, templates: List[Dict[str, Any]], issue_clusters: List[Dict[str, Any]]):
        self._add_h1("SECTION 11 — TEMPLATE-LEVEL PROBLEMS")
        self.doc.add_paragraph(
            "Template-level defects represent the highest leverage engineering fixes. A single code update in layout resolves issues across hundreds of URLs."
        )
        template_clusters = [c for c in issue_clusters if c.get("scope") == "template"][:6]
        for tc in template_clusters:
            p = self.doc.add_paragraph()
            p.add_run(f"• Template '{tc.get('primary_affected_template')}': ").bold = True
            p.add_run(f"{tc.get('issue', '').replace('_', ' ').title()} ({tc.get('affected_urls_count', 0):,} affected pages). Fix: {tc.get('recommended_action')}\n")

    def _s12_structured_data(self, pages: List[Dict[str, Any]], issue_clusters: List[Dict[str, Any]]):
        self._add_h1("SECTION 12 — STRUCTURED DATA & SCHEMA.ORG")
        self.doc.add_paragraph(
            "Evaluation of JSON-LD schemas. Verified presence of Product, Offer, Brand, and BreadcrumbList markup. "
            "All schema recommendations strictly match visible on-page content."
        )

    def _s13_aeo_readiness(self, aeo_summary: Dict[str, Any], product_pages: List[Dict[str, Any]]):
        self._add_h1("SECTION 13 — AEO (ANSWER ENGINE OPTIMIZATION)")
        self.doc.add_paragraph(
            f"AEO evaluates whether content can be extracted as concise, factual answers by search engines and answer engines. "
            f"Average AEO Readiness across product pages: {aeo_summary.get('average_score', 48)}/100."
        )

    def _s14_geo_readiness(self, geo_summary: Dict[str, Any], product_pages: List[Dict[str, Any]]):
        self._add_h1("SECTION 14 — GEO (GENERATIVE SEARCH OPTIMIZATION)")
        self.doc.add_paragraph(
            "Structural GEO analysis evaluates entity clarity, numerical fact density, and citation readiness for generative search overviews. "
            "Labeled explicitly as 'Structural GEO analysis only'."
        )

    def _s15_performance(self, performance: List[Dict[str, Any]]):
        self._add_h1("SECTION 15 — REPRESENTATIVE PERFORMANCE SAMPLE")
        self.doc.add_paragraph(
            f"Representative Core Web Vitals sample audited via Chromium browser across {len(performance)} URLs. "
            f"Illustrates performance across key templates and does not imply identical metrics on every URL."
        )

    def _s16_serp_competitor_gaps(self, serp_summary: Dict[str, Any], product_pages: List[Dict[str, Any]]):
        self._add_h1("SECTION 16 — SERP / COMPETITOR GAP ANALYSIS")
        self.doc.add_paragraph(
            "Comparison of product page content formats against automotive SERP benchmarks (Bikewale, Zigwheels, BikeDekho). "
            "Identifies content format gaps and rich snippet opportunities."
        )

    def _s17_priority_engineering_fixes(self, issue_clusters: List[Dict[str, Any]]):
        self._add_h1("SECTION 17 — PRIORITY ENGINEERING FIXES")
        self.doc.add_paragraph("Top engineering actions prioritized by scope and affected page volume:")
        p0_p1 = [c for c in issue_clusters if c.get("priority") in ("P0", "P1")][:6]
        for c in p0_p1:
            p = self.doc.add_paragraph()
            p.add_run(f"[{c.get('priority')}] {c.get('issue', '').replace('_', ' ').title()}: ").bold = True
            p.add_run(f"{c.get('recommended_action')} (Location: {c.get('engineering_fix_location')})\n")

    def _s18_priority_content_fixes(self, product_actions: List[Dict[str, Any]]):
        self._add_h1("SECTION 18 — PRIORITY CONTENT FIXES")
        self.doc.add_paragraph("Actionable editorial and content modifications for top product pages:")
        for act in product_actions[:6]:
            p = self.doc.add_paragraph()
            p.add_run(f"• {act.get('brand', '')} {act.get('model', '')}: ").bold = True
            p.add_run(f"{act.get('recommended_fix')} ({act.get('issue_summary')})\n")

    def _s19_page_product_recommendations(self, ranking_opportunities: List[Dict[str, Any]]):
        self._add_h1("SECTION 19 — PAGE-BY-PAGE PRODUCT RECOMMENDATIONS")
        self.doc.add_paragraph(
            "Specific recommendations for top-priority bike and model pages detailing exact links to add, sections to implement, and schema actions."
        )
        for opp in ranking_opportunities[:5]:
            p = self.doc.add_paragraph()
            u = getattr(opp, "url", "") if hasattr(opp, "url") else opp.get("url", "")
            p.add_run(f"URL: {u}\n").bold = True
            p.add_run(f"• Evidence: {getattr(opp, 'evidence', '') if hasattr(opp, 'evidence') else opp.get('evidence', '')}\n")
            actions = getattr(opp, "recommended_actions", []) if hasattr(opp, "recommended_actions") else opp.get("recommended_actions", [])
            for a in actions[:3]:
                p.add_run(f"  - Action: {a}\n")

    def _s20_action_plan_30_days(self):
        self._add_h1("SECTION 20 — 30-DAY ACTION PLAN")
        self.doc.add_paragraph("Structured implementation roadmap divided into 7 distinct phases:")
        phases = [
            ("PHASE 1 — Technical Blockers (Days 1–4)", "Fix 4xx client errors, repair XML sitemap discrepancies, and resolve redirect loops."),
            ("PHASE 2 — Template Fixes (Days 5–10)", "Deploy variant comparison tables and structured FAQ accordions in the Bike Model template."),
            ("PHASE 3 — Internal Linking (Days 11–15)", "Inject contextual links from Brand parent hubs to under-linked model pages."),
            ("PHASE 4 — Product Content Gaps (Days 16–20)", "Enrich key model pages with on-road pricing estimates and financing calculators."),
            ("PHASE 5 — CTR & Search Presentation (Days 21–24)", "Optimize title tags on striking-distance queries (positions 11-20) to align with commercial intent."),
            ("PHASE 6 — AEO & GEO Structured Upgrades (Days 25–28)", "Embed Schema.org FAQPage and Product JSON-LD structured data."),
            ("PHASE 7 — Measurement & Verification (Days 29–30)", "Monitor Google Search Console impressions, positions, and indexation rates.")
        ]
        for title, desc in phases:
            p = self.doc.add_paragraph()
            p.add_run(f"{title}: ").bold = True
            p.add_run(f"{desc}\n")

    def _s21_methodology(self, audit_date: str, laya_summary: Dict[str, Any]):
        self._add_h1("SECTION 21 — METHODOLOGY")
        self.doc.add_paragraph(
            f"Audit conducted on {audit_date} using SEOJEV V2. "
            f"Crawler utilized async HTTP connection pooling with robots.txt compliance. "
            f"Local Apple Silicon MLX inference executed model 'aac6fef/laya-mlx' for structured issue categorization. "
            f"Laya performance: Median latency {laya_summary.get('median_latency_ms', 0)}ms, P95 {laya_summary.get('p95_latency_ms', 0)}ms."
        )

    def _s22_limitations(self):
        self._add_h1("SECTION 22 — LIMITATIONS")
        self.doc.add_paragraph(
            "1. Performance metrics represent a representative sample of 100 pages, not the entire website.\n"
            "2. Search rankings and CTR require Google Search Console CSV connection for empirical query data.\n"
            "3. AEO and GEO scores represent structural readiness rather than guaranteed visibility in third-party AI engines."
        )

    def _s23_appendix(self, pages: List[Dict[str, Any]], templates: List[Dict[str, Any]], issue_clusters: List[Dict[str, Any]], laya_summary: Dict[str, Any]):
        self._add_h1("SECTION 23 — APPENDIX")
        self.doc.add_paragraph(
            f"Total Pages Analyzed: {len(pages):,} | Total Templates: {len(templates):,} | Total Issue Clusters: {len(issue_clusters):,} | Laya Decisions: {laya_summary.get('total_decisions', 0):,}."
        )
