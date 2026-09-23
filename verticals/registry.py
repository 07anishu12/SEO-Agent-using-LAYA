from typing import Dict, Any, List, Tuple
from .base import VerticalInterface
from .generic import GenericVertical
from .automotive import AutomotiveVertical
from .ymyl_finance import YMYLFinanceOverlay

class VerticalRegistry:
    """Discovers, auto-selects, and stacks vertical intelligence plugins."""
    def __init__(self):
        self.verticals: List[VerticalInterface] = [
            AutomotiveVertical(),
            GenericVertical()
        ]
        self.overlays: List[VerticalInterface] = [
            YMYLFinanceOverlay()
        ]

    def select_vertical(self, profile: Any) -> Tuple[VerticalInterface, float, List[VerticalInterface]]:
        """Auto-selects highest-confidence vertical; falls back to Generic when confidence is low."""
        best_v = self.verticals[-1] # Default generic
        best_score = 0.0

        for v in self.verticals:
            if v.name == "generic":
                continue
            score = v.detect(profile)
            if score > best_score:
                best_score = score
                best_v = v

        if best_score < 0.50:
            best_v = GenericVertical()
            best_score = 1.0

        # Check applicable overlays
        active_overlays = []
        for o in self.overlays:
            if o.detect(profile) >= 0.50:
                active_overlays.append(o)

        return best_v, best_score, active_overlays
