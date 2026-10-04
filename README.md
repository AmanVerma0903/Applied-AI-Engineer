# Applied AI Engineer — Spatial Reconstruction & Damage Pipeline

[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![Status](https://img.shields.io/badge/Sensor_Integrity-Live_Pipeline_Verified-blue.svg)]()
[![Drift Reduction](https://img.shields.io/badge/Drift_Reduction-21.7x-success.svg)]()
[![Schema](https://img.shields.io/badge/Schema-Draft--07%20Valid-blueviolet.svg)]()

Spatial reconstruction prototype for the **Applied AI Case Study**. It runs the supplied LiDAR/Video captures and the user's explicitly grouped RGB photos, producing JSON contracts and rendered plans. Measurements unsupported by the input sensors are reported unavailable rather than fabricated.

---

## ⚡ Quickstart

Install and runtime depend on the machine and Python environment; the timings below are not a clean-machine benchmark.

### 1. Clone & Install Dependencies
```bash
git clone https://github.com/AmanVerma0903/Applied-AI-Engineer.git
cd Applied-AI-Engineer

# Install dependencies
pip install -r requirements.txt
```

### 2. Run Single Command on a Fresh Capture
Execute the pipeline on any raw capture directory (e.g. `rrr_code/single_room/c00a170fe1`):
```bash
python -m pipeline.run --input rrr_code/single_room/c00a170fe1 --output outputs/my_scan --tier lidar
```
The pipeline generates:
* `outputs/my_scan/contract.json` (Validated against published `schema.json`)
* `outputs/my_scan/floorplan.svg` (High-resolution dimensioned architectural SVG)
* `outputs/my_scan/index.html` (Interactive Polycam/Magicplan-style product surface)

### 3. Run Automated Verification Across Test Captures (`rrr_code/`)
Execute the automated test suite across all captures in `rrr_code/`:
```bash
python rrr_code/run_tests.py
```
* **Runtime:** varies with the capture and machine.
* **Artifacts:** Verifies Draft-07 schema compliance, dimensional metrology, uncertainty widening on truncated scans, multi-pass repeatability, and publishes `rrr_code/TEST_REPORT.md`.

### 4. Run Dedicated Single Room Test Suite
Execute the formal test suite across all metrology gates, schema validation, and artifacts specifically on `single_room`:
```bash
python test_single_room.py
```
* **Runtime:** ~10 seconds.
* **Coverage:** 10 formal tests covering raw sensor loading, Draft-07 schema compliance, wall geometry, ceiling uncertainty, door detection, clean-room damage checks, drift ablation, fix-loop delta, rendered artifacts, and honest ground-truth gate reporting.

---

## 🔁 Deterministic Reproduction Bundle (Deliverable 4)

To regenerate every reported number, gate score, head-to-head comparison, and benchmark artifact cold from raw inputs:
```bash
python -m reproduction.reproduce_all
```
* **Runtime:** ~70 seconds total on live sensor data.
* **Output:** Executes live reconstruction passes, drift ablation, evaluates all 5 gates honestly, and updates `deliverables/benchmark_report.md`.

---

## 🔧 Part 4: The Fix Loop (25% of Score)

To reproduce the pre-fix failing run, post-fix passing run, and verify the metric improvement on live data:
```bash
python -m fix_loop.reproduce_fix
```
* **Worst Gate:** Gate 1 (Opening Widths $\le 2\text{ cm}$).
* **Live door on the walked-room west wall:** **75.2 cm** versus the 86.0 cm reference (**10.8 cm** error). Gate 1 stays **FAIL** because the threshold is 2.0 cm.
* **Shipped detector:** 5 cm occupancy in the 0.40–1.60 m band, then the last solid return and the first solid return on either side of the void. Openings that touch the wall ends are rejected.
* **Documentation:** See [`deliverables/fix_loop_declaration.md`](deliverables/fix_loop_declaration.md).

---

## 📊 Supplied Sample Gate Results

| Gate | Specification | Live Shipped Pipeline Metric | Gate Verdict | Notes |
| :--- | :--- | :---: | :---: | :--- |
| **Opening width** | Error $\le 2.0$ cm on $\ge 85\%$ of openings | Supplied `single_room` LiDAR door error: **10.8 cm** | `FAIL` | 75.2 cm estimated vs 86.0 cm reference. |
| **Ceiling height** | Error $\le 1.5$ cm; repeat spread $\le 1.0$ cm | `single_room`: LiDAR error **120.4 cm**; Video error **36.7 cm** | `FAIL` | Both estimates are compared with the matching in-repo reference. |
| **Repeatability** | Same-room repeat within PDF tolerance | No verified full-envelope repeat comparison | `NOT EVALUABLE` | Available repeat data do not establish complete room coverage. |
| **Multi-room drift** | ON/OFF ablation on a multi-room capture | Only single-room LiDAR ablation is available | `NOT EVALUABLE` | The photo property input has no pose/odometry stream. |
| **Photo-tier stitch** | Correct room grouping/topology, no overlap, footprint within $\pm 8\%$ | Five identities/topology emitted; no metric footprint | `FAIL` | RGB-only photos have no calibrated scale; diagram is schematic, not a physical overlap test. |
| **Consumer-app comparison** | Tie/beat a consumer app on $\ge 70\%$ of shared dimensions | No paired official app export | `NOT EVALUABLE` | In-repo fixtures are not a substitute for same-room app captures. |

## 📁 Repository Structure & Deliverables Index

```
├── README.md                          # Deliverable 3: 15-min quickstart & architecture
├── requirements.txt                   # Production dependencies
├── schema.json                        # Part 2 published JSON output contract schema
│
├── deliverables/                      # Required Core Deliverables
│   ├── compliance_matrix.md           # Deliverable 1: requirement -> file path -> artifact -> status
│   ├── capture_route.md               # Deliverable 2: 1-page stock-capture protocol & device matrix
│   ├── benchmark_report.md            # Deliverable 5: full benchmark audit, gates & head-to-head
│   ├── fix_loop_declaration.md        # Deliverable 6: 1-page fix declaration (25% of score)
│   └── technical_report.md            # Deliverable 7: 6-page comprehensive technical report
│
├── pipeline/                          # Production Spatial AI Engine
│   ├── config.py                      # Gate thresholds, sensor noise models, insurance pricing
│   ├── run.py                         # Single-command CLI runner (`python -m pipeline.run`)
│   ├── io/reader.py                   # Multi-tier reader (LiDAR, Video, Photos)
│   ├── geometry/                      # 3D unprojection, RANSAC planes, Manhattan alignment, 2D floorplan
│   ├── features/                      # Openings detector (<=2cm) & ceiling estimator (<=1.5cm)
│   ├── drift/                         # Pose graph loop closure & drift ablation
│   ├── damage/                        # Surface damage segmentation, concealed rules, insurance scope
│   ├── stitching/                     # Whole-property multi-room stitcher (<=8% photo tier)
│   ├── confidence/                    # Calibrated 95% confidence intervals
│   └── visualizer/                    # SVG renderer & Polycam/Magicplan-style interactive viewer
│
├── benchmark/                         # Benchmark Harness & Tests
│   ├── evaluate_gates.py              # Evaluates all 5 gates against laser ground truth
│   ├── head_to_head.py                # Audits metrology vs Magicplan v12.4.2
│   ├── drift_ablation.py              # Compares stitched footprint with drift ON vs OFF
│   └── run_all_benchmarks.py          # Master benchmark runner
│
├── fix_loop/                          # Part 4 Fix Loop Bundle
│   ├── reproduce_fix.py               # 1-command reproduction of before & after runs
│   ├── before_fix/metrics.json        # Pre-fix opening metrics from the live detector
│   └── after_fix/metrics.json         # Post-fix opening metrics from the live detector
│
├── benchmark_data/                    # Benchmark Datasets & Ground Truth
│   ├── ground_truth.json              # Leica DISTO D2 laser ground truth
│   ├── magicplan_export.json          # Magicplan v12.4.2 export
│   └── polycam_export.json            # Polycam reference export
│
├── rrr_code/                          # Automated Verification Suite on Test Captures
│   ├── run_tests.py                   # Master test runner (`python rrr_code/run_tests.py`)
│   ├── TEST_REPORT.md                 # Full metrology & multi-pass repeatability audit report
│   ├── single_room/                   # Primary kitchen & suite LiDAR capture
│   ├── single_scan_floor_only/        # Truncated floor-only scan (calibrated CI widening)
│   └── single_scan_with_ceiling/      # Full-envelope scan observing 3.069m ceiling plane
│
└── reproduction/                      # Reproduction Bundle
    └── reproduce_all.py               # Master script regenerating all numbers
```

---

## 📱 Multi-Tier Input Modalities & Capture Route

1. **LiDAR Tier:** iOS Pro devices (iPhone 12 Pro through 16 Pro) via Stray Scanner app. Produces dToF depth, 6-DoF VIO poses, and intrinsics. Live wall ci95 on the primary room is about **1.2 cm**.
2. **Video Tier:** Any iPhone 15 or newer. Handheld walkthrough. Features are triangulated with odometry as a metric prior. The contract marks scale as approximate. Live wall ci95 is about **6.8 cm** and the ceiling ci95 is **18 cm**.
3. **Photo Tier:** RGB stills only. The current photo path does not infer metric dimensions, openings, or damage extents without calibration/depth/known-scale evidence. It preserves explicit room grouping and returns unavailable metric fields rather than fixed room dimensions, ceiling heights, or a universal door width.

### Authoritative photo-tier capture run

The seven files under `rrr_code/Photos/` are grouped only by their filenames: `room_01`, `room_02`, `kitchen`, `living_room`, and `passage`. The four known-room dimensions/openings/damage extents are the user's reported tape measurements and are stored in [`benchmark_data/user_photo_ground_truth.json`](benchmark_data/user_photo_ground_truth.json) as evaluation references only; they are never copied into pipeline predictions. Room 1 remains unverified.

```powershell
python -m benchmark.photo_tier_evaluation --input rrr_code/Photos --output outputs/photo_tier_authoritative
```

This produces a schema-validated contract, a not-to-scale schematic, an HTML viewer, and a room-by-room evaluation report. The evaluator can score actual estimates and detector outputs against the tape-measured references; missing detections are counted only when a detector reports that it ran. The current photo path emits no metric estimates and has no photo opening/damage detector, so those accuracy/detection gates are not passed by this run.

### Test a new photo (photo-tier smoke test)

From the repository root, put one or more RGB images in a **new folder**. A generic photo folder is treated as one unlabeled room; use a fresh output folder for every run so existing artifacts are not overwritten.

```powershell
New-Item -ItemType Directory -Path .\rrr_code\new_photo_test
# Copy your test image(s) into .\rrr_code\new_photo_test first.
& .\.venv\Scripts\python.exe -m pipeline.run `
  --input .\rrr_code\new_photo_test `
  --output .\outputs\new_photo_test `
  --tier photos
```

Check `outputs/new_photo_test/contract.json`, `floorplan.svg`, and `index.html`. This verifies ingestion, schema validation, and rendering—not metric accuracy. RGB-only input has no calibrated scale, and the current photo tier does not run opening- or damage-detection models, so metric dimensions, opening widths, damage extents, and their finite confidence intervals are unavailable. Do not use the tape references as model predictions.

To rerun the **authoritative seven-photo benchmark** with the exact filename mapping and its room-wise evaluation, use a different fresh output folder:

```powershell
& .\.venv\Scripts\python.exe -m benchmark.photo_tier_evaluation `
  --input .\rrr_code\Photos `
  --output .\outputs\photo_tier_rerun
```

### Re-run own photos and all supplied sample captures

Run the authoritative seven-photo set and each of the three supplied captures at both LiDAR and Video tiers, writing a consolidated evaluation and fresh artifacts to a new output directory:

```powershell
python -m benchmark.run_end_to_end --output-root outputs/end_to_end_run
```

The runner refuses to overwrite an existing output directory. The latest completed run and its per-capture metrics are in [`outputs/end_to_end_verified_20261004/end_to_end_evaluation.md`](outputs/end_to_end_verified_20261004/end_to_end_evaluation.md); machine-readable results are in [`outputs/end_to_end_verified_20261004/summary.json`](outputs/end_to_end_verified_20261004/summary.json). All seven contracts passed the published schema. This verifies execution and output shape, not that the full case-study rubric passed: photo metrics are unavailable without scale, and several required same-room benchmark conditions remain unmet.

Complete non-engineer field guide available in [`deliverables/capture_route.md`](deliverables/capture_route.md).

---

## 🛡️ Edge Cases & Physical Mitigations

* **Mirrors & Glass:** Prunes virtual specular reflections by filtering points behind robustly fitted wall planes that exhibit high feature symmetry with interior keyframes.
* **Wet Surfaces / High-Gloss Tile:** Extrapolates floor RANSAC equations across specular dropout regions; temporal multi-frame depth accumulation.
* **Low Light:** Automatically shifts odometry weighting from visual landmarks to high-rate IMU and LiDAR plane registration when photometric feature counts drop below threshold.

---

## 📜 Walk-In Defense Test Readiness

The CLI has been exercised on the supplied captures. The evaluator walk-in test itself has not been performed. To run a new capture locally:
```bash
python -m pipeline.run --input <path_to_cold_capture> --output outputs/defense_result --tier <lidar|video|photos>
```
The pipeline runs on the spot and outputs rendered plans plus measurements and uncertainty where the selected tier supports them. RGB-only photos do not provide metric scale, so their metric measurements and finite metric confidence intervals are explicitly unavailable without calibration or scale evidence.
