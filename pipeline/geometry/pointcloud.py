"""
pipeline.geometry.pointcloud
Vectorized 3D point cloud reconstruction, unprojection, and voxel filtering.
"""

from dataclasses import dataclass
from typing import Optional, Tuple, List
import numpy as np
from scipy.spatial.transform import Rotation as R

from pipeline.io.reader import CaptureData, SensorReader


@dataclass
class PointCloud:
    points: np.ndarray      # (N, 3) float32 [X, Y, Z]
    colors: Optional[np.ndarray] = None   # (N, 3) uint8 [R, G, B]
    normals: Optional[np.ndarray] = None  # (N, 3) float32

    def __len__(self) -> int:
        return len(self.points)


class PointCloudBuilder:
    """Builds filtered metric 3D point clouds from multi-frame sensor captures."""

    @staticmethod
    def unproject_depth(
        depth_m: np.ndarray,
        cam_matrix_full: np.ndarray,
        pose_t: np.ndarray,
        pose_quat: np.ndarray,
        conf: Optional[np.ndarray] = None,
        min_conf: int = 1,
        min_range: float = 0.3,
        max_range: float = 4.5,
        subsample_step: int = 2
    ) -> np.ndarray:
        """
        Unprojects a 2D depth map into world coordinates.
        cam_matrix_full is scaled to depth map resolution (e.g. 192x256 from 1440x1920).
        """
        h, w = depth_m.shape
        # Scale intrinsics to depth buffer resolution
        scale_x = w / 1920.0 if cam_matrix_full[0, 2] > 500 else 1.0
        scale_y = h / 1440.0 if cam_matrix_full[1, 2] > 400 else 1.0

        fx = cam_matrix_full[0, 0] * scale_x
        fy = cam_matrix_full[1, 1] * scale_y
        cx = cam_matrix_full[0, 2] * scale_x
        cy = cam_matrix_full[1, 2] * scale_y

        u, v = np.meshgrid(
            np.arange(0, w, subsample_step),
            np.arange(0, h, subsample_step)
        )

        d_sub = depth_m[::subsample_step, ::subsample_step]
        valid = (d_sub > min_range) & (d_sub < max_range)
        if conf is not None:
            c_sub = conf[::subsample_step, ::subsample_step]
            valid &= (c_sub >= min_conf)

        if not np.any(valid):
            return np.empty((0, 3), dtype=np.float32)

        z = d_sub[valid].astype(np.float32)
        x = (u[valid] - cx) * z / fx
        y = (v[valid] - cy) * z / fy

        pts_c = np.stack([x, y, z], axis=1)

        # Transform to world coordinates: P_w = R * P_c + t
        rot = R.from_quat(pose_quat).as_matrix().astype(np.float32)
        pts_w = (rot @ pts_c.T).T + pose_t
        return pts_w.astype(np.float32)

    @staticmethod
    def from_capture(
        capture: CaptureData,
        capture_dir: str,
        frame_stride: int = 15,
        voxel_size: float = 0.025,
        min_conf: int = 1
    ) -> PointCloud:
        """Constructs unified downsampled point cloud from LiDAR capture."""
        total_frames = len(capture.depth_frames)
        sampled_indices = list(range(0, total_frames, frame_stride))

        all_pts: List[np.ndarray] = []
        for idx in sampled_indices:
            depth_m, conf = SensorReader.load_depth_and_conf(capture_dir, idx)
            if depth_m is None:
                continue

            pose = capture.poses[idx] if idx < len(capture.poses) else None
            if pose is None:
                continue

            pts = PointCloudBuilder.unproject_depth(
                depth_m=depth_m,
                cam_matrix_full=capture.camera_matrix,
                pose_t=pose.t,
                pose_quat=pose.quat,
                conf=conf,
                min_conf=min_conf,
                min_range=0.35,
                max_range=4.2,
                subsample_step=3
            )
            if len(pts) > 0:
                all_pts.append(pts)

        if not all_pts:
            return PointCloud(points=np.empty((0, 3), dtype=np.float32))

        merged_pts = np.vstack(all_pts)
        downsampled_pts = PointCloudBuilder.voxel_downsample(merged_pts, voxel_size)
        cleaned_pts = PointCloudBuilder.remove_outliers(downsampled_pts, k_neighbors=12, std_ratio=1.8)

        return PointCloud(points=cleaned_pts)

    @staticmethod
    def voxel_downsample(points: np.ndarray, voxel_size: float = 0.025) -> np.ndarray:
        """Fast grid-based voxel centroid downsampling."""
        if len(points) == 0:
            return points
        # Voxel integer indices
        coords = np.floor(points / voxel_size).astype(np.int32)
        # Unique voxel keys
        _, unique_indices = np.unique(coords, axis=0, return_index=True)
        return points[unique_indices]

    @staticmethod
    def remove_outliers(points: np.ndarray, k_neighbors: int = 12, std_ratio: float = 1.8) -> np.ndarray:
        """Statistical outlier rejection via KD-Tree nearest neighbor distance."""
        if len(points) < k_neighbors * 2:
            return points
        from scipy.spatial import cKDTree
        tree = cKDTree(points)
        if len(points) > 15000:
            sample_idx = np.random.choice(len(points), 15000, replace=False)
            dists, _ = tree.query(points[sample_idx], k=k_neighbors, workers=-1)
            mean_dists = np.mean(dists[:, 1:], axis=1)
            thresh = np.mean(mean_dists) + std_ratio * np.std(mean_dists)
            dists_1nn, _ = tree.query(points, k=2, workers=-1)
            return points[dists_1nn[:, 1] <= thresh * 1.6]
        else:
            dists, _ = tree.query(points, k=k_neighbors, workers=-1)
            mean_dists = np.mean(dists[:, 1:], axis=1)
            thresh = np.mean(mean_dists) + std_ratio * np.std(mean_dists)
            return points[mean_dists <= thresh]
