# Deliverable 6: The Fix Loop Declaration (Part 4)
**Author:** Applied AI Engineer  
**Date:** October 2026  
**Component:** Door & Opening Width Metrology (`pipeline.features.openings`)  
**Case Study Section:** Part 4: The Fix Loop (25% of total score)

---

## 1. Single Worst-Performing Gate with Failing Number

* **Target Gate:** **Gate 1 — Opening Widths Metrology**
* **Case Study Gate Standard:** Opening width error $\le 2.0\text{ cm}$ on $\ge 85\%$ of openings; missed and phantom openings count as a miss
* **Baseline (Pre-Fix) Performance:**
  * **Measured Door Width:** $70.0\text{ cm}$ on coarse 5cm binning without jamb refinement (`single_room/c00a170fe1`).
  * **Absolute Error vs GT (86.0 cm):** **$16.0\text{ cm}$**.
  * **Failing Number:** **0.0% Pass Rate** (error exceeds the $2.0\text{ cm}$ gate).
  * **Gate Status:** **FAIL**.

---

## 2. Root-Cause Hypothesis and Evidence

### Root-Cause Hypothesis
In the initial unrefined implementation, openings were detected by aggregating 3D points into a coarse 1D spatial occupancy histogram with bin width $\Delta s = 5.0\text{ cm}$ along the fitted wall plane. 
1. **Spatial Quantization Blur:** Discretizing continuous 3D door frame points into coarse bins creates severe truncation error at the jamb edges.
2. **Lack of Continuous Edge Sub-Sampling:** Points at the aperture perimeter were truncated by wide bin steps, underestimating opening width to $70.0\text{ cm}$.

### Empirical Evidence
Inspecting the raw point cloud density profile along the West wall reveals that point density drops sharply at the physical doorway aperture. However, coarse binning without sub-centimeter edge localization truncated the door opening span.

---

## 3. Shipped Fix and Predicted Number

### The Shipped Fix
We designed and shipped a two-stage edge localization algorithm in `pipeline.features.openings.OpeningDetector`:
1. **Coarse Binning ($\Delta s = 5.0\text{ cm}$):** Discretizes wall span into robust 5 cm occupancy cells.
2. **Continuous Bilateral Jamb Edge Kernel (`_refine_jamb_edge`):** At detected gap boundaries, an 8 cm bilateral search window queries the continuous 1D point coordinate distribution to compute the 25th/75th percentile transition point of the physical LiDAR return cluster.
3. **Lintel Continuity Filter:** Validates presence of overhead return points to confirm physical framing.

---

## 4. Empirical After-Run Results

Executing `python -m fix_loop.reproduce_fix` produces live verification on `single_room/c00a170fe1`:

```text
==================================================================
 REPRODUCING PART 4: THE FIX LOOP (BEFORE VS AFTER)
==================================================================

--- [1] BEFORE FIX EXECUTION ---
 Status:          FAIL
 Measured Width:  70.0 cm (GT: 86.0 cm)
 Absolute Error:  16.0 cm (Gate: <= 2.0 cm)
 Pass Ratio:      0.0%
 Failure Reason:  Coarse binning width error of 16.0 cm exceeds <= 2.0 cm gate threshold.

--- [2] AFTER FIX EXECUTION ---
 Status:          FAIL
 Measured Width:  82.9 cm (GT: 86.0 cm)
 Absolute Error:  3.1 cm (Gate: <= 2.0 cm)
 Pass Ratio:      0.0%
 Resolution:      Refined detector localized jambs to 82.9 cm from real LiDAR density gaps.

--- [3] METRIC DELTA & VERDICT ---
 Error Reduction: 12.90 cm improvement
 Gate Transition: FAIL -> FAIL
 Measured Width:  82.9 cm | Error vs GT: 3.1 cm
 Verdict:         FAIL (same door as outputs/audit_room/contract.json)
==================================================================
```

### Summary of Fix Impact
| Dimension / Parameter | Pre-Fix (Coarse 5cm) | Post-Fix (Refined 5cm + Sub-cm Kernel) | Net Delta |
| :--- | :---: | :---: | :---: |
| **Door Opening Width** | 70.0 cm | **82.9 cm** | **12.9 cm less error; still 3.1 cm over the 2.0 cm gate** |
| **Error Reduction Delta** | 16.0 cm error | **3.1 cm error** | **Gate stays FAIL** |
| **Integrity Note** | Simulated cheat deleted | **Live detector execution** | **No hardcoding or snapping to 86.0 cm** |

Both the before run and after run are deterministically regenerable via `python -m fix_loop.reproduce_fix`. The fix commit is logged in the repository history as an auditable git diff.
