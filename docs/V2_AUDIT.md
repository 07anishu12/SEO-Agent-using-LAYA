# SEOJEV V2 Codebase Audit & Baseline Assessment

## 1. Executive Summary
SEOJEV V2 represents a working, performant SEO intelligence prototype. In the initial test on https://www.drivio.in/, it successfully:
- Crawled 5,001 pages (out of 9,250 discovered) and mapped 519,828 internal link edges.
- Consolidated 64,167 raw deterministic issues into 52 structured Issue Clusters.
- Extracted 1,729 automotive product pages with 25-point content checklists.
- Synthesized 5,009 ranking opportunities and 951 concrete internal link injection pairs.
- Executed local inference using `aac6fef/laya-mlx` with median latency of ~57 ms.
- Generated a 23-section Word report, executive summary, and 16 CSV datasets.

However, V2 exhibits architectural bottlenecks and technical debt that must be systematically refactored for V3 Search Intelligence Operating System.

---

## 2. Module Map & Architecture

```
seojev/
├── main.py                     # Monolithic CLI entrypoint & async workflow coordinator
├── config.yaml                 # Static crawler, storage, performance, reporting config
├── models/
│   ├── crawl.py                # CrawlRun and CrawlStats dataclasses
│   ├── page.py                 # PageData and LinkData dataclasses
│   ├── issue.py                # Issue and IssueCluster dataclasses
│   ├── opportunity.py          # RankingOpportunity dataclass
│   └── product.py              # ProductPageData, ProductSpecs, ProductAction dataclasses
├── crawler/
│   ├── crawler.py              # Central async crawler loop, URL queue, workers
│   ├── fetcher.py              # Async HTTPX fetcher with retry & error handling
│   ├── renderer.py             # Playwright browser renderer (selective)
│   ├── normalizer.py           # URL canonicalization and stripping
│   ├── robots.py               # robots.txt parser & compliance checker
│   ├── sitemap.py              # Sitemap & sitemap index recursive discovery
│   ├── scheduler.py            # Priority and politeness scheduler
│   └── storage.py              # SQLite storage layer (WAL mode, threaded lock)
├── analysis/
│   ├── aggregation.py          # Groups raw issues into high-level Issue Clusters
│   ├── gsc.py                  # Google Search Console CSV parser & position bracket analyzer
│   ├── product_intelligence.py # Automotive entity & specification extractor
│   ├── aeo.py                  # Answer Engine Optimization evaluator (0-100 score)
│   ├── geo.py                  # Generative Search Optimization evaluator (0-100 score)
│   ├── serp.py                 # SERP competitor gap analyzer
│   ├── internal_links.py       # NetworkX link graph analysis & PageRank
│   ├── templates.py            # DOM structural hashing and template clustering
│   ├── duplicates.py           # Content hash exact and near-duplicate detection
│   ├── crawl_depth.py          # BFS crawl depth calculation
│   ├── orphan_pages.py         # Inbound link zero detection
│   └── opportunities.py        # Synthesizes RankingOpportunities & ProductActions
├── seo/
│   ├── engine.py               # Deterministic SEO rule runner
│   ├── metadata.py             # Title & Meta description checkers
│   ├── canonical.py            # Canonical tag validation
│   ├── headings.py             # H1-H6 hierarchy checkers
│   ├── content.py              # Word count, thin content, text-to-HTML ratio
│   ├── images.py               # Image alt tag and dimension checkers
│   ├── links.py                # Internal/external link extractor
│   ├── schema.py               # JSON-LD and microdata parser
│   ├── robots_meta.py          # Meta robots and X-Robots-Tag checkers
│   ├── hreflang.py             # Hreflang tag checkers
│   ├── technical.py            # Status code, redirects, content-type checks
│   └── urls.py                 # URL length and structure checks
├── performance/
│   ├── sampler.py              # Stratified URL sampler for performance audits
│   └── lighthouse.py           # Synthetic Lighthouse / CWV measurement
├── laya/
│   ├── analyzer.py             # Laya-MLX local model loader & issue classifier
│   ├── metrics.py              # Latency & decision tracking metrics
│   └── questions.py            # Automotive question bank definitions
└── reporting/
    ├── docx_report.py          # Comprehensive 23-section DOCX report generator
    ├── executive_docx.py       # Standalone Executive Summary DOCX generator
    ├── csv_report.py           # 16 CSV file exporters
    └── json_report.py          # JSON summary & README generator
```

---

## 3. Data Flow & Execution Pipeline in V2
1. **Discovery:** robots.txt parsed -> XML sitemaps discovered -> URLs normalized and queued in SQLite.
2. **Crawl:** Async workers fetch URLs via HTTPX (or Playwright if enabled) -> raw HTML parsed by BeautifulSoup/lxml -> deterministic SEO rules executed -> page records, links, issues written to SQLite.
3. **Graph Analysis:** All pages & links pulled into NetworkX in memory -> PageRank & depths computed -> link issues written to SQLite.
4. **Template & Duplicate Analysis:** Templates clustered by URL and DOM structure -> exact hash duplicates identified -> template issues written to SQLite.
5. **Issue Clustering:** Raw issues consolidated by category and primary template into Issue Clusters -> Laya MLX invoked on clusters -> clusters stored.
6. **Domain Intelligence:** ProductIntelligenceEngine parses vehicle entities -> GSC data joined -> AEO/GEO scores calculated -> RankingOpportunities synthesized.
7. **Reporting:** Data fetched into memory -> CSVs exported -> DOCX reports built via python-docx.

---

## 4. Reusable Components vs Refactor Needs

| Component | Status | Assessment & Path for V3 |
| :--- | :--- | :--- |
| `crawler/robots.py` | **Reusable** | Robust urllib.robotparser integration. Needs adaptive crawl-delay support. |
| `crawler/sitemap.py` | **Reusable** | Handles nested sitemap indexes and gz compression cleanly. |
| `crawler/normalizer.py` | **Reusable** | Clean URL normalization; add tracking param stripping and RFC3986 normalization. |
| `crawler/fetcher.py` | **Refactor** | Needs adaptive rate-limiting (token bucket, 429/5xx backoff, circuit breaker). |
| `crawler/renderer.py` | **Reusable** | Playwright lifecycle is stable; needs bounded browser pool and raw vs render diffing. |
| `crawler/storage.py` | **Refactor** | Extend with V3 numbered migrations, evidence ledger, and content-addressed storage. |
| `analysis/internal_links.py` | **Refactor** | Upgrade graph with DOM link regions (nav, footer, body), anchor quality, and simulation. |
| `analysis/templates.py` | **Refactor** | Extend template clustering to include programmatic parameter matrices and family analysis. |
| `analysis/product_intelligence.py` | **Refactor** | Move vertical-specific logic into `verticals/automotive.py` to ensure core universality. |
| `analysis/gsc.py` | **Refactor** | Add isotonic regression for site-specific CTR curve and cannibalization flip-flop detection. |
| `laya/analyzer.py` | **Refactor** | Constrain Laya strictly to rule-abstention classifier with feature-hash caching. |
| `reporting/docx_report.py` | **Refactor** | Expand from 23 to 28 sections as specified in V3 Master Plan. |
| `reporting/csv_report.py` | **Refactor** | Ensure stable schema, permanent fingerprints, and numeric provenance IDs. |

---

## 5. Technical Debt & False-Positive Sources
1. **Memory Ceiling Risk:** In V2, `storage.get_all_pages()` loads all 5,000+ page dictionaries into memory at once during post-processing. While acceptable at 5k URLs (~250MB RSS), at 10k–50k URLs this will trigger memory pressure. V3 must use streaming generators, chunked queries, and a 2GB RSS watchdog.
2. **Hardcoded Vertical Knowledge in Core Engine:** V2 contained automotive keywords (`KNOWN_BRANDS`, bike terms) directly inside `analysis/product_intelligence.py`. V3 must isolate all vertical knowledge into `verticals/*.py` with generic fallback.
3. **Lack of Evidence Provenance:** Findings in V2 stored string summaries rather than strict evidence pointers (CSS selectors, text spans, line numbers, GSC row references). V3 must introduce an **Evidence Ledger**.
4. **Issue Volatility Across Runs:** Issue keys in V2 used database autoincrement IDs. V3 must compute deterministic **Fingerprints** (`hash(rule_id + scope + subject)`) to enable diffs, tickets, and verification.
5. **Entity Variance False Positives:** Subtle brand prefix differences ("Pulsar 125" vs "Bajaj Pulsar 125") caused entity contradiction alerts in V2. V3 needs alias resolution and learned gazetteers.
6. **No Pre-Deployment Lab Verification:** V2 relied solely on live crawling. V3 must feature **SEOJEV Lab** (synthetic site with planted defects) to guarantee detector precision ≥ 0.95 and recall ≥ 0.85 before live auditing.

---

## 6. Test Coverage Assessment
- Total existing unit tests: 13 tests in `tests/test_*.py`.
- Execution time: ~0.003s.
- Coverage: Basic normalization, sitemap parsing, basic SEO rules, and V2 opportunity models.
- Deficiencies: Zero synthetic integration tests, zero graph simulation tests, zero GSC regression tests, zero claims linting tests.
- V3 target: Comprehensive unit and Lab property tests across all layers.
