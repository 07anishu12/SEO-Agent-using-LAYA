"""
SEOJEV Phase 2: Stage 10b Cloud-Portable Laya Backends Test Suite.

Validates:
1. Backend Selection via Configuration:
   - MLX (Apple Silicon)
   - llama.cpp (CPU/CUDA non-Apple cloud inference)
   - Remote HTTP API
2. Contract Conformance:
   - Classifies sample issue data through LayaSEOAnalyzer.
   - Asserts output conforms to contract: category, severity, action, confidence, latency_ms.
3. Live Remote API Integration:
   - Sets up a test HTTP server responding to remote Laya API prediction format.
   - Confirms API backend dispatches request, parses answers, and records metrics.
4. Seamless Swapping:
   - Demonstrates that switching LAYA_BACKEND env variable switches the active backend
     without requiring any engine changes.
"""
import json
import os
import socket
import threading
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Dict, Any

import pytest

from laya.analyzer import LayaSEOAnalyzer
from laya.backends import get_laya_backend, MLXBackend, LlamaCppBackend, APIBackend


def find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        return s.getsockname()[1]


MOCK_API_PORT = find_free_port()


class MockLayaAPIHandler(BaseHTTPRequestHandler):
    requests_received = []

    def log_message(self, format, *args):
        pass

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length).decode("utf-8")
        try:
            payload = json.loads(body)
        except Exception:
            payload = {}

        MockLayaAPIHandler.requests_received.append(payload)

        # Return mock Laya answers response
        resp_data = {
            "model": "laya-cloud-test",
            "answers": {
                "category": {"choice": "technical", "confidence": 0.94},
                "severity": {"choice": "critical", "confidence": 0.91},
                "action": {"choice": "fix_template", "confidence": 0.89}
            }
        }
        resp_bytes = json.dumps(resp_data).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(resp_bytes)))
        self.end_headers()
        self.wfile.write(resp_bytes)


@pytest.fixture(scope="session")
def mock_laya_api_server():
    MockLayaAPIHandler.requests_received.clear()
    server = HTTPServer(("127.0.0.1", MOCK_API_PORT), MockLayaAPIHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{MOCK_API_PORT}/v1/predict"
    server.shutdown()


def test_llama_cpp_backend_classification():
    """Validates llama.cpp non-Apple cloud inference backend contract."""
    os.environ["LAYA_BACKEND"] = "llama_cpp"
    analyzer = LayaSEOAnalyzer(backend_type="llama_cpp")

    assert isinstance(analyzer.backend, LlamaCppBackend)
    assert analyzer.is_available() is True
    health = analyzer.get_health()
    assert health["backend"] == "llama_cpp"
    assert health["available"] is True

    # Test classification
    sample_issue = {
        "page_type": "product_page",
        "issue": "Accidental noindex directive detected on product template",
        "template": "tpl_product_v2",
        "affected_urls_count": 42,
        "evidence": "Meta tag <meta name='robots' content='noindex'> found on 42 pages"
    }
    decision = analyzer.classify_issue(sample_issue)

    # Validate schema contract
    assert decision["category"] in ("technical", "content", "schema", "architecture")
    assert decision["severity"] in ("critical", "high", "medium", "low")
    assert decision["action"] in ("fix_template", "fix_page", "no_action", "investigate")
    assert isinstance(decision["confidence"], float)
    assert 0.0 <= decision["confidence"] <= 1.0
    assert isinstance(decision["latency_ms"], float)
    assert decision["latency_ms"] >= 0.0


def test_remote_api_backend_classification(mock_laya_api_server):
    """Validates remote HTTP API inference backend dispatch and contract."""
    os.environ["LAYA_BACKEND"] = "api"
    os.environ["LAYA_API_URL"] = mock_laya_api_server

    analyzer = LayaSEOAnalyzer(
        backend_type="api",
        options={"endpoint_url": mock_laya_api_server}
    )

    assert isinstance(analyzer.backend, APIBackend)
    assert analyzer.is_available() is True
    health = analyzer.get_health()
    assert health["backend"] == "api"
    assert health["endpoint_url"] == mock_laya_api_server

    sample_issue = {
        "page_type": "category_page",
        "issue": "Missing canonical tag causing duplicate indexation",
        "template": "tpl_category",
        "evidence": "Self-referencing canonical tag omitted from 15 pages"
    }

    decision = analyzer.classify_issue(sample_issue)

    # Verify remote server was invoked
    assert len(MockLayaAPIHandler.requests_received) >= 1
    last_req = MockLayaAPIHandler.requests_received[-1]
    assert "prompt_state" in last_req
    assert "questions" in last_req

    # Verify output conforms to contract
    assert decision["category"] == "technical"
    assert decision["severity"] == "critical"
    assert decision["action"] == "fix_template"
    assert decision["confidence"] == 0.94
    assert decision["latency_ms"] >= 0.0


def test_mlx_backend_initialization_on_apple_silicon():
    """Validates MLX Apple Silicon backend initialization and health reporting."""
    backend = get_laya_backend(backend_type="mlx", force_new=True)
    assert isinstance(backend, MLXBackend)
    health = backend.health_status()
    assert health["backend"] == "mlx"
    assert health["device"] == "apple_silicon"


def test_seamless_configuration_switching():
    """
    Validates that changing LAYA_BACKEND environment variable or parameter
    dynamically switches the active inference backend without code modifications.
    """
    # 1. Select llama_cpp
    os.environ["LAYA_BACKEND"] = "llama_cpp"
    analyzer_cpu = LayaSEOAnalyzer()
    assert isinstance(analyzer_cpu.backend, LlamaCppBackend)

    # 2. Select api
    os.environ["LAYA_BACKEND"] = "api"
    analyzer_api = LayaSEOAnalyzer()
    assert isinstance(analyzer_api.backend, APIBackend)

    # 3. Select mlx
    os.environ["LAYA_BACKEND"] = "mlx"
    analyzer_mlx = LayaSEOAnalyzer()
    assert isinstance(analyzer_mlx.backend, MLXBackend)
