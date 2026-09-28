"""First-class Laya SEO Decision object — the atomic unit of AI-powered SEO judgment."""
import hashlib
import json
import time
import uuid
import math
from pathlib import Path
import yaml
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Optional, List, Dict, Any


LAYA_PROMPT_VERSION = "laya-seo-decision-v3"


def load_settings():
    with (Path(__file__).resolve().parents[1] / "config.yaml").open() as source:
        return yaml.safe_load(source)["laya"]


def load_policy():
    return load_settings()["confidence"]


def confidence_gate(verdict, verdict_probability, action_probability, policy=None):
    """Route chosen probabilities; the boundaries are measured config, not entropy."""
    policy = load_policy() if policy is None else policy
    if verdict not in {"real_issue", "noise"}:
        raise ValueError("Missing or invalid Laya verdict")
    for value in [verdict_probability, action_probability, *policy.values()]:
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not 0 <= value <= 1:
            raise ValueError("Laya probabilities and thresholds must be finite numbers in [0, 1]")
    if not 0 < policy["verdict_min"] <= policy["auto_accept_min"] or not 0 < policy["action_min"] <= policy["auto_accept_min"]:
        raise ValueError("Invalid Laya confidence threshold ordering")
    if verdict == "noise" or verdict_probability < policy["verdict_min"] or action_probability < policy["action_min"]:
        return "SUPPRESS"
    if min(verdict_probability, action_probability) >= policy["auto_accept_min"]:
        return "AUTO_ACCEPT"
    return "HUMAN_REVIEW"


class DecisionType(Enum):
    """Bounded set of Laya decision types."""
    SEO_PROBLEM = "SEO_PROBLEM"
    NO_SEO_PROBLEM = "NO_SEO_PROBLEM"
    INDEX = "INDEX"
    NOINDEX = "NOINDEX"
    CANONICAL_ACTION = "CANONICAL_ACTION"
    REDIRECT_ACTION = "REDIRECT_ACTION"
    CONTENT_ACTION = "CONTENT_ACTION"
    INTERNAL_LINK_ACTION = "INTERNAL_LINK_ACTION"
    DUPLICATION = "DUPLICATION"
    CANNIBALIZATION = "CANNIBALIZATION"
    THIN_CONTENT = "THIN_CONTENT"
    SEARCH_INTENT_MISMATCH = "SEARCH_INTENT_MISMATCH"
    TEMPLATE_PROBLEM = "TEMPLATE_PROBLEM"
    PAGE_PROBLEM = "PAGE_PROBLEM"
    SITE_PROBLEM = "SITE_PROBLEM"
    SEVERITY = "SEVERITY"
    PRIORITY = "PRIORITY"
    RECOMMENDED_ACTION = "RECOMMENDED_ACTION"
    HUMAN_REVIEW = "HUMAN_REVIEW"


class ConfidenceGate(Enum):
    """Confidence-based decision routing."""
    AUTO_ACCEPT = "AUTO_ACCEPT"
    HUMAN_REVIEW = "HUMAN_REVIEW"
    SUPPRESS = "SUPPRESS"


@dataclass
class LayaDecision:
    """Immutable, auditable Laya SEO decision.
    
    Every decision is reproducible via (input_hash, model_version).
    Deterministic facts are authoritative — Laya interprets what facts mean for SEO.
    """
    decision_id: str = field(default_factory=lambda: f"dec_{uuid.uuid4().hex[:16]}")
    run_id: str = ""
    cluster_id: str = ""
    decision_type: str = DecisionType.SEO_PROBLEM.value
    choice: str = ""                    # The specific decision (e.g., SELF_CANONICAL, CONSOLIDATE)
    is_real_issue: Optional[bool] = None
    verdict: str = ""
    head_confidences: Dict[str, Any] = field(default_factory=dict)
    checkpoint_id: str = ""
    prompt_version: str = LAYA_PROMPT_VERSION
    policy: Dict[str, float] = field(default_factory=load_policy)
    confidence: float = 0.0
    severity: str = "medium"            # critical / high / medium / low
    scope: str = "page"
    root_cause: str = ""
    canonical_indexability: Dict[str, Any] = field(default_factory=dict)
    content_assessment: Dict[str, Any] = field(default_factory=dict)
    cannibalization: Dict[str, Any] = field(default_factory=dict)
    internal_linking: Dict[str, Any] = field(default_factory=dict)
    reason_codes: List[str] = field(default_factory=list)
    recommended_action: str = ""
    affected_scope: str = "page"        # page / template / site
    affected_count: int = 1
    evidence_refs: List[str] = field(default_factory=list)
    model_version: str = ""
    input_hash: str = ""
    latency_ms: float = 0.0
    created_at: str = field(default_factory=lambda: time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
    from_cache: bool = False
    raw_response: str = ""
    gate: str = ConfidenceGate.HUMAN_REVIEW.value

    def __post_init__(self):
        """Derive validity and gate exclusively from validated model answers."""
        from .heads import validate_heads
        self.head_confidences = validate_heads({"answers": self.head_confidences})
        self.verdict = self.head_confidences["verdict"]["choice"]
        self.is_real_issue = self.verdict == "real_issue"
        self.choice = self.head_confidences["action"]["choice"]
        self.severity = self.head_confidences["severity"]["choice"]
        self.scope = self.head_confidences["scope"]["choice"]
        self.root_cause = self.head_confidences["root_cause"]["choice"]
        vp = self.head_confidences["verdict"]["chosen_probability"]
        ap = self.head_confidences["action"]["chosen_probability"]
        self.confidence = min(vp, ap)
        self.gate = confidence_gate(self.verdict, vp, ap, self.policy)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), default=str)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LayaDecision":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class LayaCandidateInput:
    """Compact structured context for Laya decisions.
    
    Never sends entire HTML — only structured evidence sufficient for the decision.
    """
    cluster_id: str = ""
    template_id: str = ""
    issue_type: str = ""
    page_count: int = 0
    sample_urls: List[str] = field(default_factory=list)
    status_distribution: Dict[str, int] = field(default_factory=dict)
    canonical_relationship: Dict[str, Any] = field(default_factory=dict)
    indexability: Dict[str, Any] = field(default_factory=dict)
    content_metrics: Dict[str, Any] = field(default_factory=dict)
    link_metrics: Dict[str, Any] = field(default_factory=dict)
    query_metrics: Dict[str, Any] = field(default_factory=dict)
    schema_metrics: Dict[str, Any] = field(default_factory=dict)
    evidence_refs: List[str] = field(default_factory=list)
    candidate_actions: List[str] = field(default_factory=list)
    severity_hint: str = "medium"
    category_hint: str = "technical"
    prompt_version: str = LAYA_PROMPT_VERSION

    def compute_hash(self, model_version: str = "") -> str:
        """Compute stable SHA-256 hash of this candidate input for caching."""
        from .prompt import issue_data, prompt_hash
        return prompt_hash(issue_data(self), self.prompt_version, model_version)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
