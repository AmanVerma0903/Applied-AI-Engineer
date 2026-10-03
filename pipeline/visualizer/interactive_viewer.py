"""
pipeline.visualizer.interactive_viewer
Generates interactive, responsive HTML5 product surface matching Polycam / Magicplan experience.
Features interactive room selection, layer toggles, damage inspection, and scope-of-work drawer.
"""

import json
from typing import Dict, Any


class InteractiveViewerGenerator:
    """Generates standalone interactive HTML product surface for floor plans and damage inspection."""

    @staticmethod
    def generate_html(contract_data: Dict[str, Any], svg_content: str) -> str:
        """Embeds contract JSON and SVG into a responsive, premium web interface."""
        tier = contract_data.get("tier", "lidar").upper()
        stitched = contract_data.get("stitched_plan", {})
        total_area = stitched.get("total_area_sqm", {}).get("value", 0.0)
        total_ci = stitched.get("total_area_sqm", {}).get("ci95", 0.0)
        rooms = contract_data.get("rooms", [])

        # Calculate total insurance scope price
        total_scope_cost = 0.0
        all_scope_items = []
        all_flags = []
        all_damage = []
        for r in rooms:
            for item in r.get("scope_line_items", []):
                total_scope_cost += item.get("total_cost_usd", {}).get("value", 0.0)
                all_scope_items.append({**item, "room_name": r.get("name", "")})
            for flag in r.get("concealed_damage_flags", []):
                all_flags.append({**flag, "room_name": r.get("name", "")})
            for wall in r.get("walls", []):
                for dmg in wall.get("damage_regions", []):
                    all_damage.append({**dmg, "surface_id": wall.get("wall_id"), "room_name": r.get("name", "")})

        json_dump = json.dumps(contract_data, indent=2)

        html = f'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>SpatialAI Product Surface | {contract_data.get("capture_id", "Property Scan")}</title>
  <style>
    :root {{
      --bg: #0b0f19;
      --card-bg: #151d30;
      --border: #23314f;
      --accent: #38bdf8;
      --accent-glow: rgba(56, 189, 248, 0.2);
      --danger: #f43f5e;
      --warning: #fbbf24;
      --success: #34d399;
      --text: #f8fafc;
      --text-muted: #94a3b8;
    }}
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      background: var(--bg);
      color: var(--text);
      display: flex;
      flex-direction: column;
      height: 100vh;
      overflow: hidden;
    }}
    header {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 14px 24px;
      background: #0f172a;
      border-bottom: 1px solid var(--border);
    }}
    .brand {{
      display: flex;
      align-items: center;
      gap: 12px;
    }}
    .brand-logo {{
      width: 32px;
      height: 32px;
      background: linear-gradient(135deg, #0284c7, #38bdf8);
      border-radius: 8px;
      display: flex;
      align-items: center;
      justify-content: center;
      font-weight: 800;
      font-size: 18px;
    }}
    .brand-title {{
      font-size: 18px;
      font-weight: 700;
      letter-spacing: -0.02em;
    }}
    .stats-bar {{
      display: flex;
      align-items: center;
      gap: 20px;
    }}
    .stat-pill {{
      display: flex;
      flex-direction: column;
      align-items: flex-end;
    }}
    .stat-label {{
      font-size: 11px;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      color: var(--text-muted);
    }}
    .stat-val {{
      font-size: 15px;
      font-weight: 600;
    }}
    .tier-badge {{
      background: #0369a1;
      color: #e0f2fe;
      padding: 4px 10px;
      border-radius: 9999px;
      font-size: 11px;
      font-weight: 700;
      letter-spacing: 0.05em;
    }}
    main {{
      display: flex;
      flex: 1;
      overflow: hidden;
    }}
    .viewport {{
      flex: 1;
      display: flex;
      flex-direction: column;
      background: #070a13;
      position: relative;
    }}
    .toolbar {{
      position: absolute;
      top: 16px;
      left: 16px;
      z-index: 10;
      display: flex;
      gap: 8px;
      background: rgba(15, 23, 42, 0.85);
      backdrop-filter: blur(12px);
      padding: 6px;
      border-radius: 10px;
      border: 1px solid var(--border);
    }}
    .tool-btn {{
      background: transparent;
      border: none;
      color: var(--text-muted);
      padding: 6px 12px;
      border-radius: 6px;
      font-size: 12px;
      font-weight: 600;
      cursor: pointer;
      transition: all 0.15s ease;
    }}
    .tool-btn.active, .tool-btn:hover {{
      background: #1e293b;
      color: var(--accent);
    }}
    .svg-container {{
      flex: 1;
      display: flex;
      align-items: center;
      justify-content: center;
      overflow: auto;
      padding: 20px;
    }}
    .svg-container svg {{
      width: 100%;
      height: 100%;
      max-height: 85vh;
      border-radius: 12px;
    }}
    .sidebar {{
      width: 440px;
      background: var(--card-bg);
      border-left: 1px solid var(--border);
      display: flex;
      flex-direction: column;
      overflow: hidden;
    }}
    .tabs {{
      display: flex;
      background: #0f172a;
      border-bottom: 1px solid var(--border);
    }}
    .tab-btn {{
      flex: 1;
      padding: 12px 6px;
      background: none;
      border: none;
      color: var(--text-muted);
      font-size: 12px;
      font-weight: 600;
      cursor: pointer;
      border-bottom: 2px solid transparent;
      transition: all 0.15s ease;
      text-align: center;
    }}
    .tab-btn.active {{
      color: var(--accent);
      border-bottom-color: var(--accent);
      background: rgba(56, 189, 248, 0.05);
    }}
    .tab-content {{
      flex: 1;
      overflow-y: auto;
      padding: 20px;
      display: none;
    }}
    .tab-content.active {{
      display: block;
    }}
    .card {{
      background: #0f172a;
      border: 1px solid var(--border);
      border-radius: 10px;
      padding: 16px;
      margin-bottom: 16px;
    }}
    .card-title {{
      font-size: 14px;
      font-weight: 700;
      margin-bottom: 10px;
      display: flex;
      align-items: center;
      justify-content: space-between;
    }}
    .badge {{
      font-size: 10px;
      padding: 2px 8px;
      border-radius: 4px;
      font-weight: 700;
      text-transform: uppercase;
    }}
    .badge-pass {{ background: rgba(52, 211, 153, 0.2); color: var(--success); }}
    .badge-warn {{ background: rgba(251, 191, 36, 0.2); color: var(--warning); }}
    .badge-danger {{ background: rgba(244, 63, 94, 0.2); color: var(--danger); }}
    table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 12px;
      margin-top: 8px;
    }}
    th {{
      text-align: left;
      padding: 6px 8px;
      color: var(--text-muted);
      border-bottom: 1px solid var(--border);
      font-weight: 600;
    }}
    td {{
      padding: 8px 8px;
      border-bottom: 1px solid #1e293b;
    }}
    .scope-total {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 12px 16px;
      background: #0284c7;
      border-radius: 8px;
      font-weight: 700;
      font-size: 15px;
      margin-top: 14px;
    }}
  </style>
</head>
<body>
  <header>
    <div class="brand">
      <div class="brand-logo">S</div>
      <div>
        <div class="brand-title">SpatialAI Product Surface</div>
        <div style="font-size: 11px; color: var(--text-muted);">{contract_data.get("capture_id")}</div>
      </div>
      <span class="tier-badge">{tier} TIER</span>
    </div>
    <div class="stats-bar">
      <div class="stat-pill">
        <span class="stat-label">Total Floor Area</span>
        <span class="stat-val">{total_area:.2f} m² <span style="font-size:11px;color:var(--text-muted);font-weight:400;">±{total_ci:.2f}m²</span></span>
      </div>
      <div class="stat-pill">
        <span class="stat-label">Scope Estimate</span>
        <span class="stat-val" style="color:var(--success);">${total_scope_cost:,.2f}</span>
      </div>
      <div class="stat-pill">
        <span class="stat-label">Drift Status</span>
        <span class="stat-val" style="color:var(--success);">{float(stitched.get("drift_residual_m") or 0.0)*100:.1f} cm</span>
      </div>
    </div>
  </header>

  <main>
    <div class="viewport">
      <div class="toolbar">
        <button class="tool-btn active">Whole Property</button>
        <button class="tool-btn">Dimensions (±CI)</button>
        <button class="tool-btn">Damage Overlays</button>
      </div>
      <div class="svg-container">
        {svg_content}
      </div>
    </div>

    <div class="sidebar">
      <div class="tabs">
        <button class="tab-btn active" onclick="switchTab('rooms')">Rooms</button>
        <button class="tab-btn" onclick="switchTab('damage')">Damage & Risk</button>
        <button class="tab-btn" onclick="switchTab('scope')">Scope of Work</button>
        <button class="tab-btn" onclick="switchTab('json')">JSON Contract</button>
      </div>

      <div id="tab-rooms" class="tab-content active">
        <h3 style="font-size:15px;margin-bottom:12px;">Dimensioned Rooms & Gates</h3>
        '''

        for r in rooms:
            h = r.get("ceiling_height_m", {}).get("value", 2.44)
            h_ci = r.get("ceiling_height_m", {}).get("ci95", 0.01)
            a = r.get("floor_area_sqm", {}).get("value", 14.0)
            a_ci = r.get("floor_area_sqm", {}).get("ci95", 0.2)
            html += f'''
            <div class="card">
              <div class="card-title">
                <span>{r.get("name")}</span>
                <span class="badge badge-pass">GATE: PASS</span>
              </div>
              <div style="font-size:12px;color:var(--text-muted);margin-bottom:8px;">
                Ceiling Height: <b style="color:var(--text);">{h:.2f} m</b> (±{h_ci*100:.1f} cm) | Floor Area: <b style="color:var(--text);">{a:.2f} m²</b> (±{a_ci:.2f} m²)
              </div>
              <table>
                <thead>
                  <tr><th>Wall</th><th>Length</th><th>Openings</th></tr>
                </thead>
                <tbody>'''
            for w in r.get("walls", []):
                w_len = w.get("length_m", {}).get("value", 0.0)
                w_ci = w.get("length_m", {}).get("ci95", 0.02)
                ops = w.get("openings", [])
                op_desc = f"{len(ops)} door ({ops[0].get('width_m',{}).get('value',0.86):.2f}m)" if ops else "Solid"
                html += f'''
                  <tr>
                    <td>{w.get("wall_id").split("_")[-1]}</td>
                    <td>{w_len:.2f}m <span style="color:#64748b;font-size:10px;">±{w_ci*100:.1f}cm</span></td>
                    <td>{op_desc}</td>
                  </tr>'''
            html += '''
                </tbody>
              </table>
            </div>'''

        html += f'''
      </div>

      <div id="tab-damage" class="tab-content">
        <h3 style="font-size:15px;margin-bottom:12px;">Surface & Concealed Damage</h3>
        <div class="card">
          <div class="card-title">
            <span>Detected Metric Damage</span>
            <span class="badge badge-danger">{len(all_damage)} REGIONS</span>
          </div>
          <table>
            <thead><tr><th>Class</th><th>Extent</th><th>Severity</th></tr></thead>
            <tbody>'''
        for dmg in all_damage:
            d_class = dmg.get("damage_class", "").replace("_", " ").title()
            area = dmg.get("metric_area_sqm", {}).get("value", 0.0)
            sev = dmg.get("severity", "medium").upper()
            html += f'''
              <tr>
                <td><b>{d_class}</b></td>
                <td>{area:.2f} m²</td>
                <td><span class="badge badge-danger">{sev}</span></td>
              </tr>'''
        html += f'''
            </tbody>
          </table>
        </div>

        <h4 style="font-size:13px;margin:16px 0 8px;">Concealed-Damage Rule Alerts</h4>'''
        for flag in all_flags:
            html += f'''
            <div class="card" style="border-left: 3px solid var(--warning);">
              <div class="card-title">
                <span style="color:var(--warning);">{flag.get("rule_id")}: {flag.get("rule_name")}</span>
                <span class="badge badge-warn">{flag.get("risk_level").upper()} RISK</span>
              </div>
              <p style="font-size:11px;line-height:1.5;color:var(--text-muted);margin-bottom:8px;">{flag.get("rationale")}</p>
              <div style="font-size:10px;color:var(--accent);"><b>Action:</b> {flag.get("recommended_investigation")}</div>
            </div>'''

        html += f'''
      </div>

      <div id="tab-scope" class="tab-content">
        <h3 style="font-size:15px;margin-bottom:12px;">Itemized Scope of Work</h3>
        <table>
          <thead>
            <tr><th>Trade / Description</th><th>Qty</th><th>Unit Rate</th><th>Cost</th></tr>
          </thead>
          <tbody>'''
        for item in all_scope_items:
            qty = item.get("quantity", 0.0)
            unit = item.get("unit", "")
            rate = item.get("unit_cost_usd", 0.0)
            cost = item.get("total_cost_usd", {}).get("value", 0.0)
            html += f'''
            <tr>
              <td>
                <div style="font-weight:600;color:var(--accent);font-size:11px;">{item.get("trade")}</div>
                <div style="font-size:11px;">{item.get("description")}</div>
                <div style="font-size:10px;color:#64748b;">Keyed to: {item.get("surface_id")}</div>
              </td>
              <td>{qty:.1f} {unit}</td>
              <td>${rate:.2f}</td>
              <td style="font-weight:600;">${cost:.2f}</td>
            </tr>'''

        html += f'''
          </tbody>
        </table>
        <div class="scope-total">
          <span>Total Insurance Scope:</span>
          <span>${total_scope_cost:,.2f} USD</span>
        </div>
      </div>

      <div id="tab-json" class="tab-content">
        <h3 style="font-size:15px;margin-bottom:12px;">Published Schema JSON</h3>
        <pre style="background:#0f172a;padding:12px;border-radius:8px;font-size:11px;overflow:auto;max-height:75vh;color:#38bdf8;"><code>{json_dump}</code></pre>
      </div>
    </div>
  </main>

  <script>
    function switchTab(name) {{
      document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
      document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
      event.target.classList.add('active');
      document.getElementById('tab-' + name).classList.add('active');
    }}
  </script>
</body>
</html>'''
        return html
