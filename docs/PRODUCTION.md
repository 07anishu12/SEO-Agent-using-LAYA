# SEOJEV Production Deployment Guide

This guide details the requirements, architecture, deployment procedures, operational practices, and troubleshooting steps for deploying **SEOJEV** in production.

---

## 1. Architectural Overview & Boundaries

SEOJEV is a deterministic technical SEO intelligence and automated work-order generation platform. Its architecture is split into two primary operational tiers:

1. **State & Orchestration Tier**:
   - **PostgreSQL 15+**: Canonical relational storage for sites, runs, pages, links, issues, opportunities, work orders, verifications, and audit logs.
   - **Redis 7+**: Bounded job queues, task backpressure, rate-limiting counters, and worker task synchronization.
   - **Object Storage (S3 / MinIO)**: Content-addressed HTML snapshot storage, PDF/Word audit reports, CSV exports, and verification artifacts.
   - **FastAPI Platform Service**: REST API handling multi-tenant authentication, run lifecycle management, and artifact downloads.
   - **Background Workers**: Asynchronous ingestion, deterministic evidence extraction, and work order generation.

2. **AI Decision Tier (Laya-MLX)**:
   - **Exclusive Model**: `aac6fef/laya-mlx` (4-bit quantized transformer on Apple Silicon Metal framework).
   - **Native Hardware Boundary**: MLX requires direct access to Apple Silicon GPU hardware via the macOS Metal driver framework. **MLX cannot run inside standard Linux Docker containers on macOS.**
   - **Fail-Closed Policy**: Laya-MLX is the **exclusive** decision engine. The system never falls back to OpenAI, Claude, Gemini, DeepSeek, Ollama, llama.cpp, or heuristic substitutes. If Laya-MLX is unavailable, the pipeline terminates immediately with an explicit fatal error.

---

## 2. Target Deployment Topologies

SEOJEV supports three production deployment topologies:

```
┌────────────────────────────────────────────────────────────────────────┐
│ TOPOLOGY 1: Local Apple Silicon Workstation (MacBook Pro / Mac Studio) │
│ - Host OS: macOS 14+ (Darwin arm64)                                    │
│ - Storage/Cache: PostgreSQL & Redis running via Homebrew or Docker     │
│ - MLX Engine: Native virtual environment running directly on host Metal│
│ - Scope: Single-node high-performance audits                           │
└────────────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────────────┐
│ TOPOLOGY 2: Dedicated Apple Silicon Server (Mac Studio / Mac Pro)      │
│ - Host OS: macOS Sonoma/Sequoia                                        │
│ - Process Supervision: launchd or systemd-compatible process manager   │
│ - Storage: Dedicated PostgreSQL + Redis + MinIO / S3                   │
│ - MLX Engine: Native host worker process with single-owner lock        │
│ - High Availability: Host-level automated restart and health probes    │
└────────────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────────────┐
│ TOPOLOGY 3: Hybrid Dedicated / Cloud Topology                          │
│ - Cloud Tier (Linux/AWS/GCP): Dockerized PostgreSQL, Redis, S3, API    │
│ - Inference Worker (Apple Silicon host): Connects to remote Redis queue│
│   and Postgres to pull Pass 4 candidates and execute native MLX Metal  │
│   inference with full provenance.                                      │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Host System Requirements

### Hardware
- **Processor**: Apple Silicon (M1/M2/M3/M4 Pro, Max, or Ultra recommended).
- **RAM**: Minimum 16 GB unified memory (32 GB+ recommended for large sites).
- **Disk**: 50 GB+ NVMe SSD storage for crawl databases and content snapshots.

### Software
- **Operating System**: macOS 14.0+ (Sonoma) or macOS 15.0+ (Sequoia).
- **Python**: Python 3.11 or 3.12 (Native `arm64`).
- **File Descriptors**: `ulimit -n 10240` (automatically managed by CLI and worker).
- **Supporting Services**:
  - PostgreSQL 15 or 16
  - Redis 7.0+
  - MinIO (or AWS S3)

---

## 4. Environment Configuration

In production, all secrets and configurations **must** be provided via environment variables. The API and workers execute strict preflight validation (`api/config.py:validate_production_secrets()`) and will refuse to boot if insecure defaults are detected.

### Mandatory Environment Variables

Create `/etc/seojev/production.env` or configure your secret store:

```bash
# Environment Mode
ENVIRONMENT=production
SEOJEV_PROFILE=prod

# Security & Secrets (MUST BE HIGH ENTROPY)
# Generate with: openssl rand -hex 32
JWT_SECRET=9f8e7d6c5b4a3928172635441324354657687980818283848586878889909192
ACCESS_TOKEN_EXPIRE_MINUTES=60
CORS_ORIGINS=https://seo.yourdomain.com,https://api.yourdomain.com

# PostgreSQL Connection (Connection pooling enabled)
DATABASE_URL=postgresql://seojev_user:StrongPassword987!@127.0.0.1:5432/seojev_prod

# Redis Connection (Authentication required in production)
REDIS_URL=redis://:StrongRedisAuth987!@127.0.0.1:6379/0
REDIS_MAX_QUEUE_SIZE=1000

# Object Storage (MinIO / S3)
S3_ENDPOINT_URL=https://s3.yourdomain.com
S3_ACCESS_KEY=prod_access_key_987
S3_SECRET_KEY=prod_secret_key_extremely_secure_xyz
S3_BUCKET_NAME=seojev-artifacts-prod
S3_REGION=us-east-1
S3_USE_SSL=true

# Engine & Memory Limits
SEOJEV_MAX_URLS=5000000
SEOJEV_MEMORY_BUDGET_MB=32768
SEOJEV_MIN_AVAILABLE_MB=4096
SEOJEV_MAX_SWAP_DELTA_MB=128.0
SEOJEV_MAX_WORKERS=8
SEOJEV_BATCH_SIZE=32
SEOJEV_QUEUE_SIZE=64

# Laya-MLX Exclusive AI Backend
LAYA_MODEL_CHECKPOINT=aac6fef/laya-mlx
LAYA_LOCK_FILE=/var/run/seojev/laya-mlx.lock
```

---

## 5. Step-by-Step Production Deployment

### Step 1: Clone and Prepare Virtual Environment

```bash
git clone https://github.com/07anishu12/SEO-Agent-using-LAYA.git /opt/seojev
cd /opt/seojev
git checkout fix/laya-pipeline

# Create dedicated Python arm64 virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install production dependencies
pip install --upgrade pip
pip install -r requirements.txt
playwright install chromium
```

### Step 2: Database Setup & Migrations

1. Create PostgreSQL user and database:
```sql
CREATE USER seojev_user WITH PASSWORD 'StrongPassword987!';
CREATE DATABASE seojev_prod OWNER seojev_user;
GRANT ALL PRIVILEGES ON DATABASE seojev_prod TO seojev_user;
```

2. Run schema migrations:
```bash
source .venv/bin/activate
export DATABASE_URL="postgresql://seojev_user:StrongPassword987!@127.0.0.1:5432/seojev_prod"
python -c "from database.migrator import run_migrations; run_migrations()"
```

3. Verify migration status:
```bash
python -c "from database.migrator import check_migrations_applied; check_migrations_applied()"
```

### Step 3: Object Storage Setup

Ensure your S3 bucket or MinIO bucket is created:
```bash
# Using AWS CLI or MinIO Client (mc)
mc alias set minio_prod https://s3.yourdomain.com prod_access_key_987 prod_secret_key_extremely_secure_xyz
mc mb minio_prod/seojev-artifacts-prod
```

### Step 4: Process Supervision (macOS launchd)

On dedicated Apple Silicon servers, supervise the API and background workers using `launchd`.

#### API Service: `/Library/LaunchDaemons/com.seojev.api.plist`
```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.seojev.api</string>
    <key>ProgramArguments</key>
    <array>
        <string>/opt/seojev/.venv/bin/uvicorn</string>
        <string>api.main:app</string>
        <string>--host</string>
        <string>0.0.0.0</string>
        <string>--port</string>
        <string>8000</string>
        <string>--workers</string>
        <string>4</string>
    </array>
    <key>WorkingDirectory</key>
    <string>/opt/seojev</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/opt/seojev/.venv/bin:/usr/local/bin:/usr/bin:/bin</string>
        <key>ENVIRONMENT</key>
        <string>production</string>
    </dict>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/var/log/seojev/api.log</string>
    <key>StandardErrorPath</key>
    <string>/var/log/seojev/api_error.log</string>
</dict>
</plist>
```

#### Worker Service: `/Library/LaunchDaemons/com.seojev.worker.plist`
```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.seojev.worker</string>
    <key>ProgramArguments</key>
    <array>
        <string>/opt/seojev/.venv/bin/python</string>
        <string>-m</string>
        <string>jobs.worker</string>
    </array>
    <key>WorkingDirectory</key>
    <string>/opt/seojev</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/opt/seojev/.venv/bin:/usr/local/bin:/usr/bin:/bin</string>
        <key>ENVIRONMENT</key>
        <string>production</string>
    </dict>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/var/log/seojev/worker.log</string>
    <key>StandardErrorPath</key>
    <string>/var/log/seojev/worker_error.log</string>
</dict>
</plist>
```

Load and start services:
```bash
sudo launchctl load -w /Library/LaunchDaemons/com.seojev.api.plist
sudo launchctl load -w /Library/LaunchDaemons/com.seojev.worker.plist
```

---

## 6. Health Probes & Monitoring

The platform provides standardized health and readiness endpoints for load balancers and container orchestrators:

### 1. Liveness Probe: `GET /health` or `GET /health/liveness`
- Checks basic HTTP server responsiveness.
- Returns `200 OK` with JSON `{"status": "ok", "environment": "production"}`.

### 2. Readiness Probe: `GET /health/ready` or `GET /ready`
- Evaluates operational status of all critical dependencies:
  - **PostgreSQL**: Queries database connectivity (`SELECT 1`).
  - **Redis**: Pings queue store (`PING`).
  - **Object Storage**: Verifies bucket accessibility and credential validity.
  - **Laya-MLX**: Verifies Apple Silicon Metal compatibility, model weights accessibility, and multi-task heads.
- Returns:
  - `200 OK` when all services are healthy.
  - `503 Service Unavailable` if any component fails.

Example response:
```json
{
  "status": "ready",
  "environment": "production",
  "components": {
    "database": {"status": "ok", "latency_ms": 2.1},
    "redis": {"status": "ok", "latency_ms": 0.8},
    "storage": {"status": "ok", "bucket": "seojev-artifacts-prod"},
    "laya_mlx": {
      "status": "ok",
      "apple_silicon": true,
      "model_id": "aac6fef/laya-mlx",
      "heads_loaded": 10
    }
  }
}
```

---

## 7. Security & Tenant Isolation

1. **Authentication & RBAC**:
   - Every protected endpoint requires a signed Bearer JWT token.
   - User roles (`admin`, `member`, `viewer`) control access levels.
2. **Organization Isolation**:
   - All database queries for sites, runs, findings, opportunities, and work orders are scoped by `organization_id`.
   - Negative authorization guarantees that Organization A cannot inspect or modify Organization B's data (verified by `tests/test_stage11_security.py`).
3. **SSRF & Dangerous URL Protection**:
   - Crawl requests to private IP ranges (`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`), loopback (`127.0.0.1`, `localhost`), and cloud metadata services (`169.254.169.254`) are strictly blocked.
4. **CORS Hardening**:
   - Wildcard CORS (`allow_origins=["*"]`) combined with credentials is explicitly prohibited. Origins must be explicitly enumerated in `CORS_ORIGINS`.

---

## 8. Backup & Recovery

### PostgreSQL Backups
Execute daily automated pg_dump backups:
```bash
pg_dump -U seojev_user -h 127.0.0.1 -Fc seojev_prod > /backup/seojev_prod_$(date +%Y%m%d_%H%M%S).dump
```

To restore:
```bash
pg_restore -U seojev_user -h 127.0.0.1 -d seojev_prod --clean /backup/seojev_prod_20260929.dump
```

### Content Store & Artifacts
The content-addressed store (`store/`) and S3 bucket contain idempotent, SHA-256 addressed objects. Enable object versioning and cross-region replication on the target S3 bucket.

---

## 9. Troubleshooting & Common Operational Issues

### 1. `MemoryBudgetExceeded` Triggered
- **Symptom**: Pipeline run transitions to `paused` with status `memory_budget_exceeded`.
- **Cause**: High concurrency or huge DOM trees exceeded `SEOJEV_MEMORY_BUDGET_MB` or caused swap growth exceeding `SEOJEV_MAX_SWAP_DELTA_MB`.
- **Resolution**:
  - Review `SEOJEV_MAX_WORKERS` and `SEOJEV_BATCH_SIZE`.
  - Resume the run safely using `python main.py <url> --resume` (state is checkpointed).

### 2. Laya-MLX Lock Contention (`seojev-laya-mlx.lock`)
- **Symptom**: Worker reports model lock acquisition timeout.
- **Cause**: Another process holds the exclusive Apple Silicon Metal lock.
- **Resolution**: Ensure only one MLX inference worker runs per host. Check for stale processes:
  ```bash
  lsof /var/run/seojev/laya-mlx.lock
  ```

### 3. Queue Backpressure (`QueueFullError`)
- **Symptom**: API returns `503 Service Unavailable` on run dispatch.
- **Cause**: Redis task queue has reached `REDIS_MAX_QUEUE_SIZE`.
- **Resolution**: Scale out background worker capacity or wait for active runs to drain.
