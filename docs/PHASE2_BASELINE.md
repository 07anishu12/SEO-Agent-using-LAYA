# SEOJEV Phase 2: Engine Regression Baseline

**Generated:** 2026-09-26  
**Reference Site:** `http://127.0.0.1:8899/` (`lab.server.SyntheticSiteServer`)  
**Scope:** Controlled synthetic test site (<= 50 pages) with 17 planted defect classes  
**Crawl Run Reference:** `crawl_20260926_223133`  
**Output Directory:** `reports/baseline/`  

---

## 1. Key Metric Baseline

Every subsequent refactor and platform stage MUST match these exact counts when executed against the baseline site:

| Metric Category | Metric Key | Baseline Value | Evidence Table / Query |
|:---|:---|:---|:---|
| **Crawl Frontier** | URLs Discovered | **17** | `urls` table count |
| **Crawl Frontier** | URLs Crawled | **12** | `urls WHERE status = 'crawled'` |
| **Crawl Frontier** | URLs Failed | **2** | `urls WHERE status = 'failed'` (redirect loop, dead page) |
| **Crawl Frontier** | URLs Blocked | **1** | `urls WHERE status = 'blocked'` (`/bikes/draft-release` in robots.txt) |
| **Crawl Frontier** | Indexable Pages | **13** | `pages WHERE is_indexable = 1` |
| **Crawl Frontier** | Non-Indexable Pages | **1** | `pages WHERE is_indexable = 0` |
| **Pages Stored** | Total Page Records | **14** | `SELECT count(*) FROM pages WHERE crawl_id = 'crawl_20260926_223133'` |
| **Issues** | Granular Issues | **43** | `SELECT count(*) FROM issues WHERE crawl_id = 'crawl_20260926_223133'` |
| **Clusters** | Issue Clusters | **16** | `SELECT count(*) FROM issue_clusters WHERE crawl_id = 'crawl_20260926_223133'` |
| **Templates** | Distinct Templates | **6** | `SELECT count(*) FROM templates WHERE crawl_id = 'crawl_20260926_223133'` |
| **Findings** | V3 Findings | **48** | `SELECT count(*) FROM findings WHERE run_id = 'crawl_20260926_223133'` |
| **Opportunities** | Synthesized Opportunities | **48** | `SELECT count(*) FROM opportunities WHERE run_id = 'crawl_20260926_223133'` |
| **Work Orders** | Developer Work Orders | **48** | `SELECT count(*) FROM work_orders WHERE run_id = 'crawl_20260926_223133'` |
| **Quality Gate** | Claims Lint Violations | **0** | `lint-report.json` violation count |

---

## 2. Template Clusters Baseline

| Template ID | Page Count | Derived Type | Sample URL |
|:---|:---|:---|:---|
| `tpl_homepage` | 1 | `homepage` | `http://127.0.0.1:8899/` |
| `tpl_listing` | 2 | `listing` | `http://127.0.0.1:8899/bikes` |
| `tpl_model` | 8 | `model` | `http://127.0.0.1:8899/bikes/thunder-250` |
| `tpl_other` | 3 | `other` | `http://127.0.0.1:8899/redirect-chain` |
| `tpl_article` | 0 | `article` | - |
| `tpl_category` | 0 | `category` | - |

---

## 3. Sample Opportunity Fingerprints (Top Ranked)

The opportunity synthesis algorithm generates deterministic fingerprints for each issue pattern:

| Display ID | Priority Score | Tier | Fingerprint | Type | Action Summary |
|:---|:---|:---|:---|:---|:---|
| `TPL-SEO-098` | 60.2 | Medium | `5ae19bf261054104` | TPL | Resolve H1 issues across template |
| `TPL-SEO-089` | 60.1 | Medium | `ce9307d2e5a01439` | TPL | Standardize meta description length |
| `TPL-SEO-092` | 60.0 | Medium | `6143ddca77dabbd0` | TPL | Add required Product / Vehicle Schema |
| `TPL-SEO-093` | 58.0 | Medium | `8bcb6e79e1295f68` | TPL | Audit thin content and expand copy |
| `TPL-SEO-094` | 57.6 | Medium | `935a0be56e363b03` | TPL | Correct canonical mismatch tags |

---

## 4. Generated Deliverables Suite

- `reports/baseline/SEOJEV_V3_AUDIT_REPORT.docx`: Master 28-section Word document
- `reports/baseline/SEOJEV_EXECUTIVE_SUMMARY.docx`: Master Executive summary Word document
- `reports/baseline/explorer.html`: Self-contained interactive HTML explorer
- `reports/baseline/csv/`: 25+ relational CSV tables
- `reports/baseline/tickets/`: Ready-to-import tickets (`github_issues.json`, `jira_import.json`, `linear_import.json`)
- `reports/baseline/summary.json`: Machine-readable KPI summary
- `reports/baseline/crawl-summary.json`: Crawl distribution breakdown
