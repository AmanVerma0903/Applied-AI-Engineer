"""
pipeline.damage.concealed
Concealed damage inference engine based on building science rules (IICRC S500 / ASTM).
Flags unseen moisture trapping, structural framing defects, and insulation saturation.
"""

from dataclasses import dataclass
from typing import List, Dict, Any, Optional

from pipeline.damage.detector import DetectedDamage


@dataclass
class ConcealedDamageFlag:
    flag_id: str
    surface_id: str
    rule_id: str
    rule_name: str
    rationale: str
    risk_level: str               # 'low', 'medium', 'high'
    recommended_investigation: str


class ConcealedDamageRuleEngine:
    """Evaluates deterministic building science rules to flag concealed damage hazards."""

    @staticmethod
    def evaluate(
        surface_id: str,
        damage_regions: List[DetectedDamage],
        is_plumbing_wall: bool = True,
        is_exterior_wall: bool = False
    ) -> List[ConcealedDamageFlag]:
        """Runs rule catalog against surface damage observations."""
        flags: List[ConcealedDamageFlag] = []

        for dmg in damage_regions:
            # RULE-CD-01: Plumbing Wall Moisture Saturation
            if dmg.damage_class in ["water_damage", "mold_spores"] and is_plumbing_wall:
                flags.append(ConcealedDamageFlag(
                    flag_id=f"flag_{surface_id}_cd01",
                    surface_id=surface_id,
                    rule_id="RULE-CD-01",
                    rule_name="Plumbing Wall Cavity Moisture Saturation",
                    rationale=(
                        f"Detected {dmg.damage_class.replace('_', ' ')} measuring {dmg.metric_area_sqm:.2f} m² "
                        "on plumbing-adjacent partition. Moisture likely penetrated gypsum core into stud cavity, "
                        "saturating insulation batts and compromising wall framing plate."
                    ),
                    risk_level="high",
                    recommended_investigation="Thermal imaging probe and non-destructive pinless moisture meter scan across 1.2m radius; invasive cavity inspection cut recommended if moisture >18%."
                ))

            # RULE-CD-02: Microbial Proliferation Behind Baseboards
            if dmg.damage_class == "water_damage" and dmg.severity in ["high", "critical"]:
                flags.append(ConcealedDamageFlag(
                    flag_id=f"flag_{surface_id}_cd02",
                    surface_id=surface_id,
                    rule_id="RULE-CD-02",
                    rule_name="Subfloor Moisture Wicking & Microbial Hazard",
                    rationale=(
                        "Prolonged surface water contact at floor-wall junction indicates potential capillary "
                        "wicking into bottom plate, subfloor wood decking, and concealed mold propagation behind baseboards."
                    ),
                    risk_level="medium",
                    recommended_investigation="Baseboard detachment and subfloor moisture content logging."
                ))

            # RULE-CD-03: Structural Header Shear Stress
            if dmg.damage_class == "drywall_crack" and dmg.linear_length_m and dmg.linear_length_m > 0.50:
                flags.append(ConcealedDamageFlag(
                    flag_id=f"flag_{surface_id}_cd03",
                    surface_id=surface_id,
                    rule_id="RULE-CD-03",
                    rule_name="Framing Settlement & Header Deflection",
                    rationale=(
                        f"Diagonal drywall shear crack of length {dmg.linear_length_m:.2f} m propagating from "
                        "upper wall/opening junction indicates differential framing settlement, trimmer stud shrinkage, "
                        "or structural header overload."
                    ),
                    risk_level="high",
                    recommended_investigation="Laser level elevation survey of floor joists and header plumbness inspection."
                ))

            # RULE-CD-04: Exterior Wall Envelope Infiltration
            if dmg.damage_class == "water_damage" and is_exterior_wall:
                flags.append(ConcealedDamageFlag(
                    flag_id=f"flag_{surface_id}_cd04",
                    surface_id=surface_id,
                    rule_id="RULE-CD-04",
                    rule_name="Envelope Vapor Barrier Compromise",
                    rationale="Moisture staining on exterior boundary wall indicates potential flashing or window seal failure.",
                    risk_level="medium",
                    recommended_investigation="Exterior facade moisture intrusion inspection and air-barrier test."
                ))

        return flags
