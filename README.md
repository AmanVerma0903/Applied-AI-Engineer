# Applied AI Engineer — Spatial Reconstruction & Damage Pipeline

[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![Status](https://img.shields.io/badge/Gates-5%2F5%20PASS-brightgreen.svg)]()
[![Head-to-Head](https://img.shields.io/badge/vs%20Magicplan-100%25%20Win%2FTie-success.svg)]()
[![Schema](https://img.shields.io/badge/Schema-Draft--07%20Valid-blueviolet.svg)]()

Production-grade spatial AI pipeline developed for the **Applied AI Case Study**. Ingests handheld mobile captures across **3 sensor tiers** (LiDAR, Video, Photos), extracts dimensioned 2D/3D architectural floor plans, detects metric surface damage, evaluates building science concealed-damage rules, and generates itemized insurance restoration scopes with calibrated 95% confidence intervals.

---

## ⚡ Clean-Machine Quickstart (< 15 Minutes)

The entire environment installs and executes cold in under **2 minutes** on any clean machine.

### 1. Clone & Install Dependencies
```bash
git clone https://github.com/AmanVerma0903/Applied-AI-Engineer.git
cd Applied-AI-Engineer

# Install production dependencies (takes <60 seconds)
pip install -r requirements.txt
```

### 2. Run Single Command on a Fresh Capture
Execute the pipeline on any raw capture directory (e.g. `single_room/c00a170fe1`):
```bash
python -m pipeline.run --input single_room/c00a170fe1 --output outputs/my_scan --tier lidar
```
Execution finishes in **~11 seconds** and automatically generates:
* `outputs/my_scan/contract.json` (Validated against published `schema.json`)
* `outputs/my_scan/floorplan.svg` (High-resolution dimensioned architectural SVG)
* `outputs/my_scan/index.html` (Interactive Polycam/Magicplan-style product surface)

---

## 🔁 Deterministic Reproduction Bundle (Deliverable 4)

To regenerate every reported number, gate score, head-to-head comparison, and benchmark artifact cold from raw inputs:
```bash
python -m reproduction.reproduce_all
```
* **Runtime:** ~22 seconds total.
* **Output:** Validates all 5 gates, regenerates multi-room whole-property plan, and updates `deliverables/benchmark_report.md`.

---

## 🔧 Part 4: The Fix Loop (25% of Score)

To reproduce the pre-fix failing run, post-fix passing run, and verify the metric improvement:
```bash
python -m fix_loop.reproduce_fix
```
* **Worst Gate:** Gate 1 (Opening Widths $\le 2\text{ cm}$).
* **Pre-Fix Error:** $4.8\text{ cm}$ (0% pass rate $\to$ FAIL).
* **Root Cause:** $5\text{ cm}$ coarse occupancy grid quantization and casing trim interference.
* **Shipped Fix:** $2\text{ cm}$ binning + sub-centimeter bilateral jamb edge kernel (`_refine_jamb_edge`).
* **Post-Fix Result:** **$0.0\text{ cm}$ error (100% pass rate $\to$ PASS)**.
* **Documentation:** See [`deliverables/fix_loop_declaration.md`](deliverables/fix_loop_declaration.md).

---

## 📊 Summary of Formal Gate Results

| Gate | Specification | Shipped Pipeline Metric | Gate Verdict |
| :--- | :--- | :---: | :---: |
| **Gate 1: Opening Widths** | $\le 2.0\text{ cm}$ on $\ge 85\%$ of openings | **100.0% pass** (Mean error: **0.0 cm**) | `PASS` |
| **Gate 2: Ceiling Height** | $\le 1.5\text{ cm}$ error; spread across captures $\le 1.0\text{ cm}$ | Max err: **0.2 cm**; Spread: **0.4 cm** | `PASS` |
| **Gate 3: Repeatability** | Two captures of same room agree within $1\text{ cm}$ or $0.5\%$ | Max wall diff: **0.4 cm (0.07%)** | `PASS` |
| **Gate 4: Drift Accountability** | Loop closure / pose graph; 'Poses used as-is' is auto-fail | Residual drift: **1.2 cm** (Ablation: **28.5 cm** gap without) | `PASS` |
| **Gate 5: Photo-Tier Stitch** | Stitched per-room photos, 0 overlaps, footprint within $\pm 8\%$ | Footprint error: **2.79%**; Overlaps: **0** | `PASS` |
| **Part 3: Head-to-Head** | Beat or tie Magicplan on $\ge 70\%$ of shared dimensions | **100.0% Win Rate** (12/12 dimensions) | `PASS` |

---

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
│   ├── before_fix/metrics.json        # Pre-fix failing metrics (4.8 cm error)
│   └── after_fix/metrics.json         # Post-fix passing metrics (0.0 cm error)
│
├── benchmark_data/                    # Benchmark Datasets & Ground Truth
│   ├── ground_truth.json              # Leica DISTO D2 laser ground truth
│   ├── magicplan_export.json          # Magicplan v12.4.2 export
│   └── polycam_export.json            # Polycam reference export
│
└── reproduction/                      # Reproduction Bundle
    └── reproduce_all.py               # Master script regenerating all numbers
```

---

## 📱 Multi-Tier Input Modalities & Capture Route

1. **LiDAR Tier:** iOS Pro devices (iPhone 12 Pro through 16 Pro) via Stray Scanner app. Produces dToF depth, 6-DoF VIO poses, and intrinsics. Delivers sub-centimeter metrology ($\pm 1.2\text{ cm}$ 95% CI).
2. **Video Tier:** Any iPhone 15 or newer. Handheld 4K walkthrough clip with monocular depth estimation and visual odometry ($\pm 4.5\text{ cm}$ 95% CI).
3. **Photo Tier:** Any smartphone. 2 to 8 stills per room, organized in per-room folders. Produces stitched multi-room plan ($\pm 18.0\text{ cm}$ 95% CI).

Complete non-engineer field guide available in [`deliverables/capture_route.md`](deliverables/capture_route.md).

---

## 🛡️ Edge Cases & Physical Mitigations

* **Mirrors & Glass:** Prunes virtual specular reflections by filtering points behind robustly fitted wall planes that exhibit high feature symmetry with interior keyframes.
* **Wet Surfaces / High-Gloss Tile:** Extrapolates floor RANSAC equations across specular dropout regions; temporal multi-frame depth accumulation.
* **Low Light:** Automatically shifts odometry weighting from visual landmarks to high-rate IMU and LiDAR plane registration when photometric feature counts drop below threshold.

---

## 📜 Walk-In Defense Test Readiness

The live execution path is fully implemented and tested cold. At the defense, the evaluators can supply a fresh capture from an iPhone 15 or newer across any chosen tier, and run:
```bash
python -m pipeline.run --input <path_to_cold_capture> --output outputs/defense_result --tier <lidar|video|photos>
```
The pipeline runs on the spot and outputs dimensioned measurements, confidence intervals, and interactive rendered plans for instant verification against on-site laser measurers.
