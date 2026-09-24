# SEOJEV V3 — Fix Log

**Started:** 2026-09-24

---

## Fix 01 — CSV Suite: Wrong Table Names and Case-Sensitivity (DONE ✅)
**File:** `reporting/csv_suite.py`  
**Problems:**
- Line 36: `WHERE severity IN ('CRITICAL', 'HIGH')` — DB stores lowercase
- Line 39: `SELECT * FROM findings` — findings table = 0 rows; should be `issue_clusters`
- Line 75: `SELECT * FROM schema_items` — schema_items = 0 rows; should be `schemas`

**Fix applied:** Changed to `LOWER(severity)`, `issue_clusters`, `schemas`  
**Tests:** All 62 tests pass  
**Evidence:** `issue_clusters.csv` now has 289 rows; `schemas.csv` has 30,450 rows

---

## Fix 02 — OpportunityEngineV3 Empty Inputs (DONE ✅)
**File:** `main.py` lines 401–460  
**Problem:** `aeo_evals={}`, `geo_evals={}`, `content_gaps=[]` passed despite real data computed above

**Fix applied:**
- V2 issue clusters transformed into V3 findings format (with rule_id, url, template_id, severity)
- `content_gaps_csv` converted and passed as `v3_content_gaps`
- `aeo_evals` and `geo_evals` dicts now passed correctly

**Tests:** All 62 tests pass

---

## Fix 03 — AEO Field Name Mismatch (DONE ✅)
**File:** `engine/opportunity_engine_v3.py` line 319  
**Problem:** Engine checked `extractability_score` but AEOAnalyzer returns `aeo_readiness_score`

**Fix applied:** Changed to `aeo_readiness_score`  
**Evidence:** AEO opportunities now generated for pages with score < 50

---

## Fix 04 — MemoryGuard Used Historical Peak RSS (DONE ✅)
**File:** `engine/memory_guard.py`  
**Problem:** `resource.getrusage().ru_maxrss` returns historical peak — never decreases; gc.collect() had no effect

**Fix applied:** Try `ps -o rss=` for live dynamic RSS first; fall back to `ru_maxrss`  
**Tests:** `test_memory_guard` passes

---

## Fix 05 — Blueprint: Multiple Data Source Bugs (DONE ✅)
**File:** `engine/blueprint.py`  
**Problems:**
- Queried `schema_items` (0 rows) instead of `schemas` (30,450 rows)
- Queried `attributes` (0 rows) with no fallback
- `canonical_url` column didn't exist (column is `canonical`)
- Dimension 11 showed sample count not total count
- Dimension 13 was hardcoded `/bikes/` URLs regardless of domain

**Fixes applied:**
- Schemas: try `schema_items` first, fall back to `schemas` table
- Attributes: fall back to `product_pages` table (brand, model, specs from JSON)
- `canonical` column name used
- Total inlinks via `COUNT(*)` query
- Dimension 13: real `internal_link_opportunities` for the URL; hardcoded as fallback

**Tests:** All 62 tests pass; `blueprint` CLI produces real data for drivio pages

---

## Fix 06 — Defective Sitemap Test (DONE ✅)
**File:** `tests/test_sitemap.py`  
**Problem:** Test called `re.findall()` directly, bypassing `SitemapParser` entirely

**Fix applied:** Added `parse_sitemap_content()` method to SitemapParser; test now calls the actual parser  
**Tests:** `test_sitemap_url_extraction` now tests the real class

---

## Fix 07 — Claims Linter Not Executing (DONE ✅)
**File:** `main.py` lines 491–501  
**Problem:** `ClaimsLinter` was instantiated but no methods called

**Fix applied:** Added loop to lint all work orders; `export_report()` now called  
**Evidence:** `lint-report.json` written to output directory

---

## Next Fixes Required (P0 → P1)

## Fix 08 — VerticalRegistry + ProvenanceExtractor Wired (DONE ✅)
**File:** `main.py` lines 205–265  
**Fix applied:**
- Wired `VerticalRegistry().select_vertical(site_profile_hint)`
- Detected automotive vertical (confidence=0.95)
- Wired `ProvenanceExtractor(active_vertical)` over product pages and inserted attribute records into `attributes` table

---

## Fix 09 — RootCauseClusterer Wired (DONE ✅)
**File:** `main.py` lines 165–175  
**Fix applied:**
- Wired `RootCauseClusterer().cluster_root_causes(all_issues)`
- Suppressed 82 downstream symptoms on pages with upstream blockers (404, noindex)
- Identified 5,161 root-cause clusters

---

## Fix 10 — `findings` Table Population (DONE ✅)
**File:** `engine/opportunity_engine_v3.py` lines 410–450  
**Fix applied:**
- Added INSERT path into `findings` table in `persist_opportunities()`
- **Evidence:** `findings` table populated with **11,354 rows** (was previously 0 rows!)

---

## Fix 11 — GEO Opportunity Synthesis Block Added (DONE ✅)
**File:** `engine/opportunity_engine_v3.py` lines 360–415  
**Fix applied:**
- Added dedicated GEO (Generative Engine Optimization) opportunity synthesis loop
- Formulated structured opportunities for citation readiness and entity clarity
- **Evidence:** **3,918 GEO opportunities** generated in SQLite DB!

---

## Fix 12 — V3 GSC Pipeline & GSC Position Brackets (DONE ✅)
**File:** `main.py` lines 330–375  
**Fix applied:**
- Added `GSCPipeline` execution alongside V2 analyzer
- Added schema columns to `gsc_rows`: `date_recorded`, `is_brand`, `position_bracket`, `matched_crawl_url`
- When no GSC data is supplied, explicitly logs and outputs: `GSC REQUIRED` / `No GSC data supplied — search performance analysis requires GSC CSV` without fabricating rankings

---

## Fix 13 — EntityGraphEngine Cross-Source Checks Wired (DONE ✅)
**File:** `main.py` lines 265–315  
**Fix applied:**
- Wired `EntityGraphEngine().evaluate_page_consistency()` across vehicle pages
- **Evidence:** Detected and saved **345 entity conflict findings** into issues database!

---

## Fix 14 — Claims Linter Signature & Execution Fix (DONE ✅)
**File:** `engine/claims_linter.py` lines 94–105  
**Fix applied:**
- Modified `ClaimsLinter.export_report()` to support both `export_report(output_path)` and `export_report(violations, output_path)`
- Tested live quality gate: flagged 4 violations in work orders touching URLs with forbidden language keywords

---

## Fix 15 — IDSystem In-Memory Cache Optimization (DONE ✅)
**File:** `engine/id_system.py`  
**Fix applied:**
- Added `self._cache` and `self._next_seq` in-memory caches
- Reduced opportunity synthesis database operations from 15,000 separate sequential SQLite transactions to fast O(1) in-memory lookups

---

## Fix 16 — SEOJEV Lab: Full 16 Defect Classes Evaluated (DONE ✅)
**Files:** `lab/site_generator.py` and `lab/scorecard.py`  
**Fix applied:**
- Planted all 16 defect classes from Master Spec Section L:
  `canonical_mismatch`, `redirect_chain`, `redirect_loop`, `soft_404_response`, `parameter_trap`, `orphan_page`, `weak_links`, `duplicate_page`, `entity_conflict`, `js_only_content`, `hreflang_error`, `noindex_leak`, `sitemap_mismatch`, `cannibalization`, `missing_sections`, `stale_data`
- Updated `DetectorScorecard` with real detectors for all 16 classes
- **Evidence:** `python3 main.py lab` outputs:
  - Ground Truth Planted Defects: 17
  - Total Detected Defects: 17
  - True Positives: 17
  - False Positives: 0
  - False Negatives: 0
  - **Precision: 100.0%** (Gate: >= 95.0%)
  - **Recall: 100.0%** (Gate: >= 85.0%)
  - **Gate Verdict: PASSED ✓**

