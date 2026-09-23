import os
import json
import sqlite3
from typing import Dict, Any, List, Optional

class HTMLExplorerGenerator:
    """
    Generates a high-performance, single-file interactive offline HTML explorer
    allowing engineering, SEO, and product teams to search, filter, and inspect
    all findings, opportunities, and work orders without needing an internet connection.
    """
    def __init__(self, output_path: str = "reports/drivio/explorer.html", db_path: str = "data/seo.db"):
        self.output_path = output_path
        self.db_path = db_path
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

    def generate(self, domain: str = "drivio.in", run_id: Optional[str] = None) -> str:
        """Pulls latest data from SQLite and generates the offline HTML dashboard."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            # KPI Counts
            pages_count = conn.execute("SELECT COUNT(*) FROM pages").fetchone()[0]
            indexable_count = conn.execute("SELECT COUNT(*) FROM pages WHERE is_indexable = 1").fetchone()[0]
            opps_rows = [dict(r) for r in conn.execute("SELECT * FROM opportunities ORDER BY priority_score DESC LIMIT 200").fetchall()]
            wo_rows = [dict(r) for r in conn.execute("SELECT * FROM work_orders ORDER BY priority ASC LIMIT 200").fetchall()]
            q_rows = [dict(r) for r in conn.execute("SELECT * FROM query_page_map ORDER BY impressions DESC LIMIT 100").fetchall()]
            cluster_rows = [dict(r) for r in conn.execute("SELECT * FROM findings LIMIT 100").fetchall()]

        data_bundle = {
            "domain": domain,
            "stats": {
                "total_pages": pages_count,
                "indexable_pages": indexable_count,
                "total_opportunities": len(opps_rows),
                "total_work_orders": len(wo_rows),
                "high_priority_orders": sum(1 for w in wo_rows if w.get("priority") in ("P0", "P1")),
                "queries_analyzed": len(q_rows)
            },
            "opportunities": opps_rows,
            "work_orders": wo_rows,
            "queries": q_rows,
            "clusters": cluster_rows
        }

        json_data = json.dumps(data_bundle, ensure_ascii=False)

        html_template = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>SEOJEV V3 Search Intelligence Explorer — {domain}</title>
  <style>
    :root {{
      --bg: #0f172a;
      --card-bg: #1e293b;
      --border: #334155;
      --text: #f8fafc;
      --text-muted: #94a3b8;
      --accent: #38bdf8;
      --accent-hover: #0284c7;
      --danger: #ef4444;
      --warning: #f59e0b;
      --success: #10b981;
      --font: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    }}
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{ background: var(--bg); color: var(--text); font-family: var(--font); line-height: 1.5; padding: 24px; }}
    .header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px; border-bottom: 1px solid var(--border); padding-bottom: 16px; }}
    .title {{ font-size: 24px; font-weight: 700; color: var(--accent); }}
    .badge {{ display: inline-block; padding: 3px 8px; border-radius: 4px; font-size: 11px; font-weight: 600; text-transform: uppercase; }}
    .badge-p0 {{ background: #7f1d1d; color: #fca5a5; }}
    .badge-p1 {{ background: #78350f; color: #fcd34d; }}
    .badge-p2 {{ background: #1e3a8a; color: #93c5fd; }}
    .badge-p3 {{ background: #14532d; color: #86efac; }}
    .kpi-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 16px; margin-bottom: 24px; }}
    .kpi-card {{ background: var(--card-bg); border: 1px solid var(--border); border-radius: 8px; padding: 16px; text-align: center; }}
    .kpi-val {{ font-size: 28px; font-weight: 700; color: var(--accent); margin-bottom: 4px; }}
    .kpi-label {{ font-size: 12px; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.5px; }}
    .controls {{ display: flex; gap: 12px; margin-bottom: 20px; align-items: center; flex-wrap: wrap; }}
    .search-input {{ flex: 1; min-width: 250px; background: var(--card-bg); border: 1px solid var(--border); border-radius: 6px; padding: 10px 14px; color: var(--text); font-size: 14px; outline: none; }}
    .search-input:focus {{ border-color: var(--accent); }}
    .tab-btn {{ background: var(--card-bg); border: 1px solid var(--border); border-radius: 6px; padding: 10px 16px; color: var(--text-muted); font-size: 13px; font-weight: 600; cursor: pointer; transition: all 0.2s; }}
    .tab-btn.active, .tab-btn:hover {{ background: var(--accent); color: #000; border-color: var(--accent); }}
    .card-list {{ display: grid; gap: 14px; }}
    .card {{ background: var(--card-bg); border: 1px solid var(--border); border-radius: 8px; padding: 16px; transition: border-color 0.2s; }}
    .card:hover {{ border-color: var(--accent); }}
    .card-header {{ display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 8px; }}
    .card-title {{ font-size: 15px; font-weight: 600; color: var(--text); flex: 1; margin-right: 12px; }}
    .card-body {{ font-size: 13px; color: var(--text-muted); margin-bottom: 12px; white-space: pre-wrap; }}
    .spec-box {{ background: #090d16; border: 1px solid #1e293b; border-radius: 4px; padding: 8px 12px; font-family: monospace; font-size: 12px; color: #38bdf8; overflow-x: auto; }}
  </style>
</head>
<body>
  <div class="header">
    <div>
      <div class="title">SEOJEV V3 Search Intelligence Explorer</div>
      <div style="font-size: 13px; color: var(--text-muted); margin-top: 4px;">Universal Search Optimization & Diagnostic Engine — Target: <strong>{domain}</strong></div>
    </div>
    <div style="font-size: 12px; color: var(--text-muted);">Offline Interactive Dashboard</div>
  </div>

  <div class="kpi-grid">
    <div class="kpi-card"><div class="kpi-val" id="kpi-total">0</div><div class="kpi-label">URLs Crawled</div></div>
    <div class="kpi-card"><div class="kpi-val" id="kpi-indexable">0</div><div class="kpi-label">Indexable Pages</div></div>
    <div class="kpi-card"><div class="kpi-val" id="kpi-opps">0</div><div class="kpi-label">Opportunities</div></div>
    <div class="kpi-card"><div class="kpi-val" id="kpi-wo">0</div><div class="kpi-label">Work Orders</div></div>
    <div class="kpi-card"><div class="kpi-val" id="kpi-p0">0</div><div class="kpi-label">P0/P1 Actions</div></div>
  </div>

  <div class="controls">
    <input type="text" id="searchInput" class="search-input" placeholder="Search opportunities, work orders, URLs, rules, specs...">
    <button class="tab-btn active" onclick="setTab('work_orders')">Work Orders</button>
    <button class="tab-btn" onclick="setTab('opportunities')">Opportunities</button>
    <button class="tab-btn" onclick="setTab('queries')">Queries & Fit</button>
  </div>

  <div id="cardList" class="card-list"></div>

  <script>
    const DATA = {json_data};
    let currentTab = 'work_orders';

    document.getElementById('kpi-total').innerText = DATA.stats.total_pages.toLocaleString();
    document.getElementById('kpi-indexable').innerText = DATA.stats.indexable_pages.toLocaleString();
    document.getElementById('kpi-opps').innerText = DATA.stats.total_opportunities.toLocaleString();
    document.getElementById('kpi-wo').innerText = DATA.stats.total_work_orders.toLocaleString();
    document.getElementById('kpi-p0').innerText = DATA.stats.high_priority_orders.toLocaleString();

    function setTab(tab) {{
      currentTab = tab;
      document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
      event.target.classList.add('active');
      render();
    }}

    function render() {{
      const query = document.getElementById('searchInput').value.toLowerCase();
      const container = document.getElementById('cardList');
      container.innerHTML = '';

      if (currentTab === 'work_orders') {{
        const filtered = DATA.work_orders.filter(w => 
          w.title.toLowerCase().includes(query) ||
          w.problem.toLowerCase().includes(query) ||
          w.display_id.toLowerCase().includes(query)
        );
        filtered.forEach(w => {{
          const card = document.createElement('div');
          card.className = 'card';
          card.innerHTML = `
            <div class="card-header">
              <div class="card-title"><strong>[${{w.display_id}}]</strong> ${{w.title}}</div>
              <span class="badge badge-${{w.priority.toLowerCase()}}">${{w.priority}}</span>
            </div>
            <div class="card-body"><strong>Problem:</strong> ${{w.problem}}</div>
            <div class="card-body"><strong>Required Change:</strong> ${{w.required_change}}</div>
            <div class="card-body"><strong>Verification Spec:</strong></div>
            <div class="spec-box">${{w.verify_spec}}</div>
          `;
          container.appendChild(card);
        }});
      }} else if (currentTab === 'opportunities') {{
        const filtered = DATA.opportunities.filter(o => 
          o.action.toLowerCase().includes(query) ||
          o.observation.toLowerCase().includes(query) ||
          o.type.toLowerCase().includes(query)
        );
        filtered.forEach(o => {{
          const card = document.createElement('div');
          card.className = 'card';
          card.innerHTML = `
            <div class="card-header">
              <div class="card-title"><strong>[${{o.type}}]</strong> ${{o.action}}</div>
              <span class="badge badge-p2">Score: ${{o.priority_score}} | ${{o.opportunity_tier}}</span>
            </div>
            <div class="card-body"><strong>Observation:</strong> ${{o.observation}}</div>
            <div class="card-body"><strong>Diagnosis:</strong> ${{o.diagnosis}}</div>
            <div class="card-body"><strong>Hypothesis:</strong> ${{o.hypothesis}}</div>
            <div class="card-body"><strong>Location:</strong> ${{o.implementation_location}} (${{o.affected_urls_count}} URLs affected)</div>
          `;
          container.appendChild(card);
        }});
      }} else if (currentTab === 'queries') {{
        const filtered = DATA.queries.filter(q => 
          q.query.toLowerCase().includes(query) ||
          q.url.toLowerCase().includes(query) ||
          q.verdict.toLowerCase().includes(query)
        );
        filtered.forEach(q => {{
          const card = document.createElement('div');
          card.className = 'card';
          card.innerHTML = `
            <div class="card-header">
              <div class="card-title">Query: "<strong>${{q.query}}</strong>"</div>
              <span class="badge badge-${{q.verdict === 'CORRECT_LANDING' ? 'p3' : 'p1'}}">${{q.verdict}}</span>
            </div>
            <div class="card-body"><strong>Landing Page:</strong> ${{q.url}}</div>
            <div class="card-body">Position: <strong>${{q.position}}</strong> | Impressions: <strong>${{q.impressions}}</strong> | Clicks: <strong>${{q.clicks}}</strong></div>
          `;
          container.appendChild(card);
        }});
      }}
    }}

    document.getElementById('searchInput').addEventListener('input', render);
    render();
  </script>
</body>
</html>
"""
        with open(self.output_path, "w", encoding="utf-8") as f:
            f.write(html_template)

        return self.output_path
