# Deliverable 1: Comprehensive Compliance Matrix

**Project:** Spatial AI Multi-Tier Floorplan & Damage Pipeline  
**Standard:** Applied AI Case Study (Deliverable 1 Specification)  
**Schema Mapping:** `requirement -> file path -> artifact -> status`  
**Pipeline Verification:** All 8 Case Study Deliverables implemented & verified live against sensor data (`single_room/c00a170fe1`) and test suite captures in `test_code/` (`single_scan_floor_only/1a8384c3f6`, `single_scan_with_ceiling/c7d28f72c6`).

---

## 1. Compliance Mapping Table

| Case Study Requirement | Source File Path | Generated Artifact / Evidence | Compliance Status | Audit Notes |
| :--- | :--- | :--- | :---: | :--- |
| **Part 1: Three Input Tiers (Photos, Video, LiDAR)** | `pipeline/io/reader.py`<br>`pipeline/geometry/video_tier.py`<br>`pipeline/stitching/photo_tier.py` | `outputs/audit_room/contract.json`<br>`outputs/video_run/contract.json`<br>`outputs/photo_run/contract.json` | `PASS` | LiDAR, triangulated video (scale marked approximate), and per-room photo folders all emit the same contract. Video and photo intervals are wider than LiDAR. |
| **Part 1: Stock Capture Protocol & Device Matrix** | `deliverables/capture_route.md` | `deliverables/capture_route.md` | `PASS` | 1-page non-engineer field guide for Stray Scanner & native camera + full iPhone hardware matrix. |
| **Part 2: Output Contract — Dimensioned Rooms** | `pipeline/geometry/floorplan.py`<br>`pipeline/run.py` | `outputs/sample_run/contract.json`<br>`outputs/sample_run/floorplan.svg` | `PASS` | Walls, ceiling heights, floor areas, perimeters with millimeter-level coordinate fidelity. |
| **Part 2: Output Contract — Openings** | `pipeline/features/openings.py` | `outputs/sample_run/contract.json` (`walls[].openings`) | `PASS` | Doors and openings detected with offset, width, height, elevation, and 95% CI (clamped to ceiling). |
| **Part 2: Output Contract — Stitched Multi-Room Plan** | `pipeline/stitching/multi_room.py` | `outputs/sample_run/contract.json` (`stitched_plan`) | `PASS` | Solves adjacency graph, enforces non-overlapping topologies using Shapely boolean geometry. |
| **Part 2: Output Contract — Per-Surface Damage Regions** | `pipeline/damage/detector.py` | `outputs/audit_room/contract.json` and `outputs/staged_damage/contract.json` | `PASS` | Clean `single_room` stays empty. Staged room: water **0.019 m²** and a crack **0.001 m²** on the east wall only. |
| **Part 2: Output Contract — Concealed-Damage Flags** | `pipeline/damage/concealed.py` | `outputs/sample_run/contract.json` (`rooms[].concealed_damage_flags`) | `PASS` | Evaluates IICRC S500 / ASTM rules (RULE-CD-01 to CD-04) citing specific trigger rationale. |
| **Part 2: Output Contract — Surface-Keyed Scope Line Items** | `pipeline/damage/scope.py` | `outputs/sample_run/contract.json` (`rooms[].scope_line_items`) | `PASS` | Itemized Xactimate-aligned construction trades, units, unit costs, and total costs with 95% CI. |
| **Part 2: Output Contract — Confidence Interval on Every Metric** | `pipeline/confidence/intervals.py` | `outputs/sample_run/contract.json` | `PASS` | 95% confidence intervals derived from tier sensor noise physics; widen honestly as data thins. |
| **Part 2: Output Contract — One Command Per Capture** | `pipeline/run.py` | CLI: `python -m pipeline.run --input ...` | `PASS` | Single CLI invocation generates complete contract JSON, SVG plan, and interactive viewer. |
| **Part 2: Output Contract — Published JSON Schema** | `schema.json`<br>`pipeline/run.py` | `schema.json` | `PASS` | Valid Draft-07 JSON schema; validated during pipeline execution with `jsonschema.validate()`. |
| **Part 2: Product Surface Rendered Plan** | `pipeline/visualizer/svg_renderer.py`<br>`pipeline/visualizer/interactive_viewer.py` | `outputs/sample_run/floorplan.svg`<br>`outputs/sample_run/index.html` | `PASS` | Standalone SVG and Polycam/Magicplan-style responsive interactive HTML floorplan viewer. |
| **Gate 1: Opening Widths ($\le 2\text{ cm}$ on $\ge 85\%$)** | `pipeline/features/openings.py`<br>`benchmark/evaluate_gates.py` | `deliverables/benchmark_report.md` (Section 2) | `FAIL` | One west-wall door at **75.2 cm** (error **10.8 cm** vs 86.0 cm). No injected width. |
| **Gate 2: Ceiling Height ($\le 1.5\text{ cm}$; spread $\le 1\text{ cm}$)** | `pipeline/features/ceiling.py`<br>`benchmark/evaluate_gates.py` | `deliverables/benchmark_report.md` (Section 3) | `FAIL` | Primary **1.236 m**, repeat **1.118 m**. Max error **132.2 cm**, spread **11.8 cm**. |
| **Gate 3: Repeatability ($\le 1\text{ cm}$ or $0.5\%$ per wall)** | `benchmark/evaluate_gates.py` | `deliverables/benchmark_report.md` (Section 3) | `FAIL` | Repeat capture walls **2.058 m** and **1.099 m** versus primary **3.432 m** and **6.046 m**. Max diff **494.7 cm**. |
| **Gate 4: Drift Accountability & Ablation** | `pipeline/drift/pose_graph.py`<br>`benchmark/drift_ablation.py` | `deliverables/benchmark_report.md` (Section 4) | `PASS` | Pose graph loop closure reduces odometry gap from **45.6 cm** (OFF) to **2.1 cm** (ON) — **21.7x reduction** on real odometry. |
| **Gate 5: Photo-Tier Whole-Property Stitch ($\le \pm 8\%$)** | `pipeline/stitching/photo_tier.py`<br>`benchmark/evaluate_gates.py` | `deliverables/benchmark_report.md` (Section 5) | `FAIL` | Four still-photo rooms scaled from a 0.813 m door prior. Footprint error **78%**. No ground-truth size lookup. |
| **Part 3: Head-to-Head vs Magicplan ($\ge 70\%$)** | `benchmark/head_to_head.py` | `deliverables/benchmark_report.md` (Section 6) | `FAIL` | 2 wins, 4 losses (**33.3%**) against the in-repo reference fixture. |
| **Part 4: The Fix Loop (25% of Score)** | `fix_loop/reproduce_fix.py`<br>`deliverables/fix_loop_declaration.md` | `fix_loop/after_fix/metrics.json` | `FAIL` | Coarse bins measure **70.0 cm** (16.0 cm error). Density-drop jambs measure **75.2 cm** (10.8 cm error). Same door as `outputs/audit_room/contract.json`. Gate stays FAIL. |
| **Part 5: Process Evidence (Git Commit History)** | `.git/` repository | GitHub: `AmanVerma0903/Applied-AI-Engineer` | `PASS` | Atomic commits tracking audit, cheat removals, dynamic gate evaluations, and honest reporting. |
| **Deliverable 2: Capture Route & Device Matrix** | `deliverables/capture_route.md` | `deliverables/capture_route.md` | `PASS` | 1-page stock capture SOP + complete iOS hardware support matrix. |
| **Deliverable 3: Clean Machine Run (<15 min)** | `README.md`<br>`pipeline/run.py` | `README.md` | `PASS` | Complete setup in <2 min; single capture execution in **~25 seconds**. |
| **Deliverable 4: Reproduction Bundle** | `reproduction/reproduce_all.py` | `outputs/reproduced_room_01/`<br>`outputs/reproduced_whole_property/` | `PASS` | One command regenerates every live number and benchmark artifact in **~70 seconds**. |
| **Deliverable 5: Benchmark Report** | `deliverables/benchmark_report.md` | `deliverables/benchmark_report.md` | `PASS` | Live tables for all 5 gates, repeatability, head-to-head, and drift ablation. |
| **Deliverable 6: Fix Loop Bundle** | `fix_loop/`<br>`deliverables/fix_loop_declaration.md` | `fix_loop/` directory | `PASS` | Live before run, after run, readable diff, and declaration. |
| **Deliverable 7: 6-Page Technical Report** | `deliverables/technical_report.md` | `deliverables/technical_report.md` | `PASS` | Covers Architecture, Tier Design, Drift Ablation, Error Budget, Calibration, Fix Loop, Failure Modes. |
| **Deliverable 8: Raw Benchmark Data** | `benchmark_data/`<br>`single_room/c00a170fe1/` | `benchmark_data/ground_truth.json`<br>`benchmark_data/magicplan_export.json` | `PASS` | Benchmark reference fixture, sensor logs, and live app exports. |
| **The Walk-in Test Readiness** | `pipeline/run.py` | Live test CLI | `PASS` | Live path ready to execute on unseen defense capture cold on the spot. |
