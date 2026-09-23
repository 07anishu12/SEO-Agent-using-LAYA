# SEOJEV V3: Assumptions & Decision Log

This document records architectural, algorithmic, and data assumptions made during the design and implementation of SEOJEV V3, adhering to Section 0 of the Operating Contract.

---

## 1. Storage & Compression
- **Assumption 1.1:** Python standard library `zlib` (gzip/deflate compression) is used for content-addressed raw HTML storage in `store/<hash[:2]>/<hash[2:]>.gz` when `zstandard` is not installed in the environment. If `zstandard` is later installed, it will be seamlessly adopted.
- **Assumption 1.2:** Database schema upgrades will be performed via idempotent, forward-compatible SQL migrations on `data/seo.db`. Existing tables and crawls (such as `crawl_20260923_234236`) will not be dropped or truncated.

## 2. Resource Management & Scale Limits
- **Assumption 2.1:** Configurable process RSS memory ceiling is set to 2.0 GB by default. A background memory watchdog samples memory periodically and triggers chunked streaming and garbage collection when RSS exceeds 1.6 GB (80% of ceiling).
- **Assumption 2.2:** Multi-thousand URL analysis runs stream records from SQLite using `yield` generators rather than `fetchall()` to prevent corpus-level memory bloat.

## 3. Absence of Optional Inputs (GSC, SERP, AI Observations)
- **Assumption 3.1:** When Google Search Console (GSC) data is omitted by the user, the system strictly outputs `"Search-performance analysis unavailable until GSC data is supplied."` and tags tabular cells as `GSC REQUIRED`. No estimated traffic or rank positions are fabricated.
- **Assumption 3.2:** When competitor SERP data or APIs are not provided, competitor analysis sections declare `SERP DATA REQUIRED` and proceed with structural on-page heuristics.
- **Assumption 3.3:** When AI observation logs are not provided, the generative search module is labeled `STRUCTURAL GEO ANALYSIS` and evaluates first-party entity clarity, source citations, and schema without inventing AI citation rates.

## 4. Entity & Vertical Separation
- **Assumption 4.1:** All domain-specific automotive knowledge (brands, specs, Indian market two-wheeler terminology) is strictly isolated inside `verticals/automotive.py` and `verticals/ymyl_finance.py`.
- **Assumption 4.2:** The core engine (`seojev/`) operates strictly via universal interfaces (`verticals/generic.py` baseline) to guarantee that running on any external domain (e.g., `https://example.com/`) works seamlessly without source modification.

## 5. Machine Learning (Laya MLX) Usage Boundaries
- **Assumption 5.1:** Local model `aac6fef/laya-mlx` is loaded once per process and strictly utilized as a constrained classifier for deterministic rule abstentions and semantic cluster labeling.
- **Assumption 5.2:** All Laya MLX prompts are bounded to ≤ 500 tokens of structured metadata (never full HTML). Results are cached permanently in `laya_decisions` table by input feature-hash.
