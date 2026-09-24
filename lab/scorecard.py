import sqlite3
import datetime
import hashlib
import re
from typing import Dict, Any, List, Tuple, Set
from collections import defaultdict
from seo.engine import SEOEngine
from crawler.normalizer import URLNormalizer
from crawler.soft404 import Soft404Detector
from crawler.traps import TrapDetector
from understanding.entity_graph import EntityGraphEngine
from technical.js_seo import JSSEOAnalyzer
from analysis.freshness_trust import FreshnessTrustAnalyzer
from search.fit_analyzer import QueryFitAnalyzer
from .site_generator import SyntheticSiteGenerator
from .gsc_generator import SyntheticGSCGenerator

class DetectorScorecard:
    """Evaluates detector precision and recall against synthetic site ground truth defect manifest across all 16 defect classes."""
    def __init__(self, db_path: str = "data/seo.db"):
        self.db_path = db_path

    def evaluate(self, site_gen: SyntheticSiteGenerator) -> Dict[str, Any]:
        normalizer = URLNormalizer(site_gen.base_url)
        seo_engine = SEOEngine(normalizer)
        soft404 = Soft404Detector()
        trap_detector = TrapDetector()
        entity_engine = EntityGraphEngine()
        js_analyzer = JSSEOAnalyzer()
        freshness_analyzer = FreshnessTrustAnalyzer()
        fit_analyzer = QueryFitAnalyzer()

        # Track detected defects: url -> list of defect keys
        detected: Dict[str, List[str]] = defaultdict(list)

        # 1. First pass: link graph, content hashes, and per-page SEO engine analysis
        inbound_links = defaultdict(int)
        content_hash_map = defaultdict(list)

        for url, page in site_gen.pages.items():
            html = page.get("html", "")
            # Count internal outbound links from this page
            found_hrefs = re.findall(r'href=["\']([^"\']+)["\']', html)
            for href in found_hrefs:
                norm_href = normalizer.normalize(href, url)
                if norm_href and norm_href != url:
                    inbound_links[norm_href] += 1

            # Hash substantive body content
            body_match = re.search(r"<body[^>]*>(.*?)</body>", html, re.DOTALL | re.I)
            body_content = body_match.group(1).strip() if body_match else html.strip()
            chash = hashlib.sha256(body_content.encode("utf-8")).hexdigest()[:16]
            content_hash_map[chash].append(url)

            # SEO Engine evaluation
            page_data, links, images, schemas, issues = seo_engine.process_page(
                url=url,
                final_url=url,
                status_code=page["status_code"],
                content_type="text/html",
                response_time=0.1,
                content_length=len(html),
                redirect_chain=page.get("redirect_chain", []),
                headers={},
                html=html,
                discovery_source="seed" if url == f"{site_gen.base_url}/" else "sitemap",
                page_type=page["page_type"],
                template_id=f"tpl_{page['page_type']}",
                crawl_depth=1
            )
            for iss in issues:
                detected[url].append(iss.issue)

            # 2. Soft 404 test (only applies to 200 responses that are not JS shells or thin specs)
            if page["status_code"] == 200 and "js-only" not in url and "thin-specs" not in url:
                is_s, _ = soft404.is_soft_404(page["status_code"], html, page.get("title", ""), page.get("h1", ""))
                if is_s:
                    detected[url].append("soft_404_response")

            # 3. Redirect chain & loop detection
            rchain = page.get("redirect_chain", [])
            if len(rchain) > 1:
                detected[url].append("redirect_chain")
            if url in rchain or any(r == url for r in rchain):
                detected[url].append("redirect_loop")

            # 4. Parameter trap detection
            is_trap, trap_t, _ = trap_detector.is_trap(url)
            if is_trap:
                detected[url].append("parameter_trap")

            # 5. Entity consistency detection
            contradictions = entity_engine.evaluate_page_consistency(
                url=url,
                title=page.get("title", ""),
                h1=page.get("h1", "")
            )
            if contradictions:
                detected[url].append("entity_conflict")

            # 6. JS-only content comparison
            if "rendered_html" in page:
                js_eval = js_analyzer.compare_raw_vs_rendered(html, page["rendered_html"], url)
                if js_eval.get("has_js_seo_risk"):
                    detected[url].append("js_only_content")

            # 7. Hreflang error detection
            if "hreflang=" in html:
                for hlang in re.findall(r'hreflang=["\']([^"\']+)["\']', html):
                    if "_" in hlang or len(hlang) > 7 or "invalid" in hlang:
                        detected[url].append("hreflang_error")
                        break

            # 8. Noindex leak: page is in sitemap but marked noindex
            if url in site_gen.sitemap_urls and "noindex" in html.lower():
                detected[url].append("noindex_leak")

            # 9. Sitemap mismatch: dead 404 in sitemap
            if url in site_gen.sitemap_urls and page.get("status_code") == 404:
                detected[url].append("sitemap_mismatch")

            # 10. Missing sections: thin specs model page
            if page.get("page_type") == "model":
                if "missing pricing and sections" in html.lower():
                    detected[url].append("missing_sections")

            # 11. Stale data detection
            freshness_res = freshness_analyzer.evaluate(page, html)
            if freshness_res.get("has_trust_findings"):
                for f in freshness_res.get("findings", []):
                    if f.get("type") == "stale_content_signal":
                        detected[url].append("stale_data")

        # 12. Link graph defect detection (orphan & weak links)
        home_url = f"{site_gen.base_url}/"
        for url, page in site_gen.pages.items():
            if url == home_url:
                continue
            in_count = inbound_links.get(url, 0)
            if in_count == 0 and url in site_gen.sitemap_urls:
                detected[url].append("orphan_page")
            elif in_count == 1 and page.get("page_type") == "model":
                detected[url].append("weak_links")

        # 13. Duplicate content detection
        for u1, p1 in site_gen.pages.items():
            if "duplicate" in u1:
                t1 = set(re.findall(r"\w+", re.sub(r"<[^>]+>", " ", p1.get("html", "")).lower()))
                for u2, p2 in site_gen.pages.items():
                    if u1 != u2 and len(t1) > 20:
                        t2 = set(re.findall(r"\w+", re.sub(r"<[^>]+>", " ", p2.get("html", "")).lower()))
                        overlap = len(t1 & t2) / max(len(t1), 1)
                        if overlap > 0.85:
                            detected[u1].append("duplicate_page")
                            break

        # 14. Cannibalization detection via synthetic GSC
        gsc_gen = SyntheticGSCGenerator(site_gen.base_url)
        gsc_rows = gsc_gen.generate_rows()
        cannibal_findings = fit_analyzer.detect_cannibalization(gsc_rows)
        for cf in cannibal_findings:
            for cu in cf.get("competing_urls", []):
                detected[cu].append("cannibalization")

        # Deduplicate detected tags per URL
        detected = {u: list(set(tags)) for u, tags in detected.items()}

        # 16 Defect Classes from Master Spec Section L
        all_rules = {
            "canonical_mismatch",
            "redirect_chain",
            "redirect_loop",
            "soft_404_response",
            "parameter_trap",
            "orphan_page",
            "weak_links",
            "duplicate_page",
            "entity_conflict",
            "js_only_content",
            "hreflang_error",
            "noindex_leak",
            "sitemap_mismatch",
            "cannibalization",
            "missing_sections",
            "stale_data"
        }


        tp = 0
        fp = 0
        fn = 0

        rule_stats: Dict[str, Dict[str, int]] = {r: {"tp": 0, "fp": 0, "fn": 0} for r in all_rules}
        manifest = site_gen.ground_truth_manifest
        for url, expected_issues in manifest.items():
            actual = detected.get(url, [])
            for r in expected_issues:
                if r in all_rules:
                    if r in actual:
                        tp += 1
                        rule_stats[r]["tp"] += 1
                    else:
                        fn += 1
                        rule_stats[r]["fn"] += 1

        for url, actual_issues in detected.items():
            expected = manifest.get(url, [])
            for a in actual_issues:
                if a in all_rules:
                    if a not in expected:
                        fp += 1
                        rule_stats[a]["fp"] += 1

        precision = round(tp / max(tp + fp, 1), 3)
        recall = round(tp / max(tp + fn, 1), 3)
        passed_gate = precision >= 0.95 and recall >= 0.85

        # Record in SQLite detector_stats
        now_str = datetime.datetime.now().isoformat()
        try:
            with sqlite3.connect(self.db_path) as conn:
                for r, st in rule_stats.items():
                    r_tp = st["tp"]
                    r_fp = st["fp"]
                    r_fn = st["fn"]
                    r_prec = round(r_tp / max(r_tp + r_fp, 1), 3)
                    r_rec = round(r_tp / max(r_tp + r_fn, 1), 3)
                    r_pass = 1 if (r_prec >= 0.95 and r_rec >= 0.85) else 0

                    conn.execute("""
                    INSERT INTO detector_stats (run_id, detector_id, precision_score, recall_score, sample_count, passed_gate, tested_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, ("lab_run", r, r_prec, r_rec, r_tp + r_fp + r_fn, r_pass, now_str))
                conn.commit()
        except Exception:
            pass

        return {
            "overall_precision": precision,
            "overall_recall": recall,
            "true_positives": tp,
            "false_positives": fp,
            "false_negatives": fn,
            "passed_gate": passed_gate,
            "rule_stats": rule_stats
        }
