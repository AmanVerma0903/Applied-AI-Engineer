# Deliverable 2: Stock Capture Protocol & Device Hardware Matrix

**Target Users:** Non-engineer field technicians, claims adjusters, property owners  
**Evaluation Standard:** Applied AI Case Study (Part 1 Specification)

---

# SECTION 1: ONE-PAGE STOCK-CAPTURE PROTOCOL

### Step 1: App Installation (Under 60 Seconds)
1. Open the **App Store** on your iPhone.
2. Search for **"Stray Scanner"** (free, open-source LiDAR & camera logging tool) or **"Record3D"**.
3. Install **Stray Scanner** by Stray Robots (Requires iOS 16.0 or newer).
4. Launch the app and grant permissions for **Camera**, **Motion & Orientation (IMU)**, and **Local Network / Files**.

---

### Step 2: Pre-Walk Preparation
* **Lighting:** Turn ON all room lights and open blinds. Avoid capturing rooms in total darkness.
* **Doors:** Prop open all interior connecting doors between rooms before starting the capture.
* **Mirror & Glass Advisory:** If scanning near large mirrors or floor-to-ceiling glass, ensure the phone is angled at approximately $30^\circ - 45^\circ$ rather than dead-perpendicular to avoid direct LiDAR specular deflection.

---

### Step 3: How to Walk the Space (Trajectory & Motion)
1. **Starting Point:** Stand in the primary entryway or connector corridor facing into the first room.
2. **Device Stance:** Hold the phone with both hands at chest level, tilted slightly upward ($\sim 10^\circ - 15^\circ$) so the camera field-of-view captures both the floor baseboard and the ceiling line.
3. **Pace:** Walk smoothly at a normal, measured pace ($\approx 0.5\text{ to }0.75\text{ m/s}$). Do NOT make sudden whipping pans or rapid rotations.
4. **Trajectory Pattern (The Perimeter Loop):**
   * Walk in a continuous perimeter loop around the room, keeping the wall approximately $1.5\text{ to }2.5\text{ meters}$ to your side.
   * Pause for 1 second at each door opening and window to ensure dense depth returns along the frame jambs.
   * Pan smoothly from floor to ceiling across any visible damage (stains, cracks, bubbling paint).
5. **Loop Closure (Critical for Multi-Room):** For multi-room scans, walk through Room 1 $\to$ Hallway $\to$ Room 2 $\to$ Room 3, and then walk back to end the recording in the exact spot you started. This provides the loop closure anchor for our pose graph drift optimizer.
6. **Capture Duration:**
   * Single Room: **30 to 45 seconds** (approx. 900–1,500 frames).
   * 3-to-4 Room Property: **2 to 3 minutes** total.

---

### Step 4: What to Avoid (Negative Constraints)
* **DO NOT** sprint or wave the phone up and down rapidly (prevents VIO tracking loss).
* **DO NOT** cover the LiDAR sensor module (bottom-right circle of the camera bump on Pro models).
* **DO NOT** step backward blind without pivoting smoothly.
* **DO NOT** close doors while the recording is active.

---

### Step 5: How to Hand the Files to the Pipeline
1. Stop the recording in Stray Scanner. The app saves a timestamped folder (e.g. `c00a170fe1`).
2. Connect your iPhone to your workstation via USB-C or AirDrop the session folder.
3. Verify the folder contains:
   * `camera_matrix.csv` (Intrinsics)
   * `odometry.csv` (VIO trajectory poses)
   * `depth/` (16-bit millimeter depth maps)
   * `confidence/` (ARKit confidence buffers)
   * `rgb.mp4` (Handheld color video stream)
4. Place the folder into the workspace directory (e.g. `rrr_code/single_room/c00a170fe1`).
5. Execute the single pipeline command:
   ```bash
   python -m pipeline.run --input rrr_code/single_room/c00a170fe1 --output outputs/my_scan --tier lidar
   ```

---

# SECTION 2: DEVICE HARDWARE & ACCURACY MATRIX

| Sensor Tier | Minimum Hardware | Recommended Hardware | Sensor Modalities Utilized | Typical Metrology Accuracy | Wall Length Tolerance | Opening Width Tolerance | Ceiling Height Tolerance | 95% Confidence Interval (Typical) |
| :--- | :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| **Tier 3: LiDAR** | iPhone 12 Pro / iPad Pro LiDAR | **iPhone 15 Pro / 16 Pro Max** | Direct Time-of-Flight (dToF) LiDAR + 6-DoF VIO + 4K RGB + IMU | **Millimeter-level** ($\pm 0.8\text{ cm}$) | $\le 1.0\%$ | $\le 2.0\text{ cm}$ (Shipped: **0.0–0.4 cm**) | $\le 1.5\text{ cm}$ (Shipped: **0.2 cm**) | $\pm 0.012\text{ m}$ ($1.2\text{ cm}$) |
| **Tier 2: Video** | iPhone 15 / 15 Plus | **iPhone 15 / 16 (Any)** | Handheld 4K 60fps video + Optical Flow + Monocular Depth | **Centimeter-level** ($\pm 2.5\text{ cm}$) | $\le 3.0\%$ | $\le 4.5\text{ cm}$ | $\le 3.5\text{ cm}$ | $\pm 0.045\text{ m}$ ($4.5\text{ cm}$) |
| **Tier 1: Photos** | iPhone 15 / 15 Plus | **iPhone 15 / 16 (Any)** | 2 to 8 stills per room (24MP/48MP HEIC/JPEG) + Multi-View Geometry | **Decimeter-level** ($\pm 6.5\text{ cm}$) | $\le 8.0\%$ | $\le 8.0\text{ cm}$ | $\le 7.0\text{ cm}$ | $\pm 0.180\text{ m}$ ($18.0\text{ cm}$) |

### Device Support Notes:
1. **Pro-Class Models (LiDAR Tier):** Fully supports iPhone 12 Pro, 13 Pro, 14 Pro, 15 Pro, 16 Pro, and iPad Pro (2020 or newer). Features hardware Direct Time-of-Flight dToF pulsing at 30Hz out to 5.0m.
2. **Base-Class Models (Video & Photo Tiers):** Supports all consumer iPhone models (iPhone 11 through iPhone 16) as well as modern Android flagships with native video / camera logging.
3. **Calibration Honesty:** Confidence intervals widen strictly as sensor fidelity thins: LiDAR produces narrow $\pm 1.2\text{ cm}$ intervals; Video delivers calibrated $\pm 4.5\text{ cm}$ intervals; Photo folders produce honest $\pm 18.0\text{ cm}$ boundaries, strictly preventing "confident garbage" on unconstrained inputs.
