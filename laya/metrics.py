import numpy as np
from typing import List, Dict, Any

class LayaMetricsTracker:
    def __init__(self):
        self.latencies_ms: List[float] = []
        self.total_decisions: int = 0
        self.error_count: int = 0

    def record_decision(self, latency_ms: float):
        self.latencies_ms.append(latency_ms)
        self.total_decisions += 1

    def record_error(self):
        self.error_count += 1

    def get_summary(self) -> Dict[str, Any]:
        if not self.latencies_ms:
            return {
                "total_decisions": self.total_decisions,
                "error_count": self.error_count,
                "avg_latency_ms": 0.0,
                "median_latency_ms": 0.0,
                "p95_latency_ms": 0.0,
                "min_latency_ms": 0.0,
                "max_latency_ms": 0.0
            }

        arr = np.array(self.latencies_ms)
        return {
            "total_decisions": self.total_decisions,
            "error_count": self.error_count,
            "avg_latency_ms": round(float(np.mean(arr)), 2),
            "median_latency_ms": round(float(np.median(arr)), 2),
            "p95_latency_ms": round(float(np.percentile(arr, 95)), 2),
            "min_latency_ms": round(float(np.min(arr)), 2),
            "max_latency_ms": round(float(np.max(arr)), 2)
        }
