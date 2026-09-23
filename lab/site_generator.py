import random
from typing import Dict, Any, List

class SyntheticSiteGenerator:
    """Generates an in-memory synthetic website with ground-truth planted SEO/AEO/GEO defects."""
    def __init__(self, base_url: str = "https://synthetic-moto.test", seed: int = 42):
        self.base_url = base_url.rstrip("/")
        self.seed = seed
        random.seed(seed)
        self.pages: Dict[str, Dict[str, Any]] = {}
        self.sitemap_urls: List[str] = []
        self.ground_truth_manifest: Dict[str, List[str]] = {}
        self._build_site()

    def _build_site(self):
        lorem_substantive = (
            "<p>Explore our complete catalog of two-wheelers, scooters, and commuter motorcycles in India. "
            "We offer flexible low down payment financing, transparent EMI calculators, instant loan approvals, "
            "certified dealer networks across major cities, and comprehensive technical comparisons for 2026 models.</p>"
        )

        # 1. Homepage (Clean)
        home_url = f"{self.base_url}/"
        self.pages[home_url] = {
            "url": home_url,
            "status_code": 200,
            "title": "Synthetic Moto - Best Bikes and Scooters in India",
            "h1": "Explore Two Wheelers in India",
            "html": f"""
            <html><head><title>Synthetic Moto - Best Bikes and Scooters in India</title>
            <meta name="description" content="Discover top rated motorcycles and scooters in India with transparent on-road prices, EMI calculators, and genuine customer reviews on Synthetic Moto." />
            <link rel="canonical" href="{home_url}" /></head>
            <body><h1>Explore Two Wheelers in India</h1>
            {lorem_substantive}
            <nav>
                <a href="{self.base_url}/bikes">Bikes Catalog</a>
                <a href="{self.base_url}/bikes/thunder-250">Thunder 250</a>
                <a href="{self.base_url}/bikes/blaze-125">Blaze 125</a>
                <a href="{self.base_url}/cities/delhi">Delhi Showroom</a>
                <a href="{self.base_url}/soft-404-candidate">Discontinued Model</a>
                <a href="{self.base_url}/bikes/eco-scooter">Eco Electric</a>
            </nav>
            </body></html>
            """,
            "page_type": "homepage"
        }
        self.sitemap_urls.append(home_url)

        # 2. Planted Defect: Canonical Mismatch
        canon_mismatch_url = f"{self.base_url}/bikes/thunder-250"
        self.pages[canon_mismatch_url] = {
            "url": canon_mismatch_url,
            "status_code": 200,
            "title": "Thunder 250 Price, Specs and Mileage in India",
            "h1": "Thunder 250",
            "html": f"""
            <html><head><title>Thunder 250 Price, Specs and Mileage in India</title>
            <meta name="description" content="Check Thunder 250 ex-showroom price, 24 bhp power, 35 kmpl mileage, available colors, and flexible EMI financing on Synthetic Moto." />
            <link rel="canonical" href="{self.base_url}/bikes/thunder-250-wrong-canonical" /></head>
            <body><h1>Thunder 250</h1>
            {lorem_substantive}
            <p>Thunder 250 ex-showroom price is ₹1,50,000. Engine 250 cc single cylinder, max power 24 bhp @ 8500 rpm, ARAI mileage 35 kmpl.</p>
            <a href="{home_url}">Home</a>
            </body></html>
            """,
            "page_type": "model"
        }
        self.sitemap_urls.append(canon_mismatch_url)
        self.ground_truth_manifest.setdefault(canon_mismatch_url, []).append("canonical_mismatch")

        # 3. Planted Defect: Entity Conflict (Title says Thunder 250, H1 says Blaze 125)
        entity_conflict_url = f"{self.base_url}/bikes/blaze-125"
        self.pages[entity_conflict_url] = {
            "url": entity_conflict_url,
            "status_code": 200,
            "title": "Thunder 250 - Specifications, Colors and Price",
            "h1": "Blaze 125 Scooter",
            "html": f"""
            <html><head><title>Thunder 250 - Specifications, Colors and Price</title>
            <meta name="description" content="Discover Blaze 125 commuter scooter specifications, 50 kmpl real mileage, alloy wheels, and on-road price in your city." />
            <link rel="canonical" href="{entity_conflict_url}" /></head>
            <body><h1>Blaze 125 Scooter</h1>
            {lorem_substantive}
            <p>Blaze 125 scooter price starting ₹85,000. Real-world mileage 50 kmpl with digital instrument cluster.</p>
            <a href="{home_url}">Home</a>
            </body></html>
            """,
            "page_type": "model"
        }
        self.sitemap_urls.append(entity_conflict_url)
        self.ground_truth_manifest.setdefault(entity_conflict_url, []).append("entity_conflict")

        # 4. Planted Defect: Soft-404 returning HTTP 200
        soft_404_url = f"{self.base_url}/soft-404-candidate"
        self.pages[soft_404_url] = {
            "url": soft_404_url,
            "status_code": 200,
            "title": "404 Not Found - Synthetic Moto",
            "h1": "Page Not Found",
            "html": f"""
            <html><head><title>404 Not Found - Synthetic Moto</title>
            <meta name="description" content="Page not found error page on Synthetic Moto." />
            <link rel="canonical" href="{soft_404_url}" /></head>
            <body><h1>Page Not Found</h1>
            <p>Oops! The two-wheeler model you are looking for has been discontinued or moved. Return to our homepage to explore active models.</p>
            <a href="{home_url}">Back to Home</a>
            </body></html>
            """,
            "page_type": "other"
        }
        self.ground_truth_manifest.setdefault(soft_404_url, []).append("soft_404_response")

        # 5. Planted Defect: Orphan Page (in sitemap but 0 incoming links)
        orphan_url = f"{self.base_url}/bikes/hidden-cruiser"
        self.pages[orphan_url] = {
            "url": orphan_url,
            "status_code": 200,
            "title": "Hidden Cruiser 400 - Specifications and Price",
            "h1": "Hidden Cruiser 400",
            "html": f"""
            <html><head><title>Hidden Cruiser 400 - Specifications and Price</title>
            <meta name="description" content="Complete details of Hidden Cruiser 400 with 400cc liquid-cooled twin-cylinder engine." />
            <link rel="canonical" href="{orphan_url}" /></head>
            <body><h1>Hidden Cruiser 400</h1>
            {lorem_substantive}
            <p>Ex-showroom price ₹2,20,000. Engine 400 cc, power 42 bhp, torque 37 Nm.</p>
            </body></html>
            """,
            "page_type": "model"
        }
        self.sitemap_urls.append(orphan_url)
        self.ground_truth_manifest.setdefault(orphan_url, []).append("orphan_page")

        # 6. Planted Defect: Missing H1 AND Missing Meta Description
        missing_meta_url = f"{self.base_url}/bikes/eco-scooter"
        self.pages[missing_meta_url] = {
            "url": missing_meta_url,
            "status_code": 200,
            "title": "Eco Electric Scooter Online Booking",
            "h1": "",
            "html": f"""
            <html><head><title>Eco Electric Scooter Online Booking</title>
            <link rel="canonical" href="{missing_meta_url}" /></head>
            <body>
            {lorem_substantive}
            <p>Eco Electric scooter starting at ₹60,000 with 85 km range and portable lithium battery pack.</p>
            </body></html>
            """,
            "page_type": "model"
        }
        self.sitemap_urls.append(missing_meta_url)
        self.ground_truth_manifest.setdefault(missing_meta_url, []).append("missing_h1")
        self.ground_truth_manifest.setdefault(missing_meta_url, []).append("missing_meta_description")

        # 7. Clean Benchmark Catalog Page
        clean_url = f"{self.base_url}/bikes"
        self.pages[clean_url] = {
            "url": clean_url,
            "status_code": 200,
            "title": "All Motorcycles and Bikes in India | Synthetic Moto",
            "h1": "Explore All Motorcycles",
            "html": f"""
            <html><head><title>All Motorcycles and Bikes in India | Synthetic Moto</title>
            <meta name="description" content="Browse our complete list of 2026 bikes and scooters with ex-showroom prices, mileage, and user ratings." />
            <link rel="canonical" href="{clean_url}" /></head>
            <body><h1>Explore All Motorcycles</h1>
            {lorem_substantive}
            <p>Find the best two-wheeler for your commute with detailed specs, dealer quotes, and financing calculators.</p>
            <a href="{home_url}">Home</a>
            <a href="{canon_mismatch_url}">Thunder 250</a>
            <a href="{entity_conflict_url}">Blaze 125</a>
            <a href="{missing_meta_url}">Eco Scooter</a>
            </body></html>
            """,
            "page_type": "listing"
        }
        self.sitemap_urls.append(clean_url)
