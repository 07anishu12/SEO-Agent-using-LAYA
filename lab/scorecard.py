import sqlite3
import datetime
from typing import Dict, Any, List, Tuple
from seo.engine import SEOEngine
from crawler.normalizer import URLNormalizer
from crawler.soft404 import Soft404Detector
from .site_generator import SyntheticSiteGenerator

class DetectorScorecard:
    """Evaluates detector precision and recall against synthetic site ground truth defect manifest."""
    def __init__(self, db_path: str = "data/seo.db"):
        self.db_path = db_path

    def evaluate(self, site_gen: SyntheticSiteGenerator) -> Dict[str, Any]:
        normalizer = URLNormalizer(site_gen.base_url)
        seo_engine = SEOEngine(normalizer)
        soft404 = Soft404Detector()

        # Track detected defects: url -> list of defect keys
        detected: Dict[str, List[str]] = {}

        for url, page in site_gen.pages.items():
            page_data, links, images, schemas, issues = seo_engine.process_page(
                url=url,
                final_url=url,
                status_code=page["status_code"],
                content_type="text/html",
                response_time=0.1,
                content_length=len(page["html"]),
                redirect_chain=[],
                headers={},
                html=page["html"],
                discovery_source="seed" if url == f"{site_gen.base_url}/" else "sitemap",
                page_type=page["page_type"],
                template_id=f"tpl_{page['page_type']}",
                crawl_depth=1
            )
            for iss in issues:
                detected.setdefault(url, []).append(iss.issue)

            # Soft 404 test
            is_s, _ = soft404.is_soft_404(page["status_code"], page["html"], page["title"], page["h1"])
            if is_s:
                detected.setdefault(url, []).append("soft_404_response")

        # Compare against ground truth
        manifest = site_gen.ground_truth_manifest
        all_rules = {
            "canonical_mismatch",
            "soft_404_response",
            "missing_h1",
            "missing_meta_description"
        }

        tp = 0
        fp = 0
        fn = 0

        rule_stats: Dict[str, Dict[str, int]] = {r: {"tp": 0, "fp": 0, "fn": 0} for r in all_rules}

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
