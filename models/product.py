from dataclasses import dataclass, field, asdict
from typing import Dict, Any, Optional, List

@dataclass
class ProductSpecs:
    mileage: Optional[str] = None
    engine_cc: Optional[str] = None
    power_bhp: Optional[str] = None
    torque_nm: Optional[str] = None
    fuel_type: Optional[str] = None
    transmission: Optional[str] = None
    curb_weight_kg: Optional[str] = None
    dimensions: Optional[str] = None
    brakes: Optional[str] = None
    suspension: Optional[str] = None
    tyres: Optional[str] = None
    top_speed: Optional[str] = None

@dataclass
class ProductPageData:
    url: str
    page_type: str = "model"
    template: str = "tpl_model"
    brand: str = ""
    model: str = ""
    variant: str = ""
    price_str: str = ""
    ex_showroom_price: str = ""
    on_road_price: str = ""
    emi_str: str = ""
    specs: ProductSpecs = field(default_factory=ProductSpecs)
    variants_list: List[str] = field(default_factory=list)
    colors_list: List[str] = field(default_factory=list)
    features_list: List[str] = field(default_factory=list)
    pros_list: List[str] = field(default_factory=list)
    cons_list: List[str] = field(default_factory=list)
    faq_items: List[Dict[str, str]] = field(default_factory=list)
    has_reviews: bool = False
    has_video: bool = False
    has_comparison: bool = False
    has_alternatives: bool = False
    breadcrumbs: List[str] = field(default_factory=list)
    
    # Coverage mapping
    coverage_score_pct: float = 0.0 # 0-100%
    present_content_sections: List[str] = field(default_factory=list)
    missing_content_sections: List[str] = field(default_factory=list)
    
    # Entity consistency
    entity_consistency_ok: bool = True
    entity_contradictions: List[str] = field(default_factory=list)
    
    # Inferred Search Intents
    primary_intent: str = "commercial" # commercial, pricing, mileage, comparison, finance, specification, review
    secondary_intents: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        return d

@dataclass
class ProductAction:
    url: str
    brand: str
    model: str
    action_type: str # internal_links, content_section, schema, aeo, geo, metadata
    priority: str # P0, P1, P2, P3
    issue_summary: str
    evidence: str
    recommended_fix: str
    implementation_details: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
