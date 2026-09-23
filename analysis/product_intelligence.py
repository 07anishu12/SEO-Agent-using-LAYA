import re
import urllib.parse
from typing import Dict, Any, List, Optional, Tuple
from bs4 import BeautifulSoup
from models.product import ProductPageData, ProductSpecs, ProductAction

KNOWN_BRANDS = [
    "tvs", "honda", "hero", "bajaj", "yamaha", "royal enfield", "suzuki",
    "ktm", "ather", "ola", "revolt", "tork", "matter", "ultraviolette",
    "kawasaki", "bmw", "triumph", "harley-davidson", "ducati", "aprilia",
    "vespa", "jawa", "yezdi", "husqvarna", "benelli"
]

CONTENT_CHECKLIST = [
    "price", "on_road_price", "variants", "specifications", "mileage",
    "engine", "power", "torque", "features", "colors", "dimensions",
    "brakes", "suspension", "tyres", "safety", "pros", "cons",
    "alternatives", "comparison", "emi", "finance", "faqs", "images", "reviews"
]

class ProductIntelligenceEngine:
    def __init__(self):
        pass

    def is_product_page(self, page_data: Dict[str, Any]) -> bool:
        page_type = page_data.get("page_type", "").lower()
        if page_type in ("model", "product", "vehicle"):
            return True
        url = page_data.get("url", "").lower()
        segments = [s.lower() for s in urllib.parse.urlsplit(url).path.strip("/").split("/") if s]
        if any(seg in url for seg in ("/bikes/", "/cars/", "/scooters/", "/model/", "/electric-vehicles/")):
            if len(segments) >= 2:
                return True
        if len(segments) == 2 and any(b in segments[0] for b in KNOWN_BRANDS):
            return True
        return False

    def extract_product_intelligence(self, page_data: Dict[str, Any], html: str = "") -> ProductPageData:
        url = page_data.get("url", "")
        title = page_data.get("title", "")
        h1 = page_data.get("h1_text", "")
        desc = page_data.get("description", "")
        template = page_data.get("template_id", "tpl_model")
        
        # Combine text for entity extraction
        combined_text = f"{title} {h1} {desc} {url}".lower()

        # 1. Detect Brand
        brand = ""
        for b in KNOWN_BRANDS:
            if re.search(rf"\b{b}\b", combined_text):
                brand = b.title()
                break

        # 2. Detect Model
        model = ""
        parsed = urllib.parse.urlsplit(url)
        segments = [s for s in parsed.path.strip("/").split("/") if s]
        if len(segments) >= 3 and segments[0].lower() in ("bikes", "cars", "scooters"):
            raw_model = segments[2].replace("-", " ").title()
            model = raw_model
        elif len(segments) >= 2 and segments[0].lower() in ("bikes", "cars"):
            raw_model = segments[1].replace("-", " ").title()
            model = raw_model
        elif len(segments) == 2 and any(b in segments[0].lower() for b in KNOWN_BRANDS):
            if not brand:
                brand = segments[0].replace("-", " ").title()
            raw_model = segments[1].replace("-", " ").title()
            model = raw_model
        else:
            # Fallback to cleaning H1 or title
            clean_h1 = re.sub(r"(price|specs|mileage|on road|drivio|india|features).*", "", h1, flags=re.I).strip()
            model = clean_h1 if clean_h1 else "Vehicle Model"

        # 3. Extract Automotive Specifications from text/DOM
        soup = None
        body_text = combined_text
        if html:
            try:
                soup = BeautifulSoup(html, "lxml")
                body_text = soup.get_text(separator=" ").lower()
            except Exception:
                body_text = combined_text

        specs = self._extract_specs(body_text, combined_text)
        price_str, ex_price, on_road_price, emi_str = self._extract_pricing(body_text, combined_text)
        variants = self._extract_variants(body_text, soup)
        colors = self._extract_colors(body_text)
        features = self._extract_features(body_text)
        pros, cons = self._extract_pros_cons(body_text)
        faqs = self._extract_faqs(soup, body_text)
        breadcrumbs = self._extract_breadcrumbs(soup, segments)

        # 4. Content Coverage Evaluation
        present_sections = []
        missing_sections = []

        if price_str or "price" in body_text: present_sections.append("price")
        else: missing_sections.append("price")

        if on_road_price or "on road" in body_text: present_sections.append("on_road_price")
        else: missing_sections.append("on_road_price")

        if variants or "variant" in body_text: present_sections.append("variants")
        else: missing_sections.append("variants")

        if specs.engine_cc or specs.power_bhp or "specification" in body_text: present_sections.append("specifications")
        else: missing_sections.append("specifications")

        if specs.mileage or "mileage" in body_text or "kmpl" in body_text: present_sections.append("mileage")
        else: missing_sections.append("mileage")

        if specs.engine_cc or "engine" in body_text: present_sections.append("engine")
        else: missing_sections.append("engine")

        if specs.power_bhp or "bhp" in body_text or "power" in body_text: present_sections.append("power")
        else: missing_sections.append("power")

        if specs.torque_nm or "torque" in body_text: present_sections.append("torque")
        else: missing_sections.append("torque")

        if features or "feature" in body_text: present_sections.append("features")
        else: missing_sections.append("features")

        if colors or "color" in body_text or "colour" in body_text: present_sections.append("colors")
        else: missing_sections.append("colors")

        if pros: present_sections.append("pros")
        else: missing_sections.append("pros")

        if cons: present_sections.append("cons")
        else: missing_sections.append("cons")

        has_comparison = any(k in body_text for k in ("vs ", "compare", "competitor", "alternative"))
        if has_comparison: present_sections.append("comparison")
        else: missing_sections.append("comparison")

        if emi_str or "emi" in body_text or "finance" in body_text: present_sections.append("emi")
        else: missing_sections.append("emi")

        if faqs or "faq" in body_text or "frequently asked" in body_text: present_sections.append("faqs")
        else: missing_sections.append("faqs")

        if page_data.get("images_count", 0) > 0: present_sections.append("images")
        else: missing_sections.append("images")

        has_reviews = "review" in body_text or "rating" in body_text
        if has_reviews: present_sections.append("reviews")
        else: missing_sections.append("reviews")

        total_checked = len(present_sections) + len(missing_sections)
        coverage_pct = round((len(present_sections) / max(total_checked, 1)) * 100, 1)

        # 5. Entity Consistency
        contradictions = []
        schema_raw = page_data.get("schema_types", "[]")
        if brand and brand.lower() not in title.lower() and brand.lower() not in h1.lower():
            contradictions.append(f"Brand '{brand}' identified in URL path but omitted from Title/H1.")
        if "car" in combined_text and "bike" in combined_text:
            contradictions.append("Conflicting vehicle category terms ('bike' and 'car') present in metadata.")

        # 6. Intent Classification
        primary_intent = "commercial"
        secondary_intents = []
        if "price" in combined_text or "on road" in combined_text:
            primary_intent = "pricing"
        elif "mileage" in combined_text:
            primary_intent = "mileage"
        elif "vs" in combined_text or "compare" in combined_text:
            primary_intent = "comparison"
        elif "emi" in combined_text or "loan" in combined_text:
            primary_intent = "finance"

        if "spec" in combined_text: secondary_intents.append("specification")
        if "variant" in combined_text: secondary_intents.append("variant")
        if "review" in combined_text: secondary_intents.append("review")

        return ProductPageData(
            url=url,
            page_type="model",
            template=template,
            brand=brand,
            model=model,
            variant="",
            price_str=price_str,
            ex_showroom_price=ex_price,
            on_road_price=on_road_price,
            emi_str=emi_str,
            specs=specs,
            variants_list=variants,
            colors_list=colors,
            features_list=features,
            pros_list=pros,
            cons_list=cons,
            faq_items=faqs,
            has_reviews=has_reviews,
            has_video="youtube" in body_text or "video" in body_text,
            has_comparison=has_comparison,
            has_alternatives=has_comparison,
            breadcrumbs=breadcrumbs,
            coverage_score_pct=coverage_pct,
            present_content_sections=present_sections,
            missing_content_sections=missing_sections,
            entity_consistency_ok=len(contradictions) == 0,
            entity_contradictions=contradictions,
            primary_intent=primary_intent,
            secondary_intents=secondary_intents
        )

    def _extract_specs(self, text: str, meta: str) -> ProductSpecs:
        specs = ProductSpecs()
        # Mileage
        m_match = re.search(r"(\d+(\.\d+)?)\s*(kmpl|km/l|km/litre)", text)
        if m_match: specs.mileage = f"{m_match.group(1)} kmpl"

        # Engine
        e_match = re.search(r"(\d+(\.\d+)?)\s*(cc|cubic capacity)", text)
        if e_match: specs.engine_cc = f"{e_match.group(1)} cc"

        # Power
        p_match = re.search(r"(\d+(\.\d+)?)\s*(bhp|ps|hp|kw)", text)
        if p_match: specs.power_bhp = f"{p_match.group(1)} {p_match.group(3)}"

        # Torque
        t_match = re.search(r"(\d+(\.\d+)?)\s*(nm|newton meters)", text)
        if t_match: specs.torque_nm = f"{t_match.group(1)} Nm"

        if "electric" in text or "ev" in meta:
            specs.fuel_type = "Electric"
        elif "petrol" in text:
            specs.fuel_type = "Petrol"

        if "automatic" in text or "cvt" in text:
            specs.transmission = "Automatic"
        elif "manual" in text or "speed gearbox" in text:
            specs.transmission = "Manual"

        w_match = re.search(r"(\d{2,3})\s*(kg|kilograms)", text)
        if w_match: specs.curb_weight_kg = f"{w_match.group(1)} kg"

        return specs

    def _extract_pricing(self, text: str, meta: str) -> Tuple[str, str, str, str]:
        price = ""
        ex_price = ""
        on_road = ""
        emi = ""

        # Price search: ₹ or Rs. followed by digits/Lakh
        p_match = re.search(r"(₹|rs\.?)\s*([\d,]+(\.\d+)?\s*(lakh|crore|k)?)", text, re.I)
        if p_match: price = f"₹{p_match.group(2).strip()}"

        if "ex-showroom" in text or "ex showroom" in text:
            ex_match = re.search(r"ex-?showroom\s*(price)?\s*(is|:)?\s*(₹|rs\.?)?\s*([\d,]+(\.\d+)?\s*(lakh)?)", text, re.I)
            if ex_match: ex_price = f"₹{ex_match.group(4).strip()}"

        if "on road" in text or "on-road" in text:
            on_match = re.search(r"on-?road\s*(price)?\s*(is|:)?\s*(₹|rs\.?)?\s*([\d,]+(\.\d+)?\s*(lakh)?)", text, re.I)
            if on_match: on_road = f"₹{on_match.group(4).strip()}"

        if "emi" in text:
            emi_match = re.search(r"emi\s*(starts\s*at|from|:)?\s*(₹|rs\.?)?\s*([\d,]+)\s*(per\s*month|/month|pm)?", text, re.I)
            if emi_match: emi = f"₹{emi_match.group(3).strip()}/mo"

        return price, ex_price, on_road, emi

    def _extract_variants(self, text: str, soup) -> List[str]:
        variants = []
        if soup:
            for el in soup.find_all(class_=re.compile(r"variant", re.I))[:5]:
                t = el.get_text(strip=True)
                if 3 < len(t) < 40 and t not in variants:
                    variants.append(t)
        return variants

    def _extract_colors(self, text: str) -> List[str]:
        colors = []
        common_colors = ["black", "red", "blue", "white", "grey", "silver", "yellow", "green", "matte black"]
        for c in common_colors:
            if re.search(rf"\b{c}\b", text):
                colors.append(c.title())
        return colors[:6]

    def _extract_features(self, text: str) -> List[str]:
        features = []
        feat_keywords = ["abs", "disc brake", "led headlight", "digital console", "bluetooth connectivity", "tubeless tyres", "usb charger", "riding modes"]
        for f in feat_keywords:
            if f in text:
                features.append(f.title())
        return features

    def _extract_pros_cons(self, text: str) -> Tuple[List[str], List[str]]:
        pros = []
        cons = []
        if "pros" in text: pros.append("Reported pros section present in page text.")
        if "cons" in text: cons.append("Reported cons section present in page text.")
        return pros, cons

    def _extract_faqs(self, soup, text: str) -> List[Dict[str, str]]:
        faqs = []
        if soup:
            # Check for details/summary or schema FAQ
            for details in soup.find_all("details")[:5]:
                summary = details.find("summary")
                if summary:
                    q = summary.get_text(strip=True)
                    a = details.get_text(strip=True).replace(q, "").strip()
                    faqs.append({"question": q, "answer": a[:150]})
        return faqs

    def _extract_breadcrumbs(self, soup, segments: List[str]) -> List[str]:
        crumbs = []
        if soup:
            b_nav = soup.find(attrs={"aria-label": re.compile(r"breadcrumb", re.I)}) or soup.find(class_=re.compile(r"breadcrumb", re.I))
            if b_nav:
                crumbs = [a.get_text(strip=True) for a in b_nav.find_all("a") if a.get_text(strip=True)]
        if not crumbs and segments:
            crumbs = ["Home"] + [s.replace("-", " ").title() for s in segments]
        return crumbs
