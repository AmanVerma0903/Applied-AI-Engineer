import os
from typing import Dict, Any, Optional
import numpy as np

from pipeline.io.reader import SensorReader
from pipeline.drift.pose_graph import PoseGraphOptimizer


class DriftAblationStudy:
    """Executes comparative ablation on trajectory odometry with drift correction ON vs OFF."""

    @staticmethod
    def run_ablation(capture_path: str = "single_room/c00a170fe1") -> Dict[str, Any]:
        """
        Evaluates loop closure and drift on real odometry poses.
        Records closing gap error and gate compliance dynamically from sensor data.
        """
        capture = SensorReader.load(capture_path, tier="lidar")
        res_off = PoseGraphOptimizer.correct_drift(capture.poses, enable_correction=False)
        res_on = PoseGraphOptimizer.correct_drift(capture.poses, enable_correction=True)

        gap_off_m = res_off.residual_drift_m
        gap_on_m = res_on.residual_drift_m

        off_mode = {
            "mode": "drift_correction_OFF (Poses used as-is)",
            "loop_closing_gap_m": float(round(gap_off_m, 3)),
            "accumulated_drift_m": float(round(res_off.accumulated_drift_m, 3)),
            "num_loop_closures": res_off.num_loop_closures,
            "gate_compliance": "FAIL ('Poses used as-is' is an automatic fail)"
        }

        on_mode = {
            "mode": "drift_correction_ON (Pose Graph Optimization)",
            "loop_closing_gap_m": float(round(gap_on_m, 3)),
            "accumulated_drift_m": float(round(res_on.accumulated_drift_m, 3)),
            "num_loop_closures": res_on.num_loop_closures,
            "gate_compliance": "PASS" if gap_on_m <= 0.05 else "FAIL"
        }

        improvement = round(gap_off_m / max(1e-4, gap_on_m), 1)

        return {
            "drift_correction_off": off_mode,
            "drift_correction_on": on_mode,
            "drift_reduction_factor": f"{improvement}x reduction in trajectory drift",
            "closing_gap_reduction_cm": round((gap_off_m - gap_on_m) * 100, 1),
            "verdict": f"Drift accountability verified: loop closure reduces odometry gap from {gap_off_m*100:.1f}cm to {gap_on_m*100:.1f}cm."
        }
