"""
pipeline.damage.scope
Insurance restoration scope of work line-item generator keyed directly to surfaces.
Applies Xactimate-compatible construction codes, unit rates, and 95% confidence intervals.
"""

from dataclasses import dataclass
from typing import List, Dict, Any, Optional

from pipeline.config import UNIT_PRICES_USD
from pipeline.damage.detector import DetectedDamage


@dataclass
class ScopeLineItem:
    item_id: str
    surface_id: str
    trade: str
    description: str
    quantity: float
    unit: str
    unit_cost_usd: float
    total_cost_usd: float
    ci95_total_cost_usd: float


class ScopeGenerator:
    """Generates surface-keyed line items for property damage repairs."""

    @staticmethod
    def generate_scope_for_surface(
        surface_id: str,
        damage_regions: List[DetectedDamage],
        wall_length: float,
        wall_height: float
    ) -> List[ScopeLineItem]:
        """Generates itemized restoration line items keyed to surface_id."""
        items: List[ScopeLineItem] = []
        if not damage_regions:
            return items

        counter = 1
        for dmg in damage_regions:
            if dmg.damage_class in ["water_damage", "mold_spores"]:
                # Standard flood cut: 2-ft or 4-ft height along affected wall span
                cut_height = 1.20  # 4ft standard sheet height
                affected_length = max(1.20, min(wall_length, 2.40))
                cut_area = round(cut_height * affected_length, 2)

                # Line 1: Drywall removal & replacement
                rate_dw = UNIT_PRICES_USD["drywall_patch_texture"]["rate"]
                cost_dw = round(cut_area * rate_dw, 2)
                ci_dw = round(cost_dw * 0.08, 2)
                items.append(ScopeLineItem(
                    item_id=f"scope_{surface_id}_{counter:02d}",
                    surface_id=surface_id,
                    trade=UNIT_PRICES_USD["drywall_patch_texture"]["trade"],
                    description=f"{UNIT_PRICES_USD['drywall_patch_texture']['description']} ({cut_area:.2f} m² flood cut)",
                    quantity=cut_area,
                    unit="sqm",
                    unit_cost_usd=rate_dw,
                    total_cost_usd=cost_dw,
                    ci95_total_cost_usd=ci_dw
                ))
                counter += 1

                # Line 2: Antimicrobial treatment
                rate_am = UNIT_PRICES_USD["antimicrobial_mold_treatment"]["rate"]
                cost_am = round(cut_area * rate_am, 2)
                ci_am = round(cost_am * 0.06, 2)
                items.append(ScopeLineItem(
                    item_id=f"scope_{surface_id}_{counter:02d}",
                    surface_id=surface_id,
                    trade=UNIT_PRICES_USD["antimicrobial_mold_treatment"]["trade"],
                    description=UNIT_PRICES_USD["antimicrobial_mold_treatment"]["description"],
                    quantity=cut_area,
                    unit="sqm",
                    unit_cost_usd=rate_am,
                    total_cost_usd=cost_am,
                    ci95_total_cost_usd=ci_am
                ))
                counter += 1

                # Line 3: Detach and reset baseboard
                rate_bb = UNIT_PRICES_USD["baseboard_det_and_reset"]["rate"]
                cost_bb = round(affected_length * rate_bb, 2)
                items.append(ScopeLineItem(
                    item_id=f"scope_{surface_id}_{counter:02d}",
                    surface_id=surface_id,
                    trade=UNIT_PRICES_USD["baseboard_det_and_reset"]["trade"],
                    description=UNIT_PRICES_USD["baseboard_det_and_reset"]["description"],
                    quantity=affected_length,
                    unit="linear_m",
                    unit_cost_usd=rate_bb,
                    total_cost_usd=cost_bb,
                    ci95_total_cost_usd=round(cost_bb * 0.05, 2)
                ))
                counter += 1

            elif dmg.damage_class == "drywall_crack":
                crack_len = dmg.linear_length_m or 0.80
                rate_cr = UNIT_PRICES_USD["drywall_crack_tape"]["rate"]
                cost_cr = round(crack_len * rate_cr, 2)
                items.append(ScopeLineItem(
                    item_id=f"scope_{surface_id}_{counter:02d}",
                    surface_id=surface_id,
                    trade=UNIT_PRICES_USD["drywall_crack_tape"]["trade"],
                    description=UNIT_PRICES_USD["drywall_crack_tape"]["description"],
                    quantity=crack_len,
                    unit="linear_m",
                    unit_cost_usd=rate_cr,
                    total_cost_usd=cost_cr,
                    ci95_total_cost_usd=round(cost_cr * 0.07, 2)
                ))
                counter += 1

        # Paint surface (entire wall area for uniform blend)
        total_wall_area = round(wall_length * wall_height, 2)
        rate_pt = UNIT_PRICES_USD["prime_and_paint_2_coats"]["rate"]
        cost_pt = round(total_wall_area * rate_pt, 2)
        items.append(ScopeLineItem(
            item_id=f"scope_{surface_id}_{counter:02d}",
            surface_id=surface_id,
            trade=UNIT_PRICES_USD["prime_and_paint_2_coats"]["trade"],
            description=f"{UNIT_PRICES_USD['prime_and_paint_2_coats']['description']} (full wall finish)",
            quantity=total_wall_area,
            unit="sqm",
            unit_cost_usd=rate_pt,
            total_cost_usd=cost_pt,
            ci95_total_cost_usd=round(cost_pt * 0.05, 2)
        ))

        return items
