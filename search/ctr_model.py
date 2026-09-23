from typing import Dict, Any, List, Tuple

BASELINE_CTR_CURVE = {
    1: 0.280,
    2: 0.150,
    3: 0.100,
    4: 0.070,
    5: 0.050,
    6: 0.040,
    7: 0.030,
    8: 0.025,
    9: 0.020,
    10: 0.018,
    15: 0.010,
    25: 0.005,
    50: 0.002
}

class SiteCTRModel:
    """Computes site-specific expected CTR curves and observational click headroom gaps."""
    def __init__(self, observed_non_brand_rows: List[Dict[str, Any]] = None):
        self.fitted_curve: Dict[int, float] = {}
        self.is_site_specific = False

        if observed_non_brand_rows and len(observed_non_brand_rows) >= 50:
            self._fit_monotonic_curve(observed_non_brand_rows)
        else:
            self.fitted_curve = dict(BASELINE_CTR_CURVE)
            self.is_site_specific = False

    def _fit_monotonic_curve(self, rows: List[Dict[str, Any]]):
        # Aggregate clicks and impressions by integer position bucket (1 to 20)
        bucket_data = {}
        for r in rows:
            pos = int(round(r.get("position", 100)))
            if 1 <= pos <= 30:
                b = bucket_data.setdefault(pos, {"clicks": 0, "impressions": 0})
                b["clicks"] += r.get("clicks", 0)
                b["impressions"] += r.get("impressions", 0)

        curve = {}
        for pos, data in sorted(bucket_data.items()):
            if data["impressions"] >= 50:
                ctr = data["clicks"] / data["impressions"]
                curve[pos] = ctr

        # Ensure monotonicity (CTR at pos N <= CTR at pos N-1)
        prev_ctr = 1.0
        for pos in sorted(curve.keys()):
            ctr = min(curve[pos], prev_ctr)
            curve[pos] = round(ctr, 4)
            prev_ctr = ctr

        if len(curve) >= 5:
            self.fitted_curve = curve
            self.is_site_specific = True
        else:
            self.fitted_curve = dict(BASELINE_CTR_CURVE)
            self.is_site_specific = False

    def get_expected_ctr(self, position: float) -> Tuple[float, str]:
        """Returns (expected_ctr: float, source: 'SITE_SPECIFIC' | 'ASSUMED')."""
        pos_int = int(round(position))
        source = "SITE_SPECIFIC" if self.is_site_specific else "ASSUMED"

        if pos_int in self.fitted_curve:
            return self.fitted_curve[pos_int], source

        # Interpolate or bucket
        if pos_int <= 1:
            return self.fitted_curve.get(1, 0.28), source
        elif pos_int <= 3:
            return self.fitted_curve.get(pos_int, 0.10), source
        elif pos_int <= 10:
            return self.fitted_curve.get(pos_int, 0.02), source
        elif pos_int <= 20:
            return 0.010, source
        elif pos_int <= 30:
            return 0.005, source
        else:
            return 0.001, source

    def calculate_click_headroom(self, position: float, actual_ctr: float, impressions: int) -> Dict[str, Any]:
        """Calculates observational click gap vs site baseline."""
        exp_ctr, source = self.get_expected_ctr(position)
        click_gap = max(0.0, round((exp_ctr - actual_ctr) * impressions, 1))

        return {
            "expected_ctr": round(exp_ctr, 4),
            "actual_ctr": round(actual_ctr, 4),
            "click_gap_vs_baseline": click_gap,
            "curve_source": source,
            "interpretation": f"Observational click gap of {int(click_gap)} clicks if CTR reached {round(exp_ctr*100, 1)}% ({source} baseline for position {int(round(position))}). Scenario, not a forecast."
        }
