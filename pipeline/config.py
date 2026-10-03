"""
pipeline.config
Configuration parameters, error bounds, gate thresholds, and pricing constants.
"""

from dataclasses import dataclass
from typing import Dict, Any


@dataclass(frozen=True)
class TierNoiseModel:
    """Noise parameters for sensor input tiers."""
    tier_name: str
    depth_noise_std_m: float       # 1-sigma depth uncertainty
    pose_drift_rate_per_m: float   # Drift rate (m / m walked)
    max_range_m: float             # Effective sensor range
    confidence_scale: float        # Scaling multiplier for 95% CI


TIER_CONFIGS: Dict[str, TierNoiseModel] = {
    "lidar": TierNoiseModel(
        tier_name="lidar",
        depth_noise_std_m=0.008,     # Pro LiDAR dToF 8mm nominal noise
        pose_drift_rate_per_m=0.004,  # ARKit VIO drift rate
        max_range_m=4.8,
        confidence_scale=1.96,
    ),
    "video": TierNoiseModel(
        tier_name="video",
        depth_noise_std_m=0.028,     # Monocular depth / VO uncertainty
        pose_drift_rate_per_m=0.018,
        max_range_m=5.0,
        confidence_scale=2.15,
    ),
    "photos": TierNoiseModel(
        tier_name="photos",
        depth_noise_std_m=0.065,     # Multi-view SfM / epipolar uncertainty
        pose_drift_rate_per_m=0.045,
        max_range_m=6.0,
        confidence_scale=2.50,
    ),
}

# Formal Gates (Applied AI Case Study Part 2 & 3)
GATE_OPENING_WIDTH_M = 0.020           # <= 2 cm gate
GATE_OPENING_PASS_PERCENT = 0.85       # >= 85% of openings
GATE_CEILING_HEIGHT_ERROR_M = 0.015    # <= 1.5 cm per room
GATE_CEILING_SPREAD_M = 0.010          # spread across captures <= 1.0 cm
GATE_REPEATABILITY_ABS_M = 0.010       # 1 cm per wall
GATE_REPEATABILITY_REL = 0.005         # 0.5% per wall
GATE_PHOTO_FOOTPRINT_TOLERANCE = 0.08  # Photo whole-property footprint <= 8%
GATE_VIDEO_WALL_TOLERANCE = 0.03       # Video wall length <= 3%
GATE_HEAD_TO_HEAD_WIN_RATE = 0.70      # Beat or tie >= 70% shared dimensions

# Insurance Scope Unit Pricing (Xactimate / IICRC S500 benchmarks)
UNIT_PRICES_USD: Dict[str, Dict[str, Any]] = {
    "drywall_patch_texture": {
        "trade": "Drywall",
        "description": "Cut out damaged gypsum board, hang new 5/8\" sheetrock, tape, mud & sand",
        "unit": "sqm",
        "rate": 195.00,
    },
    "drywall_crack_tape": {
        "trade": "Drywall",
        "description": "V-groove stress crack, fiberglass mesh tape, 3-coat compound finish",
        "unit": "linear_m",
        "rate": 42.50,
    },
    "antimicrobial_mold_treatment": {
        "trade": "Water Remediation",
        "description": "HEPA vacuum, apply EPA-registered antimicrobial disinfectant spray & wipe",
        "unit": "sqm",
        "rate": 128.00,
    },
    "water_extraction_drying": {
        "trade": "Water Remediation",
        "description": "Deploy commercial LGR dehumidifier & axial air movers (3-day cycle)",
        "unit": "room",
        "rate": 450.00,
    },
    "prime_and_paint_2_coats": {
        "trade": "Painting",
        "description": "Stain-blocking primer coat plus two coats low-VOC latex finish paint",
        "unit": "sqm",
        "rate": 46.00,
    },
    "baseboard_det_and_reset": {
        "trade": "Finish Carpentry",
        "description": "Carefully detach 3-1/4\" colonial baseboard, de-nail, prep and reinstall",
        "unit": "linear_m",
        "rate": 22.00,
    },
}
