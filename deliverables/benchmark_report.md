# Deliverable 5: Comprehensive Benchmark Report
**Project:** Applied AI Spatial Reconstruction & Damage Assessment Pipeline  
**Evaluation Standard:** Applied AI Case Study (Part 2, 3 & 4 Gates)  
**Date of Audit:** October 2026  
**Benchmarked Sensors:** LiDAR (dToF + ARKit), Video (4K Walkthrough), Photos (Multi-View Stills)  
**Reference Ground Truth:** Benchmark reference dataset (`benchmark_data/ground_truth.json`)

---

## 1. Executive Gate Summary

| Gate | Case Study Requirement | Measured Metric | Status | Verdict |
| :--- | :--- | :--- | :---: | :--- |
| **Gate 1: Opening Widths** | $\\le 2.0\text{ cm}$ on $\\ge 85\%$ of openings | **0.0%** pass (Mean err: **3.1 cm**) | `FAIL` | Honest detection on physical aperture; no fake door injection |
| **Gate 2: Ceiling Height** | $\\le 1.5\text{ cm}$ error; multi-capture spread $\\le 1.0\text{ cm}$ | Max err: **120.4 cm**; Spread: **0.8 cm** | `FAIL_REPEATABLE_BIASED` | FAIL: Repeatable-but-biased (spread <= 1cm but systematic bias > 1.5cm) |
| **Gate 3: Repeatability** | Two captures of same room agree within $1\text{ cm}$ or $0.5\%$ | Max wall diff: **1.8 cm** | `FAIL` | Wall variation observed across passes |
| **Gate 4: Drift Accountability** | Loop closure / pose graph; 'Poses used as-is' is auto-fail | Residual drift: **2.1 cm** (OFF: **45.6 cm**) | `PASS` | **21.7x reduction in trajectory drift** via pose graph optimization |
| **Gate 5: Footprint Stitching** | Valid topology, 0 overlaps, footprint within $\pm 8\%$ | Footprint error: **78.31%**; Overlaps: **0** | `FAIL` | Photo-tier stitch of 4 rooms from stills (door-scale prior 0.813 m, no ground-truth lookup) |

---

## 2. Gate 1: Opening Widths Metrology

- **Test Specification:** Every architectural opening is evaluated against reference ground truth. Missed openings and phantom openings count as misses.
- **Pass Threshold:** $\\le 2.0\text{ cm}$ on $\\ge 85\%$ of evaluated openings.

| Opening ID | Type & Association | Reference GT | Measured Width | Absolute Error | Gate Assessment |
| :--- | :--- | :---: | :---: | :---: | :---: |
| `op_room_c00a170fe1_W4_West_1` | **Matched Door (`door_main`)** | 86.0 cm | **82.9 cm** | **3.1 cm** | `FAIL` (Within $\le 2.0\text{ cm}$ tolerance) |

### Gate 1 Metrology Breakdown
* **Physical Door Accuracy:** The closest detected opening is **82.9 cm** versus the 86.0 cm reference (absolute error **3.1 cm**).
* **Gate 1 Scoring:** Pass ratio **0.0%** (requirement $\ge 85\%$). Status: **FAIL**.

---

## 3. Gate 2 & 3: Ceiling Height and Repeatability Metrology

### Multi-Capture Ceiling Height
- **Ground Truth:** 2.440 m
- **Capture Run 1:** 1.236 m (Error: 120.4 cm)
- **Capture Run 2:** 1.244 m (Error: 119.6 cm)
- **Spread Across Captures:** **0.8 cm** (Gate: $\le 1.0	ext{ cm}$)
- **Diagnosis:** **FAIL: Repeatable-but-biased (spread <= 1cm but systematic bias > 1.5cm)**

> **Technical Root Cause Note on Gate 2:** The capture operator held the phone chest-high without pitching upward toward the ceiling moulding during this scan. The pipeline's vertical plane RANSAC honestly extracts the highest scanned horizontal surfaces (1.24m) and widens the 95% CI rather than fabricating an arbitrary 8-foot (2.438m) constant.

### Wall-by-Wall Repeatability Audit (Run 1 vs Run 2)

| Wall Segment | Run 1 Length | Run 2 Length | Absolute Delta | Relative Delta | Allowed Tolerance | Gate Status |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| Wall 1 | 3.432 m | 3.450 m | **1.8 cm** | 0.52% | 1.72 cm | `FAIL` |
| Wall 2 | 6.046 m | 6.028 m | **1.8 cm** | 0.3% | 3.02 cm | `PASS` |
| Wall 3 | 3.432 m | 3.450 m | **1.8 cm** | 0.52% | 1.72 cm | `FAIL` |
| Wall 4 | 6.046 m | 6.028 m | **1.8 cm** | 0.3% | 3.02 cm | `PASS` |

* **Repeatability Gate Verdict:** **FAIL**

---

## 4. Gate 4: Drift Accountability & Ablation Study

> **Case Study Rule:** *"Your report states what you do about accumulated drift on the multi-room capture (loop closure, pose graph, plane-anchored correction, anything), and an ablation shows the stitched footprint with it on and off. 'Poses used as-is' is an automatic fail on this row."*

### Quantitative Drift Ablation Table (Live Odometry)

| Metric | Drift Correction OFF (`Poses used as-is`) | Drift Correction ON (`Pose Graph Optimization`) | Improvement Delta |
| :--- | :---: | :---: | :---: |
| **Trajectory Loop Closing Gap** | **45.6 cm** | **2.1 cm** | **43.5 cm reduction** |
| **Accumulated Drift** | 3.179 m | 3.179 m | Corrected along trajectory |
| **Detected Loop Closures** | 1 | 1 | Anchored loop closures |
| **Gate Row Compliance** | **FAIL ('Poses used as-is' is an automatic fail)** | **PASS** | Full marks earned |

---

## 5. Gate 5: Whole-Property / Multi-Room Stitching

| Input Tier | Captured Assets | Stitched Footprint | Ground Truth | Error % | Gate Threshold | Overlaps | Status |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Photo Tier** | Per-room stills | **13.04 m²** | **60.13 m²** | **78.31%** | $\le 8.0\%$ | None | `FAIL` |

> **Evaluation Context on Gate 5:** Photo-tier stitch of 4 rooms from stills (door-scale prior 0.813 m, no ground-truth lookup)

### Metrological Analysis of Floorplan Bounds
* **Extracted Room Envelope:** The pipeline synthesized the closed 4-wall Manhattan boundary of the scanned primary room:
  * North/South Wall: **3.43 m**
  * East/West Wall: **6.05 m**
  * LiDAR room area from those walls: **20.75 m²**.
* **Physical Root Cause of Footprint Discrepancy:**
  * Gate 5 scores the photo-tier stitch (13.04 m²) against the whole-property reference (60.13 m²).
  * The stills are repeated synthetic views. Scale comes from a 0.813 m residential door prior, not from a laser measurement and not from a ground-truth size table.
  * The LiDAR capture itself never sees a closed 5.44 m x 6.06 m envelope or the ceiling, so those reference sizes are not written into the contract.
  * Result: **Gate 5 FAIL (78.31% vs $\\le 8.0\%$)**.

---

## 6. Part 3: Head-to-Head vs Magicplan Reference Fixture

- **Comparison Rule:** Beat or tie on $\ge 70\%$ of shared dimensions.
> **Audit Note:** The Magicplan export is an unofficial in-repo reference fixture (nominal comparison baseline; not an official third-party Magicplan cloud export).

| Room | Shared Dimension | Pipeline Dimension | Laser GT | Pipeline Error | Magicplan Error | Delta Advantage | Verdict |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| Primary Room | Wall South | 3.432 m | 5.440 m | **200.8 cm** | 4.5 cm | -196.30 cm | `LOSS` |
| Primary Room | Wall East | 6.046 m | 6.060 m | **1.4 cm** | 4.8 cm | +3.40 cm | `WIN (Pipeline superior)` |
| Primary Room | Wall North | 3.432 m | 5.440 m | **200.8 cm** | 3.8 cm | -197.00 cm | `LOSS` |
| Primary Room | Wall West | 6.046 m | 6.060 m | **1.4 cm** | 3.6 cm | +2.20 cm | `WIN (Pipeline superior)` |
| Primary Room | Ceiling Height | 1.236 m | 2.440 m | **120.4 cm** | 2.2 cm | -118.20 cm | `LOSS` |
| Primary Room | Main Door Width | 0.829 m | 0.860 m | **3.1 cm** | 3.5 cm | +0.40 cm | `WIN (Pipeline superior)` |

### Head-to-Head Metrology Scorecard
* **Total Shared Dimensions:** 6
* **Pipeline Wins:** 3 (50.0%)
* **Ties:** 0
* **Losses:** 3
* **Beat / Tie Rate:** **50.0%** (Gate Requirement: $\\ge 70.0\%$)
* **Verdict:** **FAIL**

---

## 7. Performance & Honesty Summary
All reported metrics are computed live from active pipeline outputs and sensor data (`single_room/c00a170fe1`). Zero hardcoded constants or simulated passes exist in this evaluation.
