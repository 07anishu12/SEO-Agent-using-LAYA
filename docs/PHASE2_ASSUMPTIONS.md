# SEOJEV Phase 2: Decisions & Assumptions Log

**Started:** 2026-09-26  
**Status:** Active  
**Reference:** Operating Contract (Section 0)

---

## 1. Engine Library Wrapping (Stage 0)
- **Assumption 1.1 (Six Passes):** The V3 pipeline is partitioned into 6 discrete, callable passes:
  - `P1_CRAWL`: Crawl & Discovery (Robots.txt, Sitemap indexes, Async HTTP, Selective Playwright rendering, WAL storage, Content store).
  - `P2_SIGNALS`: Signals & Architecture (NetworkX link graph, PageRank, Templates SimHash, Duplicates, Core Web Vitals sample, Product Intelligence, Vertical Provenance, Entity Graph).
  - `P3_SEARCH_OPPORTUNITIES`: Search & Opportunity Synthesis (GSC / SERP pipelines, AEO/GEO evaluators, V3 OpportunityEngine synthesis, Findings population).
  - `P4_CALIBRATION`: Calibration & Decision (Laya MLX local inference on Apple Silicon / fallback classifier, ICE prioritization sensitivity check).
  - `P5_WORK_ORDERS`: Action & Work Orders (WorkOrderManager, Ticket exporters for GitHub/Jira/Linear, ClaimsLinter quality gate).
  - `P6_DELIVERABLES`: Deliverables & Reports (28-Section Master Word Report, Executive Summary Word Report, 25+ CSV suite, Offline HTML explorer, JSON summaries).
- **Assumption 1.2 (Progress Callback Contract):** The progress callback signature is:
  `callback(pass_name: str, pct: float, message: str, meta: Optional[Dict[str, Any]] = None)`
  where `pct` is normalized to `0.0`–`100.0` over the whole run, and `meta` carries pass-specific counters (`urls_crawled`, `issues_count`, `opportunities_count`, etc.).
- **Assumption 1.3 (Cooperative Cancellation):** Cancellation is supported cooperatively via `cancel_check: Callable[[], bool]` checked between URLs in the crawler worker loop and before/during each pipeline pass. When cancelled, the run status in the database transitions to `cancelled`, and a structured `PipelineCancelledException` or status dict is returned without orphan processes.
- **Assumption 1.4 (CLI Preservation):** `main.py` CLI interface and all subcommands (`blueprint`, `verify`, `page`, `template`, `why`, `query`, `watch`, `feedback`, `lab`, `snapshot`, `diff`) remain 100% backward compatible by delegating to `SEOJEVPipeline`.

---

## 2. Data Model & ETL Strategy (Stage 1)
- **Assumption 2.1 (Dual Storage):** The per-run SQLite WAL database in `data/seo.db` (or custom per-run path) remains the engine's scratchpad and local audit store, preserving byte-for-byte fidelity. PostgreSQL serves as the persistent multi-tenant metadata and time-series query layer.
- **Assumption 2.2 (Org Isolation):** Every table in Postgres carries `org_id` (UUID or string) for strict row-level security from Day 1, with a default organization (`org_default`) for single-tenant or initial deployments.
- **Assumption 2.3 (ETL Boundary):** An idempotent ETL process runs upon completion of `P6_DELIVERABLES`, extracting structured records from SQLite into Postgres (`sites`, `runs`, `findings`, `opportunities`, `work_orders`, `templates`, `gsc_summary`, `snapshots`, `audit_log`).

---

## 3. Job Queue & Orchestration (Stages 2–4)
- **Assumption 3.1 (In-Process Library Invocation):** Celery/RQ workers import `SEOJEVPipeline` directly in Python. No shell subprocesses or CLI text scraping are used.
- **Assumption 3.2 (Redis Pub/Sub SSE):** Progress events emitted by `progress_callback` publish directly to Redis channel `run:{run_id}:progress`, which the FastAPI SSE endpoint streams to the browser.
- **Assumption 3.3 (Object Storage):** Deliverables (`.docx`, `.csv`, `.html`, `.zip`) are stored in S3/MinIO. Downloads are served via pre-signed expiring URLs rather than streaming large binaries through the API process.

---

## 4. Frontend & Power Features (Stages 5–11)
- **Assumption 4.1 (Next.js App):** The web frontend is built as a Next.js (TypeScript + Tailwind CSS) client communicating with FastAPI via REST and SSE.
- **Assumption 4.2 (Cloud-Portable Laya):** To ensure portability beyond Apple Silicon Macs, an abstraction interface (`laya/backends/`) allows runtime selection between `mlx` (local Apple Silicon), `llama_cpp` (CPU/CUDA), and `api` (hosted endpoint), defaulting to deterministic fallback when no LLM runtime is available.
- **Assumption 4.3 (Synthetic Lab Generalization):** A held-out synthetic test suite and a hand-labeled sample from a real crawl are added to `lab/` to evaluate real-world false-positive rates beyond planted generator defects.
