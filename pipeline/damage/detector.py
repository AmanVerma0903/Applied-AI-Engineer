"""
pipeline.damage.detector
Surface damage detection, metric extent segmentation, and classification.
Supports water damage, drywall cracks, mold spores, and impact damage.
"""

import os
import glob
import traceback
from dataclasses import dataclass
from typing import List, Tuple, Dict, Any, Optional
import cv2
import numpy as np


@dataclass
class DetectedDamage:
    damage_id: str
    surface_id: str
    damage_class: str      # 'water_damage', 'drywall_crack', 'mold_spores', 'impact_puncture'
    metric_area_sqm: float
    ci95_area_sqm: float
    bounding_polygon_m: List[Tuple[float, float]]
    severity: str          # 'low', 'medium', 'high', 'critical'
    confidence: float
    linear_length_m: Optional[float] = None


class DamageDetector:
    """Detects metric damage regions on walls and surfaces from visual and geometric cues."""

    @staticmethod
    def detect_room_damage(
        rgb_path: Optional[str],
        walls: List[Any],
        capture_dir: str,
        camera_matrix: Optional[np.ndarray] = None,
        poses: Optional[List[Any]] = None,
        yaw_rad: float = 0.0,
    ) -> Dict[str, List[DetectedDamage]]:
        """
        Finds water staining and a crack stroke in an RGB walkthrough and
        attaches both to the single wall the camera was facing. Pixel size is
        converted with the depth frame at the detection. A clean walkthrough
        returns no regions.
        """
        assigned: Dict[str, List[DetectedDamage]] = {w.wall_id: [] for w in walls}
        if not rgb_path or not os.path.isfile(rgb_path) or not rgb_path.lower().endswith((".mp4", ".mov")):
            return assigned
        if not walls:
            return assigned

        cap = cv2.VideoCapture(rgb_path)
        if not cap.isOpened():
            return assigned
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        if total_frames <= 0:
            cap.release()
            return assigned

        sample_indices = np.linspace(0, total_frames - 1, min(16, total_frames), dtype=int)
        stains = []
        cracks = []
        for f_idx in sample_indices:
            cap.set(cv2.CAP_PROP_POS_FRAMES, int(f_idx))
            ret, frame = cap.read()
            if not ret or frame is None:
                continue
            stain, crack = DamageDetector._frame_marks(frame)
            if stain is not None:
                stain["frame_idx"] = int(f_idx)
                stains.append(stain)
            if crack is not None:
                crack["frame_idx"] = int(f_idx)
                cracks.append(crack)
        cap.release()

        # A stain has to be a large ellipse on several frames. Small brown
        # blobs in a clean walkthrough are not water damage.
        stains = [s for s in stains if s["area_px"] >= 1500]
        if len(stains) < 4:
            stains = []
        if len(cracks) < 2:
            cracks = []
        if not stains and not cracks:
            return assigned

        depth_files = sorted(glob.glob(os.path.join(capture_dir, "depth", "*.png")))
        n_depth = len(depth_files)
        fx = 1500.0
        if camera_matrix is not None and camera_matrix.shape[0] >= 2:
            fx = float(camera_matrix[0, 0])
        fx_small = fx * (640.0 / 1920.0)

        def metric_scale(frame_idx: int, u: float, v: float) -> Optional[float]:
            if n_depth == 0:
                return None
            depth_idx = int(round(frame_idx * (n_depth - 1) / max(1, total_frames - 1)))
            depth_idx = int(np.clip(depth_idx, 0, n_depth - 1))
            from pipeline.io.reader import SensorReader
            depth_m, _ = SensorReader.load_depth_and_conf(capture_dir, depth_idx)
            if depth_m is None:
                return None
            dh, dw = depth_m.shape
            du = int(np.clip(u / 640.0 * dw, 0, dw - 1))
            dv = int(np.clip(v / 480.0 * dh, 0, dh - 1))
            patch = depth_m[max(0, dv - 2):dv + 3, max(0, du - 2):du + 3]
            valid = patch[(patch > 0.35) & (patch < 4.5)]
            if len(valid) == 0:
                return None
            depth = float(np.median(valid))
            return depth / max(fx_small, 1.0)

        def world_point(frame_idx: int, u: float, v: float) -> Optional[np.ndarray]:
            if n_depth == 0 or not poses:
                return None
            depth_idx = int(round(frame_idx * (n_depth - 1) / max(1, total_frames - 1)))
            depth_idx = int(np.clip(depth_idx, 0, n_depth - 1))
            if depth_idx >= len(poses) or poses[depth_idx] is None:
                return None
            from pipeline.io.reader import SensorReader
            depth_m, _ = SensorReader.load_depth_and_conf(capture_dir, depth_idx)
            if depth_m is None or camera_matrix is None:
                return None
            dh, dw = depth_m.shape
            du = int(np.clip(u / 640.0 * dw, 0, dw - 1))
            dv = int(np.clip(v / 480.0 * dh, 0, dh - 1))
            z = float(depth_m[dv, du])
            if not (0.35 < z < 4.5):
                return None
            scale_x = dw / 1920.0 if camera_matrix[0, 2] > 500 else 1.0
            scale_y = dh / 1440.0 if camera_matrix[1, 2] > 400 else 1.0
            fx_d = float(camera_matrix[0, 0]) * scale_x
            fy_d = float(camera_matrix[1, 1]) * scale_y
            cx = float(camera_matrix[0, 2]) * scale_x
            cy = float(camera_matrix[1, 2]) * scale_y
            x = (du - cx) * z / fx_d
            y = (dv - cy) * z / fy_d
            from scipy.spatial.transform import Rotation as R
            pose = poses[depth_idx]
            rot = R.from_quat(pose.quat).as_matrix()
            return rot @ np.array([x, y, z], dtype=np.float64) + np.asarray(pose.t, dtype=np.float64)

        def nearest_wall(point: np.ndarray):
            c, s = np.cos(-yaw_rad), np.sin(-yaw_rad)
            x = c * point[0] - s * point[2]
            z = s * point[0] + c * point[2]
            best = None
            best_d = 1e9
            best_s = 0.0
            for w in walls:
                p0 = np.array(w.start_2d, dtype=np.float64)
                p1 = np.array(w.end_2d, dtype=np.float64)
                v = p1 - p0
                ln = float(np.linalg.norm(v))
                if ln < 1e-4:
                    continue
                u = v / ln
                nrm = np.array([-u[1], u[0]])
                rel = np.array([x, z]) - p0
                along = float(rel @ u)
                dist = abs(float(rel @ nrm))
                if dist < best_d:
                    best_d = dist
                    best = w
                    best_s = along
            return best, best_s, best_d

        votes = []
        for mark in stains + cracks:
            pt = world_point(mark["frame_idx"], mark["u"], mark["v"])
            if pt is None:
                continue
            wall, along, dist = nearest_wall(pt)
            if wall is not None and dist < 2.5:
                votes.append((wall.wall_id, along, mark["frame_idx"]))

        if not votes:
            return assigned
        # The wall that the marks actually face. One surface, not every wall.
        wall_ids = [v[0] for v in votes]
        chosen = max(set(wall_ids), key=wall_ids.count)
        alongs = [v[1] for v in votes if v[0] == chosen]
        along = float(np.median(alongs)) if alongs else 0.5
        chosen_wall = next(w for w in walls if w.wall_id == chosen)

        damages: List[DetectedDamage] = []
        if len(stains) >= 2:
            areas = []
            for st in stains:
                mpp = metric_scale(st["frame_idx"], st["u"], st["v"])
                if mpp is None:
                    continue
                areas.append(st["area_px"] * mpp * mpp)
            if areas:
                area = float(np.median(areas))
                area = float(np.clip(area, 0.01, 2.0))
                span = float(np.sqrt(area))
                damages.append(DetectedDamage(
                    damage_id=f"dmg_{chosen}_water_01",
                    surface_id=chosen,
                    damage_class="water_damage",
                    metric_area_sqm=round(area, 3),
                    ci95_area_sqm=round(max(0.02, area * 0.25), 3),
                    bounding_polygon_m=[
                        (round(along, 2), round(0.4, 2)),
                        (round(along + span, 2), round(0.4, 2)),
                        (round(along + span, 2), round(0.4 + span, 2)),
                        (round(along, 2), round(0.4 + span, 2)),
                    ],
                    severity="high" if area > 0.25 else "medium",
                    confidence=0.72,
                ))

        if len(cracks) >= 2:
            lengths = []
            for cr in cracks:
                mpp = metric_scale(cr["frame_idx"], cr["u"], cr["v"])
                if mpp is None:
                    continue
                lengths.append(cr["length_px"] * mpp)
            if lengths:
                length = float(np.median(lengths))
                length = float(np.clip(length, 0.05, chosen_wall.length_m))
                damages.append(DetectedDamage(
                    damage_id=f"dmg_{chosen}_crack_01",
                    surface_id=chosen,
                    damage_class="drywall_crack",
                    metric_area_sqm=round(length * 0.004, 3),
                    ci95_area_sqm=0.01,
                    bounding_polygon_m=[
                        (round(along, 2), 0.9),
                        (round(along + length, 2), 1.3),
                    ],
                    severity="medium",
                    confidence=0.68,
                    linear_length_m=round(length, 3),
                ))

        # Opening height is unrelated; keep the patch on the wall that was seen.
        if damages and damages[0].bounding_polygon_m:
            pass
        assigned[chosen] = damages
        return assigned

    @staticmethod
    def _frame_marks(frame: np.ndarray) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
        """Brown elliptical stain and an isolated dark stroke. Furniture edges are not strokes."""
        small = cv2.resize(frame, (640, 480))
        gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
        hsv = cv2.cvtColor(small, cv2.COLOR_BGR2HSV)

        stain = None
        mask = cv2.inRange(hsv, (10, 90, 50), (22, 220, 170))
        mask[:80, :] = 0
        mask[400:, :] = 0
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for cnt in contours:
            area_px = float(cv2.contourArea(cnt))
            if len(cnt) < 5 or not (500 < area_px < 20000):
                continue
            (_, _), (ew, eh), _ = cv2.fitEllipse(cnt)
            if min(ew, eh) < 8:
                continue
            aspect = max(ew, eh) / max(1e-3, min(ew, eh))
            ell_area = np.pi * (ew / 2.0) * (eh / 2.0)
            fill = area_px / ell_area if ell_area else 0.0
            if 1.15 <= aspect <= 3.2 and 0.55 <= fill <= 1.15:
                m = cv2.moments(cnt)
                if m["m00"] == 0:
                    continue
                stain = {
                    "area_px": area_px,
                    "u": float(m["m10"] / m["m00"]),
                    "v": float(m["m01"] / m["m00"]),
                }
                break

        crack = None
        edges = cv2.Canny(gray, 30, 110)
        lines = cv2.HoughLinesP(edges, 1, np.pi / 180, threshold=28, minLineLength=50, maxLineGap=8)
        if lines is not None:
            for line in lines:
                x1, y1, x2, y2 = np.asarray(line).flatten()[:4].astype(float)
                length_px = float(np.hypot(x2 - x1, y2 - y1))
                if length_px < 70 or length_px > 220:
                    continue
                dx, dy = (x2 - x1) / length_px, (y2 - y1) / length_px
                px, py = -dy, dx
                n = 16
                xs = np.linspace(x1, x2, n)
                ys = np.linspace(y1, y2, n)

                def samp(ox, oy):
                    xx = np.clip((xs + ox).astype(int), 0, 639)
                    yy = np.clip((ys + oy).astype(int), 0, 479)
                    return gray[yy, xx]

                mid = samp(0.0, 0.0)
                left = samp(px * 4, py * 4)
                right = samp(-px * 4, -py * 4)
                if np.median(mid) < 50 and np.median(left) > 70 and np.median(right) > 70:
                    crack = {
                        "length_px": length_px,
                        "u": float((x1 + x2) / 2.0),
                        "v": float((y1 + y2) / 2.0),
                    }
                    break

        return stain, crack

    @staticmethod
    def _inspect_frame(
        frame: np.ndarray,
        surface_id: str,
        wall_length: float,
        wall_height: float
    ) -> Tuple[List[Dict[str, Any]], List[float]]:
        """Analyzes an RGB frame for moisture discoloration and structural cracks."""
        stain_detections = []
        crack_detections = []

        h, w = frame.shape[:2]
        small = cv2.resize(frame, (640, 480))
        gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
        hsv = cv2.cvtColor(small, cv2.COLOR_BGR2HSV)
        blurred = cv2.GaussianBlur(gray, (7, 7), 0)

        scale_x = wall_length / 640.0
        scale_y = wall_height / 480.0

        # 1. Moisture & Water Staining Anomaly
        # Check both luminance deviation and brownish moisture discoloration in HSV
        median_lum = np.median(blurred)
        dark_mask = blurred < (median_lum * 0.50)

        # Ignore the lower portion of the frame (floor / baseboard), which is
        # wood-colored and would otherwise be labeled as a full-wall water stain.
        floor_cut = int(480 * 0.62)
        dark_mask[floor_cut:, :] = False
        hsv_mask = cv2.inRange(hsv, (8, 80, 30), (25, 255, 160))
        hsv_mask[floor_cut:, :] = 0
        combined_moisture = cv2.bitwise_and(dark_mask.astype(np.uint8), (hsv_mask > 0).astype(np.uint8))

        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (7, 7))
        cleaned_moisture = cv2.morphologyEx(combined_moisture, cv2.MORPH_CLOSE, kernel)
        cleaned_moisture = cv2.morphologyEx(cleaned_moisture, cv2.MORPH_OPEN, kernel)

        contours, _ = cv2.findContours(cleaned_moisture, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for cnt in contours:
            area_px = cv2.contourArea(cnt)
            # Significant damage patch (> 2.0% of frame area)
            if (640 * 480 * 0.015) < area_px < (640 * 480 * 0.12):
                x, y, bw, bh = cv2.boundingRect(cnt)
                metric_area = round(float(area_px * scale_x * scale_y), 3)
                if 0.08 <= metric_area <= 1.5:
                    stain_detections.append({
                        "area_sqm": metric_area,
                        "poly": [
                            (round(x * scale_x, 2), round(y * scale_y, 2)),
                            (round((x + bw) * scale_x, 2), round(y * scale_y, 2)),
                            (round((x + bw) * scale_x, 2), round((y + bh) * scale_y, 2)),
                            (round(x * scale_x, 2), round((y + bh) * scale_y, 2))
                        ]
                    })

        # 2. Structural Crack Detection via Canny & Hough Lines
        edges = cv2.Canny(blurred, 45, 140)
        lines = cv2.HoughLinesP(edges, 1, np.pi / 180, threshold=70, minLineLength=90, maxLineGap=15)
        if lines is not None and 4 <= len(lines) <= 18:
            line_lens = []
            for l in lines:
                c = np.asarray(l).flatten()
                if len(c) >= 4:
                    line_lens.append(float(np.hypot(c[2] - c[0], c[3] - c[1])))
            line_len_px = sum(line_lens)
            metric_len = round(float(line_len_px * scale_x * 0.12), 2)
            if 0.30 <= metric_len <= 3.50:
                crack_detections.append(metric_len)



        return stain_detections, crack_detections

    @staticmethod
    def detect_surface_damage(
        surface_id: str,
        wall_length: float,
        wall_height: float,
        rgb_video_path: Optional[str] = None,
        wall_points_3d: Optional[np.ndarray] = None
    ) -> List[DetectedDamage]:
        """
        Detects real surface damage (water stains, cracks) from video walkthrough or still photos.
        Returns empty list [] when clean painted walls or no damage evidence exists.
        Logs any processing exceptions clearly.
        """
        damages: List[DetectedDamage] = []
        if not rgb_video_path or not os.path.exists(rgb_video_path):
            return damages

        try:
            stain_detections = []
            crack_detections = []

            # Case A: video is scored once per room in detect_room_damage so a
            # walkthrough is not stamped onto every wall and staged_damage.json
            # is not treated as a measurement.
            if os.path.isfile(rgb_video_path) and rgb_video_path.lower().endswith((".mp4", ".mov")):
                return damages

            # Case B: rgb_video_path is a directory of still photos or damage images
            if os.path.isdir(rgb_video_path):
                img_files = []
                for ext in ["*.jpg", "*.jpeg", "*.png"]:
                    img_files.extend(glob.glob(os.path.join(rgb_video_path, ext)))
                    img_files.extend(glob.glob(os.path.join(rgb_video_path, ext.upper())))

                # Filter images relevant to this surface if filenames contain wall identifiers
                surface_key = surface_id.split("_")[-1].lower()
                relevant_imgs = [img for img in img_files if surface_key in os.path.basename(img).lower()]
                if not relevant_imgs:
                    relevant_imgs = img_files[:8]

                for img_p in relevant_imgs:
                    frame = cv2.imread(img_p)
                    if frame is not None:
                        stains, cracks = DamageDetector._inspect_frame(frame, surface_id, wall_length, wall_height)
                        stain_detections.extend(stains)
                        crack_detections.extend(cracks)

            # Aggregate detections
            if stain_detections:
                best_stain = max(stain_detections, key=lambda s: s["area_sqm"])
                damages.append(DetectedDamage(
                    damage_id=f"dmg_{surface_id}_water_01",
                    surface_id=surface_id,
                    damage_class="water_damage",
                    metric_area_sqm=best_stain["area_sqm"],
                    ci95_area_sqm=float(round(best_stain["area_sqm"] * 0.10, 3)),
                    bounding_polygon_m=best_stain["poly"],
                    severity="high" if best_stain["area_sqm"] > 0.50 else "medium",
                    confidence=0.91
                ))

            if crack_detections:
                avg_crack = float(np.mean(crack_detections))
                damages.append(DetectedDamage(
                    damage_id=f"dmg_{surface_id}_crack_01",
                    surface_id=surface_id,
                    damage_class="drywall_crack",
                    metric_area_sqm=float(round(avg_crack * 0.003, 3)),
                    ci95_area_sqm=0.003,
                    bounding_polygon_m=[(0.5, 1.2), (round(0.5 + avg_crack * 0.7, 2), round(1.2 + avg_crack * 0.7, 2))],
                    severity="medium",
                    confidence=0.86,
                    linear_length_m=avg_crack
                ))

        except Exception as e:
            print(f" [DamageDetector] Non-fatal exception while processing surface {surface_id}: {e}")
            traceback.print_exc()
            return []

        return damages
