# Manufacturing & Materials Specification — Eel Robot

The single place that answers: **what is each part made of, how is it made,
what hardware holds it together, and how is it sealed.** Numbers trace to
`cad/params.py`; change them there and re-export. Tier: desk/pool prototype.

---

## 1. Material per part (metal vs plastic)

| Part | Material | Process | Why |
|------|----------|---------|-----|
| Head bay + lid | **PETG** (or tough resin) | FDM print (or SLA) | watertight, low water-absorption, impact-tough; resin gives the best sealing surface |
| Body segments seg1–5 | **PETG** (PLA ok for short freshwater) | FDM print | complex shape, light, free-flooding so not pressure-critical |
| Dive planes, tail fin | PETG | FDM print | thin foils, low load |
| Skin sleeve | **TPU 95A** (or cast silicone) | FDM print / mould | must flex over the joints |
| Test rig | PLA/PETG | FDM print | dry bench tool |
| **Joint pins** (×5) | **Stainless steel** 3 mm dowel (or A2/A4 M3) | bought | bearing/wear + corrosion — *do not print* |
| **Dive shaft** | **Stainless steel** 4 mm rod | bought | torque + wear |
| **Fasteners** | **Stainless** M2 / M3 screws | bought | thread strength, corrosion |
| **Thread inserts** | **Brass** heat-set M2 / M3 | bought | printed plastic can't hold threads |
| Pivot bushings (optional) | Brass / PTFE, 3 mm ID flanged | bought | reduce pivot wear (printed bore works for proto) |
| Ballast | **Lead or steel** shot/sheet | bought | density — needs metal |
| **Nose window** | **Acrylic / polycarbonate** disc Ø30 × 3 mm | bought | optically clear for the camera — printed plastic is not |

**Rule of thumb:** *fairings & body = printed plastic; anything that bears a
load, threads, wears, or must be dense = metal (stainless if you'll go salt
water; brass for inserts; lead/steel for ballast).*

---

## 2. 3-D print settings

| Setting | Value | Note |
|---|---|---|
| Layer height | 0.16–0.20 mm | 0.16 on head bay for seal finish |
| Walls / perimeters | **≥ 4** (6 on head bay) | water tightness comes from walls, not infill |
| Infill | 30–40 % body segments; near-solid head bay & thin parts | |
| Material | PETG ~245 °C / bed 80 °C; TPU ~225 °C slow | dry filament — PETG/TPU absorb moisture |
| Skin (TPU) | 0.8–1.2 mm wall, 100 % flow, 15–20 mm/s | print slow for layer bonding |

**Print orientation**
- **Head bay:** flat window face **down** (nose down), open rear **up** → clean bore, flat seat, no seam across the seal.
- **Segments:** body axis **vertical (Z up)** → round cross-section, minimal supports; clevis prongs may need light support.
- **Dive planes / tail fin:** flat on the bed.
- **Pins / shaft:** **do not print — use the metal rod.**

**Supports:** servo pockets, clevis undersides, penetrator bore, and the small
rubber-band anchor posts that hang from the shell ceiling around the passive
joints (seg3 rear, seg4, seg5). **Drain holes** (Ø3 mm, `DRAIN_HOLE_D`) are
printed into the low point of each free-flooding segment so water fills/drains.

---

## 3. Tolerances & fits (printed)

| Feature | Param | Value | Action |
|---|---|---|---|
| Pin bore clearance | `PIN_CLEAR` | 0.30 mm over pin | ream/drill bore to final Ø after print |
| Servo pocket clearance | `SERVO_POCKET_CLEAR` | 0.6 mm | tune to your exact servo |
| Lid slip fit | — | 0.2 mm | sand for a smooth O-ring entry |
| Clevis gap | `CLEVIS_GAP` | tongue + 1.0 mm | 0.5 mm/side |

FDM holes print **undersize** — drill `PIN_D` (3 mm) and shaft (4 mm) bores to
size with a bit. Print one segment + the joint demo FIRST and adjust these.

---

## 4. Sealing specification

Only the **head bay is sealed**; segments are **free-flooding** (drain holes
are printed in). Six sealed interfaces:

| Interface | Seal | Spec (from params) |
|---|---|---|
| Lid → bay bore | radial O-ring | bay bore Ø **64 mm** (= 2·(R_MAX−BAY_WALL)). Use **O-ring ≈ 60 mm ID × 2 mm CS** (NBR/Buna). ONE groove, **on the lid plug**: `ORING_GROOVE_W` 2.4 × `ORING_GROOVE_D` 1.5 mm (the bay bore is plain). Target squeeze 15–25 % — verify on the printed groove. |
| Tether → lid | gland | `PENETRATOR_D` 10 mm bore, offset **+12 mm (up)**: PG7 cable gland **or** pot with marine epoxy |
| Servo / leak wires → lid | epoxy pot | `WIRE_GLAND_D` 10 mm bore, offset **−12 mm (down)**: feed all 4 servo leads + leak probe through, then **pot solid with marine epoxy** (fill the bore, wires fanned so epoxy wets every jacket) |
| MS5837 → lid | epoxy pot | `SENSOR_PORT_D` 8 mm bore at **x = +14 mm**: sensor face (gel side) looks OUT through the port into the flooded seg1; epoxy the rim from the dry side. Do NOT get epoxy on the gel. |
| Window → nose | epoxy bond | acrylic disc Ø30 × 3 into the `WINDOW_SEAT_D` 31 mm recess: thin bead of epoxy on the 3.5 mm lip, press flush, wipe squeeze-out off the aperture before it cures |
| Servo case/shaft | waterproofing | buy **waterproof servos**, or pot the case seam + shaft with marine grease/epoxy |

Aids: **silicone grease** on every O-ring; **conformal coat** the PCB as a
backup; arm the **leak sensor** before submerging.

---

## 5. Fastener & hardware schedule

| Use | Item | Qty | Detail (pilot / insert / length) |
|---|---|---|---|
| Joint pivots | 3 mm SS dowel (or M3×~25 + nylock) | 5 | Ø3.0 pin bore; double-shear, big SF (`structures.py`) |
| Dive-plane shaft | 4 mm SS rod, ~225 mm | 1 | rides in 2 hull bushings; grub-screwed to the crank |
| Servo horns | M2 self-tap (servo-supplied) | 4 | into the horn; pattern set by the chosen servo |
| **Lid clamp** | **M3×10 SS cap + brass heat-set insert** | **3** | ears at PCR 37 mm; insert **Ø4.0×6** in the head ear, **Ø3.4** clearance in the lid tab (`head_bay.py`) |
| Servo mounts | M2.5 self-tap into bosses | 8 | 2 per driven servo + dive; pilot Ø2.1 in `body.servo_mount` |
| Tail fin → seg5 | M3×10 SS + insert | 2 | insert Ø4.0×6 |
| Dive-plane hubs → shaft | M3 grub/set screw | 2 | onto a shaft flat |
| Heat-set inserts | brass M3, Ø4.0 OD × ~5–6 long | ~7 | lid ears (3) + tail (2) + spares |
| Pivot bushings (opt.) | 3 mm ID PTFE/brass | 5–10 | longer joint life |

**Ballast retention** (the stability fix is *not* optional — install it
repeatably): the **2 foam discs** are closed-cell, sized to the seg2/seg3 bore
(`params.FOAM_PLUGS`) — **friction-fit + a dab of silicone** so they can't float
out (they're positively buoyant). The **lead keel** epoxies into the forward
belly with a **2× M3 strap** as backup. The **trim weight** (~15 g) rides on a
**slotted rail / Velcro** so you can slide it fore/aft and set level in the water.

---

## 6. Waterproofing procedure (do in this order)

1. Print head bay + lid (PETG/resin), ream the bore smooth, sand the window
   seat flat.
2. **Bond the nose window:** thin epoxy bead on the seat lip, press the
   acrylic disc in flush, wipe the aperture clean. Cure fully.
3. Fit O-ring to the lid groove, grease it, insert lid — check even squeeze.
4. **Dry leak test the EMPTY bay first** (window in, lid bores taped/plugged):
   weight it, submerge 10 min, look for ingress (tissue paper inside /
   bubbles out). Fix before adding electronics.
5. Fit the tether gland (+12 mm bore); feed servo + leak wires through the
   −12 mm bore and **pot it solid with epoxy**; epoxy the MS5837 face into
   the +14 mm port (gel side out, no epoxy on the gel). Cure; re-test.
6. Waterproof servos (buy waterproof, or pot seam + shaft); conformal-coat PCB.
7. Assemble; **final powered leak test** with the leak sensor armed — camera
   picture up, light on, servos sweeping, 10 min submerged.
8. Ballast/trim to neutral (~150 g, slightly positive for fail-safe surfacing).

---

## 7. Internal layout — where each thing goes

Modeled in `cad/internals.py`; see it live in `output/eel_design.html` (tick
**internals** → body turns translucent, or click any electronics part).

- **Head dry bay** holds the electronics on a **tray that slides in from the
  rear lid**: **2S LiPo at the bottom-centre** (heaviest → keep low and a touch
  forward of the centre of buoyancy for pitch stability), **ESP32 + PCA9685**
  on the sides, **MPU6050 + buck** on top, **MS5837 on the lid end-cap** with
  its face epoxied into the lid's sensor port (reads ambient pressure through
  the flooded seg1 behind).
- **Camera + LED** sit at the very front, looking out the nose window: lens on
  the axis, LED below it, a **black foam baffle between LED and lens** so the
  light doesn't flare the image off the acrylic. Velcro or hot-glue both to a
  small printed shelf / the bay floor.
- **Dive servo (the 4th)** sits in the **front body just behind the head**,
  axis **across** the body, coupled to the dive-plane shaft — a **waterproof
  servo in the free-flooding section** (no extra shaft seal needed).
- **Joint servos (×3)** — one inside each DRIVEN segment (seg1–seg3), at the
  segment's front pivot. Joints 4–5 are the passive compliant tail: no servo —
  a printed **TPU flexure is primary** (`tail_flexure.py`, 3 variants; bench-pick
  by f_n), with **rubber bands over the anchor posts as the fallback**.
- Battery placement is the main **trim/CG** lever: shift it fore/aft to set the
  pitch attitude, low to keep the centre of mass under the centre of buoyancy.

## 8. What is NOT specified (decide when you buy)

- **Exact servo** → sets `SERVO_BODY_*` + `SERVO_TORQUE_RATED` + horn pattern in
  `params.py`. **Reference design point:** a **metal-gear ~9–20 g micro servo,
  ≥2.5 kg·cm @ 6 V** (torque is not the limiter — `structures.py`/`dive_linkage.py`
  show ~20–40× margin — *fit and waterproofing* are). After you buy, measure the
  body L×W×H + horn and set `params.py`, then print the servo-pocket fit coupon.
  - **Waterproofing reality (important):** most "waterproof" hobby servos are
    *splash/IP-rated, not rated for continuous submersion*. For a free-flooding
    body either buy a genuinely submersible servo **or pot the case seam + shaft
    exit** yourself, and run the wet-servo soak coupon (build_guide.md §12) before
    trusting it. This is the single biggest reliability risk in the build.
- Resin vs PETG for the bay (resin seals better, PETG is tougher).
- Whether you need bushings (proto: skip; longer life: add).
- Salt vs fresh water → drives stainless **316** vs 304 and NBR vs EPDM O-rings.
