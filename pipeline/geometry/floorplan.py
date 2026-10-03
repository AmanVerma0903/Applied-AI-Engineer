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
    def extract_room_geometry(
        points_aligned: np.ndarray,
        floor_elev: float,
        ceil_elev: float,
        room_id: str = "room_01",
        room_name: str = "Main Room"
    ) -> RoomGeometry:
        """
        Slices points at mid-wall height, detects bounding wall boundaries,
        and constructs a dimensioned closed polygon.
        """
        # Height bounds for wall slice (avoiding floor trim and ceiling mouldings)
        slice_min = floor_elev + 0.35
        slice_max = ceil_elev - 0.35

        mask = (points_aligned[:, 1] >= slice_min) & (points_aligned[:, 1] <= slice_max)
        wall_pts = points_aligned[mask]

        if len(wall_pts) < 100:
            # Fallback envelope
            x_min, x_max = float(points_aligned[:, 0].min()), float(points_aligned[:, 0].max())
            z_min, z_max = float(points_aligned[:, 2].min()), float(points_aligned[:, 2].max())
        else:
            # Robust density percentiles for wall boundaries
            x_min = float(np.percentile(wall_pts[:, 0], 2.0))
            x_max = float(np.percentile(wall_pts[:, 0], 98.0))
            z_min = float(np.percentile(wall_pts[:, 2], 2.0))
            z_max = float(np.percentile(wall_pts[:, 2], 98.0))

        ceiling_height = float(ceil_elev - floor_elev)

        # Build 4 primary walls in CCW order: South, East, North, West
        v0 = (x_min, z_min)
        v1 = (x_max, z_min)
        v2 = (x_max, z_max)
        v3 = (x_min, z_max)

        poly_coords = [v0, v1, v2, v3]
        poly = Polygon(poly_coords)
        floor_area = float(poly.area)
        perimeter = float(poly.length)

        # Construct WallSegments
        walls = [
            WallSegment(
                wall_id=f"{room_id}_W1_South",
                start_2d=v0,
                end_2d=v1,
                length_m=float(abs(x_max - x_min)),
                height_m=ceiling_height,
                normal_2d=(0.0, -1.0)
            ),
            WallSegment(
                wall_id=f"{room_id}_W2_East",
                start_2d=v1,
                end_2d=v2,
                length_m=float(abs(z_max - z_min)),
                height_m=ceiling_height,
                normal_2d=(1.0, 0.0)
            ),
            WallSegment(
                wall_id=f"{room_id}_W3_North",
                start_2d=v2,
                end_2d=v3,
                length_m=float(abs(x_max - x_min)),
                height_m=ceiling_height,
                normal_2d=(0.0, 1.0)
            ),
            WallSegment(
                wall_id=f"{room_id}_W4_West",
                start_2d=v3,
                end_2d=v0,
                length_m=float(abs(z_max - z_min)),
                height_m=ceiling_height,
                normal_2d=(-1.0, 0.0)
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
