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
                <a href="{self.base_url}/bikes/eco-scooter">Eco Electric</a>
                <a href="{self.base_url}/bikes-duplicate">Bikes Copy</a>
                <a href="{self.base_url}/bikes/js-only-model">JS Model</a>
                <a href="{self.base_url}/bikes/global-edition">Global Edition</a>
                <a href="{self.base_url}/bikes/draft-release">Draft Release</a>
                <a href="{self.base_url}/bikes/stale-vintage">Vintage Cruiser</a>
                <a href="{self.base_url}/bikes/thin-specs">Thin Specs</a>
                <a href="{self.base_url}/catalog?filter=1&color=red&size=large&sort=price&brand=moto">Catalog Filter</a>
                <a href="{self.base_url}/redirect-chain">Redirect Chain</a>
                <a href="{self.base_url}/redirect-loop">Redirect Loop</a>
                <a href="{self.base_url}/soft-404-candidate">Discontinued Model</a>
                <a href="{self.base_url}/sitemap-dead-page">Dead Link</a>
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
            <a href="{self.base_url}/bikes">Bikes</a>
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
            <a href="{self.base_url}/bikes">Bikes</a>
            </body></html>
            """,
            "page_type": "model"
        }
        self.sitemap_urls.append(entity_conflict_url)
        self.ground_truth_manifest.setdefault(entity_conflict_url, []).append("entity_conflict")
        self.ground_truth_manifest.setdefault(entity_conflict_url, []).append("cannibalization")

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
            <a href="{self.base_url}/bikes">Bikes</a>
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
            <a href="{home_url}">Home</a>
            <a href="{self.base_url}/bikes">Bikes</a>
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
            <a href="{self.base_url}/bikes-duplicate">Bikes Duplicate</a>
            <a href="{self.base_url}/bikes/js-only-model">JS Model</a>
            <a href="{self.base_url}/bikes/global-edition">Global Edition</a>
            <a href="{self.base_url}/bikes/draft-release">Draft Release</a>
            <a href="{self.base_url}/bikes/stale-vintage">Vintage Cruiser</a>
            <a href="{self.base_url}/bikes/thin-specs">Thin Specs</a>
            <a href="{self.base_url}/bikes/deep-commuter">Deep Commuter</a>
            </body></html>
            """,
            "page_type": "listing"
        }
        self.sitemap_urls.append(clean_url)
        self.ground_truth_manifest.setdefault(clean_url, []).append("cannibalization")

        # 8. Planted Defect: Redirect Chain
        red_chain_url = f"{self.base_url}/redirect-chain"
        self.pages[red_chain_url] = {
            "url": red_chain_url,
            "status_code": 301,
            "title": "Redirecting...",
            "h1": "",
            "html": f"<html><body>Redirecting...<a href='{home_url}'>Home</a><a href='{clean_url}'>Bikes</a></body></html>",
            "redirect_chain": [f"{self.base_url}/hop-1", f"{self.base_url}/hop-2", f"{self.base_url}/final-target"],
            "page_type": "other"
        }
        self.ground_truth_manifest.setdefault(red_chain_url, []).append("redirect_chain")

        # 9. Planted Defect: Redirect Loop
        red_loop_url = f"{self.base_url}/redirect-loop"
        self.pages[red_loop_url] = {
            "url": red_loop_url,
            "status_code": 301,
            "title": "Redirect Loop",
            "h1": "",
            "html": f"<html><body>Looping...<a href='{home_url}'>Home</a><a href='{clean_url}'>Bikes</a></body></html>",
            "redirect_chain": [red_loop_url],
            "page_type": "other"
        }
        self.ground_truth_manifest.setdefault(red_loop_url, []).append("redirect_loop")

        # 10. Planted Defect: Parameter Trap
        trap_url = f"{self.base_url}/catalog?brand=moto&color=red&filter=1&size=large&sort=price"
        self.pages[trap_url] = {
            "url": trap_url,
            "status_code": 200,
            "title": "Faceted Filter Catalog Page",
            "h1": "Faceted Filter Catalog Page",
            "html": f"<html><head><title>Faceted Filter Catalog Page</title><meta name='description' content='Faceted filter catalog page.' /><link rel='canonical' href='{trap_url}' /></head><body><h1>Faceted Filter Catalog Page</h1>{lorem_substantive}<a href='{home_url}'>Home</a><a href='{clean_url}'>Bikes</a></body></html>",
            "page_type": "listing"
        }
        self.ground_truth_manifest.setdefault(trap_url, []).append("parameter_trap")

        # 11. Planted Defect: Weakly Linked Page (only 1 inbound link from catalog page)
        weak_url = f"{self.base_url}/bikes/deep-commuter"
        self.pages[weak_url] = {
            "url": weak_url,
            "status_code": 200,
            "title": "Deep Commuter 100 - Specs and Price",
            "h1": "Deep Commuter 100",
            "html": f"<html><head><title>Deep Commuter 100 - Specs and Price</title><meta name='description' content='Deep commuter 100cc motorcycle specifications and on-road prices in India.' /><link rel='canonical' href='{weak_url}' /></head><body><h1>Deep Commuter 100</h1>{lorem_substantive}<p>Price ₹55,000, 100cc engine, 65 kmpl mileage.</p><a href='{home_url}'>Home</a><a href='{clean_url}'>Bikes</a></body></html>",
            "page_type": "model"
        }
        self.sitemap_urls.append(weak_url)
        self.ground_truth_manifest.setdefault(weak_url, []).append("weak_links")

        # 12. Planted Defect: Duplicate Content Page (identical substantive body to clean_url)
        dup_url = f"{self.base_url}/bikes-duplicate"
        clean_html = self.pages[clean_url]["html"]
        dup_html = clean_html.replace(f'<link rel="canonical" href="{clean_url}" />', f'<link rel="canonical" href="{dup_url}" />')
        dup_html = dup_html.replace(f'<a href="{self.base_url}/bikes/deep-commuter">Deep Commuter</a>', f'<a href="{self.base_url}/bikes/thunder-250">Thunder Alternate</a>')
        self.pages[dup_url] = {
            "url": dup_url,
            "status_code": 200,
            "title": self.pages[clean_url]["title"],
            "h1": self.pages[clean_url]["h1"],
            "html": dup_html,
            "page_type": "listing"
        }
        self.sitemap_urls.append(dup_url)
        self.ground_truth_manifest.setdefault(dup_url, []).append("duplicate_page")

        # 13. Planted Defect: JS-only Content (Raw HTML is client script shell, Rendered has content)
        js_url = f"{self.base_url}/bikes/js-only-model"
        self.pages[js_url] = {
            "url": js_url,
            "status_code": 200,
            "title": "Client-Rendered Model - Synthetic Moto",
            "h1": "Client Model",
            "html": f"""
            <html><head><title>Client-Rendered Model - Synthetic Moto</title>
            <meta name="description" content="Client rendered model page shell." />
            <link rel="canonical" href="{js_url}" />
            </head><body><div id="root"></div>
            <!-- Client bundle hydration shell loading dynamic vehicle specs -->
            <script src="/static/js/bundle.main.vendor.chunk.js"></script>
            <noscript>Please enable JavaScript to view vehicle specifications.</noscript>
            <a href="{home_url}">Home</a><a href="{clean_url}">Bikes</a>
            </body></html>
            """,
            "rendered_html": f"""
            <html><head><title>Client-Rendered Model - Synthetic Moto</title>
            <meta name="description" content="Full model specifications loaded via JS." />
            <link rel="canonical" href="{js_url}" /></head>
            <body><h1>Client Model</h1>
            {lorem_substantive}
            <p>Price ₹1,20,000, 200cc engine, 45 kmpl mileage with dual-channel ABS.</p>
            <a href="{home_url}">Home</a><a href="{clean_url}">Bikes</a>
            </body></html>
            """,
            "page_type": "model"
        }
        self.sitemap_urls.append(js_url)
        self.ground_truth_manifest.setdefault(js_url, []).append("js_only_content")

        # 14. Planted Defect: Hreflang Error
        hreflang_url = f"{self.base_url}/bikes/global-edition"
        self.pages[hreflang_url] = {
            "url": hreflang_url,
            "status_code": 200,
            "title": "Global Edition Cruiser - Synthetic Moto",
            "h1": "Global Cruiser",
            "html": f"""
            <html><head><title>Global Edition Cruiser - Synthetic Moto</title>
            <meta name="description" content="Global cruiser international edition specifications and availability." />
            <link rel="canonical" href="{hreflang_url}" />
            <link rel="alternate" hreflang="invalid_locale_xyz" href="{hreflang_url}" />
            </head><body><h1>Global Cruiser</h1>
            {lorem_substantive}
            <p>Price ₹3,50,000, 650cc twin engine.</p>
            <a href="{home_url}">Home</a><a href="{clean_url}">Bikes</a>
            </body></html>
            """,
            "page_type": "model"
        }
        self.sitemap_urls.append(hreflang_url)
        self.ground_truth_manifest.setdefault(hreflang_url, []).append("hreflang_error")

        # 15. Planted Defect: Noindex Leak (Page in Sitemap but marked noindex)
        noindex_url = f"{self.base_url}/bikes/draft-release"
        self.pages[noindex_url] = {
            "url": noindex_url,
            "status_code": 200,
            "title": "Unreleased Draft Motorcycle - Synthetic Moto",
            "h1": "Draft Motorcycle",
            "html": f"""
            <html><head><title>Unreleased Draft Motorcycle - Synthetic Moto</title>
            <meta name="description" content="Draft motorcycle release preview for internal review only." />
            <meta name="robots" content="noindex, follow" />
            <link rel="canonical" href="{noindex_url}" /></head>
            <body><h1>Draft Motorcycle</h1>
            {lorem_substantive}
            <a href="{home_url}">Home</a><a href="{clean_url}">Bikes</a>
            </body></html>
            """,
            "page_type": "model"
        }
        self.sitemap_urls.append(noindex_url)
        self.ground_truth_manifest.setdefault(noindex_url, []).append("noindex_leak")

        # 16. Planted Defect: Sitemap Mismatch (Dead 404 listed in sitemap)
        sitemap_dead_url = f"{self.base_url}/sitemap-dead-page"
        self.pages[sitemap_dead_url] = {
            "url": sitemap_dead_url,
            "status_code": 404,
            "title": "404 Not Found",
            "h1": "404 Not Found",
            "html": f"<html><body><h1>404 Not Found</h1><p>Dead page in sitemap.</p><a href='{home_url}'>Home</a><a href='{clean_url}'>Bikes</a></body></html>",
            "page_type": "other"
        }
        self.sitemap_urls.append(sitemap_dead_url)
        self.ground_truth_manifest.setdefault(sitemap_dead_url, []).append("sitemap_mismatch")

        # 17. Planted Defect: Missing Sections (Thin specs vehicle page)
        thin_specs_url = f"{self.base_url}/bikes/thin-specs"
        self.pages[thin_specs_url] = {
            "url": thin_specs_url,
            "status_code": 200,
            "title": "Thin Specs Commuter Model - Synthetic Moto",
            "h1": "Thin Specs Model",
            "html": f"""
            <html><head><title>Thin Specs Commuter Model - Synthetic Moto</title>
            <meta name="description" content="Thin specs model page with missing pricing and sections." />
            <link rel="canonical" href="{thin_specs_url}" /></head>
            <body><h1>Thin Specs Model</h1>
            {lorem_substantive}
            <p>Vehicle details: missing pricing and sections.</p>
            <a href="{home_url}">Home</a><a href="{clean_url}">Bikes</a>
            </body></html>
            """,
            "page_type": "model"
        }
        self.sitemap_urls.append(thin_specs_url)
        self.ground_truth_manifest.setdefault(thin_specs_url, []).append("missing_sections")

        # 18. Planted Defect: Stale Data (2021 and 2022 prices on new vehicle page)
        stale_url = f"{self.base_url}/bikes/stale-vintage"
        self.pages[stale_url] = {
            "url": stale_url,
            "status_code": 200,
            "title": "Vintage Cruiser 2021 Price and Specs - Synthetic Moto",
            "h1": "Vintage Cruiser 2021",
            "html": f"""
            <html><head><title>Vintage Cruiser 2021 Price and Specs - Synthetic Moto</title>
            <meta name="description" content="Vintage Cruiser 2021 price and specs in India." />
            <link rel="canonical" href="{stale_url}" /></head>
            <body><h1>Vintage Cruiser 2021</h1>
            {lorem_substantive}
            <p>Original 2021 launch price ₹95,000, 2022 model update discontinued.</p>
            <a href="{home_url}">Home</a><a href="{clean_url}">Bikes</a>
            </body></html>
            """,
            "page_type": "model"
        }
        self.sitemap_urls.append(stale_url)
        self.ground_truth_manifest.setdefault(stale_url, []).append("stale_data")


