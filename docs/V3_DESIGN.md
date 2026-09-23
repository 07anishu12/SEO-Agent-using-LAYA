# SEOJEV V3: Search Intelligence Operating System — Architecture & Design

## 1. System Philosophy & Non-Negotiables
SEOJEV V3 is designed as a unified search-intelligence operating system connecting:
`WEBSITE + TEMPLATE + PAGE + QUERY + INTENT + ENTITY + SERP + COMPETITOR + LINK GRAPH + CONTENT + TECHNICAL STATE + AEO + GEO + PERFORMANCE + SEARCH PERFORMANCE + CHANGE HISTORY`

### Core Principles
1. **No Guarantees & Honest Language:** Strict prohibition of predictive ranking or traffic claims. Allowed vocabulary: *observed problem, evidence-backed hypothesis, recommended action, measurable post-change outcome, scenario*.
2. **Claim Typing:** Every stored datum has a single type: `OBSERVED`, `DERIVED`, `INFERRED`, or `HYPOTHESIS`.
3. **Evidence Ledger:** Every finding links to verifiable evidence (URL + selector/line/byte-range, GSC row id, graph edge id, SQL query id).
4. **Stable Identification:** Permanent deterministic fingerprints (`hash(rule_id + scope + normalized_subject)`) combined with display IDs (`ENG-SEO-001`, `PAGE-SEO-001`).
5. **No Blind Hardcoding:** Universal domain support; vertical knowledge isolated in `verticals/` plugins.
6. **Streaming & Memory Ceiling:** Enforced 2 GB RSS ceiling with watchdog and chunked SQLite queries.

---

## 2. Six-Layer Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│ L6 CALIBRATION  - Detector precision, feedback loop, suppression │
├─────────────────────────────────────────────────────────────────┤
│ L5 VERIFICATION - Executable specs, snapshots, diffs, outcome   │
├─────────────────────────────────────────────────────────────────┤
│ L4 ACTION       - Work orders (Eng/Content), exact code points  │
├─────────────────────────────────────────────────────────────────┤
│ L3 OPPORTUNITY  - Opportunity tiering, confidence, effort       │
├─────────────────────────────────────────────────────────────────┤
│ L2 DIAGNOSIS    - Rules, models, clusters, root causes          │
├─────────────────────────────────────────────────────────────────┤
│ L1 OBSERVATION  - Crawls, DOM, GSC, SERP, AI facts, logs        │
├─────────────────────────────────────────────────────────────────┤
│ CROSS-CUTTING EVIDENCE LEDGER & NUMERIC PROVENANCE ENGINE       │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. Database Schema & Migration Strategy

Existing V2 database (`data/seo.db`) will be upgraded in-place via sequential, numbered migration scripts (`crawler/migrations/001_initial_v2.sql`, `002_v3_core_schema.sql`, etc.). Existing crawl runs (`crawl_20260923_234236`) remain intact and queryable.

### V3 Schema Tables

| Table | Layer | Primary Responsibility |
| :--- | :--- | :--- |
| `schema_migrations` | System | Tracks executed migration versions |
| `runs` | System | Extended crawl run metadata, config hashes, RSS metrics |
| `urls` | L1 | Crawl frontier with priority scoring, trap flags, depth |
| `fetches` | L1 | Raw & rendered fetch headers, status, timing, content-hash refs |
| `pages` | L1 | Parsed HTML attributes, metadata, schema tags, canonical status |
| `templates` | L1 | Structural cluster signatures, DOM SimHash, member counts |
| `template_members` | L1 | Mapping of URLs to template clusters with confidence |
| `entities` | L1/L2 | Learned gazetteer: canonical entity records |
| `entity_aliases` | L1/L2 | Fuzzy/token alias mappings to canonical entities |
| `entity_page_roles` | L1/L2 | Entity-to-page graph edges (primary, mentioned, related) |
| `links` | L1 | Enriched internal link edges: DOM region, anchor, rendered-only |
| `schema_items` | L1 | Granular JSON-LD items with property trees and validity |
| `sections` | L1/L2 | Page structural content sections (price, specs, FAQ, reviews) |
| `attributes` | L1 | Extracted entity facts (ex_showroom, emi, mileage) with provenance |
| `gsc_rows` | L1 | Normalized search console rows (query, page, clicks, impr, pos) |
| `queries` | L1/L2 | Extracted query entities, intent labels, language |
| `query_clusters` | L2 | Semantic query clusters by entity + attribute + intent |
| `query_page_map` | L2 | Query-to-page fit verdicts (CORRECT, WRONG, WEAK, CANNIBALIZING) |
| `serp_snapshots` | L1 | Captured SERP feature snapshots per query |
| `competitor_pages` | L1 | Competitor page attribute coverage snapshots |
| `ai_observations` | L1 | Third-party generative AI engine citations & mentions |
| `evidence` | Ledger | Concrete selector, byte-range, DOM snapshot, or row references |
| `findings` | L2 | Diagnosed problems linked to evidence ledger and root causes |
| `opportunities` | L3 | Synthesized opportunities with tier, confidence, effort |
| `actions` | L4 | Concrete engineering & content actionable items |
| `work_orders` | L4 | Developer-ready tickets (ENG-SEO-###, CONTENT-SEO-###) |
| `verifications` | L5 | Executable test specs and before/after verification logs |
| `snapshots` | L5 | State capture of key metrics per URL for diffing |
| `snapshot_diffs` | L5 | Regressions and fixes between snapshot runs |
| `experiments` | L5 | Difference-in-differences cohort evaluation records |
| `numeric_provenance` | Ledger | Mapping of all report figures to backing query/calculation |
| `detector_stats` | L6 | Detector precision and recall tracked against Lab fixtures |
| `feedback` | L6 | User feedback (accepted, false_positive, fixed) for suppression |

---

## 4. Module Boundaries & New Directory Structure

```
seojev/
├── main.py                     # Unified CLI with subcommands (run, blueprint, verify, etc.)
├── config/                     # Config files
│   ├── default.yaml            # Universal default settings
│   └── priority.yaml           # Weightings for Opportunity & Confidence models
├── verticals/                  # Domain-specific knowledge plugins
│   ├── base.py                 # Abstract VerticalInterface
│   ├── generic.py              # Universal baseline implementation
│   ├── automotive.py           # Indian & global automotive domain rules
│   ├── ecommerce.py            # Generic retail & e-commerce
│   ├── saas.py                 # Software-as-a-Service domain rules
│   └── ymyl_finance.py         # YMYL financial / loan compliance overlay
├── store/                      # Content-addressed compressed HTML storage (zlib/zstd)
├── lab/                        # SEOJEV Lab testing & calibration framework
│   ├── server.py               # Local synthetic site server
│   ├── site_generator.py       # Planted defect generator & ground truth manifest
│   ├── gsc_generator.py        # Synthetic GSC generator with planted patterns
│   └── fixtures/               # Golden HTML snapshots
├── engine/                     # Core system engines
│   ├── id_system.py            # Deterministic fingerprint & display ID generator
│   ├── claims_linter.py        # Final quality gate claims & guarantee linter
│   ├── provenance.py           # Numeric provenance ledger
│   └── memory_guard.py         # 2 GB RSS watchdog & streaming controls
├── understanding/              # Website & Entity Understanding
│   ├── profile.py              # Universal WebsiteProfile generator
│   ├── index_funnel.py         # Cross-source Index Funnel reconciler
│   ├── template_miner.py       # Segment & SimHash template clustering
│   ├── programmatic.py         # Matrix family detector (brand x model x city)
│   └── entity_graph.py         # Site-learned gazetteer & consistency engine
├── search/                     # Search Console & Query Intelligence
│   ├── gsc_pipeline.py         # Ingestion, deduplication, URL matching
│   ├── query_miner.py          # Entity/intent parsing & query grammar
│   ├── ctr_model.py            # Site-specific isotonic regression CTR curve
│   └── fit_analyzer.py         # Query-to-page landing fit & cannibalization
├── simulation/                 # Graph Simulation & Link Intelligence
│   ├── link_graph.py           # Enriched link graph with DOM regions
│   ├── recommender.py          # Marginal-gain internal link selector
│   └── graph_simulator.py      # Internal Site Graph Impact simulator
├── verification/               # Verification & Snapshot Loop
│   ├── snapshot.py             # Pre/post snapshot recorder
│   ├── differ.py               # Snapshot diff generator (FIXED, REGRESSED)
│   ├── experiment.py           # Observational difference-in-differences analyzer
│   ├── runner.py               # Executable verification spec runner
│   └── watch.py                # Scheduled site monitor & alert hook
└── reporting/                  # Export & Presentation
    ├── docx_master.py          # Master 28-section Word audit report
    ├── executive_master.py     # Standalone 14-question executive Word report
    ├── blueprint.py            # Page Optimization Blueprint formatter
    ├── ticket_adapters.py      # GitHub, Jira, Linear ticket exporters
    ├── html_explorer.py        # Offline interactive HTML dashboard
    └── csv_suite.py            # 25+ stable CSV exports
```

---

## 5. Upgrade vs Rewrite Matrix

| Subsystem | Strategy | Execution Details |
| :--- | :--- | :--- |
| Crawl Engine | **Upgrade** | Harden `SEOCrawler` with token-bucket politeness, priority frontier, and trap detector. |
| Storage Layer | **Upgrade** | Retain existing `seo.db` data; apply numbered migrations for V3 tables and evidence ledger. |
| Deterministic Rules | **Upgrade** | Move rules into structured detectors; attach selector-level evidence to all findings. |
| Template Engine | **Upgrade** | Extend existing template analyzer with programmatic matrix and boilerplate detection. |
| GSC Analysis | **Upgrade** | Add isotonic regression, brand/non-brand segmentation, and cannibalization evidence tests. |
| Link Graph | **Upgrade** | Retain NetworkX; add DOM region classification, anchored text matching, and graph simulation. |
| Laya Integration | **Upgrade** | Keep Apple Silicon MLX; restrict strictly to abstention classification with feature-hash caching. |
| DOCX Reporting | **Upgrade** | Extend 23-section generator to complete 28-section specification with strict provenance. |
| SEOJEV Lab | **New** | Build standalone synthetic testbench with planted defects and detector scorecards. |
| Verification Loop | **New** | Implement snapshots, diffing, and executable verification runner. |
| Claims Linter | **New** | Implement final-gate AST/regex linter to reject forbidden guarantee wording. |
