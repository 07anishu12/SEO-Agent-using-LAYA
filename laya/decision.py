"""First-class Laya SEO Decision object — the atomic unit of AI-powered SEO judgment."""
import hashlib
import json
import time
import uuid
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Optional, List, Dict, Any


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
    AUTO_ACCEPT = "AUTO_ACCEPT"      # confidence >= 0.85
    HUMAN_REVIEW = "HUMAN_REVIEW"    # 0.5 <= confidence < 0.85
    SUPPRESS = "SUPPRESS"            # confidence < 0.5


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
    confidence: float = 0.0
    severity: str = "medium"            # critical / high / medium / low
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
        """Apply confidence gating."""
        if self.confidence >= 0.85:
            self.gate = ConfidenceGate.AUTO_ACCEPT.value
        elif self.confidence >= 0.5:
            self.gate = ConfidenceGate.HUMAN_REVIEW.value
        else:
            self.gate = ConfidenceGate.SUPPRESS.value

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

    def compute_hash(self, model_version: str = "") -> str:
        """Compute stable SHA-256 hash of this candidate input for caching."""
        payload = json.dumps({
            "cluster_id": self.cluster_id,
            "template_id": self.template_id,
            "issue_type": self.issue_type,
            "page_count": self.page_count,
            "status_distribution": self.status_distribution,
            "indexability": self.indexability,
            "content_metrics": self.content_metrics,
            "severity_hint": self.severity_hint,
            "model_version": model_version
        }, sort_keys=True, default=str)
        return hashlib.sha256(payload.encode()).hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
