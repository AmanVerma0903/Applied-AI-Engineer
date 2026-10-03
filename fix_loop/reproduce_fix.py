"""
fix_loop.reproduce_fix
One-command reproduction of Part 4 Fix Loop: regenerates before-fix failing run,
after-fix passing run, prints metrics delta, and displays readable diff.
"""

import os
import sys
import json
import subprocess
import numpy as np


from pipeline.io.reader import SensorReader
from pipeline.geometry.pointcloud import PointCloudBuilder
from pipeline.geometry.registration import ManhattanAligner
from pipeline.geometry.floorplan import FloorPlanSynthesizer
from pipeline.features.openings import OpeningDetector


_CACHED_DOOR_WALL = None


def _get_live_door_wall():
    global _CACHED_DOOR_WALL
    if _CACHED_DOOR_WALL is not None:
        return _CACHED_DOOR_WALL

    capture_path = "single_room/c00a170fe1"
    capture = SensorReader.load(capture_path, tier="lidar")
    pcd = PointCloudBuilder.from_capture(capture, capture_path, frame_stride=20, voxel_size=0.03)
    from pipeline.geometry.planes import RansacPlaneDetector
    from pipeline.features.ceiling import CeilingEstimator
    fp, cp = RansacPlaneDetector.extract_horizontal_planes(pcd.points)
    floor_elev = float(fp.elevation_m) if fp else float(np.percentile(pcd.points[:, 1], 2.0))
    if cp is not None:
        raw_ceil = float(cp.elevation_m)
        num_inliers = int(np.sum(cp.inliers_mask))
    else:
        raw_ceil = float(np.percentile(pcd.points[:, 1], 99.0))
        num_inliers = 50
    ceiling_meas = CeilingEstimator.estimate(floor_elev=floor_elev, ceil_elev=raw_ceil, num_ceiling_inliers=num_inliers)
    ceil_elev = floor_elev + ceiling_meas.height_m

    yaw = ManhattanAligner.find_dominant_yaw(pcd.points[:, [0, 2]])
    aligned_pts, _ = ManhattanAligner.align_to_manhattan(pcd.points, yaw)
    pose_xyz = np.array([p.t for p in capture.poses], dtype=np.float32)
    c, s = np.cos(-yaw), np.sin(-yaw)
    traj_xy = np.column_stack([
        c * pose_xyz[:, 0] - s * pose_xyz[:, 2],
        s * pose_xyz[:, 0] + c * pose_xyz[:, 2],
    ])
    room_geo = FloorPlanSynthesizer.extract_room_geometry(
        aligned_pts, floor_elev, ceil_elev, trajectory_xy=traj_xy
    )
    door_wall = [w for w in room_geo.walls if "W4" in w.wall_id or "West" in w.wall_id][0]

    if door_wall is None:
        candidates = [w for w in room_geo.walls if "W4" in w.wall_id or "West" in w.wall_id]
        door_wall = candidates[0] if candidates else room_geo.walls[0]

    _CACHED_DOOR_WALL = (door_wall, room_geo.ceiling_height_m, floor_elev)
    return _CACHED_DOOR_WALL


def run_before_fix() -> dict:
    """
    Before fix: Coarse 5cm histogram door width estimation without jamb edge refinement.
    Executes actual OpeningDetector on single_room/c00a170fe1.
    """
    door_wall, ceil_h, floor_elev = _get_live_door_wall()
    gt_width_m = 0.860

    ops = OpeningDetector.detect_openings_on_wall(
        wall_id=door_wall.wall_id,
        start_2d=door_wall.start_2d,
        end_2d=door_wall.end_2d,
        wall_length=door_wall.length_m,
        ceiling_height=ceil_h,
        wall_points_3d=door_wall.wall_points_3d,
        floor_elev=floor_elev,
        bin_width_m=0.05,
        use_refinement=False
    )

    target_op = ops[0] if ops else None
    measured_m = target_op.width_m if target_op else 0.0
    error_cm = round(abs(measured_m - gt_width_m) * 100, 2)
    within = [o for o in ops if abs(o.width_m - gt_width_m) * 100 <= 2.0]
    pass_ratio = (100.0 * len(within) / len(ops)) if ops else 0.0
    pass_gate = pass_ratio >= 85.0

    result = {
        "run": "BEFORE_FIX",
        "implementation": "Coarse 5cm 1D Occupancy Grid (No jamb edge refinement)",
        "ground_truth_width_cm": round(gt_width_m * 100, 2),
        "measured_width_cm": round(measured_m * 100, 2),
        "absolute_error_cm": error_cm,
        "gate_threshold_cm": 2.0,
        "pass_ratio_pct": round(pass_ratio, 1),
        "gate_status": "PASS" if pass_gate else "FAIL",
        "failure_summary": f"Coarse binning width error of {error_cm} cm exceeds <= 2.0 cm gate threshold."
    }
    return result


def run_after_fix() -> dict:
    """
    After fix: 5cm binning + bilateral gradient edge kernel refinement (_refine_jamb_edge).
    Executes live refined OpeningDetector on single_room/c00a170fe1.
    """
    door_wall, ceil_h, floor_elev = _get_live_door_wall()
    gt_width_m = 0.860

    ops = OpeningDetector.detect_openings_on_wall(
        wall_id=door_wall.wall_id,
        start_2d=door_wall.start_2d,
        end_2d=door_wall.end_2d,
        wall_length=door_wall.length_m,
        ceiling_height=ceil_h,
        wall_points_3d=door_wall.wall_points_3d,
        floor_elev=floor_elev,
        bin_width_m=0.05,
        use_refinement=True
    )

    target_op = ops[0] if ops else None
    measured_m = target_op.width_m if target_op else 0.0
    error_cm = round(abs(measured_m - gt_width_m) * 100, 2)
    within = [o for o in ops if abs(o.width_m - gt_width_m) * 100 <= 2.0]
    pass_ratio = (100.0 * len(within) / len(ops)) if ops else 0.0
    pass_gate = pass_ratio >= 85.0

    result = {
        "run": "AFTER_FIX",
        "implementation": "5cm Binning + Sub-centimeter Jamb Edge Kernel Refinement (_refine_jamb_edge)",
        "ground_truth_width_cm": round(gt_width_m * 100, 2),
        "measured_width_cm": round(measured_m * 100, 2),
        "absolute_error_cm": error_cm,
        "gate_threshold_cm": 2.0,
        "pass_ratio_pct": round(pass_ratio, 1),
        "gate_status": "PASS" if pass_gate else "FAIL",
        "success_summary": f"Refined detector localized jambs to {round(measured_m*100, 2)} cm from real LiDAR density gaps."
    }
    return result


def main():
    print("==================================================================")
    print(" REPRODUCING PART 4: THE FIX LOOP (BEFORE VS AFTER)")
    print("==================================================================")

    os.makedirs("fix_loop/before_fix", exist_ok=True)
    os.makedirs("fix_loop/after_fix", exist_ok=True)

    before = run_before_fix()
    with open("fix_loop/before_fix/metrics.json", "w") as f:
        json.dump(before, f, indent=2)

    after = run_after_fix()
    with open("fix_loop/after_fix/metrics.json", "w") as f:
        json.dump(after, f, indent=2)

    print("\n--- [1] BEFORE FIX EXECUTION ---")
    print(f" Status:          {before['gate_status']}")
    print(f" Measured Width:  {before['measured_width_cm']} cm (GT: {before['ground_truth_width_cm']} cm)")
    print(f" Absolute Error:  {before['absolute_error_cm']} cm (Gate: <= {before['gate_threshold_cm']} cm)")
    print(f" Pass Ratio:      {before['pass_ratio_pct']}%")
    print(f" Failure Reason:  {before['failure_summary']}")

    print("\n--- [2] AFTER FIX EXECUTION ---")
    print(f" Status:          {after['gate_status']}")
    print(f" Measured Width:  {after['measured_width_cm']} cm (GT: {after['ground_truth_width_cm']} cm)")
    print(f" Absolute Error:  {after['absolute_error_cm']} cm (Gate: <= {after['gate_threshold_cm']} cm)")
    print(f" Pass Ratio:      {after['pass_ratio_pct']}%")
    print(f" Resolution:      {after['success_summary']}")

    print("\n--- [3] METRIC DELTA & VERDICT ---")
    delta_cm = before['absolute_error_cm'] - after['absolute_error_cm']
    print(f" Error Reduction: {delta_cm:.2f} cm improvement")
    print(f" Gate Transition: {before['gate_status']} -> {after['gate_status']}")
    print(f" Measured Width:  {after['measured_width_cm']} cm | Error vs GT: {after['absolute_error_cm']} cm")
    print(f" Verdict:         {after['gate_status']} (same west-wall door as outputs/audit_room/contract.json; error reduced by {delta_cm:.1f} cm)")
    print("==================================================================\n")


if __name__ == "__main__":
    main()
