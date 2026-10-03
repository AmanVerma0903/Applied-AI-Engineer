"""
pipeline.geometry.floorplan
2D wall boundary extraction, polygon closure, and floor area computation.
"""

from dataclasses import dataclass, field
from typing import List, Tuple, Dict, Any, Optional
import numpy as np
from shapely.geometry import Polygon, LineString


@dataclass
class WallSegment:
    wall_id: str
    start_2d: Tuple[float, float]
    end_2d: Tuple[float, float]
    length_m: float
    height_m: float
    normal_2d: Tuple[float, float]
    thickness_m: float = 0.12
    openings: List[Dict[str, Any]] = field(default_factory=list)
    damage_regions: List[Dict[str, Any]] = field(default_factory=list)
    wall_points_3d: Optional[np.ndarray] = None


@dataclass
class RoomGeometry:
    room_id: str
    name: str
    polygon_vertices: List[Tuple[float, float]]
    walls: List[WallSegment]
    floor_area_sqm: float
    perimeter_m: float
    ceiling_height_m: float
    floor_elevation_m: float
    ceiling_elevation_m: float


class FloorPlanSynthesizer:
    """Extracts 2D floor plans from aligned 3D spatial points."""

    @staticmethod
    def _fit_plane_1d(coords: np.ndarray, search_min: float, search_max: float, bin_w: float = 0.03) -> float:
        """Finds prominent 1D plane coordinate via histogram peak and local weighted average."""
        sub = coords[(coords >= search_min) & (coords <= search_max)]
        if len(sub) < 30:
            return float(np.median(coords)) if len(coords) > 0 else (search_min + search_max) / 2.0
        nbins = max(3, int(np.ceil((search_max - search_min) / bin_w)))
        hist, edges = np.histogram(sub, bins=nbins, range=(search_min, search_max))
        peak_idx = int(np.argmax(hist))
        low_idx = max(0, peak_idx - 1)
        high_idx = min(len(hist), peak_idx + 2)
        centers = 0.5 * (edges[:-1] + edges[1:])
        weights = hist[low_idx:high_idx]
        if np.sum(weights) == 0:
            return float(centers[peak_idx])
        return float(np.average(centers[low_idx:high_idx], weights=weights))

    @staticmethod
    def _outer_peak(coords: np.ndarray, side: str) -> float:
        """Leftmost or rightmost histogram peak with real wall support."""
        lo = float(np.percentile(coords, 1.0))
        hi = float(np.percentile(coords, 99.0))
        if hi - lo < 0.4 or len(coords) < 30:
            return lo if side == "min" else hi
        bin_w = 0.08
        nbins = max(16, int(np.ceil((hi - lo) / bin_w)))
        hist, edges = np.histogram(coords, bins=nbins, range=(lo, hi))
        thresh = max(40.0, 0.10 * float(hist.max()))
        peaks = np.where(hist >= thresh)[0]
        if len(peaks) == 0:
            return lo if side == "min" else hi
        ordered = list(peaks if side == "min" else peaks[::-1])
        chosen = int(ordered[0])
        bin_m = (hi - lo) / max(1, nbins)
        for nxt in ordered[1:]:
            a, b = sorted((chosen, int(nxt)))
            valley = hist[a + 1:b]
            gap_m = (b - a) * bin_m
            # A deep gap means the extreme peak is the next room seen through a doorway.
            if len(valley) and float(valley.max()) < 0.35 * float(hist[chosen]) and gap_m > 0.60:
                chosen = int(nxt)
                continue
            break
        return FloorPlanSynthesizer._fit_plane_1d(
            coords,
            float(edges[chosen]),
            float(edges[min(chosen + 1, len(edges) - 1)]),
        )

    @staticmethod
    def extract_room_geometry(
        points_aligned: np.ndarray,
        floor_elev: float,
        ceil_elev: float,
        room_id: str = "room_01",
        room_name: str = "Main Room",
        trajectory_xy: Optional[np.ndarray] = None
    ) -> RoomGeometry:
        """
        Slices points at mid-wall height, fits vertical wall planes along Manhattan axes,
        associates 3D points within 0.20m to each wall segment, and constructs a dimensioned closed polygon.
        """
        slice_min = floor_elev + 0.20
        slice_max = ceil_elev - 0.20

        mask = (points_aligned[:, 1] >= slice_min) & (points_aligned[:, 1] <= slice_max)
        wall_pts = points_aligned[mask]
        # Keep the room the camera walked, not the next room seen through a doorway.
        if trajectory_xy is not None and len(trajectory_xy) >= 10 and len(wall_pts) > 0:
            tmin = trajectory_xy.min(axis=0) - 1.15
            tmax = trajectory_xy.max(axis=0) + 1.15
            inside = (
                (wall_pts[:, 0] >= tmin[0]) & (wall_pts[:, 0] <= tmax[0]) &
                (wall_pts[:, 2] >= tmin[1]) & (wall_pts[:, 2] <= tmax[1])
            )
            if int(np.sum(inside)) > 100:
                wall_pts = wall_pts[inside]

        if len(wall_pts) < 100:
            x_min, x_max = float(points_aligned[:, 0].min()), float(points_aligned[:, 0].max())
            z_min, z_max = float(points_aligned[:, 2].min()), float(points_aligned[:, 2].max())
        else:
            # Dominant walked-room walls. The sparse tail beyond a doorway is a
            # neighboring space, so the fit stays on the high-density envelope.
            x_pts = wall_pts[:, 0]
            z_pts = wall_pts[:, 2]
            x_max = FloorPlanSynthesizer._fit_plane_1d(x_pts, float(np.percentile(x_pts, 85.0)), float(np.percentile(x_pts, 99.5)))
            z_max = FloorPlanSynthesizer._fit_plane_1d(z_pts, float(np.percentile(z_pts, 85.0)), float(np.percentile(z_pts, 99.5)))
            z_min = FloorPlanSynthesizer._fit_plane_1d(z_pts, float(np.percentile(z_pts, 0.5)), float(np.percentile(z_pts, 15.0)))
            x_min = FloorPlanSynthesizer._fit_plane_1d(x_pts, float(np.percentile(x_pts, 0.5)), float(np.percentile(x_pts, 15.0)))

        ceiling_height = float(max(0.1, ceil_elev - floor_elev))

        # Build 4 primary walls in CCW order: South, East, North, West
        v0 = (float(x_min), float(z_min))
        v1 = (float(x_max), float(z_min))
        v2 = (float(x_max), float(z_max))
        v3 = (float(x_min), float(z_max))

        poly_coords = [v0, v1, v2, v3]
        poly = Polygon(poly_coords)
        floor_area = float(poly.area)
        perimeter = float(poly.length)

        # Helper to extract wall-associated 3D points (orthogonal distance <= 0.20m)
        def get_wall_associated_points(p_start: Tuple[float, float], p_end: Tuple[float, float]) -> np.ndarray:
            p0 = np.array(p_start)
            p1 = np.array(p_end)
            v = p1 - p0
            v_norm = np.linalg.norm(v)
            if v_norm < 1e-4:
                return np.empty((0, 3), dtype=np.float32)
            u = v / v_norm
            n = np.array([-u[1], u[0]])
            pts_2d = points_aligned[:, [0, 2]]
            diff = pts_2d - p0
            s = diff @ u
            d = np.abs(diff @ n)
            in_wall = (d <= 0.20) & (s >= -0.10) & (s <= v_norm + 0.10)
            return points_aligned[in_wall]

        w1_pts = get_wall_associated_points(v0, v1)
        w2_pts = get_wall_associated_points(v1, v2)
        w3_pts = get_wall_associated_points(v2, v3)
        w4_pts = get_wall_associated_points(v3, v0)

        # Construct WallSegments with associated 3D points
        walls = [
            WallSegment(
                wall_id=f"{room_id}_W1_South",
                start_2d=v0,
                end_2d=v1,
                length_m=float(abs(x_max - x_min)),
                height_m=ceiling_height,
                normal_2d=(0.0, -1.0),
                wall_points_3d=w1_pts
            ),
            WallSegment(
                wall_id=f"{room_id}_W2_East",
                start_2d=v1,
                end_2d=v2,
                length_m=float(abs(z_max - z_min)),
                height_m=ceiling_height,
                normal_2d=(1.0, 0.0),
                wall_points_3d=w2_pts
            ),
            WallSegment(
                wall_id=f"{room_id}_W3_North",
                start_2d=v2,
                end_2d=v3,
                length_m=float(abs(x_max - x_min)),
                height_m=ceiling_height,
                normal_2d=(0.0, 1.0),
                wall_points_3d=w3_pts
            ),
            WallSegment(
                wall_id=f"{room_id}_W4_West",
                start_2d=v3,
                end_2d=v0,
                length_m=float(abs(z_max - z_min)),
                height_m=ceiling_height,
                normal_2d=(-1.0, 0.0),
                wall_points_3d=w4_pts
            )
        ]

        return RoomGeometry(
            room_id=room_id,
            name=room_name,
            polygon_vertices=poly_coords,
            walls=walls,
            floor_area_sqm=floor_area,
            perimeter_m=perimeter,
            ceiling_height_m=ceiling_height,
            floor_elevation_m=floor_elev,
            ceiling_elevation_m=ceil_elev
        )
