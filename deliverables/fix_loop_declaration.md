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
The shipped detector in `pipeline.features.openings.OpeningDetector` does two things:
1. **Coarse binning ($\Delta s = 5.0\text{ cm}$)** on points within 12 cm of the wall and between 0.40 m and 1.60 m above the floor.
2. **Density-drop jambs.** The left jamb is the last solid return before the empty bins. The right jamb is the first solid return after them. The edge is taken inside the solid bin, so it is not pulled back into the wall.

The prediction was that a sub-bin edge on this gap would land within 2 cm of 86 cm. That prediction assumed the empty span in the cloud was about 86 cm. It is not.

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
 Measured Width:  75.2 cm (GT: 86.0 cm)
 Absolute Error:  10.8 cm (Gate: <= 2.0 cm)
 Pass Ratio:      0.0%
 Resolution:      Refined detector localized jambs to 75.2 cm from real LiDAR density gaps.

--- [3] METRIC DELTA & VERDICT ---
 Error Reduction: 5.20 cm improvement
 Gate Transition: FAIL -> FAIL
 Measured Width:  75.2 cm | Error vs GT: 10.8 cm
 Verdict:         FAIL (same door as outputs/audit_room/contract.json)
==================================================================
```

### Summary of Fix Impact
| Dimension / Parameter | Pre-Fix (Coarse 5cm) | Post-Fix (Refined 5cm + Sub-cm Kernel) | Net Delta |
| :--- | :---: | :---: | :---: |
| **Door Opening Width** | 70.0 cm | **75.2 cm** | **5.2 cm less error; still 10.8 cm over the 2.0 cm gate** |
| **Error Reduction Delta** | 16.0 cm error | **10.8 cm error** | **Gate stays FAIL** |
| **Integrity Note** | Simulated cheat deleted | **Live detector execution** | **No hardcoding or snapping to 86.0 cm** |

Both the before run and after run are deterministically regenerable via `python -m fix_loop.reproduce_fix`. The fix commit is logged in the repository history as an auditable git diff.
