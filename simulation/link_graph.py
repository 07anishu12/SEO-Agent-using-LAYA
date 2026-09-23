import networkx as nx
from typing import Dict, Any, List, Tuple, Set

class EnrichedLinkGraph:
    """NetworkX-powered internal link graph with DOM region classification and equity analysis."""
    def __init__(self, target_url: str):
        self.target_url = target_url.rstrip("/")
        self.graph = nx.DiGraph()
        self.contextual_graph = nx.DiGraph()

    def build_graph(self, pages: List[Dict[str, Any]], links: List[Dict[str, Any]]):
        """Builds directed graphs for all edges and for contextual-only edges."""
        self.graph.clear()
        self.contextual_graph.clear()

        for p in pages:
            u = p["url"]
            self.graph.add_node(u, page_type=p.get("page_type", "other"), is_indexable=p.get("is_indexable", 1))
            self.contextual_graph.add_node(u, page_type=p.get("page_type", "other"))

        for l in links:
            src = l.get("source_url")
            tgt = l.get("target_url")
            if not src or not tgt or not l.get("is_internal", 1):
                continue

            region = l.get("dom_region", "body")
            anchor = l.get("anchor_text", "")

            self.graph.add_edge(src, tgt, region=region, anchor=anchor)
            if region in ("body", "contextual", "article"):
                self.contextual_graph.add_edge(src, tgt, anchor=anchor)

    def compute_metrics(self) -> Dict[str, Dict[str, Any]]:
        """Computes PageRank, click depth from homepage, and inlink/outlink counts."""
        metrics = {}
        if not self.graph.nodes:
            return metrics

        # 1. PageRank
        try:
            pr = nx.pagerank(self.graph, alpha=0.85, max_iter=100)
        except Exception:
            pr = {n: 1.0 / len(self.graph) for n in self.graph.nodes}

        # 2. Click depths from homepage
        depths = {}
        root = self.target_url
        if root not in self.graph:
            root = f"{self.target_url}/"

        if root in self.graph:
            try:
                depths = nx.single_source_shortest_path_length(self.graph, root)
            except Exception:
                depths = {root: 0}

        for n in self.graph.nodes:
            in_degree = self.graph.in_degree(n)
            out_degree = self.graph.out_degree(n)
            ctx_in = self.contextual_graph.in_degree(n) if n in self.contextual_graph else 0

            metrics[n] = {
                "inbound_links_total": in_degree,
                "outbound_links_total": out_degree,
                "inbound_contextual": ctx_in,
                "pagerank": round(pr.get(n, 0.0), 6),
                "click_depth": depths.get(n, -1),
                "is_orphan": in_degree == 0,
                "is_weakly_linked": in_degree < 3
            }

        return metrics
