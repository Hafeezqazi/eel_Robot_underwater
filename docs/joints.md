# Joint / DOF Reference

The eel is a **serial chain of 5 revolute (yaw) joints**. The head is the
fixed base; each driven segment rotates about a vertical pin relative to the
part ahead of it. All values are generated from `cad/params.py` — re-run
`python params.py` and `python gait.py` to regenerate after any change.

## Joint hardware (every joint identical in kind)

```
   part AHEAD (forward)            part BEHIND (aft)
   ───────────────┐                ┌───────────────
        TONGUE  ──┼──►   ((pin))  ◄┼──  CLEVIS (fork)
   (single blade) │   vertical Y    │  (two prongs straddle the tongue)
   ───────────────┘    pin axis     └───────────────
                         ▲
                    SERVO output shaft (in the aft part) is coaxial with the
                    pin and clamps the tongue → energising it yaws the aft part.
```

- **Type:** revolute, 1 DOF each, rotation about the global **Y (vertical)**
  axis → **yaw** (side-to-side), the swimming plane.
- **Travel:** ±28° mechanical (`JOINT_TRAVEL_DEG`).
- **Pin:** 3 mm dowel / M3 (`PIN_D`), bore clearance `PIN_CLEAR` = 0.3 mm.
- **Drive:** one waterproof servo housed in the aft segment, shaft on the pin
  axis, horn clamped to the forward part's tongue (direct drive, no linkage).

## Joint table

| Joint | Station z (mm) | Connects | Drive | Body radius here (mm) |
|------:|---------------:|----------|-------|----------------------:|
| 1 | 140 | head → seg1 | **servo** (in seg1) | 35.0 |
| 2 | 200 | seg1 → seg2 | **servo** (in seg2) | 34.1 |
| 3 | 260 | seg2 → seg3 | **servo** (in seg3) | 29.8 |
| 4 | 320 | seg3 → seg4 | *passive* (compliant) | 23.2 |
| 5 | 380 | seg4 → seg5 | *passive* (compliant) | 16.2 |

**Joints 4–5 are passive** — no servo. A 9 g servo won't fit the thin tail
(seg5 ~32 mm dia), so the rear two joints are a **springy compliant tail** the
body wave flexes on its own (biomimetic). Each passive joint has a pair of
**printed anchor posts** (hanging from the shell ceiling, one each side of the
pivot — already in the segment STLs); loop a rubber band between them and tune
band count/tension so the tail naturally undulates at the ~2 Hz beat. A TPU
flexure or silicone element works as an alternative spring.

**Segment gap:** adjacent shells are spaced **8 mm apart** (`SEGMENT_GAP`) so
they don't collide when the joint bends — the clevis/tongue/pin bridge the gap,
and the flexible skin sleeve covers it. Without the gap the rigid shells overlap
on any bend.

Tail fin: passive, **bolted** to seg5 rear (no DOF).

## Kinematics (forward chain)

`assembly.py` poses the body by marching the chain: each segment is placed at
its joint pivot and rotated by the **cumulative** sum of joint angles, so a
joint-angle vector `[θ1..θ5]` fully determines the pose. The pivot of joint
i+1 advances from joint i by the segment length rotated into the current
heading.

## Gait phasing (from `firmware/gait.py`)

Travelling body wave `θ_i(t) = A_i·sin(2π f t − φ_i) + heading`:

| Joint | Phase lag φ (deg) | Cruise amplitude A (deg) |
|------:|------------------:|-------------------------:|
| 1 | 101 | 3.9 |
| 2 | 144 | 4.7 |
| 3 | 187 | 5.4 |
| 4 | 230 | 6.2 |
| 5 | 274 | 7.0 |

- **f** = 2.0 Hz cruise. Strouhal ≈ 0.22 at the EBT-predicted speed (efficient
  band); at the ×0.5-derated realistic speed it reads ~0.44 — typical of hobby
  robotic swimmers. Pool-tune amplitude/frequency with the `S`/`H` commands.
- Cruise amplitude peaks at 7° (`CRUISE_AMP_DEG`); the ±28° mechanical travel
  is reserve for turns/bursts. Amplitude grows head→tail (anguilliform).
- **Servos drive joints 1–3** (`gait.command()` returns 3 angles). Joints 4–5
  (the compliant tail) **follow the same wave passively** — `gait.body_wave_angles()`
  returns all 5 for the sim/animation.
- A constant `heading` bias added to the driven joints steers the robot (turn).

## Extra DOF — bow dive planes (depth control)

Beyond the 5 swim joints, a **4th servo** pitches a pair of bow dive planes
about the transverse **X** axis (`DIVE_PLANE_Z`, ±25°). This is a **pitch** DOF
(not part of the undulation chain) that generates vertical lift while swimming
→ 3-D diving. Driven open-loop or by the `DepthHold` PD controller in
`firmware/gait.py`. Convention: **+angle = dive**. No authority at zero speed.
