"""
pipeline.geometry.planes
RANSAC 3D plane segmentation for floor, ceiling, and vertical walls.
"""

from dataclasses import dataclass
from typing import List, Tuple, Optional
import numpy as np


@dataclass
class PlaneModel:
    normal: np.ndarray     # (3,) unit normal [a, b, c]
    d: float               # plane offset: ax + by + cz + d = 0
    inliers_mask: np.ndarray
    plane_type: str        # 'floor', 'ceiling', 'wall'
    elevation_m: float     # representative Y coordinate or offset

    @property
    def equation(self) -> Tuple[float, float, float, float]:
        return (float(self.normal[0]), float(self.normal[1]), float(self.normal[2]), float(self.d))


class RansacPlaneDetector:
    """Robust RANSAC plane extraction for indoor spatial scans."""

    @staticmethod
    def fit_plane_ransac(
        points: np.ndarray,
        distance_threshold: float = 0.025,
        max_iterations: int = 400,
        expected_normal: Optional[np.ndarray] = None,
        normal_angle_tol_deg: float = 20.0
    ) -> Optional[Tuple[np.ndarray, float, np.ndarray]]:
        """
        Fits a 3D plane using RANSAC.
        Returns (unit_normal, d, inlier_indices).
        """
        num_points = len(points)
        if num_points < 3:
            return None

        best_inliers = np.array([], dtype=int)
        best_normal = None
        best_d = 0.0

        for _ in range(max_iterations):
            idx = np.random.choice(num_points, 3, replace=False)
            p1, p2, p3 = points[idx]

            v1 = p2 - p1
            v2 = p3 - p1
            n = np.cross(v1, v2)
            norm = np.linalg.norm(n)
            if norm < 1e-6:
                continue
            n = n / norm

            if expected_normal is not None:
                cos_angle = np.abs(np.dot(n, expected_normal))
                if cos_angle < np.cos(np.deg2rad(normal_angle_tol_deg)):
                    continue

            d = -np.dot(n, p1)
            dists = np.abs(points @ n + d)
            inliers = np.where(dists < distance_threshold)[0]

            if len(inliers) > len(best_inliers):
                best_inliers = inliers
                best_normal = n
                best_d = d

        if len(best_inliers) < 20:
            return None

        # Least squares refinement on inliers
        inlier_pts = points[best_inliers]
        centroid = inlier_pts.mean(axis=0)
        uu, dd, vv = np.linalg.svd(inlier_pts - centroid)
        refined_normal = vv[2]
        if expected_normal is not None and np.dot(refined_normal, expected_normal) < 0:
            refined_normal = -refined_normal
        refined_d = -np.dot(refined_normal, centroid)

        final_dists = np.abs(points @ refined_normal + refined_d)
        final_inliers = np.where(final_dists < distance_threshold)[0]

        return refined_normal, refined_d, final_inliers

    @staticmethod
    def extract_horizontal_planes(
        points: np.ndarray,
        dist_thresh: float = 0.02
    ) -> Tuple[Optional[PlaneModel], Optional[PlaneModel]]:
        """
        Extracts floor and ceiling planes assuming Y is approximately vertical.
        Returns (floor_plane, ceiling_plane).
        """
        if len(points) == 0:
            return None, None

        up_vector = np.array([0.0, 1.0, 0.0], dtype=np.float32)

        # Bottom 15% of points for floor
        y_vals = points[:, 1]
        y_min = np.percentile(y_vals, 1)
        floor_candidates = points[y_vals < y_min + 0.35]

        floor_plane = None
        if len(floor_candidates) >= 50:
            res = RansacPlaneDetector.fit_plane_ransac(
                floor_candidates,
                distance_threshold=dist_thresh,
                expected_normal=up_vector,
                normal_angle_tol_deg=15.0
            )
            if res is not None:
                n, d, inliers = res
                # Inlier mask relative to full points
                dists = np.abs(points @ n + d)
                mask = dists < dist_thresh
                floor_elevation = -d / n[1]
                floor_plane = PlaneModel(
                    normal=n,
                    d=d,
                    inliers_mask=mask,
                    plane_type="floor",
                    elevation_m=float(floor_elevation)
                )

        # Top 20% of points for ceiling
        y_max = np.percentile(y_vals, 98)
        ceiling_candidates = points[y_vals > y_max - 0.40]

        ceiling_plane = None
        if len(ceiling_candidates) >= 50:
            res = RansacPlaneDetector.fit_plane_ransac(
                ceiling_candidates,
                distance_threshold=dist_thresh,
                expected_normal=up_vector,
                normal_angle_tol_deg=15.0
            )
            if res is not None:
                n, d, inliers = res
                dists = np.abs(points @ n + d)
                mask = dists < dist_thresh
                ceil_elevation = -d / n[1]
                ceiling_plane = PlaneModel(
                    normal=n,
                    d=d,
                    inliers_mask=mask,
                    plane_type="ceiling",
                    elevation_m=float(ceil_elevation)
                )

        return floor_plane, ceiling_plane
