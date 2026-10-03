"""
pipeline.geometry.video_tier
Dense feature tracking and multi-view stereo triangulation for Handheld Video Tier.
Reconstructs 3D metric spatial point clouds from handheld video sequences (with or without odometry).
"""

import os
from typing import Optional, List, Tuple
import cv2
import numpy as np
import pandas as pd
from scipy.spatial.transform import Rotation as R

from pipeline.geometry.pointcloud import PointCloud


class VideoReconstructor:
    """Reconstructs 3D spatial point clouds from handheld monocular video captures."""

    @staticmethod
    def reconstruct_from_video(
        capture_path: str,
        max_keyframes: int = 60,
        frame_stride: int = 30,
        min_baseline_m: float = 0.04
    ) -> PointCloud:
        """
        Extracts keyframes from video walkthrough, tracks 2D features via Lucas-Kanade optical flow,
        triangulates 3D points using camera projection matrices, and filters spatial outliers.
        """
        # Determine video file path
        if os.path.isdir(capture_path):
            mp4_candidates = [
                os.path.join(capture_path, f) for f in os.listdir(capture_path)
                if f.lower().endswith((".mp4", ".mov"))
            ]
            if not mp4_candidates:
                raise FileNotFoundError(f"No video file (.mp4/.mov) found in {capture_path}")
            video_path = mp4_candidates[0]
            capture_dir = capture_path
        else:
            video_path = capture_path
            capture_dir = os.path.dirname(capture_path)

        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise ValueError(f"Could not open video stream at {video_path}")

        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)) or 1920
        h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) or 1440

        # Load or calibrate camera intrinsics
        cam_matrix_path = os.path.join(capture_dir, "camera_matrix.csv")
        if os.path.exists(cam_matrix_path):
            cam_matrix = np.loadtxt(cam_matrix_path, delimiter=",").astype(np.float64)
        else:
            fx = fy = max(w, h) * 0.82
            cam_matrix = np.array([
                [fx, 0.0, w / 2.0],
                [0.0, fy, h / 2.0],
                [0.0, 0.0, 1.0]
            ], dtype=np.float64)

        # Check for odometry poses
        odom_path = os.path.join(capture_dir, "odometry.csv")
        has_odometry = os.path.exists(odom_path)
        odom_df = None
        if has_odometry:
            odom_df = pd.read_csv(odom_path)
            odom_df.columns = [c.strip() for c in odom_df.columns]

        # Extract sampled keyframes
        stride = max(5, min(frame_stride, total_frames // max_keyframes if total_frames > max_keyframes else 10))
        keyframe_indices = list(range(0, total_frames, stride))
        if len(keyframe_indices) > max_keyframes:
            keyframe_indices = np.linspace(0, total_frames - 1, max_keyframes, dtype=int).tolist()

        keyframes = []
        for kf_idx in keyframe_indices:
            cap.set(cv2.CAP_PROP_POS_FRAMES, int(kf_idx))
            ret, frame = cap.read()
            if ret and frame is not None:
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                keyframes.append((int(kf_idx), gray))
        cap.release()

        if len(keyframes) < 2:
            raise ValueError(f"Video contains insufficient readable keyframes ({len(keyframes)})")

        all_points_3d: List[np.ndarray] = []

        if has_odometry and odom_df is not None:
            # Trajectory-informed Multi-View Stereo Triangulation
            for i in range(len(keyframes) - 1):
                idx0, f0 = keyframes[i]
                idx1, f1 = keyframes[i + 1]

                if idx0 >= len(odom_df) or idx1 >= len(odom_df):
                    continue

                row0 = odom_df.iloc[idx0]
                t0 = np.array([row0['x'], row0['y'], row0['z']], dtype=np.float64)
                q0 = [row0['qx'], row0['qy'], row0['qz'], row0['qw']]
                R0 = R.from_quat(q0).as_matrix()

                row1 = odom_df.iloc[idx1]
                t1 = np.array([row1['x'], row1['y'], row1['z']], dtype=np.float64)
                q1 = [row1['qx'], row1['qy'], row1['qz'], row1['qw']]
                R1 = R.from_quat(q1).as_matrix()

                baseline = float(np.linalg.norm(t1 - t0))
                if baseline < min_baseline_m:
                    continue

                # Camera-to-world to world-to-camera projection
                R0_w2c = R0.T
                t0_w2c = -R0_w2c @ t0
                P0 = cam_matrix @ np.hstack([R0_w2c, t0_w2c.reshape(3, 1)])

                R1_w2c = R1.T
                t1_w2c = -R1_w2c @ t1
                P1 = cam_matrix @ np.hstack([R1_w2c, t1_w2c.reshape(3, 1)])

                # Detect salient corners in reference keyframe
                corners = cv2.goodFeaturesToTrack(f0, maxCorners=400, qualityLevel=0.01, minDistance=12)
                if corners is None or len(corners) < 10:
                    continue

                pts0 = corners.reshape(-1, 2)
                pts1, status, _ = cv2.calcOpticalFlowPyrLK(f0, f1, pts0, None, winSize=(21, 21), maxLevel=3)
                valid = (status.flatten() == 1)
                pts0_val = pts0[valid]
                pts1_val = pts1[valid]

                if len(pts0_val) < 8:
                    continue

                # Triangulate 3D points
                homo_pts = cv2.triangulatePoints(P0[:3], P1[:3], pts0_val.T.astype(np.float32), pts1_val.T.astype(np.float32))
                pts_3d = (homo_pts[:3] / homo_pts[3]).T

                # Depth sanity checks in camera frames
                pts_c0 = (R0_w2c @ pts_3d.T + t0_w2c.reshape(3, 1)).T
                pts_c1 = (R1_w2c @ pts_3d.T + t1_w2c.reshape(3, 1)).T

                valid_depth = (
                    (pts_c0[:, 2] > 0.3) & (pts_c0[:, 2] < 7.5) &
                    (pts_c1[:, 2] > 0.3) & (pts_c1[:, 2] < 7.5)
                )
                if np.any(valid_depth):
                    all_points_3d.append(pts_3d[valid_depth])

        else:
            # Monocular Visual Odometry & Epipolar Structure from Motion
            curr_R = np.eye(3, dtype=np.float64)
            curr_t = np.zeros((3, 1), dtype=np.float64)

            # Cumulative trajectory poses
            P_prev = cam_matrix @ np.hstack([curr_R, curr_t])

            for i in range(len(keyframes) - 1):
                idx0, f0 = keyframes[i]
                idx1, f1 = keyframes[i + 1]

                corners = cv2.goodFeaturesToTrack(f0, maxCorners=400, qualityLevel=0.01, minDistance=12)
                if corners is None or len(corners) < 15:
                    continue

                pts0 = corners.reshape(-1, 2)
                pts1, status, _ = cv2.calcOpticalFlowPyrLK(f0, f1, pts0, None, winSize=(21, 21), maxLevel=3)
                valid = (status.flatten() == 1)
                p0 = pts0[valid]
                p1 = pts1[valid]

                if len(p0) < 15:
                    continue

                E, inliers = cv2.findEssentialMat(p0, p1, cam_matrix, method=cv2.RANSAC, prob=0.999, threshold=1.0)
                if E is None:
                    continue

                inliers = inliers.flatten().astype(bool)
                p0_in = p0[inliers]
                p1_in = p1[inliers]

                if len(p0_in) < 10:
                    continue

                _, dR, dt, mask_pose = cv2.recoverPose(E, p0_in, p1_in, cam_matrix)
                # Nominal scale approximation for handheld video walking speed (~0.35 m per keyframe interval)
                dt_scaled = dt * 0.35

                # Update camera pose in world frame
                curr_t = curr_t + curr_R @ dt_scaled
                curr_R = curr_R @ dR

                R_w2c = curr_R.T
                t_w2c = -R_w2c @ curr_t
                P_curr = cam_matrix @ np.hstack([R_w2c, t_w2c])

                homo_pts = cv2.triangulatePoints(P_prev[:3], P_curr[:3], p0_in.T.astype(np.float32), p1_in.T.astype(np.float32))
                pts_3d = (homo_pts[:3] / homo_pts[3]).T

                pts_c0 = pts_3d[:, 2]
                valid_pts = (pts_c0 > 0.3) & (pts_c0 < 8.0)
                if np.any(valid_pts):
                    all_points_3d.append(pts_3d[valid_pts])

                P_prev = P_curr

        if not all_points_3d:
            raise ValueError("Optical flow feature tracking failed to triangulate valid 3D points from video.")

        raw_points = np.vstack(all_points_3d).astype(np.float32)

        # Statistical outlier removal: filter points exceeding 2.8 standard deviations from centroid
        centroid = np.mean(raw_points, axis=0)
        std_dev = np.std(raw_points, axis=0)
        inlier_mask = np.all(np.abs(raw_points - centroid) <= 2.8 * std_dev, axis=1)
        cleaned_points = raw_points[inlier_mask]

        if len(cleaned_points) < 150:
            cleaned_points = raw_points

        return PointCloud(points=cleaned_points)
