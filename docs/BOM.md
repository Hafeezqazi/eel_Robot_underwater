# Bill of Materials — Eel Robot (desk/pool prototype)

Quantities for one robot. Prices are rough ballpark (USD, hobby sources) to
size a budget — verify with your supplier. Every line has an **AliExpress
search link** (cheapest route, 2-4 week shipping); Amazon equivalents exist
for all of them if you need it this week. Swap any line and update the
matching value in `cad/params.py` / `analysis/sizing.py`.

> **Materials, print settings, tolerances, sealing procedure → see
> [manufacturing.md](manufacturing.md).** This file is the shopping list; that
> file is how each part is made and sealed.

> ⚠️ **This is a REFERENCE (class-level) list, not an approved-SKU list.** The
> links are *search* links to a part *class*; pick the exact model, confirm
> dimensions / IP rating / current, and record it in **§ Exact chosen parts**
> below before calling the build purchase-ready. The servo especially drives the
> CAD fit — set `cad/params.py` to whatever you actually buy and re-export.

## Actuation
| # | Item | Qty | Notes | ~$ | Buy |
|---|------|-----|-------|----|-----|
| 1 | Metal-gear servo, **~9–20 g, ≥2.5 kg·cm @ 6 V** | 4 | 3 front joints + 1 dive-plane; **truly submersible or pot it** (splash-rated ≠ submerged — see manufacturing §8); sets `SERVO_BODY_*` in params | 40 | [AliExpress](https://www.aliexpress.com/wholesale?SearchText=waterproof+metal+gear+servo+submersible) |
| 2 | Servo horn + M2 hardware | 4 | clamps tongue / dive crank (often included with servo) | 4 | [AliExpress](https://www.aliexpress.com/wholesale?SearchText=9g+servo+horn+arm+set) |
| 2b | 4 mm stainless rod ~225 mm + 2 flanged bushings (4 mm ID) + M2 pushrod wire | 1 set | dive-plane shaft; fins + crank are printed (`dive_planes.py`) | 8 | [AliExpress](https://www.aliexpress.com/wholesale?SearchText=4mm+stainless+steel+round+rod) · [bushings](https://www.aliexpress.com/wholesale?SearchText=4mm+flanged+bushing+brass) |
| 2c | Rubber bands (or TPU flexure / silicone) for the compliant tail | ~10 | rear 2 joints are PASSIVE — bands loop over printed anchor posts; tune count/tension to the ~2 Hz beat | 3 | [AliExpress](https://www.aliexpress.com/wholesale?SearchText=small+rubber+bands+orthodontic) |

## Electronics (head dry bay)
| # | Item | Qty | Notes | ~$ | Buy |
|---|------|-----|-------|----|-----|
| 3 | ESP32 dev board | 1 | controller, runs `eel_gait.ino` | 8 | [AliExpress](https://www.aliexpress.com/wholesale?SearchText=ESP32+devkit+v1+30+pin) |
| 4 | PCA9685 16-ch PWM driver | 1 | I2C servo driver | 5 | [AliExpress](https://www.aliexpress.com/wholesale?SearchText=PCA9685+16+channel+servo+driver) |
| 5 | MPU6050 IMU | 1 | heading/attitude (I2C) | 3 | [AliExpress](https://www.aliexpress.com/wholesale?SearchText=MPU6050+module+GY-521) |
| 6 | MS5837-30BA depth/pressure sensor | 1 | depth + leak-pressure (I2C); face epoxies into the lid port | 25 | [AliExpress](https://www.aliexpress.com/wholesale?SearchText=MS5837+30BA+pressure+sensor+module) |
| 7 | Leak probe (conductive pads) | 1 | GPIO34 safety cutoff (two bare wires + 1 MΩ pulldown works) | 2 | [AliExpress](https://www.aliexpress.com/wholesale?SearchText=water+leak+detection+sensor+module) |
| 8 | 2S LiPo 300–500 mAh | 1 | buffer; the 12 V tether supplies bulk power | 10 | [AliExpress](https://www.aliexpress.com/wholesale?SearchText=2S+7.4V+500mAh+lipo+battery) |
| 9 | Buck converter, **12 V → 5–6 V, ≥5 A** (servo bus) | 1 | robot-local; powers PCA9685 V+ and all 4 servos | 4 | [AliExpress](https://www.aliexpress.com/wholesale?SearchText=12V+to+5V+5A+buck+converter+module) |
| 9b | Buck converter, **12 V → 5 V, ~1 A** (MCU rail, into ESP32 VIN) | 1 | **separate** from the servo bus so stall spikes can't reset the MCU | 3 | [AliExpress](https://www.aliexpress.com/wholesale?SearchText=mini+360+buck+converter+module) |
| 9c | Bulk capacitor **1000–2200 µF, 16 V** + **4 A fuse** (servo bus) + small LED fuse | 1 | brownout fix from `power.py` (cap across the bus, fuse the bus + LED) | 3 | [AliExpress](https://www.aliexpress.com/wholesale?SearchText=2200uF+16V+capacitor+blade+fuse+holder) |

## Camera & light (the payload)
| # | Item | Qty | Notes | ~$ | Buy |
|---|------|-----|-------|----|-----|
| C1 | Analog FPV mini camera, 700TVL+ CMOS, 5 V, PAL/NTSC | 1 | sits dry behind the nose window; composite out over a tether pair | 9 | [AliExpress](https://www.aliexpress.com/wholesale?SearchText=mini+FPV+camera+700TVL+CMOS+5V) |
| C2 | White LED module, 1–3 W (or 5730 LED board) | 1 | headlight behind the window, below the lens; black foam baffle between LED and lens kills internal glare | 3 | [AliExpress](https://www.aliexpress.com/wholesale?SearchText=3W+white+LED+module+5V) |
| C3 | Logic-level MOSFET board (AO3400 / IRLZ44 module) | 1 | ESP32 GPIO25 PWM dims the LED — never drive the LED from the pin | 2 | [AliExpress](https://www.aliexpress.com/wholesale?SearchText=mosfet+driver+module+trigger+switch+3.3V) |
| C4 | Acrylic / polycarbonate disc Ø30 × 3 mm (or cut from sheet) | 2 | nose window; epoxy-bond into the printed seat (`WINDOW_SEAT_D`); buy 2, scratch 1 | 4 | [AliExpress](https://www.aliexpress.com/wholesale?SearchText=clear+acrylic+disc+30mm+3mm) |
| C5 | USB video capture dongle (RCA composite → USB) | 1 | topside: turns the analog feed into a webcam on the laptop | 8 | [AliExpress](https://www.aliexpress.com/wholesale?SearchText=USB+video+capture+card+RCA+AV) |

## Tether & topside
| # | Item | Qty | Notes | ~$ | Buy |
|---|------|-----|-------|----|-----|
| 10 | Cat5e cable, 3–5 m | 1 | 2 pairs power, 1 pair USB-serial, 1 pair composite video | 8 | [AliExpress](https://www.aliexpress.com/wholesale?SearchText=cat5e+ethernet+cable+5m+outdoor) |
| 11 | **Bench PSU 12 V / ≥3 A** | 1 | topside; feeds 12 V down the tether (bucked at the robot) | (have) | [AliExpress](https://www.aliexpress.com/wholesale?SearchText=12V+3A+power+supply+adapter) |
| 12 | USB-serial adapter (CP2102/CH340) | 1 | if not using the ESP32's own USB through the tether | 3 | [AliExpress](https://www.aliexpress.com/wholesale?SearchText=CP2102+USB+serial+adapter) |

## Sealing (head bay)
| # | Item | Qty | Notes | ~$ | Buy |
|---|------|-----|-------|----|-----|
| 13 | O-ring, 2 mm cord, ~60 mm ID (metric assortment ok) | 2 | lid seal + a spare (see `ORING_*` params) | 3 | [AliExpress](https://www.aliexpress.com/wholesale?SearchText=nitrile+o-ring+assortment+2mm+cross+section) |
| 14 | Cable gland PG7 (or marine epoxy pot) | 1 | tether pass-through in the lid (`PENETRATOR_D` 10 mm) | 3 | [AliExpress](https://www.aliexpress.com/wholesale?SearchText=PG7+waterproof+cable+gland) |
| 15 | Marine / 2-part epoxy (30 min, not 5 min) | 1 | pots the servo-wire gland, the sensor port and bonds the window | 6 | [AliExpress](https://www.aliexpress.com/wholesale?SearchText=marine+epoxy+two+part+waterproof) |
| 16 | Silicone grease | 1 | O-ring lubrication | 4 | [AliExpress](https://www.aliexpress.com/wholesale?SearchText=silicone+grease+o-ring+waterproof) |

## Mechanical / printed
| # | Item | Qty | Notes | ~$ | Buy |
|---|------|-----|-------|----|-----|
| 17 | PETG filament (PLA ok, freshwater) | ~150 g | prints all rigid `print_*.stl` | 5 | [AliExpress](https://www.aliexpress.com/wholesale?SearchText=PETG+filament+1.75mm+1kg) |
| 18 | TPU 95A filament (skin sleeve) | ~80 g | covers joint gaps (`skin.py`) | 10 | [AliExpress](https://www.aliexpress.com/wholesale?SearchText=TPU+95A+filament+1.75mm) |
| 19 | Joint pin, 3 mm **stainless** dowel ×25 mm (or M3 bolts) | 5 | `PIN_D`; do not print | 3 | [AliExpress](https://www.aliexpress.com/wholesale?SearchText=3mm+stainless+steel+dowel+pin+25mm) |
| 20 | Tail-fin foil sheet (or print it) | 1 | bolts to seg5 | 3 | [AliExpress](https://www.aliexpress.com/wholesale?SearchText=polycarbonate+sheet+1.5mm) |
| 21 | **Lead keel** ~200 g, low + forward | 1 | neutral + roll + trim (`stability.py`) | 5 | [AliExpress](https://www.aliexpress.com/wholesale?SearchText=lead+sheet+roll+fishing+weight) |
| 21b | **Buoyancy foam** ~59 cm³ closed-cell (2 discs cut to the bore, ~38+20 cm³) | 2 | seg2 + seg3 bays; combined centroid z~310 → floats level | 4 | [AliExpress](https://www.aliexpress.com/wholesale?SearchText=closed+cell+buoyancy+foam) |
| 21c | **Adjustable trim weight** ~15 g on a fore/aft slide | 1 | final LEVEL trim in water (sub-mm trim is touchy) | 2 | [AliExpress](https://www.aliexpress.com/wholesale?SearchText=m3+brass+weight) |
| 22 | Heat-set brass inserts, M2 / M3 | ~10 | threads in printed parts | 3 | [AliExpress](https://www.aliexpress.com/wholesale?SearchText=brass+heat+set+insert+M3+kit) |
| 23 | Stainless M2 / M3 screw assortment | 1 | lid, fins, hubs, horns | 4 | [AliExpress](https://www.aliexpress.com/wholesale?SearchText=stainless+M2+M3+screw+assortment+kit) |
| 24 | Pivot bushings 3 mm PTFE/brass (optional) | 5–10 | reduce joint wear | 4 | [AliExpress](https://www.aliexpress.com/wholesale?SearchText=3mm+ID+flanged+brass+bushing) |

**Rough total: ~$190** (excluding bench PSU). Biggest single items are the
depth sensor (#6, $25 — droppable if you skip depth-hold and drive the planes
open-loop) and the servos.

## Exact chosen parts (researched starting picks — confirm before buying)
These few items drive CAD fit / sealing / reliability. Below are **concrete,
currently-available picks** to start from (researched, not invented); confirm the
exact dimensions of what you actually receive, set `cad/params.py`, and re-export.
The CAD is currently dimensioned to the **Path-A servo** row.

| Critical part | Researched pick | Key dims | params it sets |
|---|---|---|---|
| **Servo ×4 — Path A (current CAD)** | **Tower Pro MG90S**-class metal-gear micro (~9–14 g, ~2.2 kg·cm), **potted** for submersion | ~22.8 × 12.2 × 22.7 mm body | `SERVO_BODY_*`=23/12.2/22.7, `SERVO_TORQUE_RATED`=0.20 |
| Servo ×4 — Path B (IP67, needs upsize) | [Savox **SW-0250MG**](https://www.savoxusa.com/products/savsw0250mg-waterproof-digital-micro-servo) — true IP67, no potting | 29.5 × 14.0 × 32.5 mm, **25 g**, 5 kg·cm | see note ↓ |
| O-ring (lid) | NBR 70A, **60 mm ID × 2.0 mm** cord (metric assortment) | ID 60, cord 2.0 | `ORING_CS`=2.0, `ORING_GROOVE_*` |
| Cable gland | **PG7** nylon waterproof gland (3–6.5 mm) | thread PG7, bore 10 mm | `PENETRATOR_D`=10 |
| Depth sensor | [Blue Robotics **Bar30**](https://bluerobotics.com/store/sensors-cameras/sensors/bar-depth-pressure-sensor/) (MS5837-30BA, I²C, ±2 mm, $85) — or a bare MS5837-30BA module (~$25) | I²C, 3.3–5.5 V | `SENSOR_PORT_*` |
| Window disc | Cast **acrylic Ø30 × 3 mm** disc (or cut from sheet) | Ø30, t3 | `WINDOW_SEAT_*` |

> **Servo path note (a real design finding, not hand-waving).** Genuinely
> submersible (IP67) servos are either *bulky* (20 kg-class units are 40×20×40 mm
> / 60 g — they don't fit a 70 mm body) or, like the Savox SW-0250MG, *fit but are
> 25 g — +44 g over the micro*. That extra mass needs ~+44 cm³ more buoyancy than
> the servo-crowded bays can hold (the narrow tail caps foam ≈ 79 cm³), so
> **Path B requires a longer hull or an external foam collar**. **Path A**
> (a cheap metal-gear micro you pot yourself) is what the current balanced CAD
> uses — neutral, roll-stable, ~2° trim (`stability.py`). Pick A for a drop-in
> build; pick B only if you also upsize the body and re-run `stability.py`.

## Printed parts manifest
`print_head.stl` (now with the nose-window seat), `print_lid.stl` (carries
the joint-1 tongue; 3 penetrations: tether, wire gland, sensor port),
`print_seg1.stl` … `print_seg5.stl` (band anchor posts + drain holes are
printed in), `print_tailfin.stl`, `print_dive_plane.stl` (×2, mirror one),
`print_dive_crank.stl`, `print_skin.stl` (TPU), `print_test_rig.stl`.
`print_pin.stl` (×5) and `print_dive_shaft.stl` are **dry-fit templates
only** — use the stainless pins (#19) and 4 mm rod (#2b) in water.

**Stability / ballast hardware** (`cad/ballast.py`): `print_keel_strap.stl`,
`print_trim_rail.stl`, `print_trim_carrier.stl`, `print_foam_retainer.stl`.
**Passive-tail flexures** (`cad/tail_flexure.py`, print in TPU):
`print_flexure_2p8.stl`, `_3p4.stl`, `_4p0.stl` — print all three, bench-pick
by `f_n` (build_guide §12).

**Test coupons** (`cad/test_coupons.py` — print + test BEFORE the full body):
`coupon_servo.stl` (servo + mount fit), `coupon_potting.stl` (wire-gland potting
cup), `coupon_oring_bore.stl` + `coupon_oring_plug.stl` (radial-seal fit). Pass
criteria in build_guide §12.
