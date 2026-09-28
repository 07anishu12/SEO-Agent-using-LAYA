#!/usr/bin/env bash
# ==============================================================================
# SEOJEV Local Development Stack Launcher
#
# Starts Docker infra (Postgres, Redis, MinIO) and native host processes
# (FastAPI backend, Worker, Scheduler beat, Next.js frontend).
#
# MLX CONSTRAINT NOTE:
# Laya on-device MLX inference (aac6fef/laya-mlx) requires native Apple Silicon
# GPU acceleration. Docker Desktop runs in a Linux VM without MLX support.
# Hence, Postgres, Redis, and MinIO run in Docker, while FastAPI, Worker,
# Scheduler, and Next.js run NATIVELY on macOS.
# ==============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

# Handle --full-down flag to tear down docker infra
if [ "${1:-}" = "--full-down" ]; then
    echo -e "\033[1;33m[dev.sh] Tearing down Docker infra containers (postgres, redis, minio)...\033[0m"
    docker compose -f docker-compose.dev.yml down
    echo -e "\033[1;32m[dev.sh] Docker infra stopped.\033[0m"
    exit 0
fi

# 1. Environment Configuration
ENV_FILE="${ENV_FILE:-.env}"
if [ ! -f "$ENV_FILE" ]; then
    if [ -f .env.example ]; then
        echo -e "\033[1;33m[dev.sh] $ENV_FILE not found. Creating $ENV_FILE from .env.example...\033[0m"
        cp .env.example "$ENV_FILE"
    else
        echo -e "\033[1;31m[dev.sh] Error: Neither $ENV_FILE nor .env.example exists.\033[0m" >&2
        exit 1
    fi
fi

set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a

REQUIRED_VARS=(DATABASE_URL REDIS_URL S3_ENDPOINT_URL S3_ACCESS_KEY S3_SECRET_KEY JWT_SECRET)
MISSING_VARS=()
for var in "${REQUIRED_VARS[@]}"; do
    if [ -z "${!var:-}" ]; then
        MISSING_VARS+=("$var")
    fi
done

if [ ${#MISSING_VARS[@]} -gt 0 ]; then
    echo -e "\033[1;31m[dev.sh] Error: The following required environment variables are unset or empty in .env:\033[0m" >&2
    for var in "${MISSING_VARS[@]}"; do
        echo -e "  - \033[1;31m$var\033[0m" >&2
    done
    exit 1
fi

# Detect Python interpreter
if [ -f "$REPO_ROOT/.venv/bin/python" ]; then
    PYTHON="$REPO_ROOT/.venv/bin/python"
    UVICORN="$REPO_ROOT/.venv/bin/uvicorn"
elif command -v python3 >/dev/null 2>&1; then
    PYTHON="python3"
    UVICORN="uvicorn"
else
    echo -e "\033[1;31m[dev.sh] Error: Python 3 not found.\033[0m" >&2
    exit 1
fi

# 2. Start Docker Infra (PostgreSQL, Redis, MinIO)
echo -e "\033[1;34m[dev.sh] Starting Postgres, Redis, and MinIO via Docker Compose...\033[0m"
docker compose -f docker-compose.dev.yml up -d postgres redis minio

# 3. Poll Infra until Healthy (Real TCP / HTTP polling)
echo -e "\033[1;34m[dev.sh] Polling PostgreSQL until healthy...\033[0m"
PG_READY=0
for _ in $(seq 1 60); do
    if "$PYTHON" -c "import psycopg, os; conn = psycopg.connect(os.environ['DATABASE_URL']); conn.close()" >/dev/null 2>&1; then
        PG_READY=1
        break
    fi
    sleep 0.5
done
if [ "$PG_READY" -ne 1 ]; then
    echo -e "\033[1;31m[dev.sh] Error: PostgreSQL failed to become healthy within 30s at $DATABASE_URL\033[0m" >&2
    exit 1
fi
echo -e "\033[1;32m[dev.sh] PostgreSQL is healthy.\033[0m"

echo -e "\033[1;34m[dev.sh] Polling Redis until healthy...\033[0m"
REDIS_READY=0
for _ in $(seq 1 60); do
    if "$PYTHON" -c "import redis, os; r = redis.Redis.from_url(os.environ['REDIS_URL']); r.ping()" >/dev/null 2>&1; then
        REDIS_READY=1
        break
    fi
    sleep 0.5
done
if [ "$REDIS_READY" -ne 1 ]; then
    echo -e "\033[1;31m[dev.sh] Error: Redis failed to become healthy within 30s at $REDIS_URL\033[0m" >&2
    exit 1
fi
echo -e "\033[1;32m[dev.sh] Redis is healthy.\033[0m"

echo -e "\033[1;34m[dev.sh] Polling MinIO until healthy...\033[0m"
MINIO_READY=0
for _ in $(seq 1 60); do
    if "$PYTHON" -c "import urllib.request, os; urllib.request.urlopen(f\"{os.environ['S3_ENDPOINT_URL']}/minio/health/live\", timeout=2)" >/dev/null 2>&1; then
        MINIO_READY=1
        break
    fi
    sleep 0.5
done
if [ "$MINIO_READY" -ne 1 ]; then
    echo -e "\033[1;31m[dev.sh] Error: MinIO failed to become healthy within 30s at $S3_ENDPOINT_URL\033[0m" >&2
    exit 1
fi
echo -e "\033[1;32m[dev.sh] MinIO is healthy.\033[0m"

# 4. Run Pending Database Migrations
echo -e "\033[1;34m[dev.sh] Running pending database migrations against PostgreSQL...\033[0m"
PYTHONPATH="$REPO_ROOT" "$PYTHON" -m database.migrator

# 5. Process Orchestration & Cleanup Trap
BACKEND_PID=""
WORKER_PID=""
BEAT_PID=""
FRONTEND_PID=""

kill_tree() {
    local target_pid=$1
    if [ -z "$target_pid" ]; then return; fi
    local children
    children=$(pgrep -P "$target_pid" 2>/dev/null || true)
    for child in $children; do
        kill_tree "$child"
    done
    kill -TERM "$target_pid" 2>/dev/null || true
}

cleanup() {
    trap - SIGINT SIGTERM EXIT
    echo ""
    echo -e "\033[1;33m[dev.sh] Stopping SEOJEV native processes...\033[0m"
    for pid in "$BACKEND_PID" "$WORKER_PID" "$BEAT_PID" "$FRONTEND_PID"; do
        if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
            kill_tree "$pid"
        fi
    done
    sleep 0.8
    for pid in "$BACKEND_PID" "$WORKER_PID" "$BEAT_PID" "$FRONTEND_PID"; do
        if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
            kill -9 "$pid" 2>/dev/null || true
        fi
    done
    echo -e "\033[1;32m[dev.sh] All native processes stopped cleanly. (Docker infra containers remain running).\033[0m"
    exit 0
}

trap cleanup SIGINT SIGTERM EXIT

# 6. Launch Native Background Processes in Parallel
API_HOST="${HOST:-0.0.0.0}"
API_PORT="${PORT:-8000}"

echo -e "\033[1;34m[dev.sh] Starting native services in parallel...\033[0m"

# Backend (uvicorn with --reload)
PYTHONUNBUFFERED=1 PYTHONPATH="$REPO_ROOT" ENABLE_WORKER=false ENABLE_SCHEDULER=false "$UVICORN" api.main:app --reload --host "$API_HOST" --port "$API_PORT" > >(awk '{ print "\033[1;36m[backend]\033[0m  " $0; fflush(); }') 2>&1 &
BACKEND_PID=$!

# Celery Worker
PYTHONUNBUFFERED=1 PYTHONPATH="$REPO_ROOT" "$PYTHON" -m jobs.worker > >(awk '{ print "\033[1;32m[worker]\033[0m   " $0; fflush(); }') 2>&1 &
WORKER_PID=$!

# Celery Beat (Watch Scheduler)
PYTHONUNBUFFERED=1 PYTHONPATH="$REPO_ROOT" "$PYTHON" -m jobs.scheduler > >(awk '{ print "\033[1;35m[beat]\033[0m     " $0; fflush(); }') 2>&1 &
BEAT_PID=$!

# Next.js Frontend
(cd "$REPO_ROOT/frontend" && NEXT_DIST_DIR=.next-dev npm run dev) > >(awk '{ print "\033[1;33m[frontend]\033[0m " $0; fflush(); }') 2>&1 &
FRONTEND_PID=$!

# 7. Readiness Verification
echo -e "\033[1;34m[dev.sh] Waiting for native services to report ready...\033[0m"
BACKEND_HEALTHY=0
FRONTEND_HEALTHY=0

for _ in $(seq 1 60); do
    # Check for early exits
    for proc_info in "backend:$BACKEND_PID" "worker:$WORKER_PID" "beat:$BEAT_PID" "frontend:$FRONTEND_PID"; do
        proc_name="${proc_info%%:*}"
        proc_pid="${proc_info##*:}"
        if ! kill -0 "$proc_pid" 2>/dev/null; then
            echo -e "\033[1;31m[dev.sh] Error: Process [$proc_name] (PID $proc_pid) failed to start or exited immediately.\033[0m" >&2
            exit 1
        fi
    done

    # Probe Backend
    if [ "$BACKEND_HEALTHY" -ne 1 ]; then
        if curl -s -f "http://127.0.0.1:${API_PORT}/health" >/dev/null 2>&1; then
            BACKEND_HEALTHY=1
        fi
    fi

    # Probe Frontend
    if [ "$FRONTEND_HEALTHY" -ne 1 ]; then
        if curl -s -o /dev/null "http://127.0.0.1:3000" >/dev/null 2>&1; then
            FRONTEND_HEALTHY=1
        fi
    fi

    if [ "$BACKEND_HEALTHY" -eq 1 ] && [ "$FRONTEND_HEALTHY" -eq 1 ]; then
        break
    fi
    sleep 0.5
done

if [ "$BACKEND_HEALTHY" -ne 1 ]; then
    echo -e "\033[1;31m[dev.sh] Error: FastAPI backend failed to respond on http://localhost:${API_PORT}/health\033[0m" >&2
    exit 1
fi

if [ "$FRONTEND_HEALTHY" -ne 1 ]; then
    echo -e "\033[1;31m[dev.sh] Error: Next.js frontend failed to respond on http://localhost:3000\033[0m" >&2
    exit 1
fi

echo ""
echo -e "\033[1;32m================================================================================\033[0m"
echo -e "\033[1;32m  SEOJEV is running — open \033[1;36mhttp://localhost:3000\033[1;32m and paste a URL to start a crawl.\033[0m"
echo -e "\033[1;32m================================================================================\033[0m"
echo ""

# 8. Keep Running & Monitor Child Processes
while true; do
    for proc_info in "backend:$BACKEND_PID" "worker:$WORKER_PID" "beat:$BEAT_PID" "frontend:$FRONTEND_PID"; do
        proc_name="${proc_info%%:*}"
        proc_pid="${proc_info##*:}"
        if ! kill -0 "$proc_pid" 2>/dev/null; then
            echo -e "\033[1;31m[dev.sh] Process [$proc_name] (PID $proc_pid) terminated unexpectedly.\033[0m" >&2
            exit 1
        fi
    done
    sleep 1 &
    wait $! 2>/dev/null || true
done
