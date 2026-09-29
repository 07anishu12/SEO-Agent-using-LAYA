# SEOJEV — Technical SEO Intelligence & Work Order Automation Engine

> A production-hardened, deterministic technical SEO intelligence and automated work-order generation platform powered by native Apple Silicon machine learning inference (`laya-mlx`).

[![Architecture: Apple Silicon Metal](https://img.shields.io/badge/Hardware-Apple%20Silicon%20(Metal)-black.svg)](docs/PRODUCTION.md)
[![AI Engine: Laya-MLX Exclusive](https://img.shields.io/badge/AI%20Engine-Laya--MLX%20Exclusive-blue.svg)](docs/LAYA_CONFIDENCE.md)
[![Memory Safety: MemoryGuard](https://img.shields.io/badge/Memory%20Safety-Zero%20Swap%20Growth-brightgreen.svg)](docs/PRODUCTION_READINESS.md)
[![Status: Production Hardened](https://img.shields.io/badge/Status-Production%20Hardened-green.svg)](docs/PRODUCTION_READINESS.md)

SEOJEV transforms raw website crawls into an actionable search engineering operating system. Rather than flooding development teams with thousands of repetitive, unranked per-page alerts, SEOJEV groups crawled pages into structural template families, synthesizes root causes across deterministic crawl signals and internal link graphs, executes calibrated decision inference using a local Apple Silicon MLX model, and emits deduplicated, verified engineering and content work orders.

---

## Production Status & Readiness

SEOJEV is production-hardened across 25 verification dimensions. All universal development limits have been removed from the production pipeline and replaced with configuration-driven resource limits.

| Dimension | Production State | Verified Evidence |
| :--- | :---: | :--- |
| **AI Decision Engine** | **LAYA-MLX EXCLUSIVE** | Pinned checkpoint `aac6fef/laya-mlx`. Zero fallback, mock, or secondary AI models (no OpenAI, Claude, Gemini, DeepSeek, Ollama, llama.cpp). Fails fast and closed if Laya cannot run. |
| **Target Deployment** | **APPLE SILICON** | Native execution on Apple Silicon workstations (M1/M2/M3/M4) and dedicated Apple Silicon servers via Metal hardware acceleration. Supported hybrid cloud topology with containerized storage/queues. |
| **Dev/Prod Initialization** | **HARDENED** | Fresh crawls start Pass 1 cleanly without crashing; stratified dev sampling executes only when an existing crawl database is present. |
| **Memory Safety** | **ZERO SWAP GROWTH** | `MemoryGuard` continuously monitors process RSS, system available RAM, and swap delta. Raises `MemoryBudgetExceeded`, halts crawlers, flushes batches, and saves paused checkpoints for clean resumption. |
| **Authentication & Secrets** | **PRODUCTION SECURE** | High-entropy JWT secrets enforced. Negative authorization and strict tenant isolation verified across all sites, runs, artifacts, alerts, and work orders. Default credentials blocked. |
| **API & Crawler Security** | **SSRF PROTECTED** | Blocks private IP ranges (`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`), loopback (`127.0.0.1`), and cloud metadata (`169.254.169.254`). Strict CORS configuration. |
| **Database & Migrations** | **POSTGRESQL 15+** | Connection pooling with exponential backoff retry. 9 migrations applied and verified. SQLite supported for isolated local development. |
| **Queue & Backpressure** | **REDIS 7+** | Bounded Redis task queue with `max_queue_size` rejection (`QueueFullError`), stale job recovery, and worker retry backoff. |
| **Storage & Artifacts** | **S3 / MINIO** | Content-addressed storage for HTML snapshots, Word reports, CSV suites, and verification bundles. Default `minioadmin` credentials blocked in production. |
| **Health Probes** | **STANDARDIZED** | `/health` & `/health/liveness` for liveness; `/health/ready` & `/ready` checking PostgreSQL, Redis, MinIO, and Apple Silicon MLX readiness (returns 503 on degradation). |

---

## High-Level Architecture & End-to-End Pipeline

```
Raw URLs / Crawl DB
       │
       ▼
Pass 1: Ingest & State Snapshots (SQLite WAL / PostgreSQL + Content-Addressed Store)
       │
       ▼
Pass 2: Deterministic Evidence Extraction (NetworkX Link Graph, SimHash Templates, CWV, Index Funnel)
       │
       ▼
Pass 3: Candidate & Opportunity Reduction (OpportunityEngineV3 multi-factor synthesis & ICE scoring)
       │
       ▼
Pass 4: Laya-MLX Decision Engine (Native Apple Silicon inference across 10 SEO heads, gated confidence)
       │
       ▼
Pass 5: Work Orders & Verification (Class deduplication, canonical schema audit, baseline spec verification)
       │
       ▼
Pass 6: Deliverables & Reports (Master Word reports, Executive summaries, 28 CSV dataset suite, HTML explorer)
```

```mermaid
flowchart TD
    subgraph StorageAndQueue["Infrastructure Layer"]
        PG[("PostgreSQL 15+\n(Sites, Runs, Work Orders)")]
        RedisQueue[("Redis 7+\nBounded Task Queue")]
        S3Store[("S3 / MinIO\nHTML Snapshots & Artifacts")]
    end

    subgraph ServiceLayer["API & Worker Layer"]
        API["FastAPI Platform Service\n• JWT Auth & Multi-Tenancy\n• SSRF Protection\n• Health Probes (/health/ready)"]
        Worker["Background Worker\n(jobs/worker.py)"]
    end

    subgraph CoreEngine["SEOJEV Pipeline (engine/pipeline.py)"]
        P1["Pass 1: Ingest & Snapshot Recorder"]
        P2["Pass 2: Deterministic Evidence (Link Graph, SimHash)"]
        P3["Pass 3: Candidate Reduction (OpportunityEngineV3)"]
        P4["Pass 4: Laya Decision Engine (Exact Prompt Hashing)"]
        P5["Pass 5: Validated Work Orders & Verification"]
        P6["Pass 6: Deliverables (Word, 28 CSVs, Explorer)"]
        MemGuard["MemoryGuard\n(Zero Swap Delta & Budget Enforcement)"]
    end

    subgraph NativeMLX["Apple Silicon MLX Host Boundary"]
        OSLock["Exclusive Host Lock\n(seojev-laya-mlx.lock)"]
        MLX["Native Apple Silicon Metal\n(aac6fef/laya-mlx)"]
        Heads["10 Multi-Task Heads\n(Verdict, Category, Severity, Action, etc.)"]
    end

    API <-->|Enqueue / Status| RedisQueue
    Worker <-->|Pull Tasks| RedisQueue
    Worker --> CoreEngine
    CoreEngine <--> PG
    CoreEngine <--> S3Store
    CoreEngine --- MemGuard
    P4 <-->|submit_batch| MLX
    MLX --- OSLock
    MLX --> Heads
```

---

## Component Responsibilities

| Component | Module | Responsibility |
| :--- | :--- | :--- |
| **API Service** | `api/` | FastAPI REST service providing multi-tenant authentication, RBAC, site/run lifecycle management, SSRF protection, and health probes. |
| **Crawler & Ingest** | `crawler/` | Asynchronous HTTP crawler with robots.txt compliance, sitemap parsing, crawl trap filtering, memory backpressure handling, and SQLite/PostgreSQL frontier storage. |
| **Content Store** | `engine/content_store.py`, `services/object_store.py` | Content-addressed storage of raw HTML payloads keyed by SHA-256 hash in local zlib files or MinIO/S3 buckets. |
| **Evidence Extraction** | `analysis/`, `extraction/` | Internal link graphs (NetworkX PageRank, CheiRank), SimHash DOM layout clustering, Core Web Vitals sampling, and vertical attribute extraction. |
| **Opportunity Engine** | `engine/opportunity_engine_v3.py` | Synthesizes detector findings into structured opportunities with SHA-256 fingerprints, display IDs (`OPP-...`), and 7-factor ICE scores. |
| **Laya-MLX Engine** | `laya/` | Exclusive AI decision maker running on Apple Silicon Metal framework; evaluates candidates across 10 multi-task SEO heads with exact prompt caching. |
| **Memory Guard** | `engine/memory_guard.py` | Actively enforces process RSS budgets, monitors system available RAM, detects swap delta growth, and cleanly pauses runs for safe restart. |
| **Work Order Manager** | `engine/work_orders.py` | Transforms validated opportunities into engineering (`WO-ENG-...`) and content (`WO-CNT-...`) work orders conforming to canonical schema contracts. |
| **Verification Runner** | `verification/runner.py` | Executes baseline acceptance criteria against stored crawl HTML before remediation. |
| **Reporting Suite** | `reporting/` | Generates 28-section Master Word audit report, Executive Summary, 28 CSV dataset suite, and offline HTML Explorer. |

---

## Laya-MLX Exclusive AI Decision Contract

**Laya-MLX is the single, non-negotiable decision engine in SEOJEV.**
- Checkpoint: [`aac6fef/laya-mlx`](https://huggingface.co/aac6fef/laya-mlx) pinned at `@20aed815fc6acde75733882e7ec0e3f28aeb9717`
- 10 Multi-Task Heads: `verdict`, `category`, `severity`, `action`, `scope`, `root_cause`, `canonical_indexability`, `content_assessment`, `cannibalization`, `internal_linking`.
- Calibrated Gating: Decisions evaluated strictly on selected option probabilities:
  $$\text{confidence} = \min\left(P_{\text{verdict}}(\text{choice}), P_{\text{action}}(\text{choice})\right)$$
  - `AUTO_ACCEPT`: $\text{confidence} \ge 0.90$ and $\text{action} \ne \text{'ignore'}$.
  - `HUMAN_REVIEW`: $P_{\text{verdict}} \ge 0.60$ and $P_{\text{action}} \ge 0.50$.
  - `SUPPRESS`: Below threshold or classified as noise.
- **Fail-Closed Guarantee**: If Apple Silicon Metal hardware, MLX, or the pinned checkpoint is unavailable, the pipeline terminates immediately with an explicit error. No secondary AI models or heuristics are permitted.

---

## Deployment Topologies

```
TOPOLOGY 1: Local Apple Silicon Workstation (MacBook Pro / Mac Studio)
  • Host OS: macOS 14+ (Darwin arm64)
  • Storage: Local PostgreSQL & Redis via Homebrew or Docker
  • Engine: Native virtual environment running directly on Metal
  • Use Case: Local development, testing, and single-operator site audits

TOPOLOGY 2: Dedicated Apple Silicon Server (Mac Studio / Mac Pro)
  • Host OS: macOS Sonoma or Sequoia
  • Supervision: launchd daemons managing API and background workers
  • Storage: Dedicated PostgreSQL 15+, Redis 7+, and S3/MinIO
  • Engine: Exclusive native host worker process with single-owner lock
  • Use Case: Production multi-tenant SaaS platform

TOPOLOGY 3: Hybrid Cloud Topology
  • Cloud Tier (Linux/AWS/GCP): Dockerized PostgreSQL, Redis, S3, and API
  • Worker Tier (Apple Silicon host): Host-based worker connects to remote
    Redis queue and executes Pass 4 Laya-MLX Metal inference with full provenance.
```

> [!IMPORTANT]
> **Native Metal Boundary**: Apple Silicon MLX inference requires macOS Metal API access. It **cannot run inside standard Linux Docker containers on macOS**. Non-inference infrastructure (PostgreSQL, Redis, MinIO) can be run via `docker-compose.prod.yml`, while the pipeline and inference worker run on the macOS host.

---

## Quick Start & Installation

### 1. Prerequisites
- macOS 14+ (Sonoma) or 15+ (Sequoia) on Apple Silicon (`arm64`)
- Python 3.11 or 3.12
- PostgreSQL 15+ and Redis 7+
- Playwright with Chromium

### 2. Setup Virtual Environment
```bash
git clone https://github.com/07anishu12/SEO-Agent-using-LAYA.git
cd SEO-Agent-using-LAYA
git checkout fix/laya-pipeline

python3 -m venv .venv
source .venv/bin/activate

pip install --upgrade pip
pip install -r requirements.txt
playwright install chromium
```

### 3. Environment Configuration
Copy the production environment template and configure secrets:
```bash
cp .env.production.example .env.production
# Edit .env.production and set high-entropy JWT_SECRET, DATABASE_URL, REDIS_URL, etc.
```

### 4. Database Migrations
```bash
export DATABASE_URL="postgresql://seojev_user:StrongPassword987!@127.0.0.1:5432/seojev_prod"
python -c "from database.migrator import run_migrations; run_migrations()"
```

### 5. Start Infrastructure (Docker Compose)
Start supporting PostgreSQL, Redis, and MinIO instances:
```bash
docker compose -f docker-compose.prod.yml up -d
```

### 6. Run API Service
```bash
source .venv/bin/activate
uvicorn api.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### 7. Run Background Worker
```bash
source .venv/bin/activate
python -m jobs.worker
```

---

## Health Checks & Monitoring

The platform provides standardized HTTP health and readiness endpoints:

- **Liveness Probe**: `GET /health` or `GET /health/liveness`
  - Returns `200 OK` `{"status": "ok", "environment": "production"}`.
- **Readiness Probe**: `GET /health/ready` or `GET /ready`
  - Deep inspection of PostgreSQL, Redis, MinIO, and Apple Silicon MLX compatibility.
  - Returns `200 OK` when healthy, or `503 Service Unavailable` if any component fails.

---

## Operational CLI Commands

### 1. Preflight Diagnostics
```bash
# Check database tables and Laya schema
.venv/bin/python scripts/diagnose_laya.py --db data/seo.db

# Run real MLX inference probe across existing opportunities
.venv/bin/python scripts/laya_probe.py --db data/seo.db --count 10
```

### 2. Full Production Smoke Test
```bash
# Runs end-to-end bounded validation with real MLX inference, work orders, and zero swap verification
.venv/bin/python scripts/smoke_test.py
```

### 3. Run Pipeline via CLI
```bash
# Fresh crawl and audit in dev profile
.venv/bin/python main.py https://www.drivio.in/ --fresh --profile dev --output reports/audit-run/

# Production audit of existing crawl data
.venv/bin/python main.py https://www.drivio.in/ --crawl-id crawl_20260928_152046 --analyze-only --profile prod
```

### 4. Automated Work Order Verification
```bash
.venv/bin/python main.py verify --work-order SEOJEV-ENG-001 --db data/seo.db
```

---

## Testing & Verification Suites

Execute tests individually to preserve file descriptor and memory isolation:

```bash
# Production hardening suite (Dev init, memory guard, Laya fail-closed, secrets, health endpoints)
PYTHONPATH=. .venv/bin/pytest tests/test_production_hardening.py -v

# Stage 11 Multi-tenant security & SSRF suite (20 tests)
PYTHONPATH=. .venv/bin/pytest tests/test_stage11_security.py -v

# Stage 5 Artifact storage & signed URL suite
PYTHONPATH=. .venv/bin/pytest tests/test_stage5_artifacts.py -v

# Core pipeline, crawler, opportunities, and streaming tests
PYTHONPATH=. .venv/bin/pytest tests/test_v3_core.py -v
PYTHONPATH=. .venv/bin/pytest tests/test_v3_crawler.py -v
PYTHONPATH=. .venv/bin/pytest tests/test_work_order_validation.py -v
PYTHONPATH=. .venv/bin/pytest tests/test_streaming_candidates.py -v
```

---

## Documentation Index

- [Production Deployment Guide](docs/PRODUCTION.md): Topologies, environment variables, launchd supervision, backup/recovery, and troubleshooting.
- [Production Readiness Audit Matrix](docs/PRODUCTION_READINESS.md): Full 25-phase verification checklist and test evidence.
- [Laya Confidence & Gating Policy](docs/LAYA_CONFIDENCE.md): Probability calculations, temperature calibrations, and threshold specifications.
- [Local Memory & Scaling Design](docs/SCALING.md): Process memory budgets, batch autotuning, and global reducer specifications.

---

## License

All rights reserved. Proprietary software.
