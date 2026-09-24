# SEOJEV V3 — Gap Analysis: Why the System Produces Generic Output

**Audit date:** 2026-09-24

---

## Root Cause #1 — The V3 Intelligence Layer Is Entirely Disconnected (CRITICAL)

**Finding:**  
22 of 34 V3 modules were built and tested in isolation but were **never imported or called** in `main_async()`.

**Proof:**
```
evidence rows:          0
findings rows:          0
entities rows:          0
gsc_rows:               0
query_page_map rows:    0
attributes rows:        0
```

**Why this happened:**  
Each stage was developed and tested with unit tests against synthetic data. The stage reports marked them "DONE". But no integration step ever connected them to `main_async()`. The `main.py` continued running V2 analyzers for AEO, GEO, templates, link graph and ignored all V3 equivalents.

**Impact:**  
Entire subsystems (entity, GSC, query intelligence, content gaps V3, link simulation, programmatic families, JS SEO, root-cause clustering) produce zero output in production.

---

## Root Cause #2 — OpportunityEngineV3 Received Empty Data (CRITICAL)

**Before the previous fix:**
```python
v3_opps = opp_engine_v3.synthesize_opportunities(
    query_page_map=[],      # ← EMPTY despite aeo_evals computed above
    content_gaps=[],        # ← EMPTY despite content_gaps_csv computed
    aeo_evals={},           # ← EMPTY despite aeo_evals dict existing
    geo_evals={}            # ← EMPTY despite geo_evals dict existing
)
```

**After fix applied in previous session:**
- `aeo_evals` and `geo_evals` are now passed correctly
- `content_gaps_csv` from V2 pipeline is converted and passed
- V2 issue clusters are transformed into V3 findings format
- AEO field name mismatch fixed (`extractability_score` → `aeo_readiness_score`)

**Remaining gap:**  
`query_page_map=[]` still empty — GSCPipeline never called, no GSC data in DB.

---

## Root Cause #3 — The `findings` Table Has No Insert Path (CRITICAL)

**Finding:**  
`findings` table = 0 rows. No module anywhere contains `INSERT INTO findings`.

**Impact:**  
- HTML Explorer's "Clusters" tab always empty
- CSV `soft_404s.csv`, `traps.csv`, `freshness_ymyl.csv`, `js_seo_diffs.csv` always empty
- EvidenceLedger has nowhere to reference

**Why this happened:**  
The `findings` table was designed as the V3 analog to `issues`. The V3 architecture intended each analyzer to write structured findings with evidence references. But the `persist()` path was never implemented in any analyzer.

---

## Root Cause #4 — Evidence Ledger Is Never Called in Production (HIGH)

**Finding:**  
`EvidenceLedger.record_batch()` exists and is tested. But no production code (no analyzer, engine, or pipeline step) ever calls it. Result: `evidence` table = 0 rows.

**Impact:**  
- Claims linter's requirement for `evidence_refs` cannot be satisfied
- Work orders have no traceable evidence backing
- Blueprint's "evidence" dimension shows nothing

---

## Root Cause #5 — Entity System Produces Zero Output (HIGH)

**Finding:**  
`EntityGraphEngine` is fully tested. `entities`, `entity_aliases`, `entity_page_roles` tables all = 0 rows.

**Impact:**  
- Entity Coverage in blueprint = 0% for all pages (falls back to product_pages now)
- No Title vs H1 consistency checks run
- No visible-price vs JSON-LD-price consistency checks run
- No entity conflict findings produced

---

## Root Cause #6 — GSC Pipeline Replaced but Old Version Kept (HIGH)

**Finding:**  
V3 `search/gsc_pipeline.py` was built with better URL normalization, position bracketing, CTR model, and query miner. But `main.py` still imports and calls `analysis/gsc.py` (V2) for the actual pipeline. The V3 version was built but never swapped in.

**Impact:**  
- `gsc_rows` table = 0 rows (V2 GSCAnalyzer doesn't write to this table)
- `query_page_map` = 0 rows
- Striking distance, cannibalization, CTR headroom: all empty
- `query` CLI subcommand always returns "No GSC mapping found"

---

## Root Cause #7 — Root-Cause Clustering Suppressed by V2 Aggregation (MEDIUM)

**Finding:**  
`technical/root_causes.py` RootCauseClusterer suppresses downstream symptoms (e.g., missing_canonical on a 404 page). But `main.py` uses V2 `build_issue_clusters()` instead.

**Impact:**  
- Issues on 404/noindex pages are counted as separate high-priority issues
- True root causes are buried under symptom counts
- 95,617 raw issues → 289 clusters (good ratio) but many clusters are symptoms, not root causes

---

## Root Cause #8 — Lab Has Only 7 Pages and 4 Evaluated Defect Types (MEDIUM)

**Finding:**  
Lab plants 6 defect types but scorecard only evaluates 4. 14 required defect types not in lab at all.

**Impact:**  
- Lab scorecard reports 100% precision/recall — but only for 4 trivial rules on 7 pages
- JS-only content, redirect chains, hreflang errors, cannibalization: all untested
- Lab gives false confidence

---

## Root Cause #9 — MemoryGuard Used Historical Peak RSS (MEDIUM)

**Status:** Fixed. Now uses `ps -o rss=` for live RSS; falls back to `ru_maxrss`.

---

## Root Cause #10 — CSV Suite Had Table Name Bugs (MEDIUM)

**Status:** Fixed.
- `issue_clusters.csv` now queries `issue_clusters` (was `findings`)
- `schemas.csv` now queries `schemas` (was `schema_items`)
- `issues_critical_high.csv` now uses `LOWER(severity)` case-insensitive comparison

---

## Root Cause #11 — Blueprint Had Hardcoded Domain-Specific Data (LOW)

**Status:** Partially fixed. Blueprint now:
- Queries `schemas` table (with fallback) instead of `schema_items` only
- Falls back to `product_pages` table for entity coverage when `attributes` is empty
- Uses `internal_link_opportunities` for grounded recommended inlinks
- Uses `canonical` column (not `canonical_url`)
- Computes total inlink count via `COUNT(*)` not just sample count

Remaining hardcoded items in blueprint:
- Dimension 14 (recommended outbound links): still `/finance/emi-calculator`, `/services/warranty`
- Dimension 15 (JS health): `rendering_mode` hardcoded as "Server-Rendered HTML (Hydrated)"
- Dimension 18 (freshness): `has_disclaimer: True` hardcoded
- Dimension 19 (competitor comparison): static `80%` parity

---

## Root Cause #12 — GEO Opportunity Block Missing from V3 Engine (LOW)

**Finding:**  
`geo_evals` is now passed to `synthesize_opportunities()` but the engine has no code block to process it. Only AEO opportunities are synthesized. GEO opportunities are silently dropped.

---

## Summary Matrix

| Root Cause | Severity | Fixed? | Fix Required |
|-----------|----------|--------|-------------|
| 22 V3 modules unwired | CRITICAL | ❌ | Wire VerticalRegistry, ProvenanceExtractor, RootCauseClusterer, EntityGraph, IndexFunnel, GSCPipeline, ContentGapV3, JSseo |
| OpportunityEngineV3 empty inputs | CRITICAL | ✅ Partial | GSCPipeline still not wired |
| `findings` table never populated | CRITICAL | ❌ | Add findings insert in OpportunityEngineV3.persist_opportunities |
| EvidenceLedger never called | HIGH | ❌ | Wire EvidenceLedger in opportunity persistence |
| Entity system zero output | HIGH | ❌ | Wire EntityGraphEngine after crawl |
| GSC V3 pipeline not swapped | HIGH | ❌ | Replace V2 GSCAnalyzer with V3 GSCPipeline; write to gsc_rows |
| Root-cause clustering not used | MEDIUM | ❌ | Wire RootCauseClusterer before V3 engine |
| Lab too small / incomplete | MEDIUM | ❌ | Add missing defect types |
| MemoryGuard historical RSS | MEDIUM | ✅ | Fixed via ps command |
| CSV Suite table name bugs | MEDIUM | ✅ | Fixed |
| Blueprint hardcoded data | LOW | ✅ Partial | Remaining hardcoded dims 14, 15, 18, 19 |
| GEO opportunity block missing | LOW | ❌ | Add GEO block in OpportunityEngineV3 |
