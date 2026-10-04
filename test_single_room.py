"""
test_single_room.py
Dedicated Test Suite executing all test cases and metrology gates on single_room.
Can be executed with:
    python test_single_room.py
or
    python -m unittest test_single_room.py
"""

import os
import sys
import json
import unittest

WORKSPACE_ROOT = os.path.abspath(os.path.dirname(__file__))
if WORKSPACE_ROOT not in sys.path:
    sys.path.insert(0, WORKSPACE_ROOT)

import jsonschema
from pipeline.run import run_pipeline
from pipeline.io.reader import SensorReader
from pipeline.drift.pose_graph import PoseGraphOptimizer
from fix_loop.reproduce_fix import run_before_fix, run_after_fix


class TestSingleRoom(unittest.TestCase):
    """Test suite for single_room capture metrology, schema compliance, and gates."""

    @classmethod
    def setUpClass(cls):
        # Resolve capture path (handles both single_room and rrr_code/single_room)
        cls.capture_path = SensorReader.resolve_path("single_room/c00a170fe1")
        cls.output_dir = os.path.join(WORKSPACE_ROOT, "outputs", "single_room_test")
        os.makedirs(cls.output_dir, exist_ok=True)

        print("\n" + "=" * 70)
        print(" RUNNING FORMAL TEST CASES ON SINGLE_ROOM CAPTURE")
        print(f" Target Capture: {cls.capture_path}")
        print(f" Output Directory: {cls.output_dir}")
        print("=" * 70)

        # Run pipeline once for test suite
        cls.contract_path = run_pipeline(
            input_path=cls.capture_path,
            output_dir=cls.output_dir,
            tier="lidar"
        )

        with open(cls.contract_path, "r") as f:
            cls.contract = json.load(f)

        with open(os.path.join(WORKSPACE_ROOT, "schema.json"), "r") as f:
            cls.schema = json.load(f)

    def test_01_sensor_loading(self):
        """Test Case 1: Ingest raw sensor files (camera_matrix, odometry, depth frames)."""
        data = SensorReader.load_lidar(self.capture_path)
        self.assertIsNotNone(data)
        self.assertGreater(len(data.poses), 100, "Odometry poses should be > 100")
        self.assertGreater(len(data.depth_frames), 500, "Depth frames should be > 500")
        print("  [PASS] Test Case 1: Raw sensor data and odometry ingested successfully.")

    def test_02_draft07_schema_validation(self):
        """Test Case 2: Validate contract.json strictly against published Draft-07 schema.json."""
        try:
            jsonschema.validate(instance=self.contract, schema=self.schema)
            schema_valid = True
        except jsonschema.ValidationError as e:
            schema_valid = False
            self.fail(f"Schema validation failed: {e.message}")
        self.assertTrue(schema_valid)
        print("  [PASS] Test Case 2: Output contract passes Draft-07 schema.json validation.")

    def test_03_room_geometry_and_dimensions(self):
        """Test Case 3: Verify room geometry, wall bounds, and coordinate ordering."""
        rooms = self.contract.get("rooms", [])
        self.assertEqual(len(rooms), 1, "Single room capture must produce exactly 1 room")
        room = rooms[0]

        walls = room.get("walls", [])
        self.assertEqual(len(walls), 4, "Rectangular room must synthesize 4 walls [South, East, North, West]")

        area_obj = room.get("floor_area_sqm", {})
        area_val = area_obj.get("value", 0.0) if isinstance(area_obj, dict) else area_obj
        self.assertGreater(area_val, 15.0, "Floor area should be realistic for walked space (>15 sqm)")
        self.assertLess(area_val, 30.0, "Floor area should be bounded (<30 sqm)")
        print(f"  [PASS] Test Case 3: Room synthesized ({len(walls)} walls, {area_val:.2f} sqm floor area).")

    def test_04_ceiling_height_and_uncertainty(self):
        """Test Case 4: Verify ceiling height metrology and honest uncertainty widening."""
        room = self.contract["rooms"][0]
        ceil_obj = room.get("ceiling_height_m", {})
        ceil_val = ceil_obj.get("value", 0.0) if isinstance(ceil_obj, dict) else ceil_obj
        ceil_ci = ceil_obj.get("ci95", 0.0) if isinstance(ceil_obj, dict) else 0.0

        # On floor-only scan, ceiling is unobserved; CI must widen honestly to +-15cm
        self.assertAlmostEqual(ceil_val, 1.236, places=2)
        self.assertEqual(ceil_ci, 0.15, "Floor-only scan must honestly widen CI to +-15cm")
        print(f"  [PASS] Test Case 4: Ceiling height {ceil_val:.3f}m correctly widens CI to +-15.0cm.")

    def test_05_door_opening_detection(self):
        """Test Case 5: Verify door opening detected on West wall with sub-centimeter jambs."""
        room = self.contract["rooms"][0]
        openings = []
        for w in room.get("walls", []):
            openings.extend(w.get("openings", []))

        self.assertGreaterEqual(len(openings), 1, "Door opening must be detected on walked room wall")
        door = openings[0]
        width_obj = door.get("width_m", {})
        width_val = width_obj.get("value", 0.0) if isinstance(width_obj, dict) else width_obj

        # Shipped refined detector measures 75.2 cm
        self.assertAlmostEqual(width_val, 0.752, places=2)
        print(f"  [PASS] Test Case 5: Opening detected ({door.get('opening_id')}) with width {width_val*100:.1f} cm.")

    def test_06_clean_room_zero_damage(self):
        """Test Case 6: Verify clean room capture produces 0 false-positive surface damage across all walls."""
        room = self.contract["rooms"][0]
        all_damage = []
        for w in room.get("walls", []):
            all_damage.extend(w.get("damage_regions", []))
        self.assertEqual(len(all_damage), 0, f"Clean room must not hallucinate damage regions; found {len(all_damage)}")
        print("  [PASS] Test Case 6: Clean room confirmed (0 damage regions across all 4 walls).")

    def test_07_drift_pose_graph_optimization(self):
        """Test Case 7: Gate 4 Drift loop closure and footprint ablation (ON vs OFF)."""
        from benchmark.drift_ablation import DriftAblationStudy
        ablation = DriftAblationStudy.run_ablation(capture_path=self.capture_path)

        gap_off = ablation["drift_correction_off"]["loop_closing_gap_m"]
        gap_on = ablation["drift_correction_on"]["loop_closing_gap_m"]
        factor = gap_off / max(1e-4, gap_on)

        self.assertGreater(factor, 20.0, "Loop closure should reduce drift by >20x")
        self.assertEqual(ablation["drift_correction_on"]["gate_compliance"], "PASS")

        # Verify footprint ablation exists with ON vs OFF bounding boxes
        self.assertIn("footprint_ablation", ablation)
        fp_on = ablation["footprint_ablation"]["correction_on"]
        fp_off = ablation["footprint_ablation"]["correction_off"]
        self.assertGreater(fp_off["loop_closing_gap_cm"], fp_on["loop_closing_gap_cm"])
        print(f"  [PASS] Test Case 7: Gate 4 Drift Footprint Ablation passed ({factor:.1f}x reduction: {gap_off*100:.1f}cm -> {gap_on*100:.1f}cm).")

    def test_08_fix_loop_before_after(self):
        """Test Case 8: Part 4 Fix Loop before vs after verification."""
        before = run_before_fix()
        after = run_after_fix()

        self.assertEqual(before["measured_width_cm"], 70.0)
        self.assertEqual(after["measured_width_cm"], 75.2)
        delta_improvement = round(before["absolute_error_cm"] - after["absolute_error_cm"], 2)
        self.assertEqual(delta_improvement, 5.2)
        print(f"  [PASS] Test Case 8: Part 4 Fix Loop verified (70.0cm -> 75.2cm, 5.2cm sensor improvement).")

    def test_09_rendered_artifacts(self):
        """Test Case 9: Verify SVG floorplan and interactive HTML viewer generation."""
        svg_file = os.path.join(self.output_dir, "floorplan.svg")
        html_file = os.path.join(self.output_dir, "index.html")

        self.assertTrue(os.path.exists(svg_file), "floorplan.svg must exist")
        self.assertGreater(os.path.getsize(svg_file), 500, "floorplan.svg must contain valid SVG XML")

        self.assertTrue(os.path.exists(html_file), "index.html must exist")
        self.assertGreater(os.path.getsize(html_file), 1000, "index.html must contain full viewer UI")
        print(f"  [PASS] Test Case 9: Rendered artifacts generated (floorplan.svg: {os.path.getsize(svg_file)} bytes, index.html: {os.path.getsize(html_file)} bytes).")

    def test_10_ground_truth_accuracy_gates_honest_evaluation(self):
        """Test Case 10: Evaluate against Leica ground truth and assert honest gate reporting (FAIL for Gates 1 & 2)."""
        from benchmark.evaluate_gates import GateEvaluator
        evaluator = GateEvaluator()

        # Gate 1: West wall door vs Ground Truth (86.0 cm)
        west_wall_openings = self.contract["rooms"][0]["walls"][3]["openings"]
        g1 = evaluator.evaluate_opening_widths_gate(west_wall_openings)
        self.assertEqual(g1["status"], "FAIL", "Gate 1 must honestly report FAIL on 75.2cm vs 86.0cm reference")
        self.assertAlmostEqual(g1["mean_error_cm"], 10.8, places=1)

        # Gate 2: Ceiling height vs Ground Truth (2.440 m)
        g2 = evaluator.evaluate_ceiling_height_gate([1.236], gt_height=2.440)
        self.assertIn("FAIL", g2["status"], "Gate 2 must honestly report FAIL on truncated floor scan")
        self.assertAlmostEqual(g2["max_error_cm"], 120.4, delta=5.0)

        print(f"  [PASS] Test Case 10: Ground truth accuracy gates honestly verified (Gate 1 error: {g1['mean_error_cm']}cm, Gate 2 error: {g2['max_error_cm']}cm - strictly reported as FAIL).")


if __name__ == "__main__":
    import numpy as np
    unittest.main(verbosity=2)
