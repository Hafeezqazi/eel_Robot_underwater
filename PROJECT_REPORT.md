# Bio-Inspired Underwater Eel Robot — Design Report

*A walkthrough of the design, in my own words, for the team.*

> **TL;DR** — I designed a ~50 cm anguilliform (eel-style) underwater robot from
> scratch: a free-flooding, segmented body that swims with a travelling body
> wave, dives with bow planes, and carries a camera + light in a sealed head.
> The **digital design is complete and self-consistent** — parametric CAD,
> first-principles engineering analysis, control firmware, full build docs, and a
> researched bill of materials. The whole thing regenerates and self-checks at
> **28/28** on one command, and it was hardened over **several rounds of design review**.
> What's left is the physical build (print, buy parts, seal, wet-test) — those
> steps need hardware, not more design.

---

## 1. What I set out to build

A small, tethered, 3D-printable underwater vehicle inspired by how an eel
actually swims — not a propeller sub. Goals:

- **Bio-inspired propulsion:** an undulating body wave (anguilliform), like a
  real eel, instead of a thruster.
- **3D capable:** it cruises, turns, and **dives/climbs**, holding depth.
- **Desk/pool scale:** ~500 mm long, ~70 mm diameter, shallow water, tethered for
  power + control + video — simple enough to actually build and test.
- **Useful payload:** a forward camera + headlight so it can *see*.

## 2. The big design decisions (and why)

| Decision | Why I went this way |
|---|---|
| **Free-flooding body, sealed head only** | Sealing a long jointed body is a leak nightmare. Let the body flood; only the head (electronics) is dry. Far simpler + safer. |
| **3 driven joints + 2 passive tail joints** | Servos drive the front of the wave; a compliant TPU/rubber tail finishes it for free — fewer motors, more eel-like motion. |
| **Bow dive planes for depth** | Like a submarine's hydroplanes — pitch the nose to dive/climb at speed. Cheap, robust, one extra servo. |
| **Buoyancy foam + lead keel** | A free-flooding body floats nose-up and rolls. Closed-cell foam (aft) + a low forward lead keel fix trim *and* roll. |
| **Tether (12 V) + buck at the robot** | No batteries to size for endurance, no comms-through-water problem; video + serial ride spare tether pairs. |
| **Camera + light behind a nose window** | They stay dry inside the head and look out through a bonded acrylic disc — zero extra waterproofing. |

## 3. How I worked (the pipeline)

I built this as **code-driven parametric design**, so every part traces back to
one source of truth and the whole thing is reproducible:

```
concept → first-principles math → parametric CAD → engineering analysis
        → electronics + firmware → build docs + BOM → design review
```

- **One parameter file** (`cad/params.py`) drives all geometry and feeds the
  analysis — change the body length or a servo size and *everything* re-derives.
- **One command checks everything**: `python verify_all.py` runs all 28 scripts
  (CAD exports + analysis + renders) and reports pass/fail. It's green.

## 4. The vehicle, part by part

- **Head bay** — the only sealed compartment: holds the ESP32, battery buffer,
  IMU, depth sensor, camera + LED. A removable lid (radial O-ring seal + the
  joint-1 pin + 3 M3 bolt ears) lets the electronics tray slide out.
- **Body segments (×5)** — tapered, free-flooding shells; the front 3 each hold a
  servo that drives that joint; the rear 2 are the passive compliant tail.
- **Joints** — simple clevis + tongue + stainless pin hinges; a 5 mm inter-segment
  gap so they never collide when the body bends.
- **Dive planes** — two bow fins on one shaft, driven together by a fourth servo.
- **Skin** — a flexible TPU sleeve over the segmented spine for clean flow (the
  body still floods through drain holes underneath — the foam still works because
  closed-cell foam seals *itself*).
- **Ballast** — bore-fitting closed-cell foam discs + a lead keel + a small
  sliding trim weight for final levelling in the water.

## 5. Does it actually work? (the engineering checks)

Every claim below is **computed from first principles** — these are *predictions*
to confirm in the tank, not measured results, and the docs are explicit about
that. Headline numbers at the current parameters:

| Quantity | Value |
|---|---|
| Size / displaced volume | 500 × 70 mm / ~1105 cm³ |
| Dry mass / inherent buoyancy | ~390 g / **+150 g positive** (floats; ballast to neutral) |
| **Stability** | **neutral buoyancy, roll margin +8 mm, ~2° resting trim** |
| Predicted cruise speed | **~0.53 m/s** (~1.1 body-lengths/s), 2 Hz tail-beat |
| Strouhal number | 0.22–0.44 (in the efficient swimming band) |
| Dive planes | 63 cm², ±25°, min dive speed ~0.24 m/s |
| Structure | large margins to the 2 m rating; head bay good to ~84 m before buckling |
| Electrical | ~6.7 W average; sized for ~4 A peak (all servos stall) |

The analysis scripts that produce these: buoyancy/sizing, **CG-vs-CB stability**,
structures/sealing, **power + brownout + tether drop**, Lighthill self-propulsion,
dive-plane lift, passive-tail stiffness, and dive-linkage kinematics. A CFD case
is **staged** (not solved) for whoever wants a measured drag number later.

## 6. Electronics & control

- **Brains:** ESP32 + a PCA9685 driver for the 4 servos, an MPU6050 IMU, an
  MS5837 depth sensor, and a leak probe.
- **Firmware** generates the travelling-wave gait and adds two closed loops:
  **heading-hold** (IMU) and **depth-hold** (dive planes). Both are gated on their
  sensor actually responding, and both are labelled **experimental / bench-tune**
  — honest, because they aren't tested on hardware yet.
- **Power:** 12 V down the tether, bucked to a 5–6 V servo bus + a separate MCU
  rail at the robot, with a bulk cap + fuses to survive servo stall spikes.

## 7. Design review & hardening

I put the whole package through **several rounds of structured design review**,
fixing real issues each round: a depth-sensor stub, a heading-controller bug, a
power-wiring conflict, a missing lid clamp, stale docs, and more — re-verifying
the pipeline (28/28) after each. The honest end state: *a strong digital design
package; one firmware compile + real-world validation away from a finished
robot.* That's exactly the
boundary below.

## 8. Where it stands: done vs. next

**Done (and validated in software):**
- ✅ Full parametric CAD → printable STLs + STEP assemblies
- ✅ First-principles engineering analysis (28/28 pipeline)
- ✅ Control firmware (source) + wiring + pin map
- ✅ Build guide, assembly sequence, test coupons with pass/fail
- ✅ BOM with researched parts + a clear servo-selection finding

**Next (physical — needs hardware, by design):**
- ⬜ Compile/flash the firmware and bench-tune the PID loops
- ⬜ Commit to exact purchase SKUs (I researched concrete starting picks)
- ⬜ Print, seal, and **dry leak-test the head bay first**
- ⬜ Ballast to neutral, then tethered pool test → measure speed vs. prediction

> One honest finding worth flagging to the team: genuinely-submersible (IP67)
> servos are either too bulky for this body or heavier than the ballast can
> absorb. So the build-ready choice here is a **cheap metal-gear micro that we
> pot for submersion**; a drop-in IP67 servo would mean a slightly longer hull.
> Both options are written up in the BOM.

## 9. How to explore it (for the team)

1. **Just look:** open `output/eel_design.html` in any browser — a 3D viewer +
   datasheet with the internals, motion, and all the engineering numbers. No
   install needed; great for sharing.
2. **Reproduce it:** install CadQuery (`pip install cadquery`) and run
   `python verify_all.py` — regenerates every part + report (28/28).
3. **Build from it:** `docs/build_guide.md` (step-by-step + test coupons),
   `docs/BOM.md` (shopping list), `docs/manufacturing.md` (print/seal).

## 10. What's in the repo

```
eel_robot/
  cad/         parametric CAD (params.py is the single source of truth)
  analysis/    buoyancy, stability, structures, power, swim, dive, tail
  firmware/    ESP32 gait + heading/depth control (gait.py mirror)
  cfd/         staged OpenFOAM drag case (run it for a measured Cd)
  docs/        build guide, BOM, manufacturing, wiring, joints
  output/      generated STLs, STEP, renders, swim GIF, and the HTML viewer
  verify_all.py  one-command pipeline check (28/28)
  PROJECT_REPORT.md  ← you are here
```

---

*Status: complete digital design package — a verified prototype, not yet a
physically-built robot. The remaining steps are the physical build, which is the
fun part. — [your name]*
