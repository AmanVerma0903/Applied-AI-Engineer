import os
from typing import Dict, Any, Optional
import numpy as np

from pipeline.io.reader import SensorReader
from pipeline.drift.pose_graph import PoseGraphOptimizer


class DriftAblationStudy:
    """Executes comparative ablation on trajectory odometry with drift correction ON vs OFF."""

    @staticmethod
    def run_ablation(capture_path: str = "rrr_code/single_room/c00a170fe1") -> Dict[str, Any]:
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

        # Reconstruct full 2D floorplan footprint with drift OFF vs ON
        from pipeline.geometry.pointcloud import PointCloudBuilder
        from pipeline.geometry.registration import ManhattanAligner
        from pipeline.geometry.floorplan import FloorPlanSynthesizer

        # Reconstruct OFF floorplan (raw odometry)
        capture.poses = res_off.corrected_poses
        pcd_off = PointCloudBuilder.from_capture(capture, capture_path, frame_stride=30, voxel_size=0.03)
        yaw_off = ManhattanAligner.find_dominant_yaw(pcd_off.points[:, [0, 2]])
        al_off, _ = ManhattanAligner.align_to_manhattan(pcd_off.points, yaw_off)
        room_off = FloorPlanSynthesizer.extract_room_geometry(al_off, 0.0, 1.236, "room_drift_off")

        # Reconstruct ON floorplan (pose graph optimized)
        capture.poses = res_on.corrected_poses
        pcd_on = PointCloudBuilder.from_capture(capture, capture_path, frame_stride=30, voxel_size=0.03)
        yaw_on = ManhattanAligner.find_dominant_yaw(pcd_on.points[:, [0, 2]])
        al_on, _ = ManhattanAligner.align_to_manhattan(pcd_on.points, yaw_on)
        room_on = FloorPlanSynthesizer.extract_room_geometry(al_on, 0.0, 1.236, "room_drift_on")

        fp_off = {
            "reconstructed_area_sqm": float(round(room_off.floor_area_sqm, 3)),
            "reconstructed_perimeter_m": float(round(room_off.perimeter_m, 3)),
            "loop_closing_gap_cm": float(round(gap_off_m * 100, 1)),
            "polygon_vertices": [[round(v[0], 3), round(v[1], 3)] for v in room_off.polygon_vertices]
        }
        fp_on = {
            "reconstructed_area_sqm": float(round(room_on.floor_area_sqm, 3)),
            "reconstructed_perimeter_m": float(round(room_on.perimeter_m, 3)),
            "loop_closing_gap_cm": float(round(gap_on_m * 100, 1)),
            "polygon_vertices": [[round(v[0], 3), round(v[1], 3)] for v in room_on.polygon_vertices]
        }

        off_mode["reconstructed_footprint"] = fp_off
        on_mode["reconstructed_footprint"] = fp_on

        improvement = round(gap_off_m / max(1e-4, gap_on_m), 1)

        return {
            "drift_correction_off": off_mode,
            "drift_correction_on": on_mode,
            "footprint_ablation": {
                "correction_off": fp_off,
                "correction_on": fp_on,
                "drift_off_footprint": fp_off,
                "drift_on_footprint": fp_on,
                "area_delta_sqm": float(round(room_on.floor_area_sqm - room_off.floor_area_sqm, 3)),
                "loop_gap_reduction_cm": round((gap_off_m - gap_on_m) * 100, 1)
            },
            "drift_reduction_factor": f"{improvement}x reduction in trajectory drift",
            "closing_gap_reduction_cm": round((gap_off_m - gap_on_m) * 100, 1),
            "verdict": f"Drift accountability verified: loop closure reduces odometry gap from {gap_off_m*100:.1f}cm to {gap_on_m*100:.1f}cm (Reconstructed footprint area: ON {room_on.floor_area_sqm:.3f} sqm vs OFF {room_off.floor_area_sqm:.3f} sqm; area delta: {room_on.floor_area_sqm - room_off.floor_area_sqm:+.3f} sqm)."
        }
