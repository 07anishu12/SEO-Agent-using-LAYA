import networkx as nx
import urllib.parse
from typing import List, Dict, Any, Tuple, Optional
from collections import defaultdict
from models.issue import SEOIssue

def build_and_analyze_link_graph(
    pages: List[Dict[str, Any]],
    links: List[Dict[str, Any]],
    homepage_url: str
) -> Tuple[Dict[str, Dict[str, Any]], List[SEOIssue], List[Dict[str, Any]]]:
    """
    Builds a NetworkX directed graph from crawled pages and internal links.
    Calculates in-degree, out-degree, crawl depth, and internal graph structural importance.
    Generates exact internal link opportunities (Source URL -> Anchor Text -> Target URL).
    """
    G = nx.DiGraph()
    issues: List[SEOIssue] = []
    link_opportunities: List[Dict[str, Any]] = []

    # Map pages by URL and by category/brand for intelligent source recommendation
    page_by_url = {}
    brand_hubs = defaultdict(list)
    category_hubs = defaultdict(list)

    for p in pages:
        u = p["url"]
        page_by_url[u] = p
        G.add_node(u, page_type=p.get("page_type", "other"), template=p.get("template_id", "default"))

        # Index hubs
        parsed = urllib.parse.urlsplit(u)
        segments = [s.lower() for s in parsed.path.strip("/").split("/") if s]
        if len(segments) == 1:
            category_hubs[segments[0]].append(u)
        elif len(segments) == 2 and segments[0] in ("bikes", "cars", "scooters"):
            brand_hubs[segments[1]].append(u)

    # Add internal link edges
    existing_edges = set()
    for l in links:
        if l.get("is_internal"):
            src = l["source_url"]
            tgt = l["target_url"]
            if src in G:
                G.add_edge(src, tgt)
                existing_edges.add((src, tgt))

    # Compute PageRank as internal structural connectivity metric
    try:
        pagerank = nx.pagerank(G, alpha=0.85, max_iter=100)
    except Exception:
        pagerank = {node: 0.0 for node in G.nodes()}

    # Compute shortest path crawl depth from homepage
    depths = {}
    if homepage_url in G:
        try:
            depths = nx.single_source_shortest_path_length(G, homepage_url)
        except Exception:
            depths = {homepage_url: 0}

    node_metrics = {}
    for node in G.nodes():
        in_deg = G.in_degree(node)
        out_deg = G.out_degree(node)
        depth = depths.get(node, 999)
        pr = round(pagerank.get(node, 0.0) * 1000, 4)

        # Internal Link Opportunity Score (0-100)
        # High opportunity if: low in-degree + deep crawl depth + high-value page type
        p_data = page_by_url.get(node, {})
        is_product = p_data.get("page_type") in ("model", "product", "vehicle")
        
        opp_score = 0.0
        if in_deg == 0: opp_score += 50
        elif in_deg <= 3: opp_score += 35
        elif in_deg <= 8: opp_score += 15

        if depth >= 4: opp_score += 25
        elif depth == 3: opp_score += 15

        if is_product: opp_score += 25

        node_metrics[node] = {
            "in_degree": in_deg,
            "out_degree": out_deg,
            "crawl_depth": depth if depth != 999 else -1,
            "graph_importance": pr,
            "internal_link_opportunity_score": min(round(opp_score, 1), 100.0)
        }

        # Issue flags
        pt = p_data.get("page_type", "other")
        tpl = p_data.get("template_id", "default")

        if in_deg == 0 and node != homepage_url:
            issues.append(SEOIssue(
                url=node, page_type=pt, template=tpl,
                category="internal_linking", issue="orphan_page",
                severity="high" if is_product else "medium",
                priority="P1" if is_product else "P2",
                evidence="Page has 0 inbound internal links from any crawled page on the site.",
                recommendation="Link to this page from relevant category, navigation, or parent pages."
            ))
        elif in_deg <= 3 and node != homepage_url and depth > 1 and is_product:
            issues.append(SEOIssue(
                url=node, page_type=pt, template=tpl,
                category="internal_linking", issue="weakly_linked_product_page",
                severity="high",
                priority="P1",
                evidence=f"High-value product page has only {in_deg} internal inbound link(s) (depth: {depth}).",
                recommendation="Strengthen internal linking with contextual cross-links from brand hub and related models."
            ))

        # Generate concrete link opportunities for product pages with weak links
        if is_product and in_deg <= 8:
            parsed = urllib.parse.urlsplit(node)
            segs = [s.lower() for s in parsed.path.strip("/").split("/") if s]
            cat_seg = segs[0] if segs else ""
            brand_seg = segs[1] if len(segs) >= 2 else ""
            model_name = segs[2].replace("-", " ").title() if len(segs) >= 3 else p_data.get("h1_text", "Model")

            # 1. Candidate: Brand Hub
            candidate_sources = []
            if brand_seg in brand_hubs:
                for b_url in brand_hubs[brand_seg]:
                    if (b_url, node) not in existing_edges and b_url != node:
                        candidate_sources.append((b_url, f"{brand_seg.title()} {model_name}", "Brand hub missing direct link to model page"))

            # 2. Candidate: Category Hub
            if cat_seg in category_hubs:
                for c_url in category_hubs[cat_seg]:
                    if (c_url, node) not in existing_edges and c_url != node:
                        candidate_sources.append((c_url, model_name, "Category listing missing link to model"))

            for src_u, anchor, reason in candidate_sources[:3]:
                link_opportunities.append({
                    "target_url": node,
                    "target_page_type": pt,
                    "target_template": tpl,
                    "current_inbound_links": in_deg,
                    "source_url": src_u,
                    "recommended_anchor_text": anchor,
                    "reason": reason,
                    "priority": "P1" if in_deg <= 2 else "P2",
                    "opportunity_score": min(round(opp_score, 1), 100.0)
                })

    link_opportunities.sort(key=lambda x: x["opportunity_score"], reverse=True)
    return node_metrics, issues, link_opportunities
