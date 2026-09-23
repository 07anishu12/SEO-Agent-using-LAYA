import os
import sqlite3
import tempfile
import unittest
from crawler.storage import CrawlStorage
from engine.priority_model import PriorityModel
from engine.id_system import IDSystem
from engine.opportunity_engine_v3 import OpportunityEngineV3
from engine.work_orders import WorkOrderManager
from verification.runner import VerificationRunner
from engine.blueprint import PageOptimizationBlueprint

class TestV3Opportunities(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.test_db_path = os.path.join(self.temp_dir.name, "test_seo.db")
        # Initialize base storage (creates pages, urls, links, etc.)
        CrawlStorage(self.test_db_path)
        with sqlite3.connect(self.test_db_path) as conn:
            with open("crawler/migrations/001_v3_core_tables.sql", "r") as f:
                conn.executescript(f.read())

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_priority_model(self):
        pm = PriorityModel()
        
        # Test High tier
        high_factors = {
            "visibility": 90.0,
            "gap": 80.0,
            "page_importance": 85.0,
            "template_scope": 90.0,
            "technical_severity": 100.0,
            "ctr_headroom": 70.0,
            "link_gap": 60.0
        }
        score, tier = pm.calculate_opportunity_score(high_factors)
        self.assertGreaterEqual(score, 70.0)
        self.assertEqual(tier, "High")

        # Test Confidence tier
        self.assertEqual(pm.calculate_confidence_tier("E4", 100, 0.95), "High")
        self.assertEqual(pm.calculate_confidence_tier("E1", 1, 0.60), "Low")

        # Test Effort
        self.assertEqual(pm.calculate_effort("config", 1), "S")
        self.assertEqual(pm.calculate_effort("metadata_template", 100), "M")
        self.assertEqual(pm.calculate_effort("custom_code", 1000), "L")

        # Test Sensitivity
        items = [
            {"fingerprint": f"fp_{i}", "priority_score": 50.0 + i, "priority_factors": high_factors}
            for i in range(30)
        ]
        res = pm.sensitivity_check(items)
        self.assertGreaterEqual(res["top_25_stability_pct"], 80.0)

    def test_opportunity_engine_aggregation(self):
        id_sys = IDSystem(db_path=self.test_db_path)
        engine = OpportunityEngineV3(db_path=self.test_db_path, id_system=id_sys)

        pages = [
            {"url": f"https://example.com/bike/{i}", "template_id": "tpl_bike_detail"}
            for i in range(15)
        ]
        # Simulate 15 raw findings of missing meta description on the same template
        findings = [
            {
                "rule_id": "META_DESCRIPTION_MISSING",
                "scope_key": "tpl_bike_detail",
                "url": f"https://example.com/bike/{i}",
                "template_id": "tpl_bike_detail",
                "severity": "HIGH",
                "message": "Missing meta description",
                "recommended_action": "Add dynamic meta description in template."
            }
            for i in range(15)
        ]

        opps = engine.synthesize_opportunities("run_test_01", pages, findings)
        
        # Crucial assertion: 15 raw findings collapsed into 1 template opportunity!
        tpl_opps = [o for o in opps if o["type"] == "TPL"]
        self.assertEqual(len(tpl_opps), 1)
        self.assertEqual(tpl_opps[0]["affected_urls_count"], 15)
        self.assertIn("tpl_bike_detail", tpl_opps[0]["affected_templates_json"])

        # Test persistence
        engine.persist_opportunities(opps)
        with sqlite3.connect(self.test_db_path) as conn:
            row = conn.execute("SELECT COUNT(*) FROM opportunities").fetchone()
            self.assertGreaterEqual(row[0], 1)
            act_row = conn.execute("SELECT COUNT(*) FROM actions").fetchone()
            self.assertGreaterEqual(act_row[0], 1)

    def test_work_order_manager(self):
        wm = WorkOrderManager(db_path=self.test_db_path)
        sample_opps = [
            {
                "opportunity_id": "OPP-001",
                "fingerprint": "fp_001",
                "display_id": "TPL-SEO-001",
                "type": "TPL",
                "action": "Update template to add meta description",
                "observation": "15 URLs lack meta description",
                "diagnosis": "Template omission",
                "hypothesis": "Search snippet CTR will improve",
                "implementation_location": "templates/bike_detail.html",
                "affected_urls_count": 15,
                "sample_urls_json": '["https://example.com/bike/1"]',
                "opportunity_tier": "High",
                "confidence_tier": "High",
                "effort": "M",
                "priority_score": 82.0,
                "verification_spec": "has_selector(\"meta[name='description']\")"
            },
            {
                "opportunity_id": "OPP-002",
                "fingerprint": "fp_002",
                "display_id": "CONTENT-SEO-001",
                "type": "CONTENT",
                "action": "Add technical specifications section",
                "observation": "Missing mileage and power specs",
                "diagnosis": "Thin entity coverage",
                "hypothesis": "Topical completeness satisfies commercial queries",
                "implementation_location": "content/specs/bike-1.md",
                "affected_urls_count": 1,
                "sample_urls_json": '["https://example.com/bike/1"]',
                "opportunity_tier": "Medium",
                "confidence_tier": "High",
                "effort": "S",
                "priority_score": 60.0,
                "verification_spec": "word_count >= 100"
            }
        ]

        wos = wm.create_work_orders_from_opportunities("run_test_01", sample_opps)
        self.assertEqual(len(wos), 2)
        self.assertEqual(wos[0]["display_id"], "SEOJEV-ENG-001")
        self.assertEqual(wos[0]["order_type"], "engineering")
        self.assertEqual(wos[1]["display_id"], "SEOJEV-CONTENT-001")
        self.assertEqual(wos[1]["order_type"], "content")

        # Persist and lookup
        wm.persist_work_orders(wos)
        retrieved = wm.get_work_order_by_display_id("SEOJEV-ENG-001")
        self.assertIsNotNone(retrieved)
        self.assertIn("Update template", retrieved["title"])

        # Test ticket exports
        md = wm.export_markdown(wos[0])
        self.assertIn("Acceptance Criteria", md)
        gh = wm.export_github_issue(wos[0])
        self.assertIn("labels", gh)
        jira = wm.export_jira_issue(wos[0])
        self.assertEqual(jira["fields"]["project"]["key"], "SEO")
        linear = wm.export_linear_issue(wos[0])
        self.assertIn("title", linear)

    def test_verification_runner(self):
        runner = VerificationRunner(db_path=self.test_db_path)
        sample_html = """
        <!DOCTYPE html>
        <html>
          <head>
            <title>Yamaha R15 Specifications</title>
            <meta name="description" content="Read full technical specifications and mileage for Yamaha R15 V4.">
          </head>
          <body>
            <h1>Yamaha R15 V4</h1>
            <p>A sporty motorcycle with high performance.</p>
          </body>
        </html>
        """
        page_data = {"url": "https://example.com/yamaha-r15", "status_code": 200, "word_count": 50}

        # Test passing spec
        passed, msg = runner.evaluate_spec("has_selector(\"meta[name='description']\") and text_length(\"h1\") > 5", page_data, sample_html)
        self.assertTrue(passed)

        # Test failing spec
        passed_fail, msg_fail = runner.evaluate_spec("status_code == 404", page_data, sample_html)
        self.assertFalse(passed_fail)

        # Test verify_work_order persistence
        wo = {
            "work_order_id": "WO-SEOJEV-ENG-001",
            "display_id": "SEOJEV-ENG-001",
            "run_id": "run_test",
            "fingerprint": "fp_test",
            "verify_spec": "status_code == 200 and has_selector('title')",
            "evidence_json": '{"sample_urls": ["https://example.com/yamaha-r15"]}'
        }
        result = runner.verify_work_order(wo, html_content=sample_html)
        self.assertEqual(result["status"], "PASSED")

        with sqlite3.connect(self.test_db_path) as conn:
            row = conn.execute("SELECT status FROM verifications WHERE work_order_id = ?", ("WO-SEOJEV-ENG-001",)).fetchone()
            self.assertEqual(row[0], "PASSED")

    def test_page_optimization_blueprint(self):
        # Insert dummy page in test DB
        with sqlite3.connect(self.test_db_path) as conn:
            conn.execute("""
            INSERT INTO pages (crawl_id, url, title, description, h1_text, status_code, is_indexable, is_self_canonical, template_id, page_type, word_count)
            VALUES ('run_test', 'https://example.com/test-bike', 'Yamaha FZ-S FI Test Title', 'Full test specifications and review of Yamaha FZ-S FI motorcycle in India.', 'Yamaha FZ-S FI', 200, 1, 1, 'tpl_model', 'product', 450)
            """)
            conn.commit()

        store_dir = os.path.join(self.temp_dir.name, "store")
        bp_engine = PageOptimizationBlueprint(db_path=self.test_db_path, store_dir=store_dir)
        bp = bp_engine.generate_blueprint("https://example.com/test-bike")
        
        # Verify key dimensions
        self.assertEqual(bp["dimension_1_identity"]["status_code"], 200)
        self.assertEqual(bp["dimension_2_template"]["template_id"], "tpl_model")
        self.assertTrue(bp["dimension_3_indexation"]["is_indexable"])
        self.assertEqual(bp["dimension_6_core_metadata"]["title"], "Yamaha FZ-S FI Test Title")
        self.assertEqual(bp["dimension_6_core_metadata"]["h1"], "Yamaha FZ-S FI")
        self.assertIn("dimension_8_entity_coverage", bp)
        self.assertIn("dimension_16_aeo_readiness", bp)
        self.assertIn("dimension_17_geo_readiness", bp)

        # Test Markdown rendering
        md = bp_engine.render_markdown(bp)
        self.assertIn("# Page Optimization Blueprint", md)
        self.assertIn("Yamaha FZ-S FI", md)

if __name__ == "__main__":
    unittest.main()
