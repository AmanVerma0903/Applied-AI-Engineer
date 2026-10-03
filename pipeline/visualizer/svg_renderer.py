"""
pipeline.visualizer.svg_renderer
Generates dimensioned, publication-grade SVG floor plans matching Polycam / Magicplan standards.
Includes wall boundaries, door swings, window symbols, dimension lines, and damage region overlays.
"""

from typing import List, Dict, Any, Tuple, Optional
import numpy as np

from pipeline.stitching.multi_room import StitchedPropertyPlan, RoomPlacement


class SvgPlanRenderer:
    """Renders 2D architectural SVG floor plans with metric dimensions and damage overlays."""

    @staticmethod
    def render_plan(
        plan: StitchedPropertyPlan,
        rooms_data: List[Dict[str, Any]],
        width_px: int = 1200,
        height_px: int = 900
    ) -> str:
        """Renders complete multi-room or single-room stitched floor plan to SVG string."""
        # Find global bounding box
        all_x, all_y = [], []
        for p in plan.placements:
            minx, miny, maxx, maxy = p.polygon.bounds
            all_x.extend([minx, maxx])
            all_y.extend([miny, maxy])

        if not all_x:
            min_x, max_x, min_y, max_y = -3.0, 3.0, -3.0, 3.0
        else:
            min_x, max_x = min(all_x) - 1.2, max(all_x) + 1.2
            min_y, max_y = min(all_y) - 1.2, max(all_y) + 1.2

        span_x = max(1.0, max_x - min_x)
        span_y = max(1.0, max_y - min_y)

        # Coordinate transformation to SVG viewport
        scale = min((width_px - 160) / span_x, (height_px - 180) / span_y)
        origin_x = 80 - min_x * scale
        origin_y = height_px - 90 + min_y * scale  # Invert Y for screen coordinates

        def to_svg(x: float, y: float) -> Tuple[float, float]:
            return (origin_x + x * scale, origin_y - y * scale)

        svg = []
        svg.append(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width_px} {height_px}" '
                   f'style="background-color: #0f172a; font-family: -apple-system, BlinkMacSystemFont, \'Segoe UI\', Roboto, sans-serif;">')

        # Defs & Gradients
        svg.append('''
        <defs>
          <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">
            <path d="M 40 0 L 0 0 0 40" fill="none" stroke="#1e293b" stroke-width="0.75"/>
          </pattern>
          <filter id="shadow" x="-5%" y="-5%" width="110%" height="110%">
            <feDropShadow dx="0" dy="4" stdDeviation="6" flood-color="#000" flood-opacity="0.5"/>
          </filter>
        </defs>
        <rect width="100%" height="100%" fill="#0f172a"/>
        <rect width="100%" height="100%" fill="url(#grid)"/>
        ''')

        # Header Title & Metadata
        svg.append(f'''
        <g id="header">
          <text x="50" y="55" fill="#f8fafc" font-size="24" font-weight="700">Whole Property Floor Plan</text>
          <text x="50" y="80" fill="#94a3b8" font-size="13">Capture Tier: <tspan fill="#38bdf8" font-weight="600">{plan.tier.upper()}</tspan> | Total Area: <tspan fill="#f8fafc" font-weight="600">{plan.total_floor_area_sqm:.2f} m²</tspan> (±{plan.ci95_floor_area_sqm:.2f} m²) | Drift: <tspan fill="#4ade80" font-weight="600">{plan.drift_residual_m*100:.1f} cm</tspan></text>
        </g>
        ''')

        # Render each room polygon
        for p in plan.placements:
            coords = list(p.polygon.exterior.coords)
            svg_pts = [f"{to_svg(x, y)[0]:.1f},{to_svg(x, y)[1]:.1f}" for x, y in coords]
            pts_str = " ".join(svg_pts)

            # Room fill & thick architectural walls
            svg.append(f'''
            <g id="room_{p.room_id}">
              <polygon points="{pts_str}" fill="#1e293b" fill-opacity="0.85" stroke="#334155" stroke-width="1.5" filter="url(#shadow)"/>
              <polygon points="{pts_str}" fill="none" stroke="#cbd5e1" stroke-width="6" stroke-linejoin="round" stroke-linecap="round"/>
            ''')

            # Room Center Label & Area
            cx, cy = p.polygon.centroid.x, p.polygon.centroid.y
            scx, scy = to_svg(cx, cy)
            svg.append(f'''
              <text x="{scx:.1f}" y="{scy - 8:.1f}" fill="#f1f5f9" font-size="15" font-weight="600" text-anchor="middle">{p.name}</text>
              <text x="{scx:.1f}" y="{scy + 12:.1f}" fill="#38bdf8" font-size="12" font-weight="500" text-anchor="middle">{p.floor_area_sqm:.2f} m²</text>
              <text x="{scx:.1f}" y="{scy + 28:.1f}" fill="#94a3b8" font-size="10" text-anchor="middle">Ceil: {p.ceiling_height_m:.2f}m</text>
            </g>
            ''')

        # Render Wall Dimensions and Openings from rooms_data
        for r_dict in rooms_data:
            r_id = r_dict.get("room_id", "")
            # Find placement offset
            placement = next((p for p in plan.placements if p.room_id == r_id), None)
            ox = placement.position_m[0] if placement else 0.0
            oy = placement.position_m[1] if placement else 0.0

            for wall in r_dict.get("walls", []):
                w_start = wall.get("start_m", [0, 0])
                w_end = wall.get("end_m", [0, 0])
                x0, y0 = w_start[0] + ox, w_start[1] + oy
                x1, y1 = w_end[0] + ox, w_end[1] + oy

                sx0, sy0 = to_svg(x0, y0)
                sx1, sy1 = to_svg(x1, y1)

                length = wall.get("length_m", {}).get("value", 0.0)
                ci = wall.get("length_m", {}).get("ci95", 0.02)

                # Midpoint offset for dimension text
                mx, my = (sx0 + sx1) / 2.0, (sy0 + sy1) / 2.0
                nx = -(sy1 - sy0)
                ny = sx1 - sx0
                n_norm = np.hypot(nx, ny) or 1.0
                mx += (nx / n_norm) * 22
                my += (ny / n_norm) * 22

                svg.append(f'''
                <text x="{mx:.1f}" y="{my:.1f}" fill="#94a3b8" font-size="11" font-weight="500" text-anchor="middle">
                  {length:.2f}m <tspan fill="#64748b" font-size="9">±{ci*100:.1f}cm</tspan>
                </text>
                ''')

                # Render Openings (Doors / Windows)
                for op in wall.get("openings", []):
                    op_type = op.get("type", "door")
                    offset = op.get("offset_m", 0.5)
                    op_w = op.get("width_m", {}).get("value", 0.85)

                    # Opening points along wall segment
                    u = np.array([x1 - x0, y1 - y0])
                    u_len = np.linalg.norm(u) or 1.0
                    u_dir = u / u_len

                    p_op0 = np.array([x0, y0]) + u_dir * offset
                    p_op1 = p_op0 + u_dir * op_w

                    sop0_x, sop0_y = to_svg(p_op0[0], p_op0[1])
                    sop1_x, sop1_y = to_svg(p_op1[0], p_op1[1])

                    # White opening cutout line
                    svg.append(f'''
                    <line x1="{sop0_x:.1f}" y1="{sop0_y:.1f}" x2="{sop1_x:.1f}" y2="{sop1_y:.1f}" stroke="#0f172a" stroke-width="8" stroke-linecap="butt"/>
                    ''')

                    if op_type == "door":
                        # Door swing arc (90 deg arc)
                        swing_radius = np.hypot(sop1_x - sop0_x, sop1_y - sop0_y)
                        svg.append(f'''
                        <line x1="{sop0_x:.1f}" y1="{sop0_y:.1f}" x2="{sop1_x:.1f}" y2="{sop1_y:.1f}" stroke="#38bdf8" stroke-width="2"/>
                        <circle cx="{sop0_x:.1f}" cy="{sop0_y:.1f}" r="3" fill="#38bdf8"/>
                        <path d="M {sop1_x:.1f} {sop1_y:.1f} A {swing_radius:.1f} {swing_radius:.1f} 0 0 1 {sop0_x - (sop1_y - sop0_y):.1f} {sop0_y + (sop1_x - sop0_x):.1f}" 
                              fill="none" stroke="#38bdf8" stroke-width="1.2" stroke-dasharray="3,3"/>
                        <text x="{(sop0_x+sop1_x)/2:.1f}" y="{(sop0_y+sop1_y)/2 - 10:.1f}" fill="#38bdf8" font-size="10" font-weight="600" text-anchor="middle">{op_w*100:.0f}cm door</text>
                        ''')
                    elif op_type == "window":
                        svg.append(f'''
                        <line x1="{sop0_x:.1f}" y1="{sop0_y:.1f}" x2="{sop1_x:.1f}" y2="{sop1_y:.1f}" stroke="#e2e8f0" stroke-width="2"/>
                        <text x="{(sop0_x+sop1_x)/2:.1f}" y="{(sop0_y+sop1_y)/2 - 10:.1f}" fill="#e2e8f0" font-size="10" text-anchor="middle">window</text>
                        ''')

                # Render Damage Overlays
                for dmg in wall.get("damage_regions", []):
                    d_class = dmg.get("damage_class", "water_damage")
                    area = dmg.get("metric_area_sqm", {}).get("value", 0.5)
                    color = "#ef4444" if "crack" in d_class else ("#38bdf8" if "water" in d_class else "#a855f7")

                    svg.append(f'''
                    <g id="damage_{dmg.get('damage_id')}">
                      <circle cx="{sx0 + 25:.1f}" cy="{sy0 + 25:.1f}" r="12" fill="{color}" fill-opacity="0.35" stroke="{color}" stroke-width="2"/>
                      <text x="{sx0 + 25:.1f}" y="{sy0 + 29:.1f}" fill="#ffffff" font-size="9" font-weight="700" text-anchor="middle">!</text>
                      <text x="{sx0 + 44:.1f}" y="{sy0 + 28:.1f}" fill="{color}" font-size="10" font-weight="600">{d_class.replace('_', ' ')} ({area:.2f} m²)</text>
                    </g>
                    ''')

        # Legend & Scale Bar
        svg.append(f'''
        <g id="legend" transform="translate(50, {height_px - 60})">
          <rect x="0" y="0" width="340" height="40" rx="8" fill="#1e293b" fill-opacity="0.9" stroke="#334155"/>
          <line x1="20" y1="20" x2="60" y2="20" stroke="#cbd5e1" stroke-width="5"/>
          <text x="70" y="24" fill="#94a3b8" font-size="11">Wall</text>
          <line x1="120" y1="20" x2="150" y2="20" stroke="#38bdf8" stroke-width="2"/>
          <text x="160" y="24" fill="#94a3b8" font-size="11">Door</text>
          <circle cx="215" cy="20" r="6" fill="#ef4444"/>
          <text x="230" y="24" fill="#94a3b8" font-size="11">Damage Region</text>
        </g>
        ''')

        svg.append('</svg>')
        return "\n".join(svg)
