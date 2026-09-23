from dataclasses import dataclass, field, asdict
from typing import Dict, Any, Optional, List

@dataclass
class SEOIssue:
    url: str
    page_type: str
    template: str
    category: str
    issue: str
    severity: str # critical, high, medium, low
    evidence: str
    recommendation: str
    source: str = "deterministic_rule"
    priority: str = "P2" # P0, P1, P2, P3
    laya_category: Optional[str] = None
    laya_severity: Optional[str] = None
    laya_action: Optional[str] = None
    laya_confidence: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SEOIssue":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})

@dataclass
class IssueCluster:
    cluster_id: str
    issue: str
    category: str
    priority: str # P0, P1, P2, P3
    severity: str
    affected_urls_count: int
    affected_templates_count: int
    primary_affected_template: str
    scope: str # template, site_wide, page_opportunity
    evidence_summary: str
    recommended_action: str
    engineering_fix_location: str
    sample_urls: List[str] = field(default_factory=list)
    laya_action: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
