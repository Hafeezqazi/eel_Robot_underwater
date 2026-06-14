"""
design_page.py  --  ONE self-contained HTML design page for the whole robot.

Generates output/eel_design.html: an interactive, animated 3-D fish PLUS a
parts catalogue (click a part -> it highlights on the fish and shows material,
size, power, qty, price and where-to-buy links), a spec dashboard, and the
full BOM. This single file is meant to be THE shareable design page.

Geometry + gait animate in the browser (three.js from CDN). Run:
    python design_page.py   ->  output/eel_design.html
"""

import os
import sys
import math
import json
import urllib.parse

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "firmware"))
sys.path.insert(0, os.path.join(HERE, "..", "analysis"))
import params as P
import gait
from body import driven_segments, servo_mock
from head_bay import build_head, build_lid
from joints import pin as joint_pin, servo_horn
import dive_planes
import internals
from assembly import tail_fin

OUT = os.path.join(HERE, "..", "output")

COL = {"head": "#2e8b57", "lid": "#9aa0a6", "body": "#4682b4",
       "servo": "#6b6f76", "pin": "#ffd700", "plane": "#e08a00",
       "shaft": "#808890", "tail": "#2e8b57", "horn": "#d14fa0",
       "post": "#2f9e6e"}


# ---------------------------------------------------------------- geometry
def mesh(shape, color, item, tol=0.6, translate=None, internal=False):
    if hasattr(shape, "val"):
        shape = shape.val()
    if translate is not None:
        shape = shape.translate(translate)
    verts, tris = shape.tessellate(tol)
    pos = []
    for v in verts:
        pos += [round(v.x, 2), round(v.y, 2), round(v.z, 2)]
    idx = []
    for t in tris:
        idx += [int(t[0]), int(t[1]), int(t[2])]
    return {"item": item, "color": color, "pos": pos, "idx": idx,
            "internal": internal}


def build_geo():
    servo = servo_mock()
    pinm = joint_pin()
    geo = {
        "params": {
            "HEAD_LEN": P.HEAD_LEN, "SEG_LEN": P.SEG_LEN, "N": P.N_JOINTS,
            "BODY_LENGTH": P.BODY_LENGTH, "DIVE_PLANE_Z": P.DIVE_PLANE_Z,
            "f": gait.tail_beat_freq(), "phi": gait.phase_lags(),
            "amp": gait.amplitude_envelope(),
        },
        "base": [mesh(build_head(), COL["head"], "head_bay"),
                 mesh(build_lid(), COL["lid"], "head_bay",
                      translate=(0, 0, P.HEAD_LEN - P.LID_LEN))],
        "dive": [mesh(dive_planes.plane(+1), COL["plane"], "dive_planes"),
                 mesh(dive_planes.plane(-1), COL["plane"], "dive_planes"),
                 mesh(dive_planes.shaft(), COL["shaft"], "dive_planes",
                      internal=True)],
        "seg": [], "tail": [mesh(tail_fin(), COL["tail"], "tail_fin")],
    }
    hornm = servo_horn()
    foam_plugs = internals.foam_plugs()               # [(z_centre, solid)]
    for i, (name, sol, part) in enumerate(driven_segments()):
        segmeshes = [mesh(sol, COL["body"], "body_segments")]
        if part["driven"]:                            # servo + horn on driven joints
            segmeshes.append(mesh(servo, COL["servo"], "servos", internal=True))
            segmeshes.append(mesh(hornm, COL["horn"], "servos", internal=True))
        # (passive segments: the rubber-band anchors are printed into the
        #  segment solid itself -- body.hang_post)
        segmeshes.append(mesh(pinm, COL["pin"], "pins", internal=True))
        # buoyancy foam discs live in whichever bay spans their centre, in that
        # segment's LOCAL frame, so they bend with the body (not the base frame)
        seg_front = P.HEAD_LEN + i * P.SEG_LEN
        for zc, fsol in foam_plugs:
            if seg_front <= zc < seg_front + P.SEG_LEN:
                segmeshes.append(mesh(fsol, "#d8d8cf", "foam", internal=True,
                                      translate=(0, 0, zc - seg_front)))
        geo["seg"].append(segmeshes)
    # internal layout: electronics/battery in the head bay + the dive servo.
    # The dive servo is FIXED to the body (base frame) -- NOT in the dive group,
    # else it double-offsets and swings with the plane pitch.
    geo["bay"] = [mesh(s, c, it, internal=True)
                  for it, c, s in internals.components()]
    geo["bay"].append(mesh(internals.dive_servo(), COL["servo"], "servos",
                           internal=True))
    return geo


# ---------------------------------------------------------------- specs
def gather_specs():
    s = []
    try:
        import sizing
        geo = sizing.geometry()
        parts, dry, disp, ball, dispf, ballf = sizing.mass_budget(geo)
        pw = sizing.power(sizing.hydro(geo))
        import swim_sim
        sp = swim_sim.predict_speed()
        U = sp["U"] * swim_sim.EBT_DERATE
        import structures
        hull = structures.hull_check()
        s = [
            ("Length x diameter", "500 x 70 mm"),
            ("Mass (dry / +ballast)", f"{dry*1000:.0f} g / +{ballf*1000:.0f} g"),
            ("Degrees of freedom", "3 driven + 2 passive joints + dive planes"),
            ("Cruise speed", f"~{U:.2f} m/s ({U/0.5:.1f} body-len/s)"),
            ("Tail-beat / Strouhal", f"{P.CRUISE_FREQ_HZ:.1f} Hz / St {sp['St_real']:.2f}"),
            ("Dive: min speed / rate", "0.24 m/s / ~0.5 m/s"),
            ("Depth (rated / collapse)", f"2 m / ~{hull['depth_buckle']:.0f} m"),
            ("Power draw", f"~{pw['p_total']:.1f} W ({pw['amps']:.2f} A @ 7.4 V)"),
            ("Buoyancy control", "free-flooding body, sealed head bay"),
            ("Material", "PETG body / stainless pins / TPU skin"),
        ]
    except Exception as e:                      # fallback if analysis import fails
        s = [("Length x diameter", "500 x 70 mm"),
             ("Mass (dry/+ballast)", "~390 g / +~150 g"),
             ("DOF", "3 driven + 2 passive joints + dive planes"),
             ("Cruise speed", "~0.5 m/s"),
             ("Depth", "2 m rated / ~84 m collapse"),
             ("Power", "~6.7 W @ 7.4 V (incl. light)"),
             ("note", f"specs fallback: {e}")]
    return [{"k": k, "v": v} for k, v in s]


def gather_eng():
    """Every engineering number, computed from the analysis modules."""
    import sizing
    import swim_sim
    import dive as dive_mod
    import structures
    geo = sizing.geometry()
    parts, dry, disp, ball, dispf, ballf = sizing.mass_budget(geo)
    pw = sizing.power(sizing.hydro(geo))
    rho, A, Cd, eta = 1000.0, geo["frontal"], P.CD_AXIAL, sizing.PROP_EFFICIENCY
    sp = swim_sim.predict_speed()
    U = sp["U"] * swim_sim.EBT_DERATE
    hull = structures.hull_check()
    pinc = structures.pin_check()
    orng = structures.oring_check()
    Ad, AR, Clmax = dive_mod.geom()

    # power vs speed
    speeds = sorted({0.2, 0.3, round(U, 2), 0.55, 0.75})
    ptab = [{"v": v, "drag": 0.5 * rho * Cd * A * v * v * 1000,
             "pd": 0.5 * rho * Cd * A * v ** 3 * 1000,
             "pp": 0.5 * rho * Cd * A * v ** 3 / eta * 1000} for v in speeds]
    # gait per joint
    phi = [math.degrees(x) for x in gait.phase_lags()]
    amp = gait.amplitude_envelope()
    gtab = [{"j": i + 1, "z": int(P.JOINT_Z[i]), "phi": round(phi[i]),
             "amp": round(amp[i], 1)} for i in range(P.N_JOINTS)]
    # dive
    reserve = 20.0 / 1000 * P.G
    vmin = math.sqrt(2 * reserve / (rho * Clmax * Ad))
    V = 0.55
    Lmax = dive_mod.downforce(V, Clmax)
    Cdi = Clmax ** 2 / (math.pi * AR * 0.7)
    Dtot = 0.5 * rho * (0.10 + Cdi) * Ad * V * V + 0.5 * rho * Cd * A * V * V
    glide = math.degrees(math.atan(Lmax / Dtot))
    descent = V * math.sin(math.radians(glide))
    return {
        "power": {"table": ptab, "hotel": sizing.HOTEL_W,
                  "servos": pw["p_servos"], "total": pw["p_total"],
                  "amps": pw["amps"], "eta": eta, "A": A * 1e4, "Cd": Cd},
        "buoy": {"dry": dry * 1000, "flood": dispf * 1000,
                 "inh": (dispf - dry) * 1000, "inhN": (dispf - dry) * P.G,
                 "ballast": ballf * 1000, "sealed": disp * 1000,
                 "sealedInh": (disp - dry) * 1000,
                 "mass": [{"k": k, "g": round(v * 1000, 1)}
                          for k, v in parts.items()]},
        "perf": {"U": U, "Uub": sp["U"], "St": sp["St_real"], "f": P.CRUISE_FREQ_HZ,
                 "tailamp": sp["tail_amp"] * 1000, "gait": gtab},
        "dive": {"area": Ad * 1e4, "AR": AR, "Clmax": Clmax, "vmin": vmin,
                 "L04": dive_mod.downforce(0.4, Clmax) * 1000,
                 "L075": Lmax * 1000, "descent": descent, "glide": glide},
        "struct": {"depthRated": P.DEPTH_RATING,
                   "depthCollapse": hull["depth_buckle"],
                   "hoop": hull["hoop"] / 1e6, "sfYield": hull["sf_yield"],
                   "Pcr": hull["Pcr"] / 1000, "sfBuckle": hull["sf_buckle"],
                   "pinF": pinc["F"], "pinTau": pinc["tau"] / 1e6,
                   "pinSF": pinc["sf"], "oring": orng["squeeze"]},
    }


# ---------------------------------------------------------------- parts catalogue
def _v(name, query):
    base = {"Amazon": "https://www.amazon.com/s?k=",
            "Adafruit": "https://www.adafruit.com/?q=",
            "Pololu": "https://www.pololu.com/search?query=",
            "AliExpress": "https://www.aliexpress.com/wholesale?SearchText=",
            "McMaster": "https://www.mcmaster.com/",
            "BlueRobotics": "https://bluerobotics.com/?s="}
    if name == "McMaster":
        return {"name": name, "url": base[name]}
    return {"name": name, "url": base[name] + urllib.parse.quote_plus(query)}


# id, label, category, 3D-mesh tag (or None), material, size, power, qty,
# price$, function, vendors
ITEMS = [
    # ---- Structure
    ("head_bay", "Head bay + lid", "Structure", "head_bay", "PETG / resin",
     "140 mm bay, Ø70", "-", "1", 5, "Sealed dry electronics compartment with O-ring lid, "
     "nose window seat and 3 lid penetrations (tether / wire gland / sensor port).",
     [_v("AliExpress", "PETG filament 1.75mm"), _v("Amazon", "PETG filament")]),
    ("body_segments", "Body segments (×5)", "Structure", "body_segments", "PETG",
     "5 × 60 mm", "-", "5", 5, "Free-flooding articulated spine; one revolute joint each. "
     "Band anchor posts + drain holes are printed in.",
     [_v("AliExpress", "PETG filament 1.75mm"), _v("Amazon", "PETG filament")]),
    ("tail_fin", "Tail fin", "Structure", "tail_fin", "PETG sheet",
     "60 mm caudal", "-", "1", 3, "Passive vertical caudal fin for thrust.",
     [_v("AliExpress", "polycarbonate sheet 1.5mm"), _v("Amazon", "polycarbonate sheet")]),
    ("skin", "Skin sleeve", "Structure", None, "TPU 95A / silicone",
     "Ø70 sleeve", "-", "1", 10, "Flexible cover over the joint gaps for clean hydrodynamics. "
     "Holes for the dive shaft + tether exit are modeled in.",
     [_v("AliExpress", "TPU 95A filament 1.75mm"), _v("Amazon", "TPU 95A filament")]),
    # ---- Actuation
    ("servos", "Servos (×4)", "Actuation", "servos", "metal-gear, waterproof",
     "9 g class, ~2 kg·cm", "5-6 V, ~0.8 W ea", "4", 40,
     "3 drive the front body joints, 1 drives the dive planes. The rear 2 "
     "joints are passive (compliant tail) -- no servo.",
     [_v("AliExpress", "9g waterproof metal gear servo"), _v("Amazon", "waterproof metal gear servo")]),
    ("dive_planes", "Dive planes + shaft", "Actuation", "dive_planes",
     "PETG fins + SS shaft", "70 × 45 mm × 2", "via 1 servo", "1 set", 5,
     "Bow fins; pitch to climb/dive while swimming (active depth control).",
     [_v("AliExpress", "4mm stainless steel round rod"), _v("McMaster", "stainless rod 4mm")]),
    # ---- Camera & light (the payload)
    ("camera", "FPV camera", "Payload", "camera", "700TVL CMOS, analog",
     "~16 mm cube", "5 V, ~0.6 W", "1", 9,
     "Looks out the nose window from inside the dry bay. Composite video runs "
     "topside over a spare tether pair into a USB capture dongle.",
     [_v("AliExpress", "mini FPV camera 700TVL CMOS 5V"), _v("Amazon", "mini FPV camera analog")]),
    ("led", "LED headlight", "Payload", "led", "1-3 W white LED + MOSFET",
     "Ø~10 mm", "5 V, ~2 W", "1", 5,
     "Behind the window below the lens; black foam baffle stops internal glare. "
     "Dimmed by ESP32 GPIO25 PWM via a logic-level MOSFET ('W' serial command).",
     [_v("AliExpress", "3W white LED module 5V"), _v("AliExpress", "mosfet driver module 3.3V")]),
    ("window", "Nose window", "Payload", "head_bay", "acrylic / polycarbonate",
     "Ø30 × 3 mm disc", "-", "2", 4,
     "Clear disc epoxy-bonded into the printed seat at the truncated nose "
     "(buy 2 -- you will scratch one).",
     [_v("AliExpress", "clear acrylic disc 30mm 3mm"), _v("Amazon", "acrylic disc 30mm")]),
    ("capture", "USB video capture", "Payload", None, "RCA composite → USB",
     "dongle", "USB", "1", 8,
     "Topside: turns the camera's analog feed into a webcam on the laptop.",
     [_v("AliExpress", "USB video capture card RCA AV"), _v("Amazon", "USB video capture RCA")]),
    # ---- Electronics
    ("esp32", "ESP32 dev board", "Electronics", "esp32", "PCB module",
     "~50 × 25 mm", "3.3 V, ~0.5 W", "1", 8, "Main controller; runs the gait + depth-hold firmware.",
     [_v("AliExpress", "ESP32 devkit v1"), _v("Adafruit", "ESP32"), _v("Amazon", "ESP32 dev board")]),
    ("pca9685", "PCA9685 driver", "Electronics", "pca9685", "PCB module",
     "~25 × 60 mm", "I2C", "1", 5, "16-channel PWM servo driver (drives all 4 servos).",
     [_v("AliExpress", "PCA9685 16 channel servo driver"), _v("Adafruit", "PCA9685")]),
    ("mpu6050", "MPU6050 IMU", "Electronics", "mpu6050", "PCB module",
     "~20 × 15 mm", "I2C", "1", 3, "Inertial sensor for heading / attitude.",
     [_v("AliExpress", "MPU6050 module GY-521"), _v("Amazon", "MPU6050")]),
    ("ms5837", "MS5837 depth sensor", "Electronics", "ms5837", "PCB module",
     "Ø~17 mm", "I2C, 30 bar", "1", 25, "Measures depth/pressure; face epoxies into the lid "
     "sensor port. Feeds the depth-hold PID.",
     [_v("AliExpress", "MS5837 30BA pressure sensor"), _v("BlueRobotics", "bar30")]),
    ("leak", "Leak probe", "Electronics", "head_bay", "conductive pads",
     "small", "GPIO", "1", 2, "Trips the safety cutoff if the bay floods.",
     [_v("AliExpress", "water leak detection sensor module"), _v("Amazon", "leak detection sensor")]),
    ("battery", "2S LiPo buffer", "Electronics", "battery", "LiPo",
     "300-500 mAh", "7.4 V", "1", 10, "Buffer pack; the tether supplies bulk power.",
     [_v("AliExpress", "2S 7.4V 500mAh lipo"), _v("Amazon", "2S LiPo 500mAh")]),
    ("buck", "Buck + BEC", "Electronics", "buck", "PCB module",
     "small", "→3.3 V / 5-6 V", "1", 6, "Power rails for logic, servo bus, camera and LED.",
     [_v("AliExpress", "mini buck converter module"), _v("Pololu", "regulator")]),
    # ---- Sealing
    ("oring", "O-ring (lid)", "Sealing", "head_bay", "NBR / Buna-N",
     "~60 mm ID × 2 mm", "-", "2", 3, "Radial seal between the lid and the bay bore.",
     [_v("AliExpress", "nitrile o-ring assortment 2mm"), _v("McMaster", "o-ring 60mm")]),
    ("penetrator", "Cable gland + epoxy", "Sealing", "head_bay", "PG7 / marine epoxy",
     "10 mm bores", "-", "1+1", 9, "PG7 gland seals the tether; marine epoxy pots the "
     "servo-wire gland, the sensor port and bonds the window.",
     [_v("AliExpress", "PG7 waterproof cable gland"), _v("AliExpress", "marine epoxy two part")]),
    ("grease", "Silicone grease", "Sealing", None, "silicone",
     "-", "-", "1", 4, "Lubricates and protects every O-ring.",
     [_v("AliExpress", "silicone grease o-ring"), _v("Amazon", "silicone grease o-ring")]),
    # ---- Hardware
    ("pins", "Joint pins (×5)", "Hardware", "pins", "stainless 304/316",
     "Ø3 mm dowel", "-", "5", 3, "Steel pivot pins for the body joints (do not print).",
     [_v("AliExpress", "3mm stainless dowel pin 25mm"), _v("McMaster", "dowel pin 3mm")]),
    ("inserts", "Heat-set inserts", "Hardware", None, "brass",
     "M2 / M3", "-", "~10", 3, "Give printed plastic real threads for screws.",
     [_v("AliExpress", "brass heat set insert M3 kit"), _v("Amazon", "heat set inserts M3")]),
    ("screws", "Screws", "Hardware", None, "stainless M2/M3",
     "assorted", "-", "1 kit", 4, "Fasten lid, fins, hubs and servo horns.",
     [_v("AliExpress", "stainless M2 M3 screw assortment"), _v("Amazon", "stainless M3 screw assortment")]),
    ("ballast", "Ballast", "Hardware", None, "lead / steel",
     "~150 g", "-", "1", 5, "Trim weight to reach neutral buoyancy.",
     [_v("AliExpress", "lead sheet roll fishing"), _v("Amazon", "steel washers")]),
    # ---- Topside
    ("tether", "Tether (Cat5e)", "Topside", None, "cable",
     "3-5 m", "power + serial + video", "1", 8, "2 pairs power, 1 pair USB-serial, "
     "1 pair composite video.",
     [_v("AliExpress", "cat5e ethernet cable 5m outdoor"), _v("Amazon", "cat5e cable 5m")]),
    ("psu", "Bench PSU", "Topside", None, "supply",
     "5-6 V / 5 A", "30 W", "1", 0, "Powers the servo bus from the surface.",
     [_v("AliExpress", "5V 5A power supply"), _v("Amazon", "5V 5A power supply")]),
]


def items_json():
    out = []
    for (iid, label, cat, m, mat, size, power, qty, price, fn, ven) in ITEMS:
        out.append({"id": iid, "label": label, "cat": cat, "mesh": m,
                    "material": mat, "size": size, "power": power,
                    "qty": qty, "price": price, "fn": fn, "vendors": ven})
    return out


# the engineering reports, grouped, embedded verbatim into the page so the one
# HTML carries the whole record: buoyancy, dynamics, CFD, structure, power
REPORTS = [
    ("Buoyancy & ballast", "sizing_report.txt"),
    ("Stability — CG vs CB, roll & trim", "stability_report.txt"),
    ("Self-propulsion dynamics (Lighthill EBT)", "swim_report.txt"),
    ("Dive dynamics — lift, min speed, descent", "dive_report.txt"),
    ("CFD case — Reynolds & drag", "cfd_report.txt"),
    ("Structure & sealing", "structures_report.txt"),
    ("Electrical — peak current, brownout, tether", "power_report.txt"),
    ("Passive-tail stiffness", "tail_stiffness_report.txt"),
    ("Dive-plane linkage — kinematics & torque", "dive_linkage_report.txt"),
]


def gather_reports():
    """Read the saved analysis reports so the page consolidates them in one file.

    Missing reports are skipped (run the analysis scripts first to populate).
    """
    out = []
    for title, fn in REPORTS:
        try:
            with open(os.path.join(OUT, fn), encoding="utf-8") as fh:
                out.append({"title": title, "text": fh.read()})
        except OSError:
            pass
    return out


# ---------------------------------------------------------------- HTML
def main():
    geo = build_geo()
    data = {"geo": geo, "specs": gather_specs(), "items": items_json(),
            "eng": gather_eng(), "reports": gather_reports()}
    total = sum(it["price"] for it in data["items"])
    data["total"] = total
    html = TEMPLATE.replace("/*DATA*/", json.dumps(data, separators=(",", ":")))
    path = os.path.normpath(os.path.join(OUT, "eel_design.html"))
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(html)
    # mirror to the repo root so it opens straight from the main repo page
    root = os.path.normpath(os.path.join(OUT, "..", "eel_design.html"))
    with open(root, "w", encoding="utf-8") as fh:
        fh.write(html)
    kb = os.path.getsize(path) / 1024
    print(f"[ok] {path}")
    print(f"     {len(data['items'])} catalogued parts, ${total} total, "
          f"{kb:.0f} KB single-file design page")
    print("     open in any browser; share the one file.")


TEMPLATE = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Eel Robot — Design Page</title>
<style>
:root{--bg:#0d1117;--panel:#161b22;--panel2:#1c2330;--line:#2b3240;
  --txt:#e6edf3;--mut:#9aa6b2;--acc:#2f81f7;--acc2:#3fb950;--orange:#e08a00}
*{box-sizing:border-box}
html,body{margin:0;height:100%;background:var(--bg);color:var(--txt);
  font-family:system-ui,Segoe UI,Arial,sans-serif;overflow:hidden}
#app{display:flex;height:100%}
#stage{flex:1;position:relative;min-width:0}
#c{position:absolute;inset:0;width:100%;height:100%;display:block}
#bar{position:absolute;left:14px;bottom:14px;background:rgba(22,27,34,.85);
  padding:10px 12px;border-radius:10px;backdrop-filter:blur(4px);font-size:12px;
  display:flex;gap:14px;align-items:center;flex-wrap:wrap;max-width:92%}
#bar .grp{display:flex;align-items:center;gap:6px}
#bar input[type=range]{width:96px}
#bar button{background:var(--acc);color:#fff;border:0;border-radius:6px;
  padding:5px 9px;cursor:pointer;font-size:12px}
#bar button.sec{background:#2b333d}
#hint{position:absolute;right:14px;bottom:14px;font-size:11px;color:#6b7480}
#depth{position:absolute;left:14px;top:14px;background:rgba(22,27,34,.85);
  padding:8px 12px;border-radius:8px;font-size:13px;font-weight:600;color:#cfe6ff}
#depth small{color:var(--mut);font-weight:400}
#side{width:380px;min-width:380px;background:var(--panel);border-left:1px solid var(--line);
  overflow-y:auto;padding:16px}
h1{font-size:18px;margin:0 0 2px}
.sub{color:var(--mut);font-size:12px;margin-bottom:14px}
.specs{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-bottom:16px}
.spec{background:var(--panel2);border:1px solid var(--line);border-radius:8px;padding:8px 10px}
.spec .k{font-size:10px;color:var(--mut);text-transform:uppercase;letter-spacing:.04em}
.spec .v{font-size:13px;font-weight:600;margin-top:2px}
h2{font-size:13px;text-transform:uppercase;letter-spacing:.05em;color:var(--mut);
  margin:18px 0 8px;border-bottom:1px solid var(--line);padding-bottom:6px}
.cat{margin-bottom:6px}
.cat .ct{font-size:11px;color:var(--orange);margin:10px 0 5px;font-weight:600}
.chip{display:inline-block;background:var(--panel2);border:1px solid var(--line);
  color:var(--txt);border-radius:14px;padding:5px 11px;margin:0 5px 6px 0;font-size:12px;
  cursor:pointer;transition:.12s}
.chip:hover{border-color:var(--acc)}
.chip.on{background:var(--acc);border-color:var(--acc);color:#fff}
#info{background:var(--panel2);border:1px solid var(--line);border-radius:10px;
  padding:14px;margin:10px 0 4px;display:none}
#info.show{display:block}
#info h3{margin:0 0 4px;font-size:15px}
#info .fn{color:var(--mut);font-size:12px;margin-bottom:10px}
#info .kv{display:grid;grid-template-columns:auto 1fr;gap:4px 12px;font-size:12px;margin-bottom:10px}
#info .kv .kk{color:var(--mut)}
.buy a{display:inline-block;background:var(--acc2);color:#06210f;font-weight:600;
  text-decoration:none;border-radius:6px;padding:5px 10px;margin:0 6px 6px 0;font-size:12px}
table{width:100%;border-collapse:collapse;font-size:12px;margin-top:6px}
th,td{text-align:left;padding:6px 6px;border-bottom:1px solid var(--line)}
th{color:var(--mut);font-weight:600;font-size:11px;text-transform:uppercase}
td a{color:var(--acc)}
.tot{font-weight:700}
.legend{font-size:11px;color:var(--mut);margin-top:6px;line-height:1.7}
.sw{display:inline-block;width:10px;height:10px;border-radius:2px;margin-right:5px}
#tabs{display:flex;flex-wrap:wrap;gap:4px;margin-bottom:14px}
.tab{background:var(--panel2);border:1px solid var(--line);color:var(--mut);
  border-radius:6px;padding:5px 9px;font-size:11px;cursor:pointer}
.tab:hover{border-color:var(--acc)}
.tab.on{background:var(--acc);color:#fff;border-color:var(--acc)}
.pane{display:none}.pane.on{display:block}
.big{background:var(--panel2);border:1px solid var(--line);border-radius:10px;
  padding:14px;margin-bottom:12px}
.big .lbl{font-size:11px;color:var(--mut);text-transform:uppercase;letter-spacing:.04em}
.big .num{font-size:24px;font-weight:800;margin-top:4px}
.big .num.pos{color:var(--acc2)}
.note{font-size:11px;color:var(--mut);line-height:1.65;margin-top:10px}
pre.rpt{background:#0b0f14;border:1px solid var(--line);border-radius:8px;
  padding:10px 12px;font-size:11px;line-height:1.45;color:#cfe0d6;overflow-x:auto;
  white-space:pre;font-family:ui-monospace,Consolas,monospace;margin:6px 0 16px}
@media(max-width:900px){#app{flex-direction:column}#side{width:100%;min-width:0;height:50%}#stage{height:50%}}
</style></head>
<body>
<div id="app">
  <div id="stage">
    <canvas id="c"></canvas>
    <div id="bar">
      <div class="grp"><button id="play">❚❚</button>
        <button id="spin" class="sec">spin</button></div>
      <div class="grp">speed<input id="speed" type="range" min="0" max="100" value="55"></div>
      <div class="grp">dive<input id="dive" type="range" min="-25" max="25" value="0"></div>
      <div class="grp"><label><input id="intern" type="checkbox" checked> internals</label></div>
      <div class="grp"><button id="reset" class="sec">reset view</button></div>
    </div>
    <div id="hint">drag orbit · scroll zoom · click a part</div>
    <div id="depth">Depth 0.00 m <small>· angle the fins + speed up to dive</small></div>
  </div>
  <div id="side">
    <h1>Bio-Inspired Eel Robot</h1>
    <div class="sub">Anguilliform underwater vehicle · full design datasheet</div>
    <div id="tabs"></div>

    <div class="pane on" data-tab="overview">
      <div class="specs" id="specs"></div>
      <div class="note">Every number on this page is <b>computed/predicted</b>
        from the design model — <b>not yet physically validated</b> (no CFD solve,
        no wet test). Speed, drag, dive and Strouhal are estimates; depth-hold and
        heading-hold are closed-loop but bench-untested. Use the tabs for power,
        buoyancy, motion, structure and the full analysis reports.</div>
    </div>

    <div class="pane" data-tab="power" id="pane-power"></div>
    <div class="pane" data-tab="buoy" id="pane-buoy"></div>
    <div class="pane" data-tab="motion" id="pane-motion"></div>
    <div class="pane" data-tab="struct" id="pane-struct"></div>
    <div class="pane" data-tab="reports" id="pane-reports"></div>

    <div class="pane" data-tab="parts">
      <h2>Parts — click to highlight & buy</h2>
      <div id="cats"></div>
      <div id="info"></div>
      <div class="legend">
        <span class="sw" style="background:#2e8b57"></span>head/tail
        &nbsp;<span class="sw" style="background:#4682b4"></span>body
        &nbsp;<span class="sw" style="background:#e08a00"></span>dive planes
        &nbsp;<span class="sw" style="background:#6b6f76"></span>internals</div>
    </div>

    <div class="pane" data-tab="bom">
      <h2>Full bill of materials</h2>
      <table id="bom"><thead><tr><th>Part</th><th>Qty</th><th>Material</th><th>~$</th><th>Buy</th></tr></thead>
        <tbody></tbody></table>
    </div>
  </div>
</div>

<script type="importmap">
{"imports":{"three":"https://unpkg.com/three@0.160.0/build/three.module.js",
"three/addons/":"https://unpkg.com/three@0.160.0/examples/jsm/"}}
</script>
<script type="module">
import * as THREE from 'three';
import {OrbitControls} from 'three/addons/controls/OrbitControls.js';
const DATA=/*DATA*/; const PRM=DATA.geo.params;

// ---- scene
const scene=new THREE.Scene(); scene.background=new THREE.Color(0x0d1117);
const camera=new THREE.PerspectiveCamera(45,2,1,9000);
const cv=document.getElementById('c');
const renderer=new THREE.WebGLRenderer({canvas:cv,antialias:true});
scene.add(new THREE.HemisphereLight(0xcfe6ff,0x1a1f27,1.05));
const dl=new THREE.DirectionalLight(0xffffff,1.35); dl.position.set(.4,1,.6); scene.add(dl);
const controls=new OrbitControls(camera,cv); controls.enableDamping=true;
const CENTER=new THREE.Vector3(0,0,PRM.BODY_LENGTH/2); controls.target.copy(CENTER);
const robot=new THREE.Group(); scene.add(robot);

// --- depth environment: water surface + depth marker rings (world-fixed) ---
const env=new THREE.Group(); scene.add(env);
{ const s=new THREE.Mesh(new THREE.PlaneGeometry(2600,1500),
    new THREE.MeshBasicMaterial({color:0x2f5d86,transparent:true,opacity:0.16,
      side:THREE.DoubleSide}));
  s.rotation.x=-Math.PI/2; s.position.set(CENTER.x,0,CENTER.z); env.add(s); }
for(let d=0; d<=2500; d+=500){
  const g=new THREE.BufferGeometry().setFromPoints([
    new THREE.Vector3(CENTER.x-440,-d,CENTER.z-380),
    new THREE.Vector3(CENTER.x+440,-d,CENTER.z-380),
    new THREE.Vector3(CENTER.x+440,-d,CENTER.z+380),
    new THREE.Vector3(CENTER.x-440,-d,CENTER.z+380),
    new THREE.Vector3(CENTER.x-440,-d,CENTER.z-380)]);
  env.add(new THREE.Line(g, new THREE.LineBasicMaterial(
    {color: d===0 ? 0x4a90d9 : 0x33506b})));
}
const ALL=[];                                   // every mesh
function mk(m){const g=new THREE.BufferGeometry();
  g.setAttribute('position',new THREE.Float32BufferAttribute(m.pos,3));
  g.setIndex(m.idx); g.computeVertexNormals();
  const mat=new THREE.MeshStandardMaterial({color:m.color,metalness:.25,roughness:.6,
    side:THREE.DoubleSide,transparent:true,opacity:1});
  const me=new THREE.Mesh(g,mat); me.userData={item:m.item,internal:!!m.internal,base:m.color};
  ALL.push(me); return me;}
DATA.geo.base.forEach(m=>robot.add(mk(m)));
(DATA.geo.bay||[]).forEach(m=>robot.add(mk(m)));   // electronics in head bay
const diveG=new THREE.Group(); diveG.position.set(0,0,PRM.DIVE_PLANE_Z);
DATA.geo.dive.forEach(m=>diveG.add(mk(m))); robot.add(diveG);
const segG=DATA.geo.seg.map(parts=>{const g=new THREE.Group();
  parts.forEach(m=>g.add(mk(m))); robot.add(g); return g;});
const tailG=new THREE.Group(); DATA.geo.tail.forEach(m=>tailG.add(mk(m))); robot.add(tailG);

// ---- gait FK
const D2R=Math.PI/180;
function pose(t,sp){let px=0,pz=PRM.HEAD_LEN,th=0;const f=PRM.f*sp;
  for(let i=0;i<PRM.N;i++){th+=PRM.amp[i]*D2R*Math.sin(2*Math.PI*f*t-PRM.phi[i]);
    segG[i].position.set(px,0,pz); segG[i].rotation.set(0,th,0);
    px+=Math.sin(th)*PRM.SEG_LEN; pz+=Math.cos(th)*PRM.SEG_LEN;}
  tailG.position.set(px,0,pz); tailG.rotation.set(0,th,0);}

// ---- highlight
let sel=null;
function applyVis(){const showInt=internCb.checked; ALL.forEach(me=>{
  const u=me.userData, isSel=sel&&u.item===sel;
  if(sel) me.material.opacity=isSel?1:0.10;          // dim others when one picked
  else if(showInt) me.material.opacity=u.internal?1:0.38; // see-through body
  else me.material.opacity=1;
  me.material.emissive=new THREE.Color(isSel?0x244a8a:0x000000);
  me.visible=u.internal?(showInt||isSel):true;});}
function select(it){ const item=DATA.items.find(x=>x.id===it); sel=item?item.mesh:null;
  renderChips(it); renderInfo(item); applyVis(); }

// ---- UI: specs
const specsEl=document.getElementById('specs');
DATA.specs.forEach(s=>{const d=document.createElement('div'); d.className='spec';
  d.innerHTML=`<div class="k">${s.k}</div><div class="v">${s.v}</div>`; specsEl.appendChild(d);});

// ---- UI: engineering panes (every number)
const E=DATA.eng;
const tbl=(h,rows)=>`<table><thead><tr>${h.map(x=>`<th>${x}</th>`).join('')}</tr></thead>`+
  `<tbody>${rows.map(r=>`<tr>${r.map(c=>`<td>${c}</td>`).join('')}</tr>`).join('')}</tbody></table>`;
const sc=(k,v)=>`<div class="spec"><div class="k">${k}</div><div class="v">${v}</div></div>`;

document.getElementById('pane-power').innerHTML=
  `<h2>Hydrodynamic power — to overcome drag</h2>`+
  tbl(['Speed m/s','Drag mN','P-drag mW','P-prop mW'],
    E.power.table.map(r=>[r.v.toFixed(2),r.drag.toFixed(0),r.pd.toFixed(0),r.pp.toFixed(0)]))+
  `<h2>Electrical power — battery / tether supplies</h2><div class="specs">`+
  sc('Hotel (MCU+sensors)',E.power.hotel.toFixed(1)+' W')+
  sc('Servos (×4)',E.power.servos.toFixed(1)+' W')+
  sc('TOTAL draw',E.power.total.toFixed(1)+' W')+
  sc('Current @7.4 V',E.power.amps.toFixed(2)+' A')+`</div>`+
  `<div class="note">Water needs &lt;0.2 W; the ~${E.power.total.toFixed(1)} W draw is `+
  `dominated by servos + electronics, NOT drag. Cd=${E.power.Cd}, `+
  `A_front=${E.power.A.toFixed(1)} cm², η=${E.power.eta}. Size the supply 2–3× for servo stall spikes.</div>`;

document.getElementById('pane-buoy').innerHTML=
  `<div class="big"><div class="lbl">Inherent buoyancy (free-flooding)</div>`+
  `<div class="num pos">+${E.buoy.inh.toFixed(0)} g&nbsp;&nbsp;(+${E.buoy.inhN.toFixed(2)} N)</div>`+
  `<div class="note">Positive → it floats. Add ~${E.buoy.ballast.toFixed(0)} g ballast `+
  `to reach neutral (trim ~+15–20 g positive so it self-surfaces on failure).</div></div>`+
  `<div class="specs">`+
  sc('Displaces (free-flood)',E.buoy.flood.toFixed(0)+' g')+
  sc('Dry weight',E.buoy.dry.toFixed(0)+' g')+
  sc('Ballast → neutral',E.buoy.ballast.toFixed(0)+' g')+
  sc('If sealed: inherent','+'+E.buoy.sealedInh.toFixed(0)+' g')+`</div>`+
  `<h2>Mass breakdown</h2>`+
  tbl(['Component','Mass g'],E.buoy.mass.map(m=>[m.k,m.g]));

document.getElementById('pane-motion').innerHTML=
  `<div class="specs">`+
  sc('Cruise speed','~'+E.perf.U.toFixed(2)+' m/s')+
  sc('EBT upper bound',E.perf.Uub.toFixed(2)+' m/s')+
  sc('Strouhal',E.perf.St.toFixed(2))+
  sc('Tail-beat',E.perf.f.toFixed(1)+' Hz')+
  sc('Tail amplitude',E.perf.tailamp.toFixed(0)+' mm')+`</div>`+
  `<h2>Gait — travelling wave, per joint</h2>`+
  tbl(['Joint','z mm','Phase °','Amp °'],
    E.perf.gait.map(g=>[g.j,g.z,g.phi,g.amp]))+
  `<h2>Dive planes (active depth)</h2><div class="specs">`+
  sc('Plane area',E.dive.area.toFixed(0)+' cm²')+
  sc('Max Cl',E.dive.Clmax.toFixed(2))+
  sc('Min dive speed',E.dive.vmin.toFixed(2)+' m/s')+
  sc('Descent rate','~'+(E.dive.descent*1000).toFixed(0)+' mm/s')+
  sc('Downforce @0.4 m/s',E.dive.L04.toFixed(0)+' mN')+
  sc('Downforce @0.55 m/s',E.dive.L075.toFixed(0)+' mN')+`</div>`+
  `<div class="note">Dive planes need forward flow — no authority at rest.</div>`;

document.getElementById('pane-struct').innerHTML=
  `<div class="specs">`+
  sc('Depth rated',E.struct.depthRated+' m')+
  sc('Collapse depth','~'+E.struct.depthCollapse.toFixed(0)+' m')+
  sc('Hull hoop stress',E.struct.hoop.toFixed(2)+' MPa')+
  sc('Buckling SF',E.struct.sfBuckle.toFixed(0)+'×')+
  sc('Joint-pin shear',E.struct.pinTau.toFixed(2)+' MPa')+
  sc('Pin shear SF',E.struct.pinSF.toFixed(0)+'×')+
  sc('O-ring squeeze',E.struct.oring.toFixed(0)+'%')+
  sc('Yield SF (hull)',E.struct.sfYield.toFixed(0)+'×')+`</div>`+
  `<div class="note">Printed-PLA properties, 2 m rating. The sealed head bay is `+
  `the limiter and buckles at ~${E.struct.depthCollapse.toFixed(0)} m — all load paths have large margins.</div>`;

// ---- Reports: the full analysis text, consolidated into this one file
const esc=s=>s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
document.getElementById('pane-reports').innerHTML=
  `<h2>How the design is driven</h2>`+
  `<div class="big"><div class="note" style="margin-top:0">`+
  `Read top-to-bottom, each report is one link in the chain:`+
  `<br><b>1 · Move</b> — a travelling sine wave down the body (Lighthill EBT) `+
  `makes thrust; Strouhal number sets how fast for a given tail-beat.`+
  `<br><b>2 · Float</b> — the body free-floods; a closed-cell foam plug + a `+
  `lead keel bring it to neutral buoyancy.`+
  `<br><b>3 · Stay upright & level</b> — keel low + foam aft put CG below CB `+
  `and line CG up with CB, so it floats level and rights itself.`+
  `<br><b>4 · Dive</b> — bow planes pitch the nose down once there's forward flow.`+
  `<br><b>5 · Survive depth</b> — only the head bay is sealed; structure rated `+
  `well past 2 m.`+
  `<br><b>6 · Be powered</b> — 4 servos dominate the budget; size for the peak, `+
  `not the average.</div></div>`+
  `<h2>Engineering analysis — full reports</h2>`+
  `<div class="note">Every number is reproducible by running the matching `+
  `script (<code>analysis/*.py</code>, <code>cfd/case_setup.py</code>); this tab `+
  `embeds their output verbatim — buoyancy, dynamics, CFD, structure, power.</div>`+
  (DATA.reports.length? DATA.reports.map(r=>
     `<h2>${r.title}</h2><pre class="rpt">${esc(r.text)}</pre>`).join('')
   : `<div class="note">No reports embedded — run the analysis scripts, then `+
     `re-run design_page.py.</div>`);

// ---- UI: tabs
const TABS=[['overview','Overview'],['power','Power'],['buoy','Buoyancy'],
  ['motion','Motion'],['struct','Structure'],['reports','Reports'],
  ['parts','Parts'],['bom','BOM']];
const tabsEl=document.getElementById('tabs');
TABS.forEach(([id,lbl],i)=>{const b=document.createElement('button');
  b.className='tab'+(i===0?' on':''); b.textContent=lbl;
  b.onclick=()=>{document.querySelectorAll('.tab').forEach(x=>x.classList.remove('on'));
    b.classList.add('on');
    document.querySelectorAll('.pane').forEach(p=>p.classList.toggle('on',p.dataset.tab===id));};
  tabsEl.appendChild(b);});

// ---- UI: part chips by category
const catsEl=document.getElementById('cats'); const cats={};
DATA.items.forEach(it=>{(cats[it.cat]=cats[it.cat]||[]).push(it);});
function renderChips(active){catsEl.innerHTML='';
  Object.keys(cats).forEach(c=>{const w=document.createElement('div'); w.className='cat';
    w.innerHTML=`<div class="ct">${c}</div>`;
    cats[c].forEach(it=>{const b=document.createElement('span');
      b.className='chip'+(it.id===active?' on':''); b.textContent=it.label;
      b.onclick=()=>select(it.id===active?null:it.id); w.appendChild(b);});
    catsEl.appendChild(w);});}
function renderInfo(it){const el=document.getElementById('info');
  if(!it){el.className='';el.innerHTML='';return;} el.className='show';
  const buy=it.vendors.map(v=>`<a href="${v.url}" target="_blank" rel="noopener">${v.name} ↗</a>`).join('');
  el.innerHTML=`<h3>${it.label}</h3><div class="fn">${it.fn}</div>
    <div class="kv"><span class="kk">Material</span><span>${it.material}</span>
    <span class="kk">Size</span><span>${it.size}</span>
    <span class="kk">Power</span><span>${it.power}</span>
    <span class="kk">Qty</span><span>${it.qty}</span>
    <span class="kk">Price</span><span>~$${it.price}</span></div>
    <div class="buy">${buy}</div>`;}
renderChips(null);

// ---- UI: BOM table
const tb=document.querySelector('#bom tbody');
DATA.items.forEach(it=>{const tr=document.createElement('tr');
  const v=it.vendors[0];
  tr.innerHTML=`<td><a style="cursor:pointer;color:#2f81f7" onclick="window.__sel('${it.id}')">${it.label}</a></td>
    <td>${it.qty}</td><td>${it.material}</td><td>${it.price}</td>
    <td><a href="${v.url}" target="_blank" rel="noopener">${v.name} ↗</a></td>`;
  tb.appendChild(tr);});
const trt=document.createElement('tr'); trt.innerHTML=
  `<td class="tot">TOTAL (≈)</td><td></td><td></td><td class="tot">$${DATA.total}</td><td></td>`;
tb.appendChild(trt);
window.__sel=select;

// ---- click-to-pick on the 3D model
const ray=new THREE.Raycaster(), mouse=new THREE.Vector2();
cv.addEventListener('click',e=>{const r=cv.getBoundingClientRect();
  mouse.x=((e.clientX-r.left)/r.width)*2-1; mouse.y=-((e.clientY-r.top)/r.height)*2+1;
  ray.setFromCamera(mouse,camera); const hit=ray.intersectObjects(ALL,false)
    .filter(h=>h.object.visible)[0];
  if(hit){const tag=hit.object.userData.item;
    const it=DATA.items.find(x=>x.mesh===tag); if(it) select(it.id);} });

// ---- controls
let playing=true,spinning=false,speed=.55,dive=0,t0=performance.now(),tcur=0;
let depth=0,prevDepth=0,lastT=performance.now();   // descent state (scene mm)
const $=id=>document.getElementById(id), internCb=$('intern');
$('play').onclick=e=>{playing=!playing; e.target.textContent=playing?'❚❚':'▶';
  if(playing)t0=performance.now()-tcur*1000;};
$('spin').onclick=e=>{spinning=!spinning; e.target.style.background=spinning?'#2f81f7':'#2b333d';};
$('speed').oninput=e=>speed=e.target.value/100;
$('dive').oninput=e=>dive=+e.target.value;
internCb.onchange=applyVis;
$('reset').onclick=()=>{depth=0;prevDepth=0;robot.position.set(0,0,0);robot.rotation.x=0;frame();};
applyVis();

function resize(){const w=cv.clientWidth,h=cv.clientHeight;
  if(cv.width!==w||cv.height!==h){renderer.setSize(w,h,false);
    camera.aspect=w/h; camera.updateProjectionMatrix();}}
function frame(){robot.rotation.y=0; const d=PRM.BODY_LENGTH*1.5;
  camera.position.set(CENTER.x+d*.28,CENTER.y+d*.42,CENTER.z+d*.9);
  controls.target.copy(CENTER); controls.update();}
function loop(){requestAnimationFrame(loop); resize();
  const now=performance.now(); const dt=Math.min(0.05,(now-lastT)/1000); lastT=now;
  if(playing)tcur=(performance.now()-t0)/1000; pose(tcur,speed);
  diveG.rotation.x=-dive*D2R;
  // DEPTH: descend/climb only while swimming; the bow fins pitch the nose
  // down (dive) or up (climb), and the body travels along that attitude.
  depth += 420*(dive/25)*speed*dt;
  depth = Math.max(0, Math.min(2500, depth));
  const dd = depth-prevDepth; prevDepth=depth;
  const pitch = -(dive/25)*0.36*(speed>0.02?1:0);     // nose-down for dive
  const Cz = PRM.BODY_LENGTH/2;
  robot.rotation.x = pitch;                            // pitch about body centre
  robot.position.set(0, -depth + Cz*Math.sin(pitch), Cz*(1-Math.cos(pitch)));
  camera.position.y -= dd; controls.target.y -= dd;   // keep it framed as it sinks
  $('depth').firstChild.textContent = 'Depth '+(depth/1000).toFixed(2)+' m  ';
  if(spinning)robot.rotation.y+=0.004;
  controls.update(); renderer.render(scene,camera);}
frame(); loop();
</script>
</body></html>
"""


if __name__ == "__main__":
    main()
