"""Pass 4 must use the real local MLX checkpoint and reject all alternatives."""
import copy
import json
from pathlib import Path
import pytest
from laya.analyzer import LayaSEOAnalyzer
from laya.backends import get_laya_backend, MLXBackend
from laya.heads import LayaHeadMissingError, validate_heads
from laya.decision import LayaDecision, confidence_gate, load_policy


def recorded_answers():
    # Recorded real inference, used to exercise parsers; never a model replacement.
    return json.loads((Path(__file__).resolve().parents[1] / "reports/laya_probe.json").read_text())["records"][0]["answers"]


@pytest.mark.parametrize("backend", ["llama_cpp", "api", "unknown"])
def test_forbidden_backends(backend, monkeypatch):
    with pytest.raises(ValueError, match="requires"):
        get_laya_backend(backend_type=backend)
    monkeypatch.setenv("LAYA_BACKEND", backend)
    with pytest.raises(ValueError, match="forbidden"):
        get_laya_backend()


def test_real_mlx_preflight_and_cache():
    analyzer = LayaSEOAnalyzer.get_singleton()
    assert isinstance(analyzer.backend, MLXBackend)
    assert len(analyzer.preflight()["heads"]) == 10
    assert analyzer.backend.checkpoint_id.startswith("aac6fef/laya-mlx@")
    evidence = {"issue": "missing_title", "evidence": "HTTP 200, indexable page has no title element"}
    first = analyzer.classify_issue(evidence)
    calls = analyzer.inference_calls
    second = analyzer.classify_issue(evidence)
    assert second["from_cache"] and analyzer.inference_calls == calls
    heads = first["head_confidences"]
    assert first["confidence"] == min(heads[n]["probabilities"][heads[n]["choice"]] for n in ("verdict", "action"))
    assert first["is_real_issue"] == (heads["verdict"]["choice"] == "real_issue")


@pytest.mark.parametrize("head", list(recorded_answers()))
def test_missing_head_fails(head):
    answers = recorded_answers()
    del answers[head]
    with pytest.raises(LayaHeadMissingError, match=head):
        validate_heads({"answers": answers})


@pytest.mark.parametrize("bad", [None, {}, {"choice": "real_issue"}, {"choice": "nonsense", "confidence": 0.9}])
def test_malformed_head_fails(bad):
    answers = recorded_answers()
    answers["verdict"] = bad
    with pytest.raises(LayaHeadMissingError, match="verdict"):
        validate_heads({"answers": answers})


def test_entropy_is_not_chosen_probability():
    answers = recorded_answers()
    answers["verdict"].update(choice="real_issue", confidence=0.0007, probabilities={"real_issue": 0.5155, "noise": 0.4845})
    decision = LayaDecision(head_confidences=answers)
    assert decision.is_real_issue
    assert decision.head_confidences["verdict"]["chosen_probability"] == 0.5155
    assert decision.gate == "SUPPRESS"


def test_gate_boundaries():
    p = load_policy()
    v, a, auto = p["verdict_min"], p["action_min"], p["auto_accept_min"]
    assert confidence_gate("real_issue", v, a, p) == "HUMAN_REVIEW"
    assert confidence_gate("real_issue", v-0.0001, a, p) == "SUPPRESS"
    assert confidence_gate("real_issue", v, a-0.0001, p) == "SUPPRESS"
    assert confidence_gate("real_issue", auto, auto, p) == "AUTO_ACCEPT"
    assert confidence_gate("real_issue", auto-0.0001, auto, p) == "HUMAN_REVIEW"
    assert confidence_gate("real_issue", auto, auto-0.0001, p) == "HUMAN_REVIEW"
    assert confidence_gate("noise", 1, 1, p) == "SUPPRESS"


@pytest.mark.parametrize("value", [None, -0.1, 1.1, float("nan"), float("inf"), "0.9", True])
def test_invalid_probability_fails(value):
    with pytest.raises(ValueError):
        confidence_gate("real_issue", value, 0.9)
    with pytest.raises(ValueError):
        confidence_gate("real_issue", 0.9, value)


def test_missing_input_and_invalid_policy():
    with pytest.raises(LayaHeadMissingError):
        LayaDecision()
    with pytest.raises(ValueError):
        confidence_gate(None, 1, 1)
    with pytest.raises(ValueError):
        confidence_gate("real_issue", 1, 1, {"verdict_min": .9, "action_min": .9, "auto_accept_min": .8})
