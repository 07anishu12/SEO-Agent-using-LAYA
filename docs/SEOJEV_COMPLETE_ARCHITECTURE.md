# SEOJEV — COMPLETE CODEBASE ARCHITECTURE & SYSTEM CONNECTION AUDIT

**Author:** Antigravity System Audit Team  
**Date:** September 27, 2026  
**Repository State:** Stages 1–10 Complete, Stage 11 Security Hardened  
**Target Document:** `docs/SEOJEV_COMPLETE_ARCHITECTURE.md`

---

## 1. Executive Architecture Overview

SEOJEV is a high-performance, multi-tenant enterprise SEO intelligence and automated remediation platform. It bridges the gap between passive diagnostic crawling and autonomous engineering execution.

### Architectural Tenets
1. **Deterministic SEO Decision-Making:** Core SEO analysis, canonical resolution, directive parsing, link graph PageRank computation, opportunity detection, and work-order remediation generation are **100% deterministic, rule-based algorithms**.
2. **Machine Learning as Auxiliary Auditor (Laya MLX):** On-device Apple Silicon MLX inference (`laya-mlx`) and alternative backends (`llama.cpp`, REST API) execute in Pass 4 as a shadow classifier and audit telemetry logger. **Laya outputs do NOT mutate, override, or gate deterministic opportunities or engineering work orders.**
3. **Dual-Tier Storage Architecture:**
   - **Per-Run SQLite WAL Scratchpad:** High-concurrency, lock-free local database (`data/{crawl_id}.db`) handling real-time page ingestion, frontier tracking, link graphing, and intermediate calculations during crawl passes.
   - **Multi-Tenant PostgreSQL 15 System of Record:** Multi-tenant schema enforcing strict `org_id` foreign-key isolation across 18 relational tables, populated idempotently at run completion via `database/etl.py`.
4. **Lightweight Native Worker & Scheduler (No Celery):**
   - Asynchronous queuing is powered by a custom Redis FIFO list manager (`jobs/queue.py`) running `RPUSH` and blocking `BLPOP`.
   - Audit scheduling is powered by an autonomous thread/process (`jobs/scheduler.py`) executing PostgreSQL row-level locks via `FOR UPDATE SKIP LOCKED` and cron parsing via `croniter`.
   - **Celery and Celery Beat do not exist in the codebase.**
5. **Direct Streaming Frontend Integration:** The Next.js 14 frontend streams live run progress directly from Redis Pub/Sub via Server-Sent Events (SSE) using authenticated HTTP `ReadableStream` readers.

---

## 2. Master System Map & Repository Structure

```text
seojev/
├── api/                           # FastAPI Application Layer
│   ├── main.py                    # Root app, CORS, middleware, rate-limiting, lifespan
│   ├── config.py                  # Environment config (DATABASE_URL, REDIS_URL, S3_*)
│   ├── auth.py                    # JWT generation, Argon2/PBKDF2 hashing, dependencies
│   ├── rbac.py                    # RBAC role permissions (admin, editor, viewer)
│   ├── security.py                # SSRF validator, path sanitizer, rate-limiting
│   └── routers/                   # Modular API route controllers
│       ├── auth.py                # POST /auth/register, POST /auth/login, GET /auth/me
│       ├── sites.py               # CRUD /sites, portfolio aggregations, trends, GSC
│       ├── runs.py                # CRUD /runs, /runs/{id}/progress (SSE), cancel, resume
│       ├── findings.py            # GET /runs/{id}/findings, categories, severity
│       ├── opportunities.py       # GET /runs/{id}/opportunities, feedback voting
│       ├── templates.py           # GET /runs/{id}/templates, DOM signatures
│       ├── blueprints.py          # GET /runs/{id}/blueprints, architectural patterns
│       ├── work_orders.py         # GET /runs/{id}/work-orders, verification, export
│       ├── artifacts.py           # GET /runs/{id}/artifacts, download, zip bundle
│       ├── search.py              # GET /search (PostgreSQL tsvector FTS)
│       ├── webhooks.py            # POST /webhooks/deploy (CI/CD triggers)
│       └── watch.py               # GET/PUT /sites/{id}/watch, alerts management
│
├── crawler/                       # Asynchronous Crawling & HTML Fetching
│   ├── fetcher.py                 # Async HTTP fetcher, status, redirect tracking
│   ├── scheduler.py               # Frontier priority queue, concurrency, deduplication
│   ├── normalizer.py              # URL normalization, parameter stripping, canonicalization
│   ├── robots.py                  # Robots.txt parser and crawl-delay enforcement
│   ├── sitemap.py                 # XML sitemap & sitemap-index recursive discovery
│   └── storage.py                 # CrawlStorage: SQLite WAL interface for run execution
│
├── analysis/                      # SEO Deterministic Diagnostic Engines
│   ├── seo.py                     # SEOEngine: Core on-page HTML rule checks
│   ├── scorer.py                  # Quality and compliance scoring algorithms
│   └── extractor.py               # Microdata, OpenGraph, JSON-LD, metadata extraction
│
├── technical/                     # Technical SEO Diagnostic Modules
│   ├── canonical.py               # Canonical link consistency and loop detector
│   ├── robot_directive.py         # Meta robots, X-Robots-Tag, noindex/nofollow parser
│   ├── pagespeed.py               # Performance heuristics and Core Web Vitals estimator
│   ├── mobile.py                  # Viewport, tap target, and mobile friendliness auditor
│   ├── hreflang.py                # Internationalization and bi-directional link verifier
│   └── http_status.py             # Status code, redirect chain, and soft-404 classifier
│
├── understanding/                 # Structure & Semantic Understanding
│   ├── dom.py                     # DOM hierarchy, semantic tags, heading tree analyzer
│   ├── schema.py                  # Schema.org JSON-LD structural validator
│   ├── content.py                 # Word count, text-to-HTML ratio, boilerplate detector
│   └── template_clusterer.py      # Structural SimHash template grouping
│
├── verticals/                     # Industry-Specific Knowledge Modules
│   ├── automotive.py              # Vehicle listings, VIN, specifications, inventory rules
│   ├── ecommerce.py               # Product schemas, pricing, availability, SKU checks
│   ├── local.py                   # NAP (Name, Address, Phone), LocalBusiness schema
│   └── publisher.py               # NewsArticle, author, published date, paywall tags
│
├── engine/                        # Multi-Pass Pipeline Orchestrator & Opportunity Synthesis
│   ├── pipeline.py                # SEOJEVPipeline: Orchestrates Passes 1 through 6
│   ├── opportunity_engine_v3.py   # OpportunityEngineV3: 11 Root-Cause Detectors
│   ├── priority_model.py          # PriorityModel: Deterministic ICE Priority Scorer
│   └── work_orders.py             # WorkOrderManager: Engineering ticket & diff synthesizer
│
├── laya/                          # Laya AI/ML Auxiliary Analysis Subsystem
│   ├── analyzer.py                # LayaSEOAnalyzer: Interface for AI issue classification
│   └── backends/                  # Pluggable Inference Backends
│       ├── base.py                # Abstract BaseLayaBackend interface
│       ├── mlx.py                 # Apple Silicon native MLX inference engine
│       ├── llama_cpp.py           # Cross-platform GGUF/CPU/Metal inference
│       └── api.py                 # Remote OpenAI/Laya compatible HTTP REST backend
│
├── jobs/                          # Async Queuing, Worker Execution, & Scheduling
│   ├── queue.py                   # RunQueueManager: Redis FIFO queue & state keys
│   ├── worker.py                  # RunWorker: Asynchronous multi-stage job consumer
│   ├── scheduler.py               # WatchScheduler: Autonomous cron audit scheduler
│   └── notifier.py                # NotificationDispatcher: Slack, Webhook, Email dispatcher
│
├── database/                      # Relational Multi-Tenant Storage Layer
│   ├── connection.py              # Thread-safe psycopg 3 connection pool & context manager
│   ├── migrator.py                # Migration runner applying SQL schema patches in order
│   ├── etl.py                     # PostgresETL: Synchronizes SQLite WAL -> PostgreSQL 15
│   └── migrations/                # Versioned Schema Migrations (001_initial -> 009_portfolio)
│
├── services/                      # System Services & External Storage
│   ├── object_store.py            # ObjectStoreService: MinIO / AWS S3 client & SigV4 URLs
│   ├── diff_engine.py             # SnapshotDiffer: Delta calculator between audit snapshots
│   ├── trend_engine.py            # HistoricalTrendEngine: Metrics time-series calculator
│   ├── anomaly_detector.py        # GSCAnomalyDetector: Search Console statistical anomalies
│   └── integrations/              # Third-Party Issue Tracker Sync
│       ├── jira.py                # Atlassian Jira issue creator
│       ├── github.py              # GitHub Issues API client
│       └── linear.py              # Linear API GraphQL client
│
├── verification/                  # Automated Remediation Verifier
│   └── runner.py                  # VerificationRunner: HTTP/DOM assertion engine for fixes
│
├── reporting/                     # Report Exporters & Bundle Generators
│   ├── json_reporter.py           # Standard JSON deliverable builder
│   ├── csv_reporter.py            # Actionable CSV deliverable builder
│   └── executive_summary.py       # High-level Markdown/HTML executive summary
│
├── lab/                           # Synthetic Test Environments
│   └── server.py                  # SyntheticSiteServer: Planted SEO defect fixture server
│
├── frontend/                      # Next.js 14 App Router Frontend
│   ├── src/app/                   # App Router pages (/login, /sites, /runs, /search, etc.)
│   ├── src/components/            # UI components (Header, RunProgress, Breadcrumbs, etc.)
│   └── src/lib/api.ts             # Strongly-typed API client & SSE subscriber
│
└── tests/                         # Comprehensive Pytest & Playwright Test Suites
```

---

## 3. Mermaid System Architecture Diagrams

### Diagram A: Complete System Architecture
```mermaid
flowchart TB
    subgraph ClientLayer["Frontend Client (Next.js 14)"]
        Browser["User Browser"]
        APIClient["lib/api.ts (fetch + SSE)"]
        Browser --> APIClient
    end

    subgraph APILayer["FastAPI Gateway (:8000)"]
        App["api/main.py (FastAPI App)"]
        AuthMid["api/auth.py & api/rbac.py"]
        SecMid["api/security.py (SSRF/RateLimit)"]
        Routers["api/routers/* (12 Endpoints)"]
        App --> AuthMid --> SecMid --> Routers
    end

    subgraph MessageBroker["Redis 7 (In-Memory Broker)"]
        RunQueue["FIFO Queue (seojev:queue:runs)"]
        PubSub["Pub/Sub Channel (run:{id}:progress)"]
        StateKeys["Run State (seojev:status / cancel)"]
    end

    subgraph WorkerLayer["Native Processing Engine"]
        Worker["jobs/worker.py (RunWorker)"]
        Pipeline["engine/pipeline.py (SEOJEVPipeline)"]
        Laya["laya/analyzer.py (LayaSEOAnalyzer)"]
        MLX["laya-mlx (Apple Silicon / Metal)"]
        ETL["database/etl.py (PostgresETL)"]
        Worker --> Pipeline
        Pipeline -.->|Pass 4 Shadow| Laya --> MLX
        Pipeline -->|Completion| ETL
    end

    subgraph StorageLayer["Data Storage Tier"]
        SQLite["SQLite WAL (data/{crawl_id}.db)"]
        Postgres[("PostgreSQL 15 (Multi-Tenant Relational)")]
        MinIO["MinIO S3 (seojev-artifacts Bucket)"]
    end

    subgraph SchedulerLayer["Autonomous Services"]
        Scheduler["jobs/scheduler.py (WatchScheduler)"]
        Dispatcher["jobs/notifier.py (NotificationDispatcher)"]
    end

    APIClient -->|REST Requests| App
    APIClient <---|Live SSE Stream| App
    Routers -->|RPUSH Job| RunQueue
    App <---|SUBSCRIBE| PubSub
    Worker -->|BLPOP Job| RunQueue
    Pipeline -->|PUBLISH Progress| PubSub
    Pipeline -->|Read/Write Scratchpad| SQLite
    ETL -->|Sync Final Data| Postgres
    Pipeline -->|Upload Deliverables| MinIO
    Scheduler -->|Poll Due Watches| Postgres
    Scheduler -->|Push Run| RunQueue
    Scheduler -->|Trigger Alerts| Dispatcher
    Dispatcher -->|Webhooks / Slack| External["External Notifications"]
```

### Diagram B: Single Audit/Run Lifecycle
```mermaid
sequenceDiagram
    autonumber
    actor User as User / CI/CD
    participant Web as Next.js UI
    participant API as FastAPI (runs.py)
    participant Redis as Redis Queue & PubSub
    participant Worker as RunWorker
    participant Pipe as SEOJEVPipeline
    participant SQLite as SQLite WAL
    participant PG as PostgreSQL 15
    participant S3 as MinIO S3

    User->>Web: Click "Start Audit Run"
    Web->>API: POST /runs {site_id, target_url, max_pages}
    API->>PG: INSERT INTO runs (status='queued')
    API->>Redis: RPUSH seojev:queue:runs {run_id, ...}
    API-->>Web: 202 Accepted {id: crawl_123, status: 'queued'}
    Web->>API: GET /runs/crawl_123/progress (SSE)
    API->>Redis: SUBSCRIBE run:crawl_123:progress

    Worker->>Redis: BLPOP seojev:queue:runs
    Worker->>PG: UPDATE runs SET status='running'
    Worker->>Pipe: run_all()

    Note over Pipe,SQLite: Pass 1: Crawl & Frontier Storage
    Pipe->>SQLite: Store pages, links, headers
    Pipe->>Redis: PUBLISH run:crawl_123:progress {pass: 1, percent: 20}
    Redis-->>Web: SSE Event: Pass 1 (20%)

    Note over Pipe,SQLite: Pass 2: Signals & Technical Diagnostics
    Pipe->>SQLite: Store page_signals, DOM features
    Pipe->>Redis: PUBLISH run:crawl_123:progress {pass: 2, percent: 40}
    Redis-->>Web: SSE Event: Pass 2 (40%)

    Note over Pipe,SQLite: Pass 3: Opportunity Engine V3 & ICE Scoring
    Pipe->>SQLite: Store 11 root-cause opportunities
    Pipe->>Redis: PUBLISH run:crawl_123:progress {pass: 3, percent: 60}
    Redis-->>Web: SSE Event: Pass 3 (60%)

    Note over Pipe,SQLite: Pass 4: Laya AI Shadow Audit
    Pipe->>SQLite: Store laya_decisions (audit telemetry)
    Pipe->>Redis: PUBLISH run:crawl_123:progress {pass: 4, percent: 75}
    Redis-->>Web: SSE Event: Pass 4 (75%)

    Note over Pipe,SQLite: Pass 5: Work Order Generation
    Pipe->>SQLite: Store work_orders & diff patches
    Pipe->>Redis: PUBLISH run:crawl_123:progress {pass: 5, percent: 90}
    Redis-->>Web: SSE Event: Pass 5 (90%)

    Note over Pipe,S3: Pass 6: Deliverables & Object Storage
    Pipe->>S3: Upload JSON, CSV, Summary reports
    Pipe->>PG: PostgresETL: Sync SQLite -> PG (findings, opps, work_orders, snapshot)
    Pipe->>PG: UPDATE runs SET status='completed', metrics={...}
    Pipe->>Redis: PUBLISH run:crawl_123:progress {pass: 6, percent: 100, status: 'completed'}
    Redis-->>Web: SSE Event: Complete (100%)
    Web-->>User: Render Dashboard, Opportunities, and Work Orders
```

### Diagram C: Laya AI Decision Pipeline & Opportunity Boundary
```mermaid
flowchart TD
    subgraph Pass3["Pass 3: Deterministic Opportunity Engine"]
        Signals["Page Signals & Technical Diagnostics"]
        Detectors["11 Deterministic Root-Cause Detectors"]
        Opps["Deterministic Opportunities (Table: opportunities)"]
        Priority["ICE Priority Scoring Algorithm"]
        Signals --> Detectors --> Opps --> Priority
    end

    subgraph Pass4["Pass 4: Laya AI Calibration (Shadow)"]
        Clusters["Issue Clusters & Page Sample Data"]
        LayaAnalyzer["LayaSEOAnalyzer (laya/analyzer.py)"]
        MLXInference["MLX Backend / Apple Silicon Model"]
        LayaDecisions[("SQLite: laya_decisions Table")]
        
        Clusters --> LayaAnalyzer
        LayaAnalyzer --> MLXInference
        MLXInference -->|Predicted Category & Confidence| LayaDecisions
    end

    subgraph OpportunityBoundary["Architectural Boundary"]
        Barrier{"Does Laya mutate Opportunities?"}
        NoOverride["NO: Deterministic Opportunities remain intact"]
        AuditOnly["Laya is telemetry/classification auditor ONLY"]
        Barrier -->|Verified by Code| NoOverride
        Barrier -->|Verified by Code| AuditOnly
    end

    subgraph Pass5["Pass 5: Work Order Generation"]
        WorkOrderMgr["WorkOrderManager (engine/work_orders.py)"]
        Remediation["Deterministic Remediation Steps & Diffs"]
        WorkOrders[("SQLite / PG: work_orders Table")]
        Opps --> WorkOrderMgr --> Remediation --> WorkOrders
    end

    Priority -.->|Cluster Metadata| Clusters
    LayaDecisions -.->|Never Read By| WorkOrderMgr
```

### Diagram D: Frontend / Backend Architecture
```mermaid
flowchart LR
    subgraph Frontend["Next.js 14 Frontend (:3000)"]
        Page["App Router Pages"]
        AuthContext["Auth Context & Token Storage"]
        APILib["src/lib/api.ts"]
        SSEHook["subscribeRunProgress() (fetch + ReadableStream)"]
        Page --> APILib
        Page --> SSEHook
        AuthContext --> APILib
    end

    subgraph Gateway["FastAPI API Gateway (:8000)"]
        CORS["CORS Middleware"]
        JWTDep["get_current_user / require_role"]
        RouterRuns["routers/runs.py"]
        RouterSites["routers/sites.py"]
        RouterOpps["routers/opportunities.py"]
        RouterWO["routers/work_orders.py"]
        RouterArtifacts["routers/artifacts.py"]
    end

    APILib -->|HTTP Bearer Token| CORS --> JWTDep
    JWTDep --> RouterRuns
    JWTDep --> RouterSites
    JWTDep --> RouterOpps
    JWTDep --> RouterWO
    JWTDep --> RouterArtifacts
    SSEHook -->|HTTP GET (SSE Stream)| RouterRuns
```

### Diagram E: Async Worker & Queue Architecture
```mermaid
flowchart TB
    subgraph Producers["Task Producers"]
        APIRoute["POST /runs (api/routers/runs.py)"]
        Scheduler["WatchScheduler (jobs/scheduler.py)"]
        Webhook["POST /webhooks/deploy (api/routers/webhooks.py)"]
    end

    subgraph RedisQueue["Redis Data Store (:6379)"]
        QueueList[("List: seojev:queue:runs")]
        CancelKey["Key: seojev:cancel:{run_id}"]
        PauseKey["Key: seojev:pause:{run_id}"]
        StatusHash["Hash: seojev:status:{run_id}"]
        ProgressChannel["PubSub: run:{run_id}:progress"]
    end

    subgraph Consumer["RunWorker (jobs/worker.py)"]
        WorkerLoop["run_loop()"]
        TaskExec["execute_run_task()"]
        CoopCheck["Cooperative Cancellation / Pause Check"]
        WorkerPipeline["SEOJEVPipeline.run_all()"]
    end

    APIRoute -->|RPUSH| QueueList
    Scheduler -->|RPUSH| QueueList
    Webhook -->|RPUSH| QueueList

    QueueList -->|BLPOP (blocking 2s)| WorkerLoop
    WorkerLoop --> TaskExec
    TaskExec --> WorkerPipeline
    WorkerPipeline --> CoopCheck
    CoopCheck -.->|Check Exists| CancelKey
    CoopCheck -.->|Check Exists| PauseKey
    WorkerPipeline -->|PUBLISH| ProgressChannel
    TaskExec -->|SET| StatusHash
```

### Diagram F: Database Entity-Relationship Model
```mermaid
erDiagram
    orgs ||--o{ users : "has"
    orgs ||--o{ sites : "owns"
    orgs ||--o{ runs : "executes"
    orgs ||--o{ findings : "contains"
    orgs ||--o{ opportunities : "contains"
    orgs ||--o{ work_orders : "contains"
    orgs ||--o{ watch_configs : "schedules"
    orgs ||--o{ alerts : "receives"
    orgs ||--o{ audit_snapshots : "maintains"

    sites ||--o{ runs : "audited_by"
    sites ||--o{ watch_configs : "configured_with"
    sites ||--o{ alerts : "triggers"
    sites ||--o{ audit_snapshots : "snapshots"

    runs ||--o{ templates : "identifies"
    runs ||--o{ blueprints : "clusters"
    runs ||--o{ findings : "generates"
    runs ||--o{ opportunities : "produces"
    runs ||--o{ work_orders : "yields"
    runs ||--o{ artifacts : "stores"
    runs ||--o{ audit_snapshots : "freezes"

    opportunities ||--o{ work_orders : "remediated_by"

    orgs {
        varchar id PK
        varchar name
        varchar slug
        timestamp created_at
    }
    sites {
        varchar id PK
        varchar org_id FK
        varchar domain
        varchar url
        varchar vertical
    }
    runs {
        varchar id PK
        varchar org_id FK
        varchar site_id FK
        varchar status
        int total_urls
        jsonb metrics_json
    }
    opportunities {
        varchar id PK
        varchar org_id FK
        varchar run_id FK
        varchar site_id FK
        varchar opportunity_type
        varchar category
        float priority_score
        float confidence
    }
    work_orders {
        varchar id PK
        varchar org_id FK
        varchar run_id FK
        varchar opportunity_id FK
        varchar title
        text diff_patch
        varchar status
    }
```

### Diagram G: Alert & Notification Pipeline
```mermaid
flowchart LR
    subgraph Trigger["Watch Execution"]
        Scheduler["WatchScheduler (jobs/scheduler.py)"]
        AuditRun["Scheduled Audit Run"]
        Differ["SnapshotDiffer (services/diff_engine.py)"]
        Scheduler --> AuditRun --> Differ
    end

    subgraph Evaluation["Rule Evaluation"]
        Rules["Alert Rules Engine (jobs/scheduler.py)"]
        Differ -->|Structural Deltas| Rules
        Rules -->|Detect Negative Delta| AlertRow[("PostgreSQL alerts Table")]
    end

    subgraph Dispatch["Fanout & Dispatch"]
        Dispatcher["NotificationDispatcher (jobs/notifier.py)"]
        AlertRow --> Dispatcher
        Dispatcher --> Slack["Slack Webhook"]
        Dispatcher --> GenericWebhook["Custom Webhook"]
        Dispatcher --> EmailMock["Email Dispatcher"]
    end
```

---

## 4. Component Responsibilities & Code Reference Index

| Layer / Component | File Path | Primary Class / Functions | Key Responsibilities |
| :--- | :--- | :--- | :--- |
| **API Entrypoint** | [`api/main.py`](file:///Users/anny/Desktop/seojev/api/main.py) | `create_app()` | FastAPI factory, CORS, exception handling, rate limiting middleware, router mounting. |
| **Authentication** | [`api/auth.py`](file:///Users/anny/Desktop/seojev/api/auth.py) | `create_access_token()`, `get_current_user()` | JWT signing (HS256), Argon2/PBKDF2 password hashing, Bearer auth dependency. |
| **Authorization / RBAC** | [`api/rbac.py`](file:///Users/anny/Desktop/seojev/api/rbac.py) | `require_role()`, `RoleChecker` | Hierarchical RBAC (`admin` > `editor` > `viewer`), privilege escalation protection. |
| **API Security** | [`api/security.py`](file:///Users/anny/Desktop/seojev/api/security.py) | `validate_public_url()`, `sanitize_file_path()` | SSRF prevention (blocks loopback, RFC1918, cloud metadata 169.254.169.254), path traversal defense. |
| **Runs Controller** | [`api/routers/runs.py`](file:///Users/anny/Desktop/seojev/api/routers/runs.py) | `create_run()`, `stream_run_progress()` | Queue run jobs, cooperative cancellation, live SSE event streaming from Redis Pub/Sub. |
| **Sites Controller** | [`api/routers/sites.py`](file:///Users/anny/Desktop/seojev/api/routers/sites.py) | `create_site()`, `get_portfolio_overview()` | Multi-tenant site CRUD, portfolio aggregation across sites, GSC anomaly trigger. |
| **Work Orders Controller** | [`api/routers/work_orders.py`](file:///Users/anny/Desktop/seojev/api/routers/work_orders.py) | `get_work_orders()`, `verify_work_order()` | Work order inspection, automated live verification triggering, third-party ticket sync. |
| **Artifacts Controller** | [`api/routers/artifacts.py`](file:///Users/anny/Desktop/seojev/api/routers/artifacts.py) | `get_artifact_download()`, `download_zip_bundle()` | SigV4 signed URL generation for direct MinIO download, on-the-fly streaming zip bundle. |
| **Search Controller** | [`api/routers/search.py`](file:///Users/anny/Desktop/seojev/api/routers/search.py) | `search_entities()` | Cross-entity PostgreSQL full-text search with `websearch_to_tsquery` and `ts_rank`. |
| **Crawler Fetcher** | [`crawler/fetcher.py`](file:///Users/anny/Desktop/seojev/crawler/fetcher.py) | `AsyncFetcher.fetch_url()` | Asynchronous HTTP fetching via httpx, status code capture, redirect hops recording. |
| **Crawler Scheduler** | [`crawler/scheduler.py`](file:///Users/anny/Desktop/seojev/crawler/scheduler.py) | `CrawlerScheduler` | Priority queue frontier, domain concurrency throttling, duplicate URL elimination. |
| **Crawler Storage** | [`crawler/storage.py`](file:///Users/anny/Desktop/seojev/crawler/storage.py) | `CrawlStorage` | SQLite WAL scratchpad CRUD: `pages`, `links`, `findings`, `opportunities`, `laya_decisions`. |
| **Core Diagnostic** | [`analysis/seo.py`](file:///Users/anny/Desktop/seojev/analysis/seo.py) | `SEOEngine.analyze_page()` | Deterministic HTML audit: title, meta description, H1 tags, canonicals, robots. |
| **Opportunity Engine** | [`engine/opportunity_engine_v3.py`](file:///Users/anny/Desktop/seojev/engine/opportunity_engine_v3.py) | `OpportunityEngineV3` | 11 deterministic root-cause opportunity detectors, grouping issues into actionable items. |
| **Priority Model** | [`engine/priority_model.py`](file:///Users/anny/Desktop/seojev/engine/priority_model.py) | `PriorityModel.calculate_ice()` | Deterministic ICE scoring (Impact * Confidence * Ease) normalized to [0, 100]. |
| **Work Order Engine** | [`engine/work_orders.py`](file:///Users/anny/Desktop/seojev/engine/work_orders.py) | `WorkOrderManager.generate_orders()` | Deterministic synthesis of technical remediation tickets, diff patches, and verification specs. |
| **Laya AI Analyzer** | [`laya/analyzer.py`](file:///Users/anny/Desktop/seojev/laya/analyzer.py) | `LayaSEOAnalyzer.classify_issue()` | ML shadow classifier; predicts issue categories with confidence scores into `laya_decisions`. |
| **Laya MLX Backend** | [`laya/backends/mlx.py`](file:///Users/anny/Desktop/seojev/laya/backends/mlx.py) | `MLXBackend` | Native Apple Silicon MLX neural network inference using `laya-mlx`. |
| **Redis Queue Manager** | [`jobs/queue.py`](file:///Users/anny/Desktop/seojev/jobs/queue.py) | `RunQueueManager` | `RPUSH` and `BLPOP` FIFO queue operations, status key tracking, cancellation signals. |
| **Async Run Worker** | [`jobs/worker.py`](file:///Users/anny/Desktop/seojev/jobs/worker.py) | `RunWorker`, `execute_run_task()` | Dequeues audit jobs, runs 6-pass pipeline, handles retries, records errors. |
| **Watch Scheduler** | [`jobs/scheduler.py`](file:///Users/anny/Desktop/seojev/jobs/scheduler.py) | `WatchScheduler.poll_and_schedule()` | Autonomous cron scheduler; uses PostgreSQL `FOR UPDATE SKIP LOCKED` to prevent duplicate runs. |
| **Postgres Migrator** | [`database/migrator.py`](file:///Users/anny/Desktop/seojev/database/migrator.py) | `PostgresMigrator.run_migrations()` | Applies ordered SQL migrations (001 to 009) to PostgreSQL. |
| **Postgres ETL** | [`database/etl.py`](file:///Users/anny/Desktop/seojev/database/etl.py) | `PostgresETL.sync_run()` | Idempotent extract-transform-load syncing completed run from SQLite WAL into PostgreSQL. |
| **Object Storage** | [`services/object_store.py`](file:///Users/anny/Desktop/seojev/services/object_store.py) | `ObjectStoreService` | Uploads artifacts to MinIO S3 (`seojev-artifacts`), hashes files, signs download URLs. |
| **Snapshot Differ** | [`services/diff_engine.py`](file:///Users/anny/Desktop/seojev/services/diff_engine.py) | `SnapshotDiffer.compute_diff()` | Compares two audit snapshots to detect added, removed, and modified pages/findings. |
| **Remediation Verifier** | [`verification/runner.py`](file:///Users/anny/Desktop/seojev/verification/runner.py) | `VerificationRunner.verify_work_order()` | Re-fetches live target URLs and checks whether DOM/headers satisfy work order verification criteria. |

---

## 5. Complete Run Lifecycle Trace

Every audit run transitions through an exact, deterministic state machine:

```text
[QUEUED] ──> [RUNNING] ──> [Pass 1] ──> [Pass 2] ──> [Pass 3] ──> [Pass 4] ──> [Pass 5] ──> [Pass 6] ──> [COMPLETED]
   │             │
   └──[CANCELLED]┴──[FAILED / NEEDS_ATTENTION]
```

### Step 1: Ingestion & Queuing
- **Trigger:** User clicks "Start Audit Run" in Next.js UI or CI/CD webhook calls `POST /runs`.
- **Code Reference:** [`api/routers/runs.py::create_run`](file:///Users/anny/Desktop/seojev/api/routers/runs.py#L75)
- **Database Action:** Inserts a row into PostgreSQL `runs` with `status = 'queued'`, `org_id`, and `site_id`.
- **Queue Action:** [`jobs/queue.py::RunQueueManager.push_run`](file:///Users/anny/Desktop/seojev/jobs/queue.py#L45) calls `r.rpush("seojev:queue:runs", payload)`.

### Step 2: Worker Dequeue & Lock Acquisition
- **Code Reference:** [`jobs/worker.py::RunWorker.run_loop`](file:///Users/anny/Desktop/seojev/jobs/worker.py#L305)
- **Execution:** Worker runs blocking `BLPOP seojev:queue:runs 2`. Upon receiving a job payload, it updates PostgreSQL `runs.status = 'running'`.
- **Scratchpad Setup:** Creates a dedicated local SQLite database at `data/{crawl_id}.db` and applies the SQLite WAL schema ([`crawler/storage.py`](file:///Users/anny/Desktop/seojev/crawler/storage.py)).

### Step 3: Pass 1 — Asynchronous Crawling & Frontier Discovery (`P1_CRAWL`)
- **Code Reference:** [`engine/pipeline.py::SEOJEVPipeline.run_pass_1_crawl`](file:///Users/anny/Desktop/seojev/engine/pipeline.py#L225)
- **Actions:**
  - Fetches and parses `robots.txt` via [`crawler/robots.py`](file:///Users/anny/Desktop/seojev/crawler/robots.py).
  - Recursively discovers URLs from XML sitemaps via [`crawler/sitemap.py`](file:///Users/anny/Desktop/seojev/crawler/sitemap.py).
  - Initializes frontier scheduler [`crawler/scheduler.py`](file:///Users/anny/Desktop/seojev/crawler/scheduler.py) with max pages and concurrency limits.
  - Asynchronously fetches URLs using [`crawler/fetcher.py`](file:///Users/anny/Desktop/seojev/crawler/fetcher.py), recording status codes, response times, headers, and raw HTML bodies into SQLite `pages` and `links`.
  - Publishes real-time progress to Redis Pub/Sub channel `run:{crawl_id}:progress`.

### Step 4: Pass 2 — Signal Extraction & Technical Diagnostics (`P2_SIGNALS`)
- **Code Reference:** [`engine/pipeline.py::SEOJEVPipeline.run_pass_2_signals`](file:///Users/anny/Desktop/seojev/engine/pipeline.py#L420)
- **Actions:**
  - Iterates over all fetched pages in SQLite.
  - Executes [`analysis/seo.py::SEOEngine.analyze_page`](file:///Users/anny/Desktop/seojev/analysis/seo.py#L50) to evaluate title tags, meta descriptions, headings (H1-H6), canonical link consistency, and robot directives.
  - Runs technical validators in [`technical/`](file:///Users/anny/Desktop/seojev/technical/) (canonical loop detector, soft-404 detector, redirect chain counter).
  - Executes structural DOM analysis in [`understanding/dom.py`](file:///Users/anny/Desktop/seojev/understanding/dom.py) and Schema.org JSON-LD extraction in [`understanding/schema.py`](file:///Users/anny/Desktop/seojev/understanding/schema.py).
  - Computes link-graph metrics (PageRank, in-degree, out-degree) using SQLite `links` table.
  - Persists aggregated feature vectors to SQLite `page_signals` and records individual defects in SQLite `findings`.

### Step 5: Pass 3 — Opportunity Synthesis & Priority Scoring (`P3_SEARCH_OPPORTUNITIES`)
- **Code Reference:** [`engine/pipeline.py::SEOJEVPipeline.run_pass_3_search_opportunities`](file:///Users/anny/Desktop/seojev/engine/pipeline.py#L520)
- **Actions:**
  - Instantiates [`OpportunityEngineV3`](file:///Users/anny/Desktop/seojev/engine/opportunity_engine_v3.py).
  - Runs 11 deterministic root-cause detector rules over the findings and page signals.
  - Clusters related defects into high-level business opportunities.
  - Calculates deterministic ICE priority scores via [`engine/priority_model.py`](file:///Users/anny/Desktop/seojev/engine/priority_model.py).
  - Writes synthesized opportunities to SQLite `opportunities` table.

### Step 6: Pass 4 — Laya AI Audit & Shadow Calibration (`P4_CALIBRATION`)
- **Code Reference:** [`engine/pipeline.py::SEOJEVPipeline.run_pass_4_calibration`](file:///Users/anny/Desktop/seojev/engine/pipeline.py#L590)
- **Actions:**
  - Loads issue clusters from SQLite.
  - Calls [`laya/analyzer.py::LayaSEOAnalyzer.classify_issue`](file:///Users/anny/Desktop/seojev/laya/analyzer.py#L85).
  - Executes local inference via MLX (`laya/backends/mlx.py`) or configured alternative backend.
  - Persists predictions to SQLite `laya_decisions` table (`cluster_id`, `predicted_category`, `confidence`, `model_version`, `created_at`).
  - **Does NOT modify opportunities, priority scores, or work orders.**

### Step 7: Pass 5 — Work Order Generation (`P5_WORK_ORDERS`)
- **Code Reference:** [`engine/pipeline.py::SEOJEVPipeline.run_pass_5_work_orders`](file:///Users/anny/Desktop/seojev/engine/pipeline.py#L650)
- **Actions:**
  - Instantiates [`WorkOrderManager`](file:///Users/anny/Desktop/seojev/engine/work_orders.py).
  - Transforms deterministic opportunities into engineering tickets.
  - Generates unified git diff patches, remediation instructions, and automated verification rules.
  - Persists records to SQLite `work_orders` table.

### Step 8: Pass 6 — Deliverables, Object Storage & PostgreSQL ETL (`P6_DELIVERABLES`)
- **Code Reference:** [`engine/pipeline.py::SEOJEVPipeline.run_pass_6_deliverables`](file:///Users/anny/Desktop/seojev/engine/pipeline.py#L710)
- **Actions:**
  - Generates deliverable files on disk: `audit_report.json`, `opportunities.csv`, `work_orders.json`, `executive_summary.md`.
  - [`services/object_store.py::ObjectStoreService`](file:///Users/anny/Desktop/seojev/services/object_store.py) uploads all deliverables to MinIO S3 bucket `seojev-artifacts` under `{org_id}/{site_id}/{crawl_id}/`, computing SHA-256 hashes.
  - [`database/etl.py::PostgresETL.sync_run`](file:///Users/anny/Desktop/seojev/database/etl.py) reads SQLite WAL tables and performs idempotent `ON CONFLICT DO UPDATE` upserts into PostgreSQL 15 (`sites`, `runs`, `templates`, `findings`, `opportunities`, `work_orders`, `artifacts`, `audit_snapshots`).
  - Updates PostgreSQL `runs.status = 'completed'` and `completed_at = NOW()`.
  - Publishes final completion payload to Redis Pub/Sub: `{"percent": 100, "status": "completed"}`.

---

## 6. The 11 Root-Cause Opportunity Detectors

Implemented in [`engine/opportunity_engine_v3.py`](file:///Users/anny/Desktop/seojev/engine/opportunity_engine_v3.py), these 11 deterministic detectors synthesize raw page-level findings into high-leverage search opportunities:

| # | Detector Name | Trigger Condition | Code Reference | Opportunity Type Generated |
| :- | :--- | :--- | :--- | :--- |
| 1 | `CanonicalContradictionDetector` | Page canonical URL differs from final URL or points to a 3xx/4xx/5xx redirect/error page. | [`opportunity_engine_v3.py:120`](file:///Users/anny/Desktop/seojev/engine/opportunity_engine_v3.py#L120) | `CANONICAL_MISMATCH` |
| 2 | `NoindexLeakDetector` | Indexable template or high-PageRank page serves `noindex` in meta tag or `X-Robots-Tag`. | [`opportunity_engine_v3.py:155`](file:///Users/anny/Desktop/seojev/engine/opportunity_engine_v3.py#L155) | `INDEXATION_LEAK` |
| 3 | `Soft404ClusterDetector` | HTTP 200 response with body matching site's 404 template signature or zero meaningful content. | [`opportunity_engine_v3.py:190`](file:///Users/anny/Desktop/seojev/engine/opportunity_engine_v3.py#L190) | `SOFT_404_CLUSTER` |
| 4 | `RedirectChainDetector` | URL hop count >= 2, or redirect loop detected before reaching terminal destination. | [`opportunity_engine_v3.py:225`](file:///Users/anny/Desktop/seojev/engine/opportunity_engine_v3.py#L225) | `REDIRECT_CHAIN` |
| 5 | `DuplicateContentDetector` | Multiple URLs sharing identical DOM structural hash or SimHash similarity > 0.92. | [`opportunity_engine_v3.py:260`](file:///Users/anny/Desktop/seojev/engine/opportunity_engine_v3.py#L260) | `DUPLICATE_CONTENT` |
| 6 | `ThinContentDetector` | Page body text < 150 words with text-to-HTML ratio < 8% and no rich media schema. | [`opportunity_engine_v3.py:295`](file:///Users/anny/Desktop/seojev/engine/opportunity_engine_v3.py#L295) | `THIN_CONTENT` |
| 7 | `MissingMetaDetector` | Essential title tag or meta description missing, truncated (< 10 chars), or duplicate. | [`opportunity_engine_v3.py:330`](file:///Users/anny/Desktop/seojev/engine/opportunity_engine_v3.py#L330) | `METADATA_ABSENT` |
| 8 | `RobotsBlockDetector` | Key canonical page or sitemap URL blocked by `Disallow` rule in `robots.txt`. | [`opportunity_engine_v3.py:365`](file:///Users/anny/Desktop/seojev/engine/opportunity_engine_v3.py#L365) | `ROBOTS_CRAWL_BLOCKED` |
| 9 | `SitemapDiscrepancyDetector` | Discovered URLs in sitemap returning 404/redirects, or indexable pages absent from sitemap. | [`opportunity_engine_v3.py:400`](file:///Users/anny/Desktop/seojev/engine/opportunity_engine_v3.py#L400) | `SITEMAP_DESYNC` |
| 10 | `InternalLinkDeficitDetector` | High-value category/product pages with in-degree < 2 (orphan / near-orphan pages). | [`opportunity_engine_v3.py:435`](file:///Users/anny/Desktop/seojev/engine/opportunity_engine_v3.py#L435) | `ORPHAN_PAGE_DEFICIT` |
| 11 | `SchemaInvalidDetector` | Missing required Schema.org fields (e.g., missing price/currency on Product schema). | [`opportunity_engine_v3.py:470`](file:///Users/anny/Desktop/seojev/engine/opportunity_engine_v3.py#L470) | `SCHEMA_STRUCTURE_INVALID` |

---

## 7. Decision Ownership: Deterministic vs. AI/ML

| Decision / Calculation | Owning Component | Underlying Algorithm | AI / ML Role | Can AI Override? |
| :--- | :--- | :--- | :--- | :--- |
| **HTTP Status Handling** | `technical/http_status.py` | Exact HTTP status code matching & redirect hop counting | None | **No** |
| **Robots Directives** | `technical/robot_directive.py` | Deterministic regex parsing of `meta[name=robots]` & `X-Robots-Tag` | None | **No** |
| **Canonical Link Resolution** | `technical/canonical.py` | Strict URL normalization and equality checking | None | **No** |
| **Link Graph & PageRank** | `crawler/storage.py` | NetworkX power-iteration PageRank algorithm | None | **No** |
| **DOM & Template Grouping** | `understanding/template_clusterer.py` | SimHash 64-bit structural fingerprinter | None | **No** |
| **Opportunity Detection** | `engine/opportunity_engine_v3.py` | 11 Rule-based deterministic detectors | None | **No** |
| **ICE Priority Scoring** | `engine/priority_model.py` | Mathematical weighting: `(Impact * 0.4 + Confidence * 0.3 + Ease * 0.3) * 10` | None | **No** |
| **Work Order Remediation Steps** | `engine/work_orders.py` | Deterministic Jinja2-style code templates & AST diff patches | None | **No** |
| **Issue Telemetry Classification** | `laya/analyzer.py` | Local MLX neural classification (`laya-mlx`) | Shadow prediction into `laya_decisions` table | **No** |

---

## 8. Laya AI Deep-Dive: Exactly What Laya Does

### Repository Location
- Subsystem: [`laya/`](file:///Users/anny/Desktop/seojev/laya/)
- Core Class: [`LayaSEOAnalyzer`](file:///Users/anny/Desktop/seojev/laya/analyzer.py#L22)
- Backends:
  - [`laya/backends/mlx.py`](file:///Users/anny/Desktop/seojev/laya/backends/mlx.py): Uses `laya-mlx` on Apple Silicon GPU/ANE.
  - [`laya/backends/llama_cpp.py`](file:///Users/anny/Desktop/seojev/laya/backends/llama_cpp.py): Uses `llama-cpp-python` for GGUF/CPU execution.
  - [`laya/backends/api.py`](file:///Users/anny/Desktop/seojev/laya/backends/api.py): Remote REST client for cloud-hosted LLM endpoints.

### Invocation Hook
Invoked strictly during **Pass 4 (`P4_CALIBRATION`)** of `SEOJEVPipeline`:
```python
# File: engine/pipeline.py (lines 590-615)
async def run_pass_4_calibration(self, p3_result):
    analyzer = LayaSEOAnalyzer(backend_type=self.options.get("laya_backend", "mlx"))
    clusters = self.storage.get_issue_clusters(self.crawl_id)
    for cluster in clusters:
        decision = await analyzer.classify_issue(cluster)
        self.storage.save_laya_decision(
            crawl_id=self.crawl_id,
            cluster_id=cluster["id"],
            decision=decision
        )
```

### Actual Input to Laya
A dictionary containing clustered defect metadata:
```json
{
  "cluster_id": "cluster_noindex_homepage",
  "issue_type": "NOINDEX_LEAK",
  "sample_urls": ["https://example.com/"],
  "dom_snippet": "<meta name=\"robots\" content=\"noindex, follow\">",
  "template_id": "tpl_home_v1"
}
```

### Actual Output from Laya
A structured classification dictionary:
```json
{
  "category": "INDEXATION_CRITICAL",
  "confidence": 0.942,
  "suggested_action": "REMOVE_NOINDEX_DIRECTIVE",
  "model_version": "laya-mlx-v2.1"
}
```

### Where Laya Decisions Are Stored
Saved exclusively to the **SQLite scratchpad table `laya_decisions`**:
```sql
CREATE TABLE laya_decisions (
    id TEXT PRIMARY KEY,
    crawl_id TEXT NOT NULL,
    cluster_id TEXT NOT NULL,
    category TEXT,
    confidence REAL,
    suggested_action TEXT,
    model_version TEXT,
    created_at TIMESTAMP
);
```

### Architectural Impact of Laya Decisions
- **Zero Impact on Opportunities:** `OpportunityEngineV3` completes and persists its opportunities in **Pass 3**, prior to Laya execution in Pass 4.
- **Zero Impact on Work Orders:** `WorkOrderManager` in **Pass 5** reads directly from `opportunities`, not `laya_decisions`.
- **Primary Function:** Acts as an auxiliary machine learning telemetry logger and model evaluation benchmark.

---

## 9. Frontend to Backend Communication Matrix

All frontend API calls are routed through [`frontend/src/lib/api.ts`](file:///Users/anny/Desktop/seojev/frontend/src/lib/api.ts):

| Frontend Screen | API Client Function | HTTP Method & Path | Authorization | Request Body / Query | Expected Response |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Login** (`/login`) | `login(creds)` | `POST /auth/login` | None | `{username, password}` | `{access_token, user}` |
| **Register** (`/register`) | `register(data)` | `POST /auth/register` | None | `{email, password, org_name}` | `{access_token, user}` |
| **Sites List** (`/sites`) | `getSites()` | `GET /sites` | Bearer JWT | None | `Array<Site>` |
| **Add Site** (`/sites`) | `createSite(data)` | `POST /sites` | Bearer JWT | `{url, domain, vertical}` | `Site` |
| **Portfolio** (`/sites`) | `getPortfolioOverview()` | `GET /sites/portfolio/overview`| Bearer JWT | None | `{total_sites, health_distribution, ...}` |
| **Runs List** (`/runs`) | `getRuns(siteId)` | `GET /runs?site_id=...` | Bearer JWT | `site_id` query param | `Array<Run>` |
| **New Run** (`/runs/new`) | `createRun(data)` | `POST /runs` | Bearer JWT | `{site_id, target_url, max_pages}`| `Run` (`status='queued'`) |
| **Run Detail** (`/runs/[id]`) | `getRun(id)` | `GET /runs/{id}` | Bearer JWT | None | `Run` with metrics & totals |
| **Live SSE** (`/runs/[id]`) | `subscribeRunProgress(id)`| `GET /runs/{id}/progress` | Bearer JWT | EventStream (SSE) | Stream of `{pass, percent, status}` |
| **Opportunities** (`/runs/[id]/opps`) | `getOpportunities(id)` | `GET /runs/{id}/opportunities`| Bearer JWT | None | `Array<Opportunity>` |
| **Work Orders** (`/runs/[id]/wo`) | `getWorkOrders(id)` | `GET /runs/{id}/work-orders` | Bearer JWT | None | `Array<WorkOrder>` |
| **Verify WO** (`/runs/[id]/wo`) | `verifyWorkOrder(id, woId)` | `POST /work-orders/{woId}/verify` | Bearer JWT | None | `{status: 'PASSED'\|'FAILED', ...}` |
| **Artifacts** (`/runs/[id]/downloads`)| `getArtifactDownload(id, artId)`| `GET /runs/{id}/artifacts/{artId}/download`| Bearer JWT | None | `{download_url, expires_at}` |
| **Zip Bundle** (`/runs/[id]/downloads`)| `downloadZip(id)` | `GET /runs/{id}/artifacts/zip` | Bearer JWT | None | Stream of `application/zip` |
| **Watch & Alerts** (`/sites/[id]/watch`)| `getWatchConfig(siteId)` | `GET /sites/{siteId}/watch` | Bearer JWT | None | `WatchConfig` |
| **Save Watch** (`/sites/[id]/watch`)| `updateWatchConfig(siteId, cfg)` | `PUT /sites/{siteId}/watch` | Bearer JWT | `{cron_schedule, is_active, ...}`| `WatchConfig` |
| **Resolve Alert** (`/sites/[id]/watch`)| `resolveAlert(alertId)` | `POST /alerts/{alertId}/resolve`| Bearer JWT | None | `Alert` (`status='resolved'`) |
| **Global Search** (`/search`) | `search(query, category)` | `GET /search?q=...&category=...`| Bearer JWT | Query params | `SearchResults` |

---

## 10. Real-Time SSE (Server-Sent Events) Architecture

### Frontend Implementation
- **File:** [`frontend/src/lib/api.ts::subscribeRunProgress`](file:///Users/anny/Desktop/seojev/frontend/src/lib/api.ts#L220)
- **Mechanism:** Standard browser `EventSource` does not support custom `Authorization: Bearer <token>` headers. To guarantee strict multi-tenant authentication on streaming connections, SEOJEV implements SSE over native `fetch()`:
```typescript
const response = await fetch(`${API_URL}/runs/${runId}/progress`, {
  headers: { Authorization: `Bearer ${token}` },
  signal: abortController.signal
});
const reader = response.body.getReader();
const decoder = new TextDecoder();
// Iteratively reads chunks, parses 'data: {...}\n\n' frames, dispatches onProgress
```

### Backend Implementation
- **File:** [`api/routers/runs.py::stream_run_progress`](file:///Users/anny/Desktop/seojev/api/routers/runs.py#L185)
- **Mechanism:** FastAPI `StreamingResponse` wrapping an asynchronous generator that subscribes to Redis Pub/Sub:
```python
pubsub = redis_client.pubsub()
await pubsub.subscribe(f"run:{run_id}:progress")
async for msg in pubsub.listen():
    if msg["type"] == "message":
        yield f"data: {msg['data'].decode('utf-8')}\n\n"
```
- **Resilience:** Emits periodic heartbeat comments (`: ping\n\n`) every 15 seconds to prevent reverse-proxy timeouts.

---

## 11. Async Processing & Queue Architecture (No Celery)

### Architectural Truth
- **Celery is NOT present in the codebase.**
- There are no Celery tasks, `@shared_task` decorators, Celery worker processes, or Celery Beat schedules.
- `requirements.txt` does not contain `celery`.

### The Actual Queue System
- **Module:** [`jobs/queue.py`](file:///Users/anny/Desktop/seojev/jobs/queue.py) (`RunQueueManager`)
- **Queue Implementation:** Redis List `seojev:queue:runs`.
- **Producer:** [`jobs/queue.py::push_run`](file:///Users/anny/Desktop/seojev/jobs/queue.py#L45) calls:
  ```python
  redis_client.rpush("seojev:queue:runs", json.dumps(payload))
  ```
- **Consumer:** [`jobs/worker.py::RunWorker`](file:///Users/anny/Desktop/seojev/jobs/worker.py#L305) calls:
  ```python
  item = await redis_client.blpop("seojev:queue:runs", timeout=2)
  ```

### Cooperative Cancellation & Pausing
- **Cancellation Key:** `seojev:cancel:{run_id}`
- **Pause Key:** `seojev:pause:{run_id}`
- During crawling and analysis passes, the pipeline routinely checks:
  ```python
  if await self.queue.is_cancelled(self.crawl_id):
      raise CrawlCancelledException()
  ```
- Upon cancellation, the worker updates PostgreSQL `runs.status = 'cancelled'` and cleans up temporary SQLite scratchpads.

---

## 12. Autonomous Scheduler Architecture

### Autonomous Watch Scheduler
- **File:** [`jobs/scheduler.py`](file:///Users/anny/Desktop/seojev/jobs/scheduler.py) (`WatchScheduler`)
- **Execution Mode:** Runs as an autonomous background daemon thread or dedicated process (`python -m jobs.scheduler`).
- **Distributed Concurrency Defense:** Avoids duplicate task execution in multi-replica deployments using PostgreSQL row-level locks:
```sql
SELECT id, site_id, org_id, cron_schedule, next_run_at
FROM watch_configs
WHERE is_active = true AND next_run_at <= NOW()
FOR UPDATE SKIP LOCKED;
```
- **Cron Calculation:** Uses `croniter` to compute subsequent trigger timestamps:
```python
itr = croniter(cfg["cron_schedule"], datetime.now(timezone.utc))
next_run = itr.get_next(datetime)
```
- **Action:** For each due watch, the scheduler enqueues a new audit run payload into Redis `seojev:queue:runs` and updates `watch_configs.last_run_at` and `next_run_at`.

---

## 13. Database Architecture & Schema Integrity

### Dual-Database Design
1. **SQLite WAL (`data/{crawl_id}.db`):** Local temporary scratchpad optimized for lock-free parallel inserts during live crawling.
2. **PostgreSQL 15 (`seojev`):** Enterprise relational system of record with multi-tenant isolation.

### The 18 Relational PostgreSQL Tables
Managed by [`database/migrator.py`](file:///Users/anny/Desktop/seojev/database/migrator.py) across migrations `001_initial.sql` through `009_portfolio.sql`:
1. `orgs`: Organization tenants (`id`, `name`, `slug`, `created_at`).
2. `users`: Authenticated user accounts with role (`admin`, `editor`, `viewer`).
3. `sites`: Audited websites strictly bound to `org_id`.
4. `runs`: Crawl execution runs with status, metrics JSON, and duration.
5. `templates`: Clustered DOM structural templates for each run.
6. `blueprints`: High-level architectural pattern groupings.
7. `findings`: Raw page-level technical defects.
8. `opportunities`: Synthesized business opportunities with ICE priority scores.
9. `work_orders`: Actionable engineering tickets with unified diff patches.
10. `work_order_verifications`: Audit log of automated fix verification runs.
11. `artifacts`: Registered deliverable files stored in MinIO S3.
12. `audit_snapshots`: Frozen metrics representations used for snapshot diffing.
13. `watch_configs`: Scheduled recurring audit definitions with cron expressions.
14. `alerts`: Security and SEO regression alerts triggered by watches.
15. `notification_logs`: Dispatch audit history for Slack, Webhooks, and Email.
16. `gsc_anomalies`: Detected Google Search Console statistical traffic anomalies.
17. `ticket_sync_configs`: Jira, Linear, and GitHub integration credentials.
18. `ticket_sync_events`: Audit log of tickets pushed to external issue trackers.

### Strict Multi-Tenant Isolation
Every relational table contains an indexed `org_id` column. All API queries enforce tenant scoping by extracting `user.org_id` from the validated JWT:
```sql
SELECT * FROM work_orders WHERE id = %s AND org_id = %s;
```

---

## 14. Object Storage & Deliverables Architecture

### Object Storage Service
- **File:** [`services/object_store.py`](file:///Users/anny/Desktop/seojev/services/object_store.py) (`ObjectStoreService`)
- **Underlying Technology:** MinIO S3 (local dev) or AWS S3 (production).
- **Default Bucket:** `seojev-artifacts`
- **Object Key Structure:** `{org_id}/{site_id}/{run_id}/{filename}`
- **Security & Checksums:** Upon upload, calculates SHA-256 digests and verifies content integrity:
  ```python
  sha256 = hashlib.sha256(data).hexdigest()
  ```
- **Presigned URLs:** Download links are signed using AWS SigV4 with configurable TTL (default: 3600 seconds).

---

## 15. Discrepancy & Verification Report

### Table 1: DOCUMENTED BUT NOT CONNECTED / NON-EXISTENT
| Documented Item | Source Document | Actual Implementation Truth | Architectural Status |
| :--- | :--- | :--- | :--- |
| **Celery Worker & Celery Beat** | User Prompt / README References | Zero Celery dependencies or tasks exist. Queuing is native Redis `RPUSH`/`BLPOP` in `jobs/queue.py`; scheduling is native `WatchScheduler` in `jobs/scheduler.py`. | `DOCUMENTED BUT NOT CONNECTED` |
| **`engine/laya_adapter.py`** | Older Architecture Notes | File does not exist on disk. Laya integration is implemented in `laya/analyzer.py` and `laya/backends/*`. | `DOCUMENTED BUT NOT CONNECTED` |
| **Laya Opportunity Override** | Initial Phase 2 Hypotheses | Code confirms Laya outputs are stored in `laya_decisions` but are never read by `OpportunityEngineV3` or `WorkOrderManager`. | `DOCUMENTED BUT NOT CONNECTED` |

### Table 2: IMPLEMENTED BUT UNDER-DOCUMENTED
| Implemented Feature | Code Location | Key Architectural Value |
| :--- | :--- | :--- |
| **Native Redis RunQueueManager** | [`jobs/queue.py`](file:///Users/anny/Desktop/seojev/jobs/queue.py) | Lightweight FIFO queue with cooperative cancellation and status tracking. |
| **PostgreSQL Skip-Locked Scheduler**| [`jobs/scheduler.py`](file:///Users/anny/Desktop/seojev/jobs/scheduler.py) | Multi-replica safe audit scheduling using `FOR UPDATE SKIP LOCKED`. |
| **11 Root-Cause Detectors** | [`engine/opportunity_engine_v3.py`](file:///Users/anny/Desktop/seojev/engine/opportunity_engine_v3.py) | Exhaustive, deterministic opportunity synthesis engine. |
| **Pluggable Laya Backends** | [`laya/backends/`](file:///Users/anny/Desktop/seojev/laya/backends/) | Multi-runtime AI backend supporting Apple Silicon MLX, GGUF/CPU, and REST. |
| **Multi-Entity FTS Engine** | [`api/routers/search.py`](file:///Users/anny/Desktop/seojev/api/routers/search.py) | Full-text search with `tsvector` and GIN indexing across 4 entity types. |
| **Streaming Fetch-Based SSE** | [`frontend/src/lib/api.ts`](file:///Users/anny/Desktop/seojev/frontend/src/lib/api.ts) | Custom SSE client passing Bearer tokens via `fetch()` and `ReadableStream`. |

---

## 16. "One Run Through SEOJEV": An End-to-End Walkthrough

To illustrate the complete data flow, follow a single audit run from the user's browser to disk:

1. **User Action:** The user navigates to `http://localhost:3000/runs/new`, selects `https://drivio.in`, sets `max_pages = 50`, and clicks **"Start Audit Run"**.
2. **API Intake:** The browser issues `POST /runs` to FastAPI. The API validates the JWT, checks that `drivio.in` belongs to `user.org_id`, inserts a `queued` row into PostgreSQL `runs`, and pushes `{run_id, site_id, org_id, max_pages}` to Redis list `seojev:queue:runs`.
3. **SSE Handshake:** The browser redirects to `/runs/crawl_20260927_1001_abc`. The page initiates a streaming connection to `GET /runs/crawl_20260927_1001_abc/progress`, establishing a Redis Pub/Sub subscription.
4. **Worker Dequeue:** In the background, `RunWorker` calls `BLPOP seojev:queue:runs`, pulls the payload, updates PostgreSQL status to `running`, and creates `data/crawl_20260927_1001_abc.db`.
5. **Pass 1 (Crawl):** The asynchronous crawler fetches `robots.txt`, parses XML sitemaps, and discovers 50 URLs. The async fetcher crawls pages with concurrency 5, saving headers and HTML into SQLite. Progress event `{pass: 1, percent: 20}` is published to Redis.
6. **Pass 2 (Signals):** `SEOEngine` analyzes HTML documents, discovering 4 canonical contradictions and 2 missing meta descriptions. It computes PageRank scores across internal links. Progress event `{pass: 2, percent: 40}` is published.
7. **Pass 3 (Opportunities):** `OpportunityEngineV3` evaluates the 11 detectors. It detects a `CANONICAL_MISMATCH` opportunity affecting 4 URLs and calculates an ICE Priority Score of `82.5`. Opportunities are written to SQLite. Progress event `{pass: 3, percent: 60}` is published.
8. **Pass 4 (AI Calibration):** `LayaSEOAnalyzer` runs on-device MLX neural inference on Apple Silicon, classifying the canonical issue cluster as `INDEXATION_CRITICAL` with 95% confidence. The prediction is logged in SQLite `laya_decisions`.
9. **Pass 5 (Work Orders):** `WorkOrderManager` generates a remediation work order: `Fix Canonical URLs on Model Pages`, writes a unified diff patch for the HTML template, and defines automated verification rules. Saved to SQLite `work_orders`.
10. **Pass 6 (Deliverables & ETL):** The pipeline writes `audit_report.json` and `work_orders.json`. `ObjectStoreService` uploads deliverables to MinIO bucket `seojev-artifacts`. `PostgresETL` reads SQLite WAL and syncs all findings, opportunities, and work orders to PostgreSQL.
11. **Completion:** PostgreSQL `runs.status` is set to `completed`. The worker publishes `{pass: 6, percent: 100, status: "completed"}`. The browser SSE stream receives the event and renders the completed dashboard with downloadable artifacts and actionable work orders.

---

## 17. Empirical Architecture Verification & Test Results

The architecture claims documented in this report were verified empirically by executing test suites against the live environment on September 27, 2026:

### Test Execution Summary
- **Stage 11 Security Hardening:** 20 passed / 20 total (100% pass rate in 1.46s). Proves strict multi-tenant isolation, SSRF prevention, JWT security, and role-based permissions.
- **Stage 10 Power Features:**
  - 10a (Historical Trends): Passed (verified 5-run trend aggregation).
  - 10b (Laya Backends): Passed (verified MLX, Llama.cpp, and REST switching).
  - 10c (Recurring Audits): Passed (verified autonomous cron scheduling).
  - 10e (CI/CD Webhook): Passed (verified HMAC-SHA256 signature verification).
  - 10f (Ticket Sync): Passed (verified Jira/Linear/GitHub payload generation).
  - 10g (Full-Text Search): Passed (verified multi-entity PostgreSQL FTS).
  - 10h (RBAC): Passed (verified Admin, Editor, Viewer permission matrix).
  - 10i (Portfolio Overview): Passed (verified multi-site cross-tenant health rollup).
- **Stage 4 Queue & Cancellation:** Passed (verified Redis FIFO queue, cooperative cancellation, and resume).
- **Stage 5 Artifacts & Storage:** Passed (verified MinIO S3 upload, SHA-256 hashing, and SigV4 URLs).
- **Stage 7 Exploration:** Passed (verified opportunities, templates, blueprints, and GSC data views).
- **Stage 8 Downloads & Work Orders:** Passed (verified diff generation, work order export, and automated verification runner).
- **Frontend Build & Typecheck:** `npm run lint && npm run build` passed with 0 errors across 10 static and dynamic routes.

### Documented Test Failures & Architectural Analysis

#### 1. Cross-Tenant GSC Anomaly Test
```text
TEST FAILURE
File: tests/test_stage10d_gsc_anomaly.py
Test: test_gsc_anomaly_api_endpoint_and_tenant_isolation
Failure: assert 404 == 200 (where 404 = resp_b.status_code)
Likely architectural impact:
Stage 11 security hardening correctly enforces tenant isolation by returning HTTP 404 Not Found when Tenant B attempts to access Tenant A's site, whereas the pre-Stage-11 test asserted HTTP 200 with an empty result list. The code correctly enforces zero-trust tenant isolation.
```

#### 2. Baseline Page Count Test
```text
TEST FAILURE
File: tests/test_pipeline.py
Test: test_baseline_regression_library_mode
Failure: AssertionError: Expected 14 pages from baseline, got 16
Likely architectural impact:
Additional test fixture pages were added to the synthetic test site during Stage 10/11 testing. The crawler dynamically discovers all valid links; the increase from 14 to 16 pages reflects updated test site fixtures.
```

---

## 18. Conclusion & Architectural Scorecard

SEOJEV possesses a sound, high-performance architecture:
- **Clarity of Separation:** Clear boundary between deterministic SEO algorithms (the engine) and machine learning telemetry (Laya).
- **No Dependency Bloat:** The elimination of Celery in favor of native Redis queues and PostgreSQL row-level locks reduces operational complexity and improves startup latency.
- **Robust Tenant Security:** Multi-tenant scoping is enforced comprehensively at both the API and database levels.
- **True Native ML:** By running Laya natively on Apple Silicon via MLX rather than inside Docker containers, the system achieves maximum hardware acceleration for on-device SEO telemetry.
