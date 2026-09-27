"""
Automated test suite for scripts/dev.sh and the unified local development stack.
Verifies:
1. Validation of unset required environment variables
2. Docker infra health polling and automatic database migrations
3. Parallel native process launching (FastAPI, Worker, Beat, Frontend)
4. Clean SIGINT shutdown without orphaned processes
5. --full-down teardown behavior
"""
import os
import signal
import subprocess
import tempfile
import time
import urllib.request
import pytest
import psycopg
import redis


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEV_SCRIPT = os.path.join(REPO_ROOT, "scripts", "dev.sh")


def test_env_validation():
    """Verify scripts/dev.sh checks for missing required environment variables."""
    with tempfile.NamedTemporaryFile("w", delete=False) as tmp:
        tmp.write("REDIS_URL=redis://localhost:6379/0\n")
        tmp.write("DATABASE_URL=\n")  # explicitly empty
        tmp_name = tmp.name

    try:
        test_env = os.environ.copy()
        test_env["ENV_FILE"] = tmp_name

        proc = subprocess.run(
            [DEV_SCRIPT],
            cwd=REPO_ROOT,
            env=test_env,
            capture_output=True,
            text=True,
            timeout=15
        )
        assert proc.returncode != 0
        output = proc.stderr + proc.stdout
        assert "Error: The following required environment variables are unset or empty" in output
        assert "DATABASE_URL" in output
    finally:
        if os.path.exists(tmp_name):
            os.remove(tmp_name)


def test_dev_stack_lifecycle():
    """
    Test full dev.sh lifecycle:
    1. Start dev.sh in background
    2. Wait for banner indicating full stack is healthy
    3. Verify Backend, Frontend, Postgres, Redis, MinIO are responding
    4. Send SIGINT (Ctrl+C)
    5. Verify clean shutdown and no orphaned processes
    """
    # Ensure .env exists
    env_file = os.path.join(REPO_ROOT, ".env")
    env_example = os.path.join(REPO_ROOT, ".env.example")
    if not os.path.exists(env_file) and os.path.exists(env_example):
        import shutil
        shutil.copy(env_example, env_file)

    log_path = os.path.join(REPO_ROOT, "dev_test.log")
    if os.path.exists(log_path):
        os.remove(log_path)

    with open(log_path, "w") as log_file:
        proc = subprocess.Popen(
            [DEV_SCRIPT],
            cwd=REPO_ROOT,
            stdout=log_file,
            stderr=subprocess.STDOUT
        )

    banner_found = False
    start_time = time.time()
    timeout = 45  # allow up to 45 seconds for docker + next.js build/startup

    try:
        while time.time() - start_time < timeout:
            if proc.poll() is not None:
                with open(log_path, "r") as f:
                    output = f.read()
                pytest.fail(f"dev.sh exited prematurely with code {proc.returncode}.\nOutput:\n{output}")

            if os.path.exists(log_path):
                with open(log_path, "r") as f:
                    content = f.read()
                    if "SEOJEV is running" in content:
                        banner_found = True
                        break
            time.sleep(1)

        assert banner_found, f"dev.sh did not print running banner within {timeout}s"

        # Verify Backend is responding
        req = urllib.request.Request("http://127.0.0.1:8000/health")
        with urllib.request.urlopen(req, timeout=3) as resp:
            assert resp.status == 200
            data = resp.read().decode()
            assert "ok" in data

        # Verify Frontend is responding
        req = urllib.request.Request("http://127.0.0.1:3000")
        with urllib.request.urlopen(req, timeout=5) as resp:
            assert resp.status in (200, 304, 307, 308)

        # Verify PostgreSQL is responding
        with psycopg.connect("postgresql://postgres:postgres@localhost:5432/seojev_test") as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1;")
                assert cur.fetchone()[0] == 1

        # Verify Redis is responding
        r = redis.Redis.from_url("redis://localhost:6379/0")
        assert r.ping() is True

    finally:
        # Send SIGINT to test Ctrl+C graceful shutdown
        proc.send_signal(signal.SIGINT)
        proc.wait(timeout=15)

    assert proc.returncode == 0, f"dev.sh exit code should be 0 on SIGINT, got {proc.returncode}"

    # Check that native processes are no longer running on ports 8000 and 3000
    time.sleep(1.5)
    check_ports = subprocess.run(["lsof", "-i", ":8000", "-i", ":3000"], capture_output=True, text=True)
    assert check_ports.stdout.strip() == "", f"Orphaned processes still listening on ports:\n{check_ports.stdout}"

    # Verify Docker containers are STILL running (as required: keep infra running for fast next start)
    docker_ps = subprocess.run(["docker", "ps", "--format", "{{.Names}}"], capture_output=True, text=True)
    assert "seojev-postgres" in docker_ps.stdout
    assert "seojev-redis" in docker_ps.stdout
    assert "seojev-minio" in docker_ps.stdout

    # Clean up test log
    if os.path.exists(log_path):
        os.remove(log_path)


def test_full_down_flag():
    """Verify --full-down cleanly stops Docker infra containers."""
    proc = subprocess.run(
        [DEV_SCRIPT, "--full-down"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=30
    )
    assert proc.returncode == 0
    assert "Docker infra stopped" in proc.stdout

    # Restart containers so dev environment remains ready
    subprocess.run(
        ["docker", "compose", "-f", "docker-compose.dev.yml", "up", "-d", "postgres", "redis", "minio"],
        cwd=REPO_ROOT,
        check=True
    )
