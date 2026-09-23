import csv
import io
from typing import List, Dict, Any

class SyntheticGSCGenerator:
    """Generates synthetic Google Search Console datasets with ground-truth search behavior patterns."""
    def __init__(self, base_url: str = "https://synthetic-moto.test"):
        self.base_url = base_url.rstrip("/")

    def generate_rows(self) -> List[Dict[str, Any]]:
        rows = [
            # 1. Striking Distance (Position 14.2, high impressions, low CTR)
            {
                "query": "thunder 250 price in delhi",
                "page": f"{self.base_url}/bikes/thunder-250",
                "clicks": 45,
                "impressions": 3200,
                "ctr": 0.014,
                "position": 14.2,
                "date": "2026-09-01"
            },
            # 2. Striking Distance (Position 22.5)
            {
                "query": "thunder 250 mileage",
                "page": f"{self.base_url}/bikes/thunder-250",
                "clicks": 12,
                "impressions": 1850,
                "ctr": 0.006,
                "position": 22.5,
                "date": "2026-09-01"
            },
            # 3. High Impressions / Weak CTR presentation opportunity (Pos 4.1, CTR 0.02 vs expected 0.08)
            {
                "query": "best bikes under 1.5 lakh",
                "page": f"{self.base_url}/bikes",
                "clicks": 210,
                "impressions": 10500,
                "ctr": 0.02,
                "position": 4.1,
                "date": "2026-09-01"
            },
            # 4. Cannibalization Flip-Flop: URL A ranks high on Day 1, URL B ranks high on Day 2
            {
                "query": "blaze 125 scooter price",
                "page": f"{self.base_url}/bikes/blaze-125",
                "clicks": 80,
                "impressions": 1200,
                "ctr": 0.066,
                "position": 3.2,
                "date": "2026-09-01"
            },
            {
                "query": "blaze 125 scooter price",
                "page": f"{self.base_url}/bikes",
                "clicks": 15,
                "impressions": 900,
                "ctr": 0.016,
                "position": 18.4,
                "date": "2026-09-01"
            },
            {
                "query": "blaze 125 scooter price",
                "page": f"{self.base_url}/bikes/blaze-125",
                "clicks": 18,
                "impressions": 1100,
                "ctr": 0.016,
                "position": 19.1,
                "date": "2026-09-15"
            },
            {
                "query": "blaze 125 scooter price",
                "page": f"{self.base_url}/bikes",
                "clicks": 75,
                "impressions": 1050,
                "ctr": 0.071,
                "position": 3.8,
                "date": "2026-09-15"
            },
            # 5. Benign Brand Navigational
            {
                "query": "synthetic moto",
                "page": f"{self.base_url}/",
                "clicks": 1500,
                "impressions": 2000,
                "ctr": 0.75,
                "position": 1.0,
                "date": "2026-09-01"
            }
        ]
        return rows

    def export_csv(self, output_path: str):
        rows = self.generate_rows()
        with open(output_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["query", "page", "clicks", "impressions", "ctr", "position", "date"])
            writer.writeheader()
            writer.writerows(rows)
