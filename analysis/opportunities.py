from typing import List, Dict, Any, Optional, Tuple
from models.opportunity import RankingOpportunity
from models.product import ProductPageData, ProductAction
from analysis.gsc import GSCAnalyzer

class OpportunitySynthesizer:
    def __init__(self, gsc_analyzer: Optional[GSCAnalyzer] = None):
        self.gsc_analyzer = gsc_analyzer

    def synthesize_opportunities(
        self,
        pages: List[Dict[str, Any]],
        product_data_map: Dict[str, ProductPageData],
        node_metrics: Dict[str, Dict[str, Any]],
        link_opportunities: List[Dict[str, Any]],
        aeo_evals: Dict[str, Dict[str, Any]],
        geo_evals: Dict[str, Dict[str, Any]],
        serp_evals: Dict[str, Dict[str, Any]]
    ) -> Tuple[List[RankingOpportunity], List[ProductAction]]:
        opportunities: List[RankingOpportunity] = []
        product_actions: List[ProductAction] = []

        # Index suggested links by target URL
        suggested_links_by_target = {}
        for lo in link_opportunities:
            t = lo["target_url"]
            if t not in suggested_links_by_target:
                suggested_links_by_target[t] = []
            suggested_links_by_target[t].append(lo)

        for page in pages:
            url = page["url"]
            p_type = page.get("page_type", "other")
            template = page.get("template_id", "default")
            is_product = p_type in ("model", "product", "vehicle") or url in product_data_map

            # GSC Metrics
            gsc_data = self.gsc_analyzer.get_page_ranking_data(url) if self.gsc_analyzer else None
            has_gsc = gsc_data is not None

            target_query = gsc_data["top_query"] if has_gsc else None
            position = gsc_data["top_query_position"] if has_gsc else None
            impressions = gsc_data["total_impressions"] if has_gsc else None
            clicks = gsc_data["total_clicks"] if has_gsc else None
            ctr = gsc_data["average_ctr"] if has_gsc else None
            bracket = gsc_data["position_bracket"] if has_gsc else "Ranking data unavailable"

            # Product signals
            prod = product_data_map.get(url)
            content_status = "Adequate"
            if prod:
                if prod.coverage_score_pct < 40:
                    content_status = "Critical Content Gaps"
                elif prod.coverage_score_pct < 70:
                    content_status = "Moderate Content Gaps"
                else:
                    content_status = "Comprehensive"

            # Link status
            metrics = node_metrics.get(url, {})
            in_deg = metrics.get("in_degree", 0)
            if in_deg == 0:
                link_status = "Orphan"
            elif in_deg <= 3:
                link_status = "Weakly Linked"
            else:
                link_status = "Normal"

            # Technical status
            status_code = page.get("status_code", 200)
            if status_code >= 400:
                tech_status = "Blocker"
            elif not page.get("is_indexable", True):
                tech_status = "Non-Indexable"
            elif not page.get("is_self_canonical", True):
                tech_status = "Canonical Mismatch"
            else:
                tech_status = "Healthy"

            # Schema status
            schemas = page.get("schema_types", [])
            if isinstance(schemas, str):
                import json
                try: schemas = json.loads(schemas)
                except Exception: schemas = []
            
            if not schemas:
                schema_status = "Missing"
            elif any(s.lower() in ("product", "vehicle") for s in schemas):
                schema_status = "Complete (Product)"
            else:
                schema_status = "Basic WebPage"

            # AEO & GEO
            aeo_data = aeo_evals.get(url, {})
            geo_data = geo_evals.get(url, {})
            serp_data = serp_evals.get(url, {})

            aeo_status = aeo_data.get("aeo_readiness_level", "Moderate")
            geo_status = geo_data.get("geo_readiness_level", "Moderate")

            # Collect Specific Actions
            recommended_actions = []
            content_sections_to_add = []
            schema_actions = []
            aeo_actions = aeo_data.get("recommended_actions", [])
            geo_actions = geo_data.get("recommended_actions", [])

            if prod and prod.missing_content_sections:
                top_missing = prod.missing_content_sections[:4]
                content_sections_to_add = [f"Add dedicated {sec.replace('_', ' ').title()} section" for sec in top_missing]
                recommended_actions.extend(content_sections_to_add)

            if schema_status in ("Missing", "Basic WebPage") and is_product:
                s_act = "Implement Schema.org Product structured data with Offer and Brand entities"
                schema_actions.append(s_act)
                recommended_actions.append(s_act)

            # Link suggestions
            link_suggs = suggested_links_by_target.get(url, [])
            if link_suggs:
                for ls in link_suggs[:2]:
                    recommended_actions.append(f"Add internal link from '{ls['source_url']}' with anchor '{ls['recommended_anchor_text']}'")

            # Prioritization Score
            score = 30.0
            if is_product: score += 25
            if has_gsc:
                if 10.5 <= (position or 0) <= 30.5: score += 30 # Striking distance
                score += min((impressions or 0) * 0.05, 20)
            if link_status in ("Orphan", "Weakly Linked"): score += 20
            if content_status == "Critical Content Gaps": score += 20
            if tech_status in ("Blocker", "Non-Indexable"): score += 35

            if score >= 90 or tech_status == "Blocker":
                priority = "P0"
            elif score >= 65:
                priority = "P1"
            elif score >= 40:
                priority = "P2"
            else:
                priority = "P3"

            primary_gap = "Content & Internal Linking"
            if tech_status != "Healthy": primary_gap = "Technical & Indexability"
            elif link_status in ("Orphan", "Weakly Linked") and content_status != "Adequate": primary_gap = "Content Gaps & Weak Internal Links"
            elif has_gsc and ctr and ctr < 1.0: primary_gap = "Search-Result Presentation (CTR)"

            evidence_parts = []
            if has_gsc: evidence_parts.append(f"Query: '{target_query}' (Pos {position}, {impressions} impr, {ctr}% CTR)")
            if is_product and prod: evidence_parts.append(f"Content Coverage: {prod.coverage_score_pct}% ({len(prod.missing_content_sections)} sections missing)")
            evidence_parts.append(f"Inbound Internal Links: {in_deg} (Depth {metrics.get('crawl_depth', 0)})")
            evidence_parts.append(f"AEO Readiness: {aeo_status}, GEO Readiness: {geo_status}")

            opp = RankingOpportunity(
                url=url,
                page_type=p_type,
                template=template,
                target_query=target_query,
                current_position=position,
                impressions=impressions,
                clicks=clicks,
                ctr=ctr,
                position_bracket=bracket,
                technical_status=tech_status,
                content_status=content_status,
                internal_link_status=link_status,
                structured_data_status=schema_status,
                performance_status="Fast" if page.get("response_time", 0.5) < 1.0 else "Slow",
                serp_coverage=serp_data.get("gap_summary", "Standard"),
                aeo_status=aeo_status,
                geo_status=geo_status,
                competitor_gap="; ".join(serp_data.get("competitor_gaps", [])) if serp_data else "None Detected",
                primary_gap_type=primary_gap,
                priority=priority,
                priority_score=round(score, 1),
                evidence=" | ".join(evidence_parts),
                recommended_actions=recommended_actions,
                internal_link_suggestions=link_suggs,
                content_sections_to_add=content_sections_to_add,
                schema_actions=schema_actions,
                aeo_actions=aeo_actions,
                geo_actions=geo_actions
            )
            opportunities.append(opp)

            # Generate granular product actions
            if is_product and prod:
                # 1. Content action
                if content_sections_to_add:
                    product_actions.append(ProductAction(
                        url=url,
                        brand=prod.brand,
                        model=prod.model,
                        action_type="content_section",
                        priority=priority,
                        issue_summary=f"Missing core automotive buyer sections: {', '.join(prod.missing_content_sections[:3])}",
                        evidence=f"Page covers {prod.coverage_score_pct}% of expected automotive commercial sections.",
                        recommended_fix=f"Add structured sections for: {', '.join(content_sections_to_add[:3])}.",
                        implementation_details="Implement responsive content blocks in template with standardized specifications table."
                    ))
                # 2. Internal link action
                if link_suggs:
                    first_sugg = link_suggs[0]
                    product_actions.append(ProductAction(
                        url=url,
                        brand=prod.brand,
                        model=prod.model,
                        action_type="internal_links",
                        priority=priority,
                        issue_summary=f"Weak internal link equity ({in_deg} inbound links)",
                        evidence=f"Inbound links: {in_deg}, crawl depth: {metrics.get('crawl_depth', 0)}.",
                        recommended_fix=f"Add contextual link from {first_sugg['source_url']} using anchor '{first_sugg['recommended_anchor_text']}'.",
                        implementation_details=f"Insert anchor in editorial copy or sub-model list on {first_sugg['source_url']}."
                    ))
                # 3. Schema action
                if schema_actions:
                    product_actions.append(ProductAction(
                        url=url,
                        brand=prod.brand,
                        model=prod.model,
                        action_type="schema",
                        priority=priority,
                        issue_summary="Missing Schema.org Product structured data",
                        evidence=f"Current schema: {schema_status}.",
                        recommended_fix=schema_actions[0],
                        implementation_details="Add JSON-LD script with @type: Product, name, brand, offers (price, priceCurrency, availability)."
                    ))

        # Sort opportunities by priority score descending
        opportunities.sort(key=lambda x: x.priority_score, reverse=True)
        return opportunities, product_actions
