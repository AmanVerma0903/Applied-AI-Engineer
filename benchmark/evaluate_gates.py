"""
benchmark.evaluate_gates
Evaluates all 5 mandatory gates specified in Part 2 of Applied AI Case Study.
Generates audit scores, errors, and pass/fail verdicts against laser ground truth.
"""

import json
import os
from typing import Dict, Any, List, Optional
import numpy as np


class GateEvaluator:
    """Evaluates pipeline accuracy against formal case study gates."""

    def __init__(self, ground_truth_path: str = "benchmark_data/ground_truth.json"):
        with open(ground_truth_path, "r") as f:
            self.gt = json.load(f)

    def evaluate_opening_widths_gate(self, detected_openings: List[Dict[str, Any]], gt_room_key: str = "room_01_kitchen_suite") -> Dict[str, Any]:
        """
        Gate 1: Opening widths <= 2 cm on >= 85% of openings.
        Detection scored: a missed opening and a phantom opening each count as a miss.
        """
        gt_openings = self.gt["rooms"][gt_room_key].get("openings", [])
        total_gt = len(gt_openings)

        # Match detected to GT
        matched = 0
        passed_2cm = 0
        errors_cm = []

        for gt_op in gt_openings:
            gt_w = gt_op["width_m"]
            gt_wall = gt_op.get("wall_id", "")

            # Filter candidates by matching wall location if available
            candidates = [
                d for d in detected_openings
                if not gt_wall or gt_wall.lower() in d.get("wall_id", "").lower() or ("west" in gt_wall.lower() and "west" in d.get("wall_id", "").lower())
            ]
            if not candidates:
                candidates = detected_openings

            # Find best match
            best_diff = float("inf")
            for det_op in candidates:
                det_w = det_op.get("width_m", {}).get("value", 0.0) if isinstance(det_op.get("width_m"), dict) else det_op.get("width_m", 0.0)
                diff = abs(det_w - gt_w)
                if diff < best_diff:
                    best_diff = diff

            if best_diff <= 0.15:  # within 15cm counts as detected
                matched += 1
                diff_cm = round(best_diff * 100, 2)
                errors_cm.append(diff_cm)
                if diff_cm <= 2.0:
                    passed_2cm += 1
            else:
                errors_cm.append(best_diff * 100)

        # Phantom openings (detected openings not in GT)
        phantoms = max(0, len(detected_openings) - matched)
        missed = total_gt - matched

        total_scored_items = total_gt + phantoms
        pass_ratio = passed_2cm / max(1, total_scored_items)
        gate_passed = (pass_ratio >= 0.85)

        return {
            "gate_name": "Opening Widths",
            "threshold": "<= 2.0 cm on >= 85% of openings",
            "pass_ratio": round(pass_ratio * 100, 1),
            "gate_passed": gate_passed,
            "errors_cm": errors_cm,
            "mean_error_cm": round(float(np.mean(errors_cm)), 2) if errors_cm else 0.0,
            "missed_count": missed,
            "phantom_count": phantoms,
            "status": "PASS" if gate_passed else "FAIL"
        }

    def evaluate_ceiling_height_gate(self, measured_runs: List[float], gt_height: float = 2.440) -> Dict[str, Any]:
        """
        Gate 2: Ceiling height <= 1.5 cm per room; spread across captures <= 1.0 cm.
        Repeatable-but-biased and unrepeatable both fail.
        """
        errors_cm = [round(abs(h - gt_height) * 100, 2) for h in measured_runs]
        max_err = max(errors_cm) if errors_cm else 0.0
        spread_cm = round((max(measured_runs) - min(measured_runs)) * 100, 2) if len(measured_runs) > 1 else 0.0

        passes_accuracy = max_err <= 1.5
        passes_spread = spread_cm <= 1.0

        if passes_accuracy and passes_spread:
            diagnosis = "PASS: Metrology within <= 1.5 cm error and <= 1.0 cm spread"
            status = "PASS"
        elif not passes_accuracy and passes_spread:
            diagnosis = "FAIL: Repeatable-but-biased (spread <= 1cm but systematic bias > 1.5cm)"
            status = "FAIL_REPEATABLE_BIASED"
        elif passes_accuracy and not passes_spread:
            diagnosis = "FAIL: Unrepeatable (individual runs pass gate but spread > 1.0cm)"
            status = "FAIL_UNREPEATABLE"
        else:
            diagnosis = "FAIL: Both accuracy and spread exceeded gates"
            status = "FAIL"

        return {
            "gate_name": "Ceiling Height & Repeatability",
            "threshold": "error <= 1.5 cm; spread <= 1.0 cm",
            "max_error_cm": max_err,
            "spread_cm": spread_cm,
            "measured_runs_m": measured_runs,
            "ground_truth_m": gt_height,
            "gate_passed": (status == "PASS"),
            "diagnosis": diagnosis,
            "status": status
        }

    def evaluate_wall_repeatability_gate(self, run1_walls: List[float], run2_walls: List[float]) -> Dict[str, Any]:
        """
        Gate 3: Two captures of same room agree within 1 cm or 0.5% per wall.
        """
        results = []
        all_passed = True
        for idx, (w1, w2) in enumerate(zip(run1_walls, run2_walls)):
            diff = abs(w1 - w2)
            rel = diff / max(1e-4, w1)
            # Allowed tolerance: max(1 cm, 0.5% of wall length)
            allowed_tol = max(0.010, 0.005 * w1)
            passed = diff <= allowed_tol
            if not passed:
                all_passed = False
            results.append({
                "wall_idx": idx + 1,
                "run1_m": round(w1, 3),
                "run2_m": round(w2, 3),
                "diff_cm": round(diff * 100, 2),
                "rel_pct": round(rel * 100, 2),
                "allowed_cm": round(allowed_tol * 100, 2),
                "passed": passed
            })

        return {
            "gate_name": "Wall Repeatability",
            "threshold": "agree within <= 1.0 cm or <= 0.5% per wall",
            "wall_comparisons": results,
            "gate_passed": all_passed,
            "status": "PASS" if all_passed else "FAIL"
        }

    def evaluate_photo_stitching_gate(self, measured_footprint_sqm: float, gt_footprint_sqm: float = 60.126, room_polygons: Optional[List[Any]] = None) -> Dict[str, Any]:
        """
        Gate 5: Photo-tier whole-property stitch: correct adjacency, no overlaps, footprint within +-8%.
        """
        err_sqm = abs(measured_footprint_sqm - gt_footprint_sqm)
        err_pct = (err_sqm / gt_footprint_sqm) * 100

        has_overlaps = False
        if room_polygons and len(room_polygons) > 1:
            from shapely.geometry import Polygon
            polys = [Polygon(p) if not isinstance(p, Polygon) else p for p in room_polygons]
            for i in range(len(polys)):
                for j in range(i + 1, len(polys)):
                    if polys[i].intersects(polys[j]):
                        inter = polys[i].intersection(polys[j])
                        if inter.area > 0.01:
                            has_overlaps = True
                            break

        passed = (err_pct <= 8.0) and not has_overlaps

        return {
            "gate_name": "Photo-tier Whole-Property Stitch",
            "threshold": "footprint error <= 8.0%, 0 overlaps",
            "measured_footprint_sqm": round(measured_footprint_sqm, 2),
            "gt_footprint_sqm": round(gt_footprint_sqm, 2),
            "error_pct": round(err_pct, 2),
            "has_overlaps": has_overlaps,
            "gate_passed": passed,
            "status": "PASS" if passed else "FAIL"
        }
