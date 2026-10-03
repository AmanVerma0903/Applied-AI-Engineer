"""
pipeline.io.reader
Multi-tier sensor data loader for LiDAR, Video, and Photo captures.
Supports Stray Scanner / ARKit formats, video streams, and multi-view photo folders.
"""

import os
import glob
from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple, Any

import cv2
import numpy as np
import pandas as pd


@dataclass
class Pose:
    timestamp: float
    frame_idx: int
    t: np.ndarray        # (3,) translation in meters
    quat: np.ndarray     # (4,) [qx, qy, qz, qw]
    intrinsics: Optional[np.ndarray] = None  # 3x3 K matrix if frame-varying


@dataclass
class LiDARFrame:
    index: int
    timestamp: float
    depth_m: np.ndarray       # (H, W) float32 in meters
    confidence: np.ndarray    # (H, W) uint8 {0, 1, 2}
    pose: Pose
    rgb_frame: Optional[np.ndarray] = None


@dataclass
class CaptureData:
    capture_id: str
    tier: str
    camera_matrix: np.ndarray  # 3x3 base camera matrix
    poses: List[Pose]
    depth_frames: List[LiDARFrame]
    video_path: Optional[str] = None
    photo_paths: Optional[List[str]] = None
    metadata: Dict[str, Any] = None


class SensorReader:
    """Robust loader for multi-tier spatial captures."""

    @staticmethod
    def load(capture_path: str, tier: str = "lidar") -> CaptureData:
        """Auto-detects format and loads capture data for the given tier."""
        capture_id = os.path.basename(os.path.normpath(capture_path))
        if tier == "lidar":
            return SensorReader.load_lidar(capture_path, capture_id)
        elif tier == "video":
            return SensorReader.load_video(capture_path, capture_id)
        elif tier == "photos":
            return SensorReader.load_photos(capture_path, capture_id)
        else:
            raise ValueError(f"Unknown tier: {tier}. Must be 'lidar', 'video', or 'photos'.")

    @staticmethod
    def load_lidar(capture_dir: str, capture_id: str = "capture_lidar") -> CaptureData:
        """Loads Stray Scanner / ARKit LiDAR directory."""
        cam_matrix_path = os.path.join(capture_dir, "camera_matrix.csv")
        if os.path.exists(cam_matrix_path):
            cam_matrix = np.loadtxt(cam_matrix_path, delimiter=",").astype(np.float32)
        else:
            # Default iPhone 15 Pro Wide LiDAR intrinsics
            cam_matrix = np.array([
                [1599.7, 0.0, 960.0],
                [0.0, 1599.7, 720.0],
                [0.0, 0.0, 1.0]
            ], dtype=np.float32)

        odom_path = os.path.join(capture_dir, "odometry.csv")
        poses = []
        if os.path.exists(odom_path):
            odom_df = pd.read_csv(odom_path)
            # Strip whitespace in column names
            odom_df.columns = [c.strip() for c in odom_df.columns]
            for _, row in odom_df.iterrows():
                frame_idx = int(row["frame"])
                t = np.array([row["x"], row["y"], row["z"]], dtype=np.float32)
                quat = np.array([row["qx"], row["qy"], row["qz"], row["qw"]], dtype=np.float32)
                poses.append(Pose(
                    timestamp=float(row.get("timestamp", 0.0)),
                    frame_idx=frame_idx,
                    t=t,
                    quat=quat
                ))

        depth_files = sorted(glob.glob(os.path.join(capture_dir, "depth", "*.png")))
        conf_files = sorted(glob.glob(os.path.join(capture_dir, "confidence", "*.png")))
        video_path = os.path.join(capture_dir, "rgb.mp4")
        if not os.path.exists(video_path):
            video_path = None

        frames = []
        # Lazy index: create lightweight frame references
        for i, df in enumerate(depth_files):
            cf = conf_files[i] if i < len(conf_files) else None
            p = poses[i] if i < len(poses) else None
            if p is not None:
                frames.append(LiDARFrame(
                    index=i,
                    timestamp=p.timestamp,
                    depth_m=None,      # Loaded on demand or in batch
                    confidence=None,
                    pose=p
                ))

        return CaptureData(
            capture_id=capture_id,
            tier="lidar",
            camera_matrix=cam_matrix,
            poses=poses,
            depth_frames=frames,
            video_path=video_path,
            metadata={
                "depth_files": depth_files,
                "confidence_files": conf_files,
                "total_frames": len(depth_files),
                "has_video": video_path is not None,
            }
        )

    @staticmethod
    def load_depth_and_conf(capture_dir: str, frame_idx: int) -> Tuple[np.ndarray, np.ndarray]:
        """Loads and converts depth (mm -> m) and confidence for a specific frame."""
        depth_path = os.path.join(capture_dir, "depth", f"{frame_idx:06d}.png")
        conf_path = os.path.join(capture_dir, "confidence", f"{frame_idx:06d}.png")

        if not os.path.exists(depth_path):
            return None, None

        depth_raw = cv2.imread(depth_path, cv2.IMREAD_UNCHANGED)
        depth_m = depth_raw.astype(np.float32) / 1000.0

        if os.path.exists(conf_path):
            conf = cv2.imread(conf_path, cv2.IMREAD_UNCHANGED)
        else:
            conf = np.ones_like(depth_raw, dtype=np.uint8) * 2

        return depth_m, conf

    @staticmethod
    def load_video(capture_path: str, capture_id: str = "capture_video") -> CaptureData:
        """Loads handheld video clip for Video Tier."""
        video_file = capture_path
        if os.path.isdir(capture_path):
            mp4s = glob.glob(os.path.join(capture_path, "*.mp4")) + glob.glob(os.path.join(capture_path, "*.mov"))
            video_file = mp4s[0] if mp4s else None

        if video_file is None or not os.path.exists(video_file):
            raise FileNotFoundError(f"No video file found in {capture_path}")

        cap = cv2.VideoCapture(video_file)
        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        cap.release()

        # Calibrated nominal intrinsics for iPhone video (approx 26mm equiv)
        fx = fy = max(w, h) * 0.85
        cam_matrix = np.array([
            [fx, 0.0, w / 2.0],
            [0.0, fy, h / 2.0],
            [0.0, 0.0, 1.0]
        ], dtype=np.float32)

        return CaptureData(
            capture_id=capture_id,
            tier="video",
            camera_matrix=cam_matrix,
            poses=[],
            depth_frames=[],
            video_path=video_file,
            metadata={
                "frame_count": frame_count,
                "fps": fps,
                "resolution": (w, h),
                "duration_sec": frame_count / fps if fps > 0 else 0
            }
        )

    @staticmethod
    def load_photos(capture_dir: str, capture_id: str = "capture_photos") -> CaptureData:
        """Loads multi-view photos folder for Photos Tier (2-8 stills per room)."""
        exts = ["*.jpg", "*.jpeg", "*.png", "*.heic"]
        photo_files = []
        for ext in exts:
            photo_files.extend(glob.glob(os.path.join(capture_dir, ext)))
            photo_files.extend(glob.glob(os.path.join(capture_dir, ext.upper())))
        photo_files = sorted(photo_files)

        if not photo_files:
            raise FileNotFoundError(f"No photo files found in {capture_dir}")

        # Read first image to determine aspect ratio and resolution
        img0 = cv2.imread(photo_files[0])
        h, w = img0.shape[:2] if img0 is not None else (3024, 4032)
        fx = fy = max(w, h) * 0.75
        cam_matrix = np.array([
            [fx, 0.0, w / 2.0],
            [0.0, fy, h / 2.0],
            [0.0, 0.0, 1.0]
        ], dtype=np.float32)

        return CaptureData(
            capture_id=capture_id,
            tier="photos",
            camera_matrix=cam_matrix,
            poses=[],
            depth_frames=[],
            photo_paths=photo_files,
            metadata={
                "photo_count": len(photo_files),
                "resolution": (w, h)
            }
        )
