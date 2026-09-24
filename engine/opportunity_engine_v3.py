import json
import sqlite3
from typing import List, Dict, Any, Optional, Tuple
from engine.priority_model import PriorityModel
from engine.id_system import IDSystem

class OpportunityEngineV3:
    """
    Synthesizes actionable, evidence-backed opportunities across:
    SITE-TECH, TPL, PAGE, QUERY, ENG, CONTENT, LINK, AEO, GEO.
    Eliminates issue explosion by aggregating template-wide and root-cause issues.
    """
    def __init__(self, db_path: str = "data/seo.db", priority_model: Optional[PriorityModel] = None, id_system: Optional[IDSystem] = None):
        self.db_path = db_path
        self.priority_model = priority_model or PriorityModel()
        self.id_system = id_system or IDSystem(db_path=db_path)

    def synthesize_opportunities(
        self,
        run_id: str,
        pages: List[Dict[str, Any]],
        findings: List[Dict[str, Any]],
        templates: Optional[Dict[str, Any]] = None,
        query_page_map: Optional[List[Dict[str, Any]]] = None,
        link_recommendations: Optional[List[Dict[str, Any]]] = None,
        content_gaps: Optional[List[Dict[str, Any]]] = None,
        aeo_evals: Optional[Dict[str, Dict[str, Any]]] = None,
        geo_evals: Optional[Dict[str, Dict[str, Any]]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Synthesizes high-level actionable opportunities from observations.
        Prevents issue explosion by grouping issues by template and root cause.
        """
        opportunities = []

        # 1. Group raw findings by rule_id and template_id
        tpl_findings_map: Dict[Tuple[str, str], List[Dict[str, Any]]] = {}
        site_findings_map: Dict[str, List[Dict[str, Any]]] = {}
        page_findings_map: Dict[str, List[Dict[str, Any]]] = {}

        # Build url -> template lookup
        url_to_template = {}
        url_to_page = {}
        for p in pages:
            u = p.get("url")
            if u:
                url_to_page[u] = p
                url_to_template[u] = p.get("template_id") or "default"

        for f in findings:
            r_id = f.get("rule_id", "GENERIC")
            u = f.get("url")
            scope = f.get("scope_key", "page")
            tpl = f.get("template_id") or url_to_template.get(u, "default")

            if scope == "site" or not u:
                site_findings_map.setdefault(r_id, []).append(f)
            elif tpl and tpl != "default":
                tpl_findings_map.setdefault((r_id, tpl), []).append(f)
            else:
                page_findings_map.setdefault(u, []).append(f)

        # 2. Synthesize SITE-TECH Opportunities
        for r_id, items in site_findings_map.items():
            first = items[0]
            count = len(items)
            fp = self.id_system.generate_fingerprint(r_id, "site", "site-wide")
            disp_id = self.id_system.get_or_create_display_id(fp, "site_tech")
            
            factors = {
                "visibility": 80.0,
                "gap": 80.0,
                "page_importance": 90.0,
                "template_scope": 100.0,
                "technical_severity": 90.0 if first.get("severity") in ("CRITICAL", "HIGH") else 50.0,
                "ctr_headroom": 40.0,
                "link_gap": 30.0
            }
            score, opp_tier = self.priority_model.calculate_opportunity_score(factors)
            conf_tier = self.priority_model.calculate_confidence_tier("E3", count, 0.95)
            effort = self.priority_model.calculate_effort("config", count)

            opp = {
                "opportunity_id": f"OPP-{disp_id}",
                "fingerprint": fp,
                "display_id": disp_id,
                "run_id": run_id,
                "type": "SITE-TECH",
                "observation": f"Site-level issue detected: {first.get('message', r_id)} affecting site-wide crawl/index configuration.",
                "diagnosis": "Site-wide configuration or architecture issue limiting global accessibility or search discovery.",
                "hypothesis": "Remediating this site-level configuration ensures search engines can reliably crawl and index core pages without obstruction.",
                "action": first.get("recommended_action") or f"Update server/site configuration to resolve {r_id}.",
                "implementation_location": "Server configuration / robots.txt / sitemap.xml",
                "affected_templates_json": json.dumps([]),
                "affected_urls_count": count,
                "sample_urls_json": json.dumps([x.get("url") for x in items[:5] if x.get("url")]),
                "opportunity_tier": opp_tier,
                "confidence_tier": conf_tier,
                "effort": effort,
                "priority_score": score,
                "priority_factors_json": json.dumps(factors),
                "verification_spec": f"check_site_config('{r_id}') == True"
            }
            opportunities.append(opp)

        # 3. Synthesize TPL Opportunities (Template-level aggregation to stop issue explosion)
        for (r_id, tpl_id), items in tpl_findings_map.items():
            count = len(items)
            first = items[0]
            sample_urls = [x.get("url") for x in items[:10] if x.get("url")]
            
            # Map rule to verification spec and action
            v_spec = self._derive_verification_spec(r_id)
            location = f"templates/{tpl_id}.html"

            fp = self.id_system.generate_fingerprint(r_id, tpl_id, "template-aggregate")
            disp_id = self.id_system.get_or_create_display_id(fp, "template")

            # Determine severity score
            sev = first.get("severity", "MEDIUM").upper()
            tech_sev = 95.0 if sev == "CRITICAL" else (75.0 if sev == "HIGH" else (50.0 if sev == "MEDIUM" else 25.0))
            
            # Scope factor
            scope_score = min(100.0, (count / 100.0) * 80.0 + 20.0)

            factors = {
                "visibility": 70.0,
                "gap": 75.0,
                "page_importance": 65.0,
                "template_scope": scope_score,
                "technical_severity": tech_sev,
                "ctr_headroom": 50.0,
                "link_gap": 40.0
            }
            score, opp_tier = self.priority_model.calculate_opportunity_score(factors)
            conf_tier = self.priority_model.calculate_confidence_tier("E4", count, 0.98)
            effort = self.priority_model.calculate_effort("metadata_template", count)

            opp = {
                "opportunity_id": f"OPP-{disp_id}",
                "fingerprint": fp,
                "display_id": disp_id,
                "run_id": run_id,
                "type": "TPL",
                "observation": f"Observed {count} URLs in template '{tpl_id}' with issue '{r_id}': {first.get('message', '')}.",
                "diagnosis": f"Template-level omission or formatting defect in component rendering {tpl_id}.",
                "hypothesis": f"Updating the template component for {tpl_id} systematically remedies all {count} affected URLs in a single engineering change.",
                "action": first.get("recommended_action") or f"Update template {tpl_id} to fix {r_id}.",
                "implementation_location": location,
                "affected_templates_json": json.dumps([tpl_id]),
                "affected_urls_count": count,
                "sample_urls_json": json.dumps(sample_urls),
                "opportunity_tier": opp_tier,
                "confidence_tier": conf_tier,
                "effort": effort,
                "priority_score": score,
                "priority_factors_json": json.dumps(factors),
                "verification_spec": v_spec
            }
            opportunities.append(opp)

        # 4. Synthesize QUERY / Landing Fit Opportunities
        if query_page_map:
            for qm in query_page_map:
                verdict = qm.get("verdict", "")
                if verdict in ("COMPETING_URLS", "WRONG_LANDING", "WEAK_LANDING", "MISSING_DEDICATED_PAGE"):
                    q = qm.get("query", "")
                    u = qm.get("url", "")
                    pos = qm.get("position", 0.0)
                    impr = qm.get("impressions", 0)
                    gap = qm.get("click_gap", 0.0)

                    fp = self.id_system.generate_fingerprint("query_fit", verdict, f"{q}|{u}")
                    disp_id = self.id_system.get_or_create_display_id(fp, "query")

                    factors = {
                        "visibility": min(100.0, (impr / 500.0) * 100.0),
                        "gap": 80.0 if verdict == "COMPETING_URLS" else 60.0,
                        "page_importance": 70.0,
                        "template_scope": 20.0,
                        "technical_severity": 40.0,
                        "ctr_headroom": min(100.0, max(20.0, gap * 5.0)),
                        "link_gap": 50.0
                    }
                    score, opp_tier = self.priority_model.calculate_opportunity_score(factors)
                    conf_tier = self.priority_model.calculate_confidence_tier("E3", 1, 0.90)

                    action_text = (
                        f"Consolidate canonical and internal anchor signals for '{q}' toward primary landing page {u}."
                        if verdict == "COMPETING_URLS" else
                        f"Align on-page content, title, and headings of {u} to explicitly address search intent for '{q}'."
                    )

                    opp = {
                        "opportunity_id": f"OPP-{disp_id}",
                        "fingerprint": fp,
                        "display_id": disp_id,
                        "run_id": run_id,
                        "type": "QUERY",
                        "observation": f"Search performance mismatch '{verdict}' observed for query '{q}' on URL {u} (Position {pos}, Impressions {impr}).",
                        "diagnosis": f"Search intent misalignment or internal keyword cannibalization splitting relevance signals across multiple pages.",
                        "hypothesis": f"Clarifying page intent and internal anchor text structure enables search engines to route query '{q}' to the definitive landing page.",
                        "action": action_text,
                        "implementation_location": f"Routing / Metadata on {u}",
                        "affected_templates_json": json.dumps([]),
                        "affected_urls_count": 1,
                        "sample_urls_json": json.dumps([u]),
                        "opportunity_tier": opp_tier,
                        "confidence_tier": conf_tier,
                        "effort": "S",
                        "priority_score": score,
                        "priority_factors_json": json.dumps(factors),
                        "verification_spec": f"target_query_matches_intent('{q}', '{u}') == True"
                    }
                    opportunities.append(opp)

        # 5. Synthesize LINK Opportunities
        if link_recommendations:
            # Group by target URL to recommend high-impact link hubs
            recs_by_target: Dict[str, List[Dict[str, Any]]] = {}
            for lr in link_recommendations:
                t = lr.get("target_url")
                if t:
                    recs_by_target.setdefault(t, []).append(lr)

            for target_url, rec_list in recs_by_target.items():
                count = len(rec_list)
                fp = self.id_system.generate_fingerprint("internal_link_injection", "link_graph", target_url)
                disp_id = self.id_system.get_or_create_display_id(fp, "link")

                sources = [x.get("source_url") for x in rec_list[:5]]
                anchors = [x.get("suggested_anchor") for x in rec_list[:5]]

                factors = {
                    "visibility": 60.0,
                    "gap": 70.0,
                    "page_importance": 75.0,
                    "template_scope": 30.0,
                    "technical_severity": 30.0,
                    "ctr_headroom": 40.0,
                    "link_gap": min(100.0, count * 25.0)
                }
                score, opp_tier = self.priority_model.calculate_opportunity_score(factors)
                conf_tier = self.priority_model.calculate_confidence_tier("E4", count, 0.95)

                opp = {
                    "opportunity_id": f"OPP-{disp_id}",
                    "fingerprint": fp,
                    "display_id": disp_id,
                    "run_id": run_id,
                    "type": "LINK",
                    "observation": f"Target page {target_url} has {count} high-relevance inbound internal link injection candidates.",
                    "diagnosis": "Target page receives insufficient internal link equity relative to its commercial or topical relevance.",
                    "hypothesis": f"Injecting {count} contextual internal links with descriptive anchor text improves crawl accessibility and distributes PageRank mass.",
                    "action": f"Add contextual internal links to {target_url} from source pages {sources} with candidate anchors {anchors}.",
                    "implementation_location": "Source article / category body content",
                    "affected_templates_json": json.dumps([]),
                    "affected_urls_count": 1,
                    "sample_urls_json": json.dumps([target_url] + sources[:3]),
                    "opportunity_tier": opp_tier,
                    "confidence_tier": conf_tier,
                    "effort": "S",
                    "priority_score": score,
                    "priority_factors_json": json.dumps(factors),
                    "verification_spec": f"inbound_link_exists('{target_url}') == True"
                }
                opportunities.append(opp)

        # 6. Synthesize CONTENT Gap Opportunities
        if content_gaps:
            for cg in content_gaps:
                url = cg.get("url") or ""
                missing_secs = cg.get("missing_sections", [])
                missing_attrs = cg.get("missing_attributes", [])
                if not missing_secs and not missing_attrs:
                    continue

                fp = self.id_system.generate_fingerprint("content_gap", "editorial", url)
                disp_id = self.id_system.get_or_create_display_id(fp, "content")

                factors = {
                    "visibility": 50.0,
                    "gap": 85.0,
                    "page_importance": 70.0,
                    "template_scope": 20.0,
                    "technical_severity": 20.0,
                    "ctr_headroom": 60.0,
                    "link_gap": 40.0
                }
                score, opp_tier = self.priority_model.calculate_opportunity_score(factors)
                conf_tier = self.priority_model.calculate_confidence_tier("E3", 1, 0.90)

                opp = {
                    "opportunity_id": f"OPP-{disp_id}",
                    "fingerprint": fp,
                    "display_id": disp_id,
                    "run_id": run_id,
                    "type": "CONTENT",
                    "observation": f"Page {url} has content gaps: missing sections {missing_secs[:3]} and missing specifications {missing_attrs[:3]}.",
                    "diagnosis": "Thin entity coverage compared to expected vertical baseline reduces topical completeness and satisfaction of search intent.",
                    "hypothesis": "Adding structured specification tables and required editorial sections provides comprehensive answers for user purchase queries.",
                    "action": f"Author missing sections ({missing_secs}) and add spec rows for {missing_attrs}.",
                    "implementation_location": f"Editorial content on {url}",
                    "affected_templates_json": json.dumps([]),
                    "affected_urls_count": 1,
                    "sample_urls_json": json.dumps([url]),
                    "opportunity_tier": opp_tier,
                    "confidence_tier": conf_tier,
                    "effort": "M",
                    "priority_score": score,
                    "priority_factors_json": json.dumps(factors),
                    "verification_spec": f"content_sections_present('{url}', {missing_secs[:2]}) == True"
                }
                opportunities.append(opp)

        # 7. Synthesize AEO & GEO Opportunities
        if aeo_evals:
            for url, aeo in aeo_evals.items():
                score_val = aeo.get("aeo_readiness_score", 100.0)
                if score_val < 50.0:
                    fp = self.id_system.generate_fingerprint("aeo_extractability", "answer_engine", url)
                    disp_id = self.id_system.get_or_create_display_id(fp, "aeo")

                    factors = {
                        "visibility": 50.0,
                        "gap": 75.0,
                        "page_importance": 65.0,
                        "template_scope": 30.0,
                        "technical_severity": 30.0,
                        "ctr_headroom": 50.0,
                        "link_gap": 30.0
                    }
                    score, opp_tier = self.priority_model.calculate_opportunity_score(factors)
                    conf_tier = self.priority_model.calculate_confidence_tier("E3", 1, 0.90)

                    opp = {
                        "opportunity_id": f"OPP-{disp_id}",
                        "fingerprint": fp,
                        "display_id": disp_id,
                        "run_id": run_id,
                        "type": "AEO",
                        "observation": f"AEO answer extractability score for {url} is {score_val}/100. Missing concise definitions and Q&A formatting.",
                        "diagnosis": "Content lacks extractable single-sentence factual answers required by AI search assistants and featured snippets.",
                        "hypothesis": "Structuring core product FAQs into clear Q&A pairs with direct answer sentences increases probability of snippet extraction.",
                        "action": "Add an explicit FAQ / summary section formatted with direct answers (under 45 words) preceding detailed explanations.",
                        "implementation_location": f"FAQ section on {url}",
                        "affected_templates_json": json.dumps([]),
                        "affected_urls_count": 1,
                        "sample_urls_json": json.dumps([url]),
                        "opportunity_tier": opp_tier,
                        "confidence_tier": conf_tier,
                        "effort": "S",
                        "priority_score": score,
                        "priority_factors_json": json.dumps(factors),
                        "verification_spec": f"has_qa_section('{url}') == True"
                    }
                    opportunities.append(opp)

        # 8. Synthesize GEO (Generative Engine Optimization) Opportunities
        if geo_evals:
            for url, geo in geo_evals.items():
                score_val = geo.get("geo_readiness_score", 100.0)
                if score_val < 50.0:
                    fp = self.id_system.generate_fingerprint("geo_entity_clarity", "generative_search", url)
                    disp_id = self.id_system.get_or_create_display_id(fp, "geo")

                    entity_gap = geo.get("entity_clarity_score", 0.0)
                    citation_gap = geo.get("citation_readiness_score", 0.0)

                    gaps_list = []
                    if entity_gap < 50.0:
                        gaps_list.append("entity naming/disambiguation")
                    if citation_gap < 50.0:
                        gaps_list.append("citation-ready fact density")
                    gaps_str = " and ".join(gaps_list) if gaps_list else "GEO signal gaps"

                    factors = {
                        "visibility": 55.0,
                        "gap": 80.0,
                        "page_importance": 70.0,
                        "template_scope": 25.0,
                        "technical_severity": 25.0,
                        "ctr_headroom": 55.0,
                        "link_gap": 35.0
                    }
                    score, opp_tier = self.priority_model.calculate_opportunity_score(factors)
                    conf_tier = self.priority_model.calculate_confidence_tier("E3", 1, 0.85)

                    opp = {
                        "opportunity_id": f"OPP-{disp_id}",
                        "fingerprint": fp,
                        "display_id": disp_id,
                        "run_id": run_id,
                        "type": "GEO",
                        "observation": f"GEO readiness score for {url} is {score_val}/100. Gaps: {gaps_str}.",
                        "diagnosis": "Page lacks the structured entity signals and factual density required for confident citation by generative AI engines (SGE, Perplexity, Bing Copilot).",
                        "hypothesis": "Adding entity disambiguation markup, factual summaries, and authoritative citations increases probability of AI citation and generative-search visibility.",
                        "action": f"Add entity-clear product name in <title>/<h1>, structured specification summary, and authoritative source references. Gaps: {gaps_str}.",
                        "implementation_location": f"Page head + main content on {url}",
                        "affected_templates_json": json.dumps([]),
                        "affected_urls_count": 1,
                        "sample_urls_json": json.dumps([url]),
                        "opportunity_tier": opp_tier,
                        "confidence_tier": conf_tier,
                        "effort": "S",
                        "priority_score": score,
                        "priority_factors_json": json.dumps(factors),
                        "verification_spec": f"entity_clarity_score('{url}') >= 60"
                    }
                    opportunities.append(opp)

        # Sort opportunities by priority_score descending
        opportunities.sort(key=lambda x: x["priority_score"], reverse=True)
        return opportunities


    def _derive_verification_spec(self, rule_id: str) -> str:
        """Translates a deterministic rule into an executable verification assertion."""
        r = rule_id.lower()
        if "meta_desc" in r or "description" in r:
            return "has_selector(\"meta[name='description']\") and text_length(\"meta[name='description'][content]\") >= 50"
        elif "title" in r:
            return "has_selector(\"title\") and text_length(\"title\") >= 10"
        elif "h1" in r:
            return "selector_count(\"h1\") == 1"
        elif "canonical" in r:
            return "canonical_matches_url == True"
        elif "schema" in r:
            return "schema_item_count >= 1"
        elif "status" in r or "404" in r or "500" in r:
            return "status_code == 200"
        return "status_code == 200"

    def persist_opportunities(self, opportunities: List[Dict[str, Any]]):
        """Persists synthesized opportunities, actions, and findings into SQLite database."""
        import datetime
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            for opp in opportunities:
                conn.execute("""
                INSERT OR REPLACE INTO opportunities (
                    opportunity_id, fingerprint, display_id, run_id, type,
                    observation, diagnosis, hypothesis, action, implementation_location,
                    affected_templates_json, affected_urls_count, sample_urls_json,
                    opportunity_tier, confidence_tier, effort, priority_score,
                    priority_factors_json, verification_spec
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    opp["opportunity_id"], opp["fingerprint"], opp["display_id"], opp["run_id"],
                    opp["type"], opp["observation"], opp["diagnosis"], opp["hypothesis"],
                    opp["action"], opp["implementation_location"], opp["affected_templates_json"],
                    opp["affected_urls_count"], opp["sample_urls_json"], opp["opportunity_tier"],
                    opp["confidence_tier"], opp["effort"], opp["priority_score"],
                    opp["priority_factors_json"], opp["verification_spec"]
                ))

                # Also record an action entry
                act_type = "engineering" if opp["type"] in ("SITE-TECH", "TPL", "ENG") else "content"
                conn.execute("""
                INSERT OR REPLACE INTO actions (
                    action_id, opportunity_id, fingerprint, action_type,
                    file_location, code_snippet, instructions
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    f"ACT-{opp['display_id']}", opp["opportunity_id"], opp["fingerprint"],
                    act_type, opp["implementation_location"], "", opp["action"]
                ))

                # FIX-10: Persist to findings table (was always empty before)
                # Map opportunity back to a V3 finding record with evidence refs
                now = datetime.datetime.utcnow().isoformat()
                severity_map = {
                    "P0": "critical", "P1": "high", "P2": "medium", "P3": "low",
                    "CRITICAL": "critical", "HIGH": "high", "MEDIUM": "medium", "LOW": "low"
                }
                opp_tier = opp.get("opportunity_tier", "P2")
                severity = severity_map.get(opp_tier, "medium")
                priority = "high" if opp_tier in ("P0", "P1") else "low"

                sample_urls = json.loads(opp.get("sample_urls_json", "[]"))
                url_val = sample_urls[0] if sample_urls else None
                template_ids = json.loads(opp.get("affected_templates_json", "[]"))
                template_id = template_ids[0] if template_ids else None
                subject = url_val or template_id or opp.get("type", "SITE")

                finding_fp = opp["fingerprint"] + ":finding"
                conn.execute("""
                INSERT OR REPLACE INTO findings (
                    fingerprint, display_id, run_id, rule_id, scope_key, subject,
                    claim_type, severity, priority, template_id, url,
                    message, evidence_refs_json, recommended_action, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    finding_fp,
                    "FND-" + opp["display_id"],
                    opp["run_id"],
                    opp["type"],
                    opp.get("opportunity_tier", "P2"),
                    subject,
                    "OBSERVED",
                    severity,
                    priority,
                    template_id,
                    url_val,
                    opp["observation"],
                    json.dumps([opp["fingerprint"]]),  # evidence ref = parent opportunity fingerprint
                    opp["action"],
                    now
                ))
            conn.commit()

