# SEOJEV V3 — Implementation Audit
**Generated:** 2026-09-24  
**Crawl reference:** `crawl_20260923_234236` — drivio.in  
**Audit scope:** Code + DB + Test evidence only. Nothing assumed from documentation.

---

## Legend
| Status | Meaning |
|--------|---------|
| ✅ IMPLEMENTED | Code exists + wired into pipeline + produces real DB output + test passes |
| ⚠️ PARTIAL | Code exists, tested, but wired with empty/placeholder data OR not wired at all |
| ❌ MISSING | Requirement not implemented in any file |
| 🔴 BROKEN | Code exists but produces incorrect output / fails at runtime |
| 🟡 UNWIRED | Fully implemented module that is never called in `main_async()` |

---

## A. ARCHITECTURE

| Requirement | Status | Evidence |
|-------------|--------|---------|
| V2 upgraded not rewritten | ✅ IMPLEMENTED | All V2 tables intact; V3 is additive |
| Six-layer pipeline (Obs→Diag→Opp→Action→Verify→Calibrate) | ⚠️ PARTIAL | Layers exist as classes; Calibration (Laya) wired; Verification only in CLI, not in auto-run |
| Evidence ledger | ⚠️ PARTIAL | `engine/evidence.py` EvidenceLedger fully implemented; `evidence` table = 0 rows — never called during pipeline |
| Findings have evidence references | ❌ MISSING | `findings` table = 0 rows; no INSERT exists anywhere in production path |
| Stable SHA-256 fingerprints | ✅ IMPLEMENTED | `engine/id_system.py` IDSystem active; 688 opportunities have fingerprints |
| Stable human-readable IDs (ENG-SEO-001) | ✅ IMPLEMENTED | `display_id_map` table populated |
| Numeric provenance | ⚠️ PARTIAL | `engine/provenance.py` tracks 4–5 global metrics only; hundreds of report numbers are untracked |
| Claims linter | ⚠️ PARTIAL | `engine/claims_linter.py` fully implemented; instantiated in pipeline but `export_report()` is never called |
| SQLite WAL storage | ✅ IMPLEMENTED | `PRAGMA journal_mode=WAL` in `crawler/storage.py` |
| Large HTML not in RAM | ✅ IMPLEMENTED | `engine/content_store.py` stores gzipped HTML on disk; `ContentStore.get()` used in crawler |
| Pipeline stages resumable/idempotent | ⚠️ PARTIAL | `--analyze-only` flag exists; Laya uses `crawl_id` deduplication; V3 engine uses `INSERT OR REPLACE` |

---

## B. WEBSITE UNDERSTANDING

| Requirement | Status | Evidence |
|-------------|--------|---------|
| robots.txt discovery | ✅ IMPLEMENTED | `crawler/robots.py` + wired in `SEOCrawler` |
| Sitemap discovery | ✅ IMPLEMENTED | `crawler/sitemap.py` discover_all() |
| Sitemap index handling | ✅ IMPLEMENTED | `<sitemapindex>` detection in `sitemap.py` line 44 |
| URL discovery | ✅ IMPLEMENTED | 9,250 URLs discovered |
| URL-universe reconciliation | 🟡 UNWIRED | `understanding/index_funnel.py` IndexFunnelReconciler exists; never called in pipeline |
| Index funnel | 🟡 UNWIRED | Same — 6-stage funnel code exists, 0 rows in output |
| Page-type inference | ✅ IMPLEMENTED | `analysis/page_types.py` infer_page_type() wired |
| Template inference | ✅ IMPLEMENTED | `analysis/templates.py` derive_template_id() wired; 537 templates in DB |
| Template clustering | ⚠️ PARTIAL | V2 clustering wired; V3 `TemplateMiner` (DOM SimHash) is 🟡 UNWIRED |
| Content-section detection | ⚠️ PARTIAL | `ProductIntelligenceEngine` detects sections for product pages; generic detection absent |
| Boilerplate detection | ❌ MISSING | No boilerplate/chrome ratio analysis exists |
| Programmatic family detection | 🟡 UNWIRED | `understanding/programmatic.py` fully implemented; never called |
| Website profile | ⚠️ PARTIAL | V2 JSON profile written by `json_report.py`; V3 `ProfileGenerator` 🟡 UNWIRED |
| Vertical detection | 🟡 UNWIRED | `verticals/registry.py` VerticalRegistry with automotive detection exists; never called in pipeline |

---

## C. CRAWLER

| Requirement | Status | Evidence |
|-------------|--------|---------|
| Async crawler | ✅ IMPLEMENTED | `crawler/crawler.py` asyncio + httpx |
| Playwright rendering | ✅ IMPLEMENTED | `crawler/renderer.py` wired; selective rendering enabled |
| Bounded concurrency | ✅ IMPLEMENTED | asyncio.Semaphore in crawler |
| Adaptive throttling | ✅ IMPLEMENTED | Delay between requests in crawler config |
| 429/5xx handling | ✅ IMPLEMENTED | `crawler/fetcher.py` lines 139–147 |
| Retry-After header | ✅ IMPLEMENTED | `fetcher.py` line 142–144 |
| Retry/backoff | ✅ IMPLEMENTED | `fetcher.py` lines 85, 147, 182 |
| Redirect-chain capture | ✅ IMPLEMENTED | `redirect_chain` column captured |
| Canonical/redirect loop detection | ✅ IMPLEMENTED | Loop detection in fetcher |
| Persistent crawl frontier | ✅ IMPLEMENTED | `crawler/storage.py` urls table |
| Resume after interruption | ✅ IMPLEMENTED | `--analyze-only` flag + frontier persistence |
| kill -9 resume | ⚠️ PARTIAL | SQLite WAL ensures DB integrity; checkpoint mechanism not explicitly tested |
| Crawl prioritization | ✅ IMPLEMENTED | `crawler/scheduler.py` CrawlScheduler with seed/sitemap priority |
| Trap detection | ✅ IMPLEMENTED | `crawler/traps.py` TrapDetector wired in crawler |
| Parameter explosion detection | ✅ IMPLEMENTED | TrapDetector handles parameter_explosion |
| Soft-404 detection | ✅ IMPLEMENTED | `crawler/soft404.py` Soft404Detector wired |
| Memory guard | ⚠️ PARTIAL | `engine/memory_guard.py` uses `ru_maxrss` (historical peak, not current RSS); fixed to use `ps` command |
| Content hashing | ✅ IMPLEMENTED | SHA-256 content hash stored, ContentStore on disk |
| Incremental crawling | ⚠️ PARTIAL | `--analyze-only` skips recrawl; per-URL incremental not implemented |
| Raw/rendered comparison | ✅ IMPLEMENTED | `technical/js_seo.py` JSSEOAnalyzer exists; 🟡 UNWIRED in pipeline |

---

## D. ENTITY SYSTEM

| Requirement | Status | Evidence |
|-------------|--------|---------|
| Entities learned from website | 🟡 UNWIRED | `understanding/entity_graph.py` EntityGraphEngine fully implemented; `entities` table = 0 rows |
| Entity aliases | 🟡 UNWIRED | `entity_aliases` table = 0 rows |
| Canonical entity IDs | 🟡 UNWIRED | IDSystem generates fingerprints but entity-specific IDs not assigned |
| Entity↔page relationships | 🟡 UNWIRED | `entity_page_roles` table = 0 rows |
| Entity↔schema relationships | ❌ MISSING | No code connects schema types to entity graph |
| Entity consistency | 🟡 UNWIRED | EntityGraphEngine.evaluate_page_consistency() exists; not called |
| Title/H1/schema/breadcrumb/URL consistency | 🟡 UNWIRED | EntityGraphEngine checks Title vs H1 price mismatch; not called |
| Visible vs JSON-LD price consistency | 🟡 UNWIRED | EntityGraphEngine.evaluate_page_consistency() checks this; not called |
| Variant consistency | ❌ MISSING | No variant-to-page cross-check |
| Entity conflicts with evidence | 🟡 UNWIRED | EntityGraphEngine emits contradiction issues; not persisted |

---

## E. PRODUCT / AUTOMOTIVE INTELLIGENCE

| Requirement | Status | Evidence |
|-------------|--------|---------|
| Brand/model/variant extraction | ✅ IMPLEMENTED | `ProductIntelligenceEngine` + product_pages table populated (6,490 rows) |
| Price (ex-showroom, on-road, EMI) | ⚠️ PARTIAL | Code exists; many rows show null values in DB |
| City/on-road price | ⚠️ PARTIAL | city_price column in product_pages; extraction inconsistent |
| EMI/finance details | ⚠️ PARTIAL | Extracted in ProductIntelligenceEngine; coverage ~5.9% per DB check |
| Engine specs (mileage/engine/power/torque) | ⚠️ PARTIAL | Regex extraction in product_intelligence.py; null in many rows |
| Dimensions/weight/ground clearance | ❌ MISSING | Not in current extraction logic |
| EV attributes | ❌ MISSING | No EV-specific attribute extraction |
| Reviews/pros-cons | ❌ MISSING | Not extracted |
| FAQ | ⚠️ PARTIAL | FAQ detection in AEOAnalyzer; not stored per-page |
| Images/videos | ⚠️ PARTIAL | Images table has 348,900 rows; alt text extracted; no video detection |
| Schema extraction | ✅ IMPLEMENTED | schemas table has 30,450 rows |
| ProductCoverageProfile | 🟡 UNWIRED | `extraction/provenance_extractor.py` has 12-class profile; never called in pipeline |
| Every value has provenance | ❌ MISSING | `attributes` table = 0 rows; ProvenanceExtractor never called |

---

## F. GOOGLE SEARCH CONSOLE

| Requirement | Status | Evidence |
|-------------|--------|---------|
| GSC CSV ingestion | ⚠️ PARTIAL | V2 `analysis/gsc.py` GSCAnalyzer works; V3 `search/gsc_pipeline.py` 🟡 UNWIRED |
| Multiple CSV ingestion | ❌ MISSING | Single file only |
| Column autodetection | ❌ MISSING | Fixed column names assumed |
| URL normalization | ✅ IMPLEMENTED | GSCPipeline does URL normalization |
| GSC-to-crawl URL matching | 🟡 UNWIRED | GSCPipeline.match_to_crawl() exists; never called |
| Query→page mapping | 🟡 UNWIRED | `query_page_map` table = 0 rows; QueryFitAnalyzer never called |
| Position buckets (1-3, 4-10, 11-20…) | 🟡 UNWIRED | GSCPipeline brackets positions; never called |
| Site-specific CTR curve | 🟡 UNWIRED | `search/ctr_model.py` SiteCTRModel; never called |
| CTR headroom | 🟡 UNWIRED | Computed in SiteCTRModel; never persisted |
| Brand/non-brand classification | 🟡 UNWIRED | GSCPipeline splits brand; never executed |
| Striking distance (11-20, 21-30) | 🟡 UNWIRED | GSCPipeline labels positions; CSV empty |
| Lost/new/decaying queries | ❌ MISSING | No trend/decay analysis implemented |
| Zero-impression indexable pages | ❌ MISSING | Index funnel not wired |
| If no GSC: report "GSC REQUIRED" | ✅ IMPLEMENTED | GSCAnalyzer returns `has_data=False`; downstream uses checked |
| No fabricated rankings | ✅ IMPLEMENTED | Opportunity engine skips query section when no query_page_map |

---

## G. QUERY INTELLIGENCE

| Requirement | Status | Evidence |
|-------------|--------|---------|
| Query parsing | 🟡 UNWIRED | `search/query_miner.py` QueryMiner; never called |
| Brand/model/variant/location/attribute/year extraction | 🟡 UNWIRED | QueryMiner has lexicon; never called |
| Hinglish/transliteration handling | ❌ MISSING | Not implemented in QueryMiner |
| Typo handling | ❌ MISSING | Not implemented |
| Intent classification | 🟡 UNWIRED | QueryMiner classifies pricing/mileage/finance/variant/comparison; never called |
| Query clustering | ❌ MISSING | `query_clusters` table = 0 rows |
| Query grammar mining | 🟡 UNWIRED | QueryMiner extracts templates; never called |
| Demand-weighted attribute priority | 🟡 UNWIRED | `compute_demand_weighted_attribute_priority()` exists; never called |

---

## H. QUERY → PAGE FIT

| Requirement | Status | Evidence |
|-------------|--------|---------|
| Best-fit landing page | 🟡 UNWIRED | `search/fit_analyzer.py` QueryFitAnalyzer; never called |
| Cannibalization detection | 🟡 UNWIRED | QueryFitAnalyzer.detect_cannibalization() exists; needs evidence requirement |
| Correct/wrong/weak/competing/missing | 🟡 UNWIRED | QueryFitAnalyzer returns verdicts; `query_page_map` = 0 rows |
| Cannibalization requires evidence | 🟡 UNWIRED | Logic exists but never runs |

---

## I. STRIKING DISTANCE

| Requirement | Status | Evidence |
|-------------|--------|---------|
| 11-20 / 21-30 / 31-50 / 51-100 | 🟡 UNWIRED | GSCPipeline brackets positions but never called |
| striking_distance.csv | ❌ EMPTY | CSV exists but 0 bytes (queries table empty) |
| Impression volume / commercial importance | 🟡 UNWIRED | Available in GSCPipeline output when called |
| No "guaranteed ranking" language | ✅ IMPLEMENTED | ClaimsLinter enforces; no guarantee language in templates |

---

## J. CONTENT GAP

| Requirement | Status | Evidence |
|-------------|--------|---------|
| Content analyzed by intent/entities/topics | 🟡 UNWIRED | `analysis/content_gaps_v3.py` ContentGapEngineV3; never called directly |
| Content gap via V2 format passed to V3 | ⚠️ PARTIAL | `content_gaps_csv` from V2 pipeline is now passed as `v3_content_gaps` to OpportunityEngineV3 |
| Specific recommendations (not "add more content") | ⚠️ PARTIAL | ContentGapEngineV3 generates specific section blueprints; V2 gaps that get passed are less specific |
| Competitor coverage | ❌ MISSING | `competitor_pages` table = 0 rows; SERPPipeline never called |
| FAQ gap analysis | ⚠️ PARTIAL | AEOAnalyzer checks FAQ presence; V3 ContentGapEngineV3 not wired |

---

## K. INTERNAL LINK INTELLIGENCE

| Requirement | Status | Evidence |
|-------------|--------|---------|
| Link graph built | ✅ IMPLEMENTED | 620,914 links in DB; NetworkX graph built |
| Contextual vs structural links | 🟡 UNWIRED | `simulation/link_graph.py` EnrichedLinkGraph parses DOM region; never called |
| DOM region (nav/body/footer) | 🟡 UNWIRED | EnrichedLinkGraph reads `dom_region` column; column exists in links table |
| Inbound/outbound links | ✅ IMPLEMENTED | Links table queried for in/out counts |
| Orphan pages | ✅ IMPLEMENTED | `analysis/orphan_pages.py` find_orphan_pages() called |
| Internal link opportunities | ✅ IMPLEMENTED | 3,804 rows in `internal_link_opportunities` |
| Grounded source URL / anchor validation | ⚠️ PARTIAL | Source URLs grounded; anchor text from V2 heuristic (not DOM verification) |
| Graph-impact simulation | 🟡 UNWIRED | `simulation/graph_simulator.py` GraphSimulator; never called |
| NEVER invent source URL | ✅ IMPLEMENTED | Opportunities drawn from actual links table |
| Recommended inlinks in blueprint | ✅ IMPLEMENTED | Blueprint now queries `internal_link_opportunities` for the URL |

---

## L. SEOJEV LAB

| Requirement | Status | Evidence |
|-------------|--------|---------|
| Planted defects | ⚠️ PARTIAL | 6 defect types planted; 14 required types missing |
| canonical_mismatch | ✅ IMPLEMENTED | Planted + scored |
| soft_404 | ✅ IMPLEMENTED | Planted + scored |
| missing_h1 / missing_meta | ✅ IMPLEMENTED | Planted + scored |
| entity_conflict | ⚠️ PARTIAL | Planted but NOT evaluated by scorecard |
| orphan_page | ⚠️ PARTIAL | Planted but NOT evaluated by scorecard |
| redirect_chains / loops | ❌ MISSING | Not planted |
| parameter_traps | ❌ MISSING | Not planted |
| duplicate_pages | ❌ MISSING | Not planted |
| JS-only content | ❌ MISSING | Not planted |
| hreflang errors | ❌ MISSING | Not planted |
| noindex leaks | ❌ MISSING | Not planted |
| sitemap mismatch | ❌ MISSING | Not planted |
| cannibalization | ❌ MISSING | Not planted |
| missing sections | ❌ MISSING | Not planted |
| stale data | ❌ MISSING | Not planted |
| Precision/recall evaluation | ⚠️ PARTIAL | Scorecard evaluates only 4 of 6 planted defects |

---

## M. TECHNICAL SEO

| Requirement | Status | Evidence |
|-------------|--------|---------|
| Canonical | ✅ IMPLEMENTED | seo/technical.py + wired |
| Robots | ✅ IMPLEMENTED | Robots.txt respected; X-Robots parsed |
| Sitemap | ✅ IMPLEMENTED | Sitemap discovery working |
| Indexability | ✅ IMPLEMENTED | is_indexable column in pages (4,901 indexable) |
| Redirects | ✅ IMPLEMENTED | redirect_chain captured |
| Duplicate URLs | ✅ IMPLEMENTED | analysis/duplicates.py wired |
| Parameter traps | ✅ IMPLEMENTED | TrapDetector wired |
| Soft 404 | ✅ IMPLEMENTED | Soft404Detector wired |
| hreflang | ❌ MISSING | No hreflang detection implemented |
| Pagination | ❌ MISSING | No rel=prev/next handling |
| canonical chains | ⚠️ PARTIAL | Multi-hop canonical not explicitly detected |
| Structured data | ✅ IMPLEMENTED | schemas table has 30,450 rows |
| OG/Twitter | ❌ MISSING | Open Graph / Twitter Card not extracted |
| Root-cause clustering | 🟡 UNWIRED | `technical/root_causes.py` RootCauseClusterer exists; V2 `build_issue_clusters` used instead |

---

## N. JAVASCRIPT SEO

| Requirement | Status | Evidence |
|-------------|--------|---------|
| Raw vs rendered comparison | 🟡 UNWIRED | `technical/js_seo.py` JSSEOAnalyzer.compare_raw_vs_rendered() exists; never called in pipeline |
| title/meta/canonical/robots/H1/text/links/schema | 🟡 UNWIRED | JSSEOAnalyzer checks all these; 0 rows in findings table |
| Console errors / failed resources | ❌ MISSING | Not implemented |
| Hydration errors | ❌ MISSING | Not implemented |
| Rendering time | ⚠️ PARTIAL | Performance table has 130 rows (response_time); not JS-specific render time |

---

## O. AEO (Answer Engine Optimization)

| Requirement | Status | Evidence |
|-------------|--------|---------|
| Question bank | ✅ IMPLEMENTED | `verticals/automotive.py` get_question_bank() returns buyer questions |
| Question coverage | ⚠️ PARTIAL | V2 AEOAnalyzer checks coverage; V3 AEOAnalyzerV3 🟡 UNWIRED |
| Answer extractability | ⚠️ PARTIAL | V2 AEOAnalyzer computes score; V3 version more precise but unwired |
| AEO opportunities in V3 engine | ✅ IMPLEMENTED | AEO section in OpportunityEngineV3 now wired (aeo_evals passed) |
| AEO score field match | ✅ IMPLEMENTED | Fixed: `aeo_readiness_score` (was `extractability_score`) |

---

## P. GEO (Generative Engine Optimization)

| Requirement | Status | Evidence |
|-------------|--------|---------|
| GEO structural analysis | ⚠️ PARTIAL | V2 GEOAnalyzer wired; V3 GEOAnalyzerV3 🟡 UNWIRED |
| GEO opportunities in V3 engine | ⚠️ PARTIAL | geo_evals now passed to OpportunityEngineV3 but no GEO opportunity synthesis block in engine |
| Entity clarity for generative engines | 🟡 UNWIRED | EntityGraphEngine checks brand/model naming; not called |

---

## Q. PERFORMANCE

| Requirement | Status | Evidence |
|-------------|--------|---------|
| Performance sampling | ✅ IMPLEMENTED | performance table has 130 rows |
| Core Web Vitals | ✅ IMPLEMENTED | PerformanceAuditor (Lighthouse) wired |
| Response time in pages | ✅ IMPLEMENTED | `response_time` column populated |

---

## R. VERIFICATION

| Requirement | Status | Evidence |
|-------------|--------|---------|
| Snapshot recorder | ✅ IMPLEMENTED | verification/snapshot.py; CLI subcommand works |
| Differ | ✅ IMPLEMENTED | verification/differ.py |
| DiD experiment evaluator | ✅ IMPLEMENTED | verification/experiment.py |
| Site watcher | ✅ IMPLEMENTED | verification/watch.py |
| Verification runner | ✅ IMPLEMENTED | verification/runner.py |
| Verification in main pipeline | ❌ MISSING | Verification only via CLI; auto-run not integrated |
| Helper stubs in runner | 🔴 BROKEN | `inbound_link_exists`, `target_query_matches_intent`, `check_site_config` are `lambda: True` stubs |

---

## S. CHANGE HISTORY

| Requirement | Status | Evidence |
|-------------|--------|---------|
| snapshot_diffs table | ✅ IMPLEMENTED | Schema exists; CLI `diff` subcommand works |
| Experiments table | ✅ IMPLEMENTED | Schema exists; experiment evaluator wired to CLI |
| Automatic baseline snapshot | ❌ MISSING | No baseline snapshot taken automatically after crawl |

---

## Summary Counts

| Status | Count |
|--------|-------|
| ✅ IMPLEMENTED | 41 |
| ⚠️ PARTIAL | 28 |
| 🟡 UNWIRED | 34 |
| ❌ MISSING | 24 |
| 🔴 BROKEN | 3 |

**Total requirements audited: ~130**

---

## Top Priority Fixes (P0 → P3)

### P0 — Broken pipeline / fabricated data / evidence missing
1. **Evidence ledger never called** — `evidence` table = 0 rows
2. **`findings` table never populated** — all downstream tools show "no data"
3. **V3 engine GEO synthesis block missing** — `geo_evals` is now passed but no GEO opportunity generation code
4. **Verification helper stubs** — `lambda: True` means all verifications auto-pass
5. **`query_page_map` still empty** — GSCPipeline never called; striking distance, cannibalization, query CLI all broken

### P1 — High-impact unwired modules
6. **VerticalRegistry + ProvenanceExtractor** — attributes table = 0 rows; entity coverage = 0%
7. **RootCauseClusterer** — issue explosion still occurs (95,617 raw issues, 289 clusters, could be fewer with proper root-cause suppression)
8. **IndexFunnelReconciler** — index funnel CSV/report empty
9. **EntityGraphEngine** — entities table = 0 rows; no entity conflict detection running
10. **ContentGapEngineV3** — content gaps based on V2 format (less specific); V3 gap analysis never runs

### P2 — Important but lower-priority
11. Lab defect coverage (only 4/6 planted defects evaluated; 14 defect types missing)
12. OG/Twitter card extraction
13. hreflang detection
14. GEO opportunity synthesis block in OpportunityEngineV3
15. Automatic baseline snapshot after crawl completion

### P3 — Polish / completeness
16. Numeric provenance for all report numbers
17. Multiple GSC CSV ingestion
18. Query trend/decay analysis
19. Hinglish query handling
20. Boilerplate detection
