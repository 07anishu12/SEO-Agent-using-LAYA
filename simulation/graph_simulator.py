import copy
import networkx as nx
from typing import Dict, Any, List

class GraphSimulator:
    """Simulates internal site graph topological impact of adding recommended link edges."""
    def __init__(self):
        pass

    def simulate_impact(
        self,
        base_graph: nx.DiGraph,
        recommendations: List[Dict[str, Any]],
        root_url: str
    ) -> Dict[str, Any]:
        """Simulates adding recommended edges and reports before/after structural changes."""
        sim_graph = base_graph.copy()
        
        # Initial metrics
        total_nodes = len(base_graph)
        if total_nodes == 0:
            return {"nodes": 0}

        try:
            initial_pr = nx.pagerank(base_graph, alpha=0.85, max_iter=50)
        except Exception:
            initial_pr = {n: 1.0 / total_nodes for n in base_graph.nodes}

        root = root_url if root_url in base_graph else f"{root_url}/"
        try:
            initial_depths = nx.single_source_shortest_path_length(base_graph, root)
        except Exception:
            initial_depths = {n: -1 for n in base_graph.nodes}

        initial_orphans = sum(1 for n in base_graph.nodes if base_graph.in_degree(n) == 0)

        # Add recommended edges
        added_count = 0
        for rec in recommendations:
            src = rec["source_url"]
            tgt = rec["target_url"]
            if src in sim_graph and tgt in sim_graph and not sim_graph.has_edge(src, tgt):
                sim_graph.add_edge(src, tgt, simulated=True)
                added_count += 1

        # Post-simulation metrics
        try:
            post_pr = nx.pagerank(sim_graph, alpha=0.85, max_iter=50)
        except Exception:
            post_pr = initial_pr

        try:
            post_depths = nx.single_source_shortest_path_length(sim_graph, root)
        except Exception:
            post_depths = initial_depths

        post_orphans = sum(1 for n in sim_graph.nodes if sim_graph.in_degree(n) == 0)

        # Calculate PR mass change for target pages
        target_urls = {r["target_url"] for r in recommendations if r["target_url"] in sim_graph}
        initial_target_pr = sum(initial_pr.get(u, 0.0) for u in target_urls)
        post_target_pr = sum(post_pr.get(u, 0.0) for u in target_urls)
        pr_gain_pct = round(((post_target_pr - initial_target_pr) / max(initial_target_pr, 1e-9)) * 100, 1)

        orphans_resolved = max(0, initial_orphans - post_orphans)

        return {
            "simulation_label": "Internal Site Graph Impact",
            "edges_added": added_count,
            "initial_orphans": initial_orphans,
            "post_orphans": post_orphans,
            "orphans_resolved": orphans_resolved,
            "target_pages_pagerank_mass_gain_pct": pr_gain_pct,
            "disclaimer": (
                "Internal Site Graph Impact simulation evaluates structural connectivity and reachability "
                "within the site's internal link graph topology. It represents internal architecture optimization "
                "and does not constitute Google ranking calculations."
            )
        }
