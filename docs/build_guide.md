# Build Guide — Bio-Inspired Eel Robot

The step-by-step to go from the files to a swimming robot. Read
[manufacturing.md](manufacturing.md) (materials/print settings) and
[BOM.md](BOM.md) (parts) first. Every number here is produced by the analysis
scripts — re-run them after any change.

> Status: this is a **design-complete preliminary package — a verified digital
> prototype**, not a finished, physically-proven product. Geometry, stability,
> structure, power and control are analysed and self-consistent and the whole
> pipeline regenerates (`verify_all.py` → 28/28). What it is **NOT**: wet-tested,
> CFD-solved, or pinned to exact purchased SKUs. Performance numbers are
> **predicted**; depth/heading hold are **experimental** (bench-untested). Treat
> the first build as the validation — the checklist and the §12 test coupons say
> exactly what's done vs what you must confirm.

---

## 0. Pre-flight (decide + buy)
- Pick your **servo** → set `SERVO_BODY_*`, `SERVO_TORQUE_RATED` in `params.py`,
  re-export. Buy **4 identical** waterproof micro servos (3 joints + 1 dive).
- Pick **fresh vs salt** → 304 vs 316 stainless, NBR vs EPDM O-rings.
- Confirm **printer build volume** vs the longest part (head ~140 mm).

## 1. Print (PETG unless noted)
`print_head`, `print_lid`, `print_seg1..5`, `print_tailfin`, `print_dive_plane`
(×2, mirror one), `print_test_rig`; **`print_skin` in TPU**. Orientation +
settings in [manufacturing.md](manufacturing.md). **Do NOT print** the pins or
shafts — buy stainless rod. Print **seg1 + the joint demo first** and check the
pin-bore + servo-pocket fit before committing to all 5.

## 2. Joints
- Every joint = **clevis + tongue + 3 mm stainless pin** (the hinge).
- **Driven (joints 1–3):** servo drops into the seg pocket, **flanges screw to
  the two bosses**, shaft up; **horn bolts to the next segment's tongue**.
- **Passive (joints 4–5):** no servo. Fit the **compliant element** — print the
  inter-segment link in **TPU**, thickness from `tail_stiffness.py`
  (**~4.0 mm at joint 4, ~2.8 mm at joint 5**), *or* loop a rubber band over the
  printed posts at the matching rate. **Tune later** (§7).
- **Tail fin:** 2 M3 screws into seg5 (solid, no hinge).
- Segments sit with a **5 mm gap** (`SEGMENT_GAP`) so they don't collide when
  bending — that's intentional; the skin covers it.

## 3. Dive planes
One rod through both fins; the **dive servo (aft of the joint-1 servo, ~z180)**
turns it via a **crank + link**; the far rod end rides in a **bushing** in the
hull. Both fins move together. `+` plane angle = dive (leading edge down).
Build the crank + link as a **parallelogram** (crank arm = servo-horn arm, link
length = the rod-to-servo offset, arms parallel at neutral) → exact **1:1**
servo-to-fin angle, no dead-point. Set the rod at **~0.28 chord** (near the
centre of pressure) so the hinge moment stays tiny. `dive_linkage.py` verifies
1:1 over ±25° and a **×29 servo torque margin** at cruise.

## 4. Head bay + camera
- Bond the **acrylic window** into the nose seat (epoxy). **Camera + LED mount
  behind it, inside the dry bay** — they stay dry, look through the window.
- Electronics tray slides in from the rear lid: **battery low+centre**, ESP32 +
  PCA9685 on the sides, IMU + buck up top, **MS5837 face epoxied into the lid
  sensor port** (gel side to water).
- Three lid bores: **O-ring lid**, **potted wire gland** (servo/leak wires),
  **sensor port**. Penetrator/gland potted with marine epoxy.

## 5. Stability hardware  (from `stability.py` — this is NOT optional)
The bare design floats **nose-up and rolls easily**. Fix:
- **Buoyancy foam ~59 cm³** (closed-cell) as **two discs cut to the bore** —
  ~38 cm³ in the seg2 bay + ~20 cm³ in the seg3 bay — straddling the joint so
  their combined centroid lands at **z~310** (rear-mid) to trim level. Each disc
  slides into its bay and is **glued/captured** so it can't float out.
- **Lead keel ~200 g**, **low + forward (z~40, belly)** — sets roll + trim.
- **Adjustable trim weight ~15 g** on a fore/aft slide for final level trim.
Result (computed): **floats level (CG=CB), roll margin ~8 mm, neutral.** Exact
pitch is touchy near neutral → set it in the water with the trim weight.

> Note — the foam works *because* the body floods. The skin is a **permeable
> fairing**, not a watertight bag: water passes through the drain holes and sits
> on both sides of it. Closed-cell foam is **self-sealing at the bubble level**
> (each cell traps its own gas), so it displaces that flood water and lifts
> ~55 g regardless of the skin. Use genuine **closed-cell** marine foam (not
> open-cell sponge — it would soak through and lift nothing), and **glue/capture
> it** in its bay so it can't float out.

## 6. Electronics + power  (from `power.py`)
- Size the supply for the **~4 A peak** (all servos stall), not the 6 W average.
- **ESP32 on its own buck (5 V → VIN)**, NOT the servo rail (or stall spikes
  reset it). One topology everywhere: **12 V tether → two robot-local bucks**
  (5–6 V servo bus + 5 V MCU). See [wiring_pinout.md](wiring_pinout.md).
- **1000–2200 µF bulk cap** across the servo bus; **~4 A fuse** on the bus,
  separate fuse for the LED.
- **Tether: run 12 V, buck to 5–6 V AT THE ROBOT** (5–6 V down thin wire drops
  >1 V at peak). Use AWG18–20 power pairs. Wire per [wiring.drawio](wiring.drawio).

## 7. Firmware  (`firmware/eel_gait.ino`)
- Libraries: `Adafruit_PWMServoDriver`, `Wire`, **`MS5837` (BlueRobotics)**.
  Build with the **ESP32 Arduino core 2.0.x** (the LED PWM uses
  `ledcSetup`/`ledcAttachPin`; 3.x changed that API). Servos on PCA9685 ch0–2
  (joints) + ch5 (dive). IMU (MPU6050) on I2C; leak GPIO34; LED GPIO25.
- On boot it **calibrates the gyro zero — hold the robot still ~1 s** and prints
  `MS5837 OK` / `FAIL`.
- Serial @115200: `S`peed, `H` manual bias, **`Y`<deg> hold heading (IMU)**,
  `M`anual, `D`<depth> hold depth, `L`evel, `W`<0–1> light, `X` e-stop.
- **Depth-hold + heading-hold are CLOSED-LOOP but BENCH-UNTESTED — treat as
  experimental.** Depth-hold is *refused* unless the MS5837 actually reads (no
  acting on a fake depth); heading is gyro-only and **drifts** (add a
  magnetometer for absolute heading). Tune the PID gains on the bench.

## 8. Tune the passive tail (bench)
Assemble the tail, **pluck it, time 10 swings → natural frequency**. Add/remove
TPU thickness (or band tension) until **f_n ≈ 2.5 Hz** (`tail_stiffness.py`).
Too stiff = won't undulate; too soft = flops and lags.

## 9. Waterproof — DRY TEST FIRST (do not skip)
1. Print + seal the head bay; grease + fit the O-ring lid.
2. **Submerge the EMPTY bay, weighted, 10 min — check for ingress.** Fix before
   any electronics go in.
3. Pot the penetrator/gland + window; re-test.
4. Waterproof the servos (buy waterproof or pot); conformal-coat the PCB.
5. Drill the segment **drain holes** open; final **powered leak test, leak
   sensor armed**.

## 10. Ballast & trim in water
1. Fit foam + keel (§5). In a tub, confirm **roughly neutral** (sinks slowly).
2. Slide the **trim weight** until it floats **level** (no pitch).
3. Aim **slightly positive (+15–20 g)** so it surfaces if powered off.

## 11. Test order
Bench (on the test rig): servo sweep in phase → heading-hold response →
depth-plane response. Then **tethered pool**: cruise, measure speed vs the
Strouhal target, turn (heading-hold), dive/climb. Log + compare to the reports
in `output/`.

## 12. Test coupons & acceptance (pass/fail — do these before the full build)
The coupons are **real printable STLs** (`cad/test_coupons.py` → `coupon_*.stl`,
`cad/ballast.py`, `cad/tail_flexure.py`) — print + test each; every row has a
**go/no-go** so you're not guessing. Don't print the whole body until the fit +
seal coupons pass.

| Test | Method | PASS threshold |
|---|---|---|
| Servo-pocket fit | print **`coupon_servo.stl`**; drop your servo in | servo seats, both mount screws bite, horn clears, no bind |
| O-ring radial fit | print **`coupon_oring_bore.stl` + `_plug.stl`**, fit with the greased O-ring | smooth slide, even squeeze, no roll-out |
| Bay seal | empty bay, lid + window in, weighted, submerged 10 min | **zero ingress** (dry tissue inside / no bubble stream) |
| Potted wire bundle | pot a bundle in **`coupon_potting.stl`**, submerge + flex 30–60 min | **zero ingress / no wicking** under the jacket |
| Wet servo soak | submerge the (potted/WP) servo, drive it 30 min | runs, no stall/ingress, insulation dry |
| Leak sensor | drip water across the probe at the bay low point | latched e-stop **< 2 s**; **no** false trip when dry |
| Depth sensor | `MS5837 OK` on boot; dunk in a measured water column | reads depth within **±3 cm** of true |
| Tail stiffness | print `print_flexure_2p8/3p4/4p0.stl`, fit each, pluck, time 10 swings | **f_n = 2.5 ± 0.5 Hz** (`tail_stiffness.py`) — keep the variant that passes |
| Power brownout | stall all 4 servos at once on the real supply | ESP32 **does not reset**; fuse holds; bus cap fitted |
| Dry gait | run the gait on the rig | 3 servos sweep in correct travelling-wave phase, no brownout |
| **Dry driven-tail** | drive the front 3 joints dry, watch the passive tail | tail **follows in-phase**, amplitude **grows** toward the tip (not floppy, not rigid) — do before any pool test |

---

## Build-readiness checklist
Legend: ✅ **designed/analysed** (reproducible in software — *not* physically
tested) · ⚠️ **placeholder/experimental** (needs your input or a bench test) ·
⬜ **physical** (only the first build can close it). Every ✅ performance number
is **predicted until wet-tested** — see §11.

| Item | State |
|---|---|
| Geometry, joints, mounts, fits | ✅ parametric, exports clean |
| Drag / buoyancy / gait / self-propulsion | ✅ first-order **predicted** (Cd assumed, **no CFD solve**) |
| **CG/CB stability + trim** | ✅ analysed + fixed (foam+keel+trim weight) |
| Structure (pressure / pin / O-ring) | ✅ analytic margins to ~84 m (no lid-clamp/penetrator/fatigue FEA) |
| **Passive-tail stiffness** | ✅ 3 TPU flexure variants generated (`tail_flexure.py`) — bench-pick the passing one (§12) |
| **Dive-plane linkage** | ✅ parallelogram 1:1, ×29 holding-torque margin (`dive_linkage.py`) |
| **Power: peak / brownout / tether drop** | ✅ analysed + mitigations specified |
| **Wiring / pin map** | ✅ pin-level table ([wiring_pinout.md](wiring_pinout.md)) matches firmware |
| **Lid retention** | ✅ radial O-ring (no clamp force) + joint-1 pin + 3 M3 bolt ears (`head_bay.py`) |
| Free-flood venting | ✅ drain/vent holes in CAD |
| **Whole pipeline reproducible** | ✅ `python verify_all.py` → 28/28 pass |
| Servo + exact part SKUs / dims | ⚠️ **placeholder** until you choose parts — then re-export |
| **Depth-hold / heading-hold** | ⚠️ **experimental** — closed-loop, bench-untested (depth needs MS5837 read; heading drifts, gyro-only) |
| Wet-side wiring / potting / leak-sensor proof | ⚠️ strategy specified — needs test coupons (§12) |
| Anything physical (print/seal/swim) | ⬜ to be validated on the first build |
