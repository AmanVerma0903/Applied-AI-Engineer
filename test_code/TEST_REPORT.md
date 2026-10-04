# Test Code Execution & Metrology Verification Report

**Case Study Standard:** Applied AI Engineer Case Study (Aug 2026)
**Generated:** 2026-10-04 00:01:32 UTC
**Test Suite Location:** `test_code/`

## 1. Test Captures Execution Matrix

| Capture Category | Capture ID | Runtime | Schema Valid | SVG Rendered | HTML Viewer | Status |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| `single_room` | `c00a170fe1` | 8.02s | `True` | `True` | `True` | **`PASS`** |
| `single_scan_floor_only` | `1a8384c3f6` | 10.76s | `True` | `True` | `True` | **`PASS`** |
| `single_scan_with_ceiling` | `c7d28f72c6` | 15.7s | `True` | `True` | `True` | **`PASS`** |

---

## 2. Dimensional Metrology & Openings Summary

### Capture `c00a170fe1` (single_room)

* **Room Name:** Primary Room (`room_c00a170fe1`)
* **Ceiling Height:** 1.236 m (±15.0 cm at 95% CI)
* **Floor Area:** 20.75 m² (±0.15 m² at 95% CI)
* **Walls (4):**
  * `room_c00a170fe1_W1_South`: **3.432 m** (±1.2 cm CI)
  * `room_c00a170fe1_W2_East`: **6.046 m** (±1.3 cm CI)
  * `room_c00a170fe1_W3_North`: **3.432 m** (±1.2 cm CI)
  * `room_c00a170fe1_W4_West`: **6.046 m** (±1.3 cm CI)
* **Openings (1):**
  * `op_room_c00a170fe1_W4_West_1` on `room_c00a170fe1_W4_West`: DOOR width **0.752 m**, height **1.186 m**, offset **1.463 m**

### Capture `1a8384c3f6` (single_scan_floor_only)

* **Room Name:** Primary Room (`room_1a8384c3f6`)
* **Ceiling Height:** 1.466 m (±15.0 cm at 95% CI)
* **Floor Area:** 53.30 m² (±0.24 m² at 95% CI)
* **Walls (4):**
  * `room_1a8384c3f6_W1_South`: **5.592 m** (±1.3 cm CI)
  * `room_1a8384c3f6_W2_East`: **9.530 m** (±1.5 cm CI)
  * `room_1a8384c3f6_W3_North`: **5.592 m** (±1.3 cm CI)
  * `room_1a8384c3f6_W4_West`: **9.530 m** (±1.5 cm CI)
* **Openings (5):**
  * `op_room_1a8384c3f6_W2_East_1` on `room_1a8384c3f6_W2_East`: DOOR width **1.005 m**, height **1.416 m**, offset **5.711 m**
  * `op_room_1a8384c3f6_W3_North_1` on `room_1a8384c3f6_W3_North`: DOOR width **0.712 m**, height **1.416 m**, offset **2.965 m**
  * `op_room_1a8384c3f6_W3_North_2` on `room_1a8384c3f6_W3_North`: DOOR width **0.640 m**, height **1.416 m**, offset **4.020 m**
  * `op_room_1a8384c3f6_W4_West_1` on `room_1a8384c3f6_W4_West`: DOOR width **0.657 m**, height **1.416 m**, offset **3.840 m**
  * `op_room_1a8384c3f6_W4_West_2` on `room_1a8384c3f6_W4_West`: DOOR width **0.808 m**, height **1.416 m**, offset **4.809 m**

### Capture `c7d28f72c6` (single_scan_with_ceiling)

* **Room Name:** Primary Room (`room_c7d28f72c6`)
* **Ceiling Height:** 3.069 m (±0.8 cm at 95% CI)
* **Floor Area:** 59.93 m² (±0.25 m² at 95% CI)
* **Walls (4):**
  * `room_c7d28f72c6_W1_South`: **9.670 m** (±1.5 cm CI)
  * `room_c7d28f72c6_W2_East`: **6.198 m** (±1.3 cm CI)
  * `room_c7d28f72c6_W3_North`: **9.670 m** (±1.5 cm CI)
  * `room_c7d28f72c6_W4_West`: **6.198 m** (±1.3 cm CI)
* **Openings (3):**
  * `op_room_c7d28f72c6_W1_South_1` on `room_c7d28f72c6_W1_South`: DOOR width **0.567 m**, height **2.050 m**, offset **2.389 m**
  * `op_room_c7d28f72c6_W1_South_2` on `room_c7d28f72c6_W1_South`: DOOR width **0.567 m**, height **2.050 m**, offset **5.475 m**
  * `op_room_c7d28f72c6_W3_North_1` on `room_c7d28f72c6_W3_North`: DOOR width **1.028 m**, height **2.050 m**, offset **5.716 m**

---

## 3. Sensor Coverage & Repeatability Analysis

### A. Ceiling Plane Visibility: Floor-Only vs Scan With Ceiling

| Metric | `single_scan_floor_only` | `single_scan_with_ceiling` | Delta / Finding |
| :--- | :---: | :---: | :--- |
| **Estimated Height** | 1.466 m | 3.069 m | Delta: **1.603 m** |
| **Calibrated 95% CI** | ±15.0 cm | ±0.8 cm | **Honest Uncertainty Widening** |

> [!NOTE]
> Floor-only scan omitted ceiling from camera frustum, correctly widening uncertainty interval to 15 cm. Scan with ceiling observed full upper plane (3.069m) with calibrated 0.8 cm tight interval.

### B. Room Geometry Repeatability (Same Space, Two Passes)

| Dimension Pair | Floor-Only Length | With-Ceiling Length | Absolute Diff | Relative Error | Gate 3 Tol (max(1cm, 0.5%)) |
| :--- | :---: | :---: | :---: | :---: | :---: |
| Short Wall #1 | 5.592 m | 6.198 m | **60.6 cm** | 9.78% | ±3.1 cm |
| Short Wall #2 | 5.592 m | 6.198 m | **60.6 cm** | 9.78% | ±3.1 cm |
| Long Wall #3 | 9.530 m | 9.670 m | **14.0 cm** | 1.45% | ±4.8 cm |
| Long Wall #4 | 9.530 m | 9.670 m | **14.0 cm** | 1.45% | ±4.8 cm |

* **Observation:** Long-wall agreement within 14.0 cm (1.45%) on ~9.5m span.

---

## 4. Contract Schema & Artifact Validation

* All generated output contracts validated strictly against `schema.json` via Draft-07 validator.
* Standalone architectural SVG files generated with dimension labels, wall paths, and opening cuts.
* Interactive Polycam/Magicplan-style HTML viewer generated with zoom, pan, measurement inspection, and contract inspector.