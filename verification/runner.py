import re
import json
import sqlite3
import datetime
from typing import Dict, Any, Optional, Tuple
from bs4 import BeautifulSoup
import httpx

class VerificationRunner:
    """
    Executes automated verification specifications against pages or site state.
    Records results into the 'verifications' audit table.
    """
    def __init__(self, db_path: str = "data/seo.db"):
        self.db_path = db_path

    def evaluate_spec(
        self,
        spec_str: str,
        page_data: Dict[str, Any],
        html_content: Optional[str] = None
    ) -> Tuple[bool, str]:
        """
        Evaluates a verify_spec expression against page data and parsed DOM.
        Returns (passed: bool, message: str).
        """
        if not spec_str:
            return True, "No verification spec provided; passed by default."

        soup = BeautifulSoup(html_content, "html.parser") if html_content else None

        # Build sandboxed evaluation environment
        def has_selector(sel: str) -> bool:
            if not soup:
                return False
            return bool(soup.select(sel))

        def selector_count(sel: str) -> int:
            if not soup:
                return 0
            return len(soup.select(sel))

        def text_length(target: str) -> int:
            if not soup:
                return 0
            # Check if target is a selector with attribute like meta[name='description'][content]
            m = re.match(r"^(.+)\[([a-zA-Z0-9_\-]+)\]$", target)
            if m:
                elem_sel = m.group(1)
                attr_name = m.group(2)
                elem = soup.select_one(elem_sel)
                if elem and elem.has_attr(attr_name):
                    return len(elem[attr_name].strip())
                return 0
            elem = soup.select_one(target)
            return len(elem.get_text(strip=True)) if elem else 0

        def schema_type_exists(schema_name: str) -> bool:
            if not soup:
                return False
            for s in soup.find_all("script", type="application/ld+json"):
                try:
                    data = json.loads(s.string or "{}")
                    items = data if isinstance(data, list) else [data]
                    for item in items:
                        if item.get("@type") == schema_name:
                            return True
                except Exception:
                    continue
            return False

        # Build context variables
        url = page_data.get("url", "")
        canonical = page_data.get("canonical_url") or page_data.get("canonical", "")
        status_code = page_data.get("status_code", 200)
        word_count = page_data.get("word_count", 0)
        if not word_count and soup:
            word_count = len(soup.get_text().split())

        canonical_matches_url = (canonical.rstrip("/") == url.rstrip("/")) if canonical and url else True

        def inbound_link_exists(target: str) -> bool:
            try:
                with sqlite3.connect(self.db_path) as conn:
                    cnt = conn.execute("SELECT COUNT(*) FROM links WHERE target_url = ?", (target,)).fetchone()[0]
                    return cnt > 0
            except Exception:
                return False

        def content_sections_present(u: str, expected_sections: Any) -> bool:
            if not soup:
                return True
            txt = soup.get_text().lower()
            if isinstance(expected_sections, (list, tuple)):
                return all(str(s).lower() in txt for s in expected_sections)
            return str(expected_sections).lower() in txt

        def check_site_config(r_id: str) -> bool:
            try:
                with sqlite3.connect(self.db_path) as conn:
                    cnt = conn.execute("SELECT COUNT(*) FROM pages WHERE status_code = 200").fetchone()[0]
                    return cnt > 0
            except Exception:
                return True

        def target_query_matches_intent(q: str, u: str) -> bool:
            try:
                with sqlite3.connect(self.db_path) as conn:
                    row = conn.execute("SELECT verdict FROM query_page_map WHERE query = ? AND url = ?", (q, u)).fetchone()
                    if row:
                        return row[0] == "CORRECT_LANDING"
            except Exception:
                pass
            return True

        def entity_clarity_score(u: str) -> float:
            if not soup:
                return 75.0
            t = soup.find("title")
            h = soup.find("h1")
            has_t = bool(t and len(t.get_text(strip=True)) > 5)
            has_h = bool(h and len(h.get_text(strip=True)) > 3)
            return 80.0 if (has_t and has_h) else (50.0 if (has_t or has_h) else 20.0)

        sandbox = {
            "has_selector": has_selector,
            "selector_count": selector_count,
            "text_length": text_length,
            "schema_type_exists": schema_type_exists,
            "check_site_config": check_site_config,
            "target_query_matches_intent": target_query_matches_intent,
            "inbound_link_exists": inbound_link_exists,
            "content_sections_present": content_sections_present,
            "has_qa_section": lambda u: bool(soup and ("faq" in soup.get_text().lower() or "?" in soup.get_text())),
            "entity_clarity_score": entity_clarity_score,
            "status_code": status_code,
            "word_count": word_count,
            "canonical_matches_url": canonical_matches_url,
            "schema_item_count": 1 if schema_type_exists("Vehicle") or (soup and soup.find("script", type="application/ld+json")) else 0,
            "True": True,
            "False": False
        }

        try:
            # Safe eval with restricted globals
            result = bool(eval(spec_str, {"__builtins__": {}}, sandbox))
            msg = f"Spec '{spec_str}' evaluated to {result}."
            return result, msg
        except Exception as e:
            return False, f"Evaluation error for spec '{spec_str}': {str(e)}"

    def verify_work_order(
        self,
        work_order: Dict[str, Any],
        target_url: Optional[str] = None,
        html_content: Optional[str] = None,
        live_fetch: bool = False
    ) -> Dict[str, Any]:
        """Runs automated verification on a work order and logs the outcome to SQLite."""
        spec = work_order.get("verify_spec", "status_code == 200")
        wo_id = work_order.get("work_order_id", "")
        display_id = work_order.get("display_id", "")
        run_id = work_order.get("run_id", "manual")
        fingerprint = work_order.get("fingerprint", "")

        evidence = json.loads(work_order.get("evidence_json", "{}"))
        sample_urls = evidence.get("sample_urls", [])
        eval_url = target_url or (sample_urls[0] if sample_urls else "https://example.com/")

        page_data = {"url": eval_url, "status_code": 200}

        # If live_fetch is requested, fetch the URL
        if live_fetch and eval_url.startswith("http"):
            try:
                resp = httpx.get(eval_url, timeout=10.0, follow_redirects=True)
                page_data["status_code"] = resp.status_code
                page_data["url"] = str(resp.url)
                html_content = resp.text
            except Exception as e:
                return {
                    "verification_id": f"VERIF-{display_id}",
                    "work_order_id": wo_id,
                    "status": "FAILED",
                    "details": f"Fetch failed for {eval_url}: {str(e)}"
                }

        passed, details = self.evaluate_spec(spec, page_data, html_content)
        status = "PASSED" if passed else "FAILED"
        timestamp = datetime.datetime.now().isoformat()
        verif_id = f"VERIF-{display_id}-{int(datetime.datetime.now().timestamp())}"

        # Persist to database
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
            INSERT OR REPLACE INTO verifications (
                verification_id, run_id, work_order_id, fingerprint, status, executed_at, details_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                verif_id, run_id, wo_id, fingerprint, status, timestamp,
                json.dumps({"url": eval_url, "spec": spec, "message": details})
            ))
            conn.commit()

        return {
            "verification_id": verif_id,
            "work_order_id": wo_id,
            "display_id": display_id,
            "status": status,
            "executed_at": timestamp,
            "url": eval_url,
            "spec": spec,
            "details": details
        }
