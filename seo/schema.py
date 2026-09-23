import json
import re
from typing import List, Tuple, Set
from bs4 import BeautifulSoup
from models.page import SchemaItem
from models.issue import SEOIssue

KNOWN_SCHEMA_TYPES = {
    "organization", "website", "breadcrumblist", "product", "offer", "review",
    "aggregaterating", "faqpage", "article", "newsarticle", "blogposting",
    "itemlist", "vehicle", "car", "motorcycle", "localbusiness", "searchaction",
    "webpage", "aboutpage", "contactpage"
}

def analyze_schemas(
    soup: BeautifulSoup,
    current_url: str,
    page_type: str,
    template: str
) -> Tuple[List[SchemaItem], List[str], bool, List[SEOIssue]]:
    issues: List[SEOIssue] = []
    schema_items: List[SchemaItem] = []
    found_types: Set[str] = set()
    all_valid = True

    # 1. Parse JSON-LD scripts
    json_ld_scripts = soup.find_all("script", attrs={"type": re.compile(r"application/ld\+json", re.I)})

    for script in json_ld_scripts:
        raw_text = script.string or script.get_text() or ""
        raw_text = raw_text.strip()
        if not raw_text:
            continue

        try:
            data = json.loads(raw_text)
            extracted = _extract_types(data)
            for st in extracted:
                found_types.add(st)
                schema_items.append(SchemaItem(
                    page_url=current_url,
                    schema_type=st,
                    is_valid=True,
                    raw_json=raw_text[:200]
                ))
        except json.JSONDecodeError as err:
            all_valid = False
            error_msg = f"JSON decode error at line {err.lineno}: {err.msg}"
            schema_items.append(SchemaItem(
                page_url=current_url,
                schema_type="Invalid_JSON_LD",
                is_valid=False,
                raw_json=raw_text[:200],
                error_message=error_msg
            ))
            issues.append(SEOIssue(
                url=current_url, page_type=page_type, template=template,
                category="structured_data", issue="malformed_json_ld",
                severity="high",
                evidence=f"Syntax error parsing JSON-LD script: {error_msg}.",
                recommendation="Fix JSON syntax (unescaped quotes, trailing commas, or encoding errors)."
            ))
        except Exception as e:
            all_valid = False
            schema_items.append(SchemaItem(
                page_url=current_url,
                schema_type="Invalid_JSON_LD",
                is_valid=False,
                raw_json=raw_text[:200],
                error_message=str(e)
            ))

    # 2. Check Microdata itemtype
    microdata_elements = soup.find_all(attrs={"itemtype": True})
    for el in microdata_elements:
        itemtype = el.get("itemtype", "")
        # Extract last segment after schema.org/
        t_name = itemtype.rsplit("/", 1)[-1]
        if t_name:
            found_types.add(t_name)
            schema_items.append(SchemaItem(
                page_url=current_url,
                schema_type=t_name,
                is_valid=True,
                raw_json=f"microdata: {itemtype}"
            ))

    # General check: informational pages with zero schema
    if not found_types:
        issues.append(SEOIssue(
            url=current_url, page_type=page_type, template=template,
            category="structured_data", issue="missing_structured_data",
            severity="low",
            evidence="No JSON-LD or Microdata structured data was detected on this page.",
            recommendation="Implement relevant Schema.org markup (e.g. BreadcrumbList, WebSite, or entity schema)."
        ))

    return schema_items, sorted(list(found_types)), all_valid, issues

def _extract_types(data) -> List[str]:
    types = []
    if isinstance(data, dict):
        t = data.get("@type")
        if t:
            if isinstance(t, list):
                types.extend(t)
            else:
                types.append(str(t))
        # Recurse into @graph or nested items
        if "@graph" in data and isinstance(data["@graph"], list):
            for item in data["@graph"]:
                types.extend(_extract_types(item))
        for v in data.values():
            if isinstance(v, (dict, list)):
                types.extend(_extract_types(v))
    elif isinstance(data, list):
        for item in data:
            types.extend(_extract_types(item))
    return types
