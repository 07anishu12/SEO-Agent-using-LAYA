from dataclasses import dataclass, field, asdict
from typing import Dict, Any, Optional, List

@dataclass
class RankingOpportunity:
    url: str
    page_type: str
    template: str
    target_query: Optional[str] = None
    current_position: Optional[float] = None
    impressions: Optional[int] = None
    clicks: Optional[int] = None
    ctr: Optional[float] = None
    position_bracket: str = "Unranked / No GSC Data" # 1-3, 4-10, 11-20, 21-30, 31-50, 51-100, Unranked
    technical_status: str = "Good" # Good, Minor Issues, Blocker
    content_status: str = "Adequate" # Comprehensive, Thin, Critical Gaps
    internal_link_status: str = "Normal" # Strong, Normal, Weakly Linked, Orphan
    structured_data_status: str = "Present" # Complete, Partial, Missing, Malformed
    performance_status: str = "Fast" # Fast, Moderate, Slow
    serp_coverage: str = "Standard"
    aeo_status: str = "Basic" # High, Moderate, Low Readiness
    geo_status: str = "Basic" # High, Moderate, Low Readiness
    competitor_gap: str = "None Detected"
    primary_gap_type: str = "Content & Internal Linking"
    priority: str = "P1" # P0, P1, P2, P3
    priority_score: float = 50.0
    evidence: str = ""
    recommended_actions: List[str] = field(default_factory=list)
    internal_link_suggestions: List[Dict[str, str]] = field(default_factory=list)
    content_sections_to_add: List[str] = field(default_factory=list)
    schema_actions: List[str] = field(default_factory=list)
    aeo_actions: List[str] = field(default_factory=list)
    geo_actions: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
