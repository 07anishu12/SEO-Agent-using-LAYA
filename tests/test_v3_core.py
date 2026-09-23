import os
import shutil
import tempfile
import unittest

from engine.id_system import IDSystem
from engine.content_store import ContentStore
from engine.evidence import EvidenceLedger, EvidenceRef
from engine.provenance import NumericProvenanceLedger
from engine.claims_linter import ClaimsLinter
from crawler.migrations import MigrationRunner

class TestV3Core(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.test_dir, "test_seo.db")
        self.store_dir = os.path.join(self.test_dir, "store")

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_id_system_deterministic_and_stable(self):
        id_sys = IDSystem(db_path=self.db_path)
        fp1 = id_sys.generate_fingerprint("rule_canonical_mismatch", "template:tpl_bike", "https://drivio.in/bike-1")
        fp2 = id_sys.generate_fingerprint("rule_canonical_mismatch", "template:tpl_bike", "https://drivio.in/bike-1")
        self.assertEqual(fp1, fp2)

        # Allocate display ID
        d_id1 = id_sys.get_or_create_display_id(fp1, "engineering")
        self.assertEqual(d_id1, "ENG-SEO-001")

        # Second call returns identical display ID
        d_id2 = id_sys.get_or_create_display_id(fp1, "engineering")
        self.assertEqual(d_id2, "ENG-SEO-001")

        # Different fingerprint gets sequential ID
        fp3 = id_sys.generate_fingerprint("rule_missing_title", "template:tpl_car", "https://drivio.in/car-1")
        d_id3 = id_sys.get_or_create_display_id(fp3, "engineering")
        self.assertEqual(d_id3, "ENG-SEO-002")

    def test_content_store_compression_and_retrieval(self):
        store = ContentStore(base_dir=self.store_dir)
        html_sample = "<html><body><h1>Hello V3 Search Intelligence</h1></body></html>"
        chash, sref = store.put(html_sample)
        
        self.assertTrue(os.path.exists(sref))
        self.assertTrue(store.exists(chash))
        
        retrieved = store.get(chash)
        self.assertEqual(retrieved, html_sample)

    def test_evidence_ledger(self):
        # Apply migration to create table
        mig_runner = MigrationRunner(db_path=self.db_path)
        mig_runner.run_migrations()

        ledger = EvidenceLedger(db_path=self.db_path)
        ref = EvidenceRef(
            run_id="run_101",
            url="https://drivio.in/bikes/bajaj",
            evidence_type="dom_selector",
            selector="meta[name=description]",
            line_number=12,
            details={"content_length": 0}
        )
        ledger.record_evidence(ref)

        fetched = ledger.get_evidence(ref.evidence_id)
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched["selector"], "meta[name=description]")
        self.assertEqual(fetched["details"]["content_length"], 0)

        url_refs = ledger.get_evidence_for_url("run_101", "https://drivio.in/bikes/bajaj")
        self.assertEqual(len(url_refs), 1)

    def test_numeric_provenance_ledger(self):
        mig_runner = MigrationRunner(db_path=self.db_path)
        mig_runner.run_migrations()

        prov = NumericProvenanceLedger(db_path=self.db_path)
        prov.record_metric(
            run_id="run_101",
            name="total_crawled_urls",
            value=5001.0,
            method="COUNT(url) WHERE status=200",
            table="pages",
            query="SELECT COUNT(*) FROM pages WHERE status_code = 200"
        )

        record = prov.verify_metric("run_101", "total_crawled_urls")
        self.assertIsNotNone(record)
        self.assertEqual(record["metric_value"], 5001.0)
        self.assertEqual(record["source_table"], "pages")

    def test_claims_linter(self):
        linter = ClaimsLinter()

        # Should flag guarantee language
        bad_text = "This optimization will rank your page at position 1 and is guaranteed to increase traffic."
        errs = linter.lint_text(bad_text)
        self.assertGreaterEqual(len(errs), 2)

        # Should pass honest diagnostic language
        good_text = "Observed missing structured data. Implementation hypothesis may improve entity discoverability."
        self.assertEqual(len(linter.lint_text(good_text)), 0)

        # Finding validation: missing evidence
        bad_finding = {
            "display_id": "FINDING-001",
            "claim_type": "INFERRED",
            "message": "Title is missing",
            "evidence_refs": []
        }
        self.assertGreater(len(linter.lint_finding(bad_finding)), 0)

        # Finding validation: invalid claim_type
        bad_finding2 = {
            "display_id": "FINDING-002",
            "claim_type": "PREDICTION",
            "message": "Title is missing",
            "evidence_refs": ["ev_1"]
        }
        self.assertGreater(len(linter.lint_finding(bad_finding2)), 0)

    def test_migration_runner_idempotency(self):
        mig_runner = MigrationRunner(db_path=self.db_path)
        applied1 = mig_runner.run_migrations()
        self.assertGreaterEqual(len(applied1), 1)

        # Second run should apply 0 new migrations
        applied2 = mig_runner.run_migrations()
        self.assertEqual(len(applied2), 0)

if __name__ == "__main__":
    unittest.main()
