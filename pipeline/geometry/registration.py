"""
pipeline.geometry.registration
Manhattan frame alignment and orientation canonicalization.
"""

from typing import Tuple
import numpy as np


class ManhattanAligner:
    """Aligns room point clouds to canonical Manhattan world coordinate axes."""

    @staticmethod
    def find_dominant_yaw(points_2d: np.ndarray, num_bins: int = 180) -> float:
        """
        Determines the dominant architectural yaw angle (mod 90 degrees)
        using fast 2D gradient / line orientation histogram.
        """
        if len(points_2d) < 50:
            return 0.0

        # Subsample for blazing fast sub-second execution
        if len(points_2d) > 3000:
            indices = np.random.choice(len(points_2d), 3000, replace=False)
            pts = points_2d[indices]
        else:
            pts = points_2d

        # Sample pairwise vectors between close neighbors
        from scipy.spatial import cKDTree
        tree = cKDTree(pts)
        pairs = tree.query_pairs(r=0.30, output_type="ndarray")
        if len(pairs) < 50:
            cov = np.cov(pts.T)
            eigvals, eigvecs = np.linalg.eigh(cov)
            return float(np.arctan2(eigvecs[1, 1], eigvecs[0, 1]))

        # Limit pairs for instant processing
        if len(pairs) > 10000:
            pair_idx = np.random.choice(len(pairs), 10000, replace=False)
            pairs = pairs[pair_idx]

        diffs = pts[pairs[:, 1]] - pts[pairs[:, 0]]
        angles = np.arctan2(diffs[:, 1], diffs[:, 0])

        # Fold into [0, pi/2)
        angles_mod = np.mod(angles, np.pi / 2.0)
        hist, bin_edges = np.histogram(angles_mod, bins=num_bins, range=(0, np.pi / 2.0))
        peak_idx = np.argmax(hist)
        dominant_angle = (bin_edges[peak_idx] + bin_edges[peak_idx + 1]) / 2.0
        return float(dominant_angle)

    @staticmethod
    def align_to_manhattan(
        points_3d: np.ndarray,
        yaw_rad: float
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Rotates 3D points around Y-axis by -yaw_rad.
        Returns (rotated_points, 3x3_rotation_matrix).
        """
        c = np.cos(-yaw_rad)
        s = np.sin(-yaw_rad)
        R_mat = np.array([
            [c, 0.0, -s],
            [0.0, 1.0, 0.0],
            [s, 0.0, c]
        ], dtype=np.float32)

        rotated_pts = (R_mat @ points_3d.T).T
        return rotated_pts, R_mat
