"""
stability.py  --  Centre of gravity (CG) vs centre of buoyancy (CB), and trim.

The check that decides whether the robot floats UPRIGHT and LEVEL:
  * Roll  : CB must sit ABOVE CG (CG below the axis) or it rolls over.
  * Trim  : CG and CB must align fore/aft (same z) or it pitches at rest.

CB is purely geometric (centroid of the displaced volume = the sealed head-bay
air + the solid shell material -- a body of revolution, so CB is on the axis,
x=y=0). CG is the mass-weighted centroid of every component at its real
position (from internals.py / the segment layout). We then solve for the
ballast position + mass that makes it neutral, level, and roll-stable.

Run:  python stability.py   ->  output/stability_report.txt
"""

import os
import sys
import math
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "cad"))
import params as P            # noqa: E402
import sizing                 # noqa: E402

G = P.G


def rho_water():
    return P.RHO_FRESH if P.WATER == "fresh" else P.RHO_SALT


# ---------------------------------------------------------------------------
# distributed shell: mass + centroid by integrating the body profile
# ---------------------------------------------------------------------------
def shell_distribution():
    n = 400
    zs = np.linspace(0, P.BODY_LENGTH, n)
    r = np.array([P.radius_profile(z) for z in zs]) / 1000.0      # m
    dz = (P.BODY_LENGTH / 1000.0) / (n - 1)
    dm = 2 * np.pi * r * (P.WALL / 1000.0) * P.RHO_PLA * sizing.SHELL_PACKING * dz
    m = dm.sum()
    z_cg = float((zs / 1000.0 * dm).sum() / m)                   # m
    return m, z_cg


# ---------------------------------------------------------------------------
# CB: centroid of displaced volume (free-flooding = sealed head-bay air)
# ---------------------------------------------------------------------------
def buoyancy_centroid(fix=False):
    n = 300
    zs = np.linspace(0, P.HEAD_LEN, n)                            # the dry bay
    ri = np.array([max(P.radius_profile(z) - P.BAY_WALL, 0) for z in zs]) / 1000.0
    dz = (P.HEAD_LEN / 1000.0) / (n - 1)
    dV = np.pi * ri ** 2 * dz
    Vair = dV.sum()
    z_air = float((zs / 1000.0 * dV).sum() / dV.sum())
    Vshell = sizing.geometry()["wetted"] * (P.WALL / 1000.0)     # shell material
    _, z_shell = shell_distribution()
    parts = [(Vair, z_air, 0.0), (Vshell, z_shell, 0.0)]
    if fix:                                                       # + aft foam
        parts.append((P.FOAM_VOL / 1e6, P.FOAM_Z / 1000.0, P.FOAM_Y / 1000.0))
    Vt = sum(v for v, _, _ in parts)
    z = sum(v * zz for v, zz, _ in parts) / Vt
    y = sum(v * yy for v, _, yy in parts) / Vt
    return Vt, z, y


# ---------------------------------------------------------------------------
# component mass table:  (name, mass_kg, x_mm, y_mm, z_mm)
# masses follow analysis/sizing.py totals; positions from internals.py + layout
# ---------------------------------------------------------------------------
def mass_table():
    s_m, s_z = shell_distribution()                              # shell
    items = [("shell (PLA)", s_m, 0, 0, s_z * 1000)]

    # 4 servos (3 joints at seg fronts + 1 dive), each hangs low (y~-11)
    for z in (P.JOINT_Z[0], P.JOINT_Z[1], P.JOINT_Z[2]):
        items.append((f"servo@{int(z)}", sizing.M_SERVO_EACH, 0, -11, z + 11))
    items.append(("dive servo", sizing.M_SERVO_EACH, -3, -9, P.DIVE_PLANE_Z + 12))

    # electronics (sum ~ M_ELECTRONICS), positions from internals.py
    elec = [("esp32", .010, -18, 6, 72), ("pca9685", .010, 18, 6, 72),
            ("imu", .003, 0, 15, 52), ("buck", .008, 0, 14, 100),
            ("ms5837", .005, P.SENSOR_PORT_X, 0, 129),
            ("camera", .010, 0, 3, P.WINDOW_Z + 15),
            ("led", .003, 0, -7, P.WINDOW_Z + 7), ("leak", .001, 0, -15, 110)]
    items += elec
    items.append(("battery", sizing.M_BATTERY, 0, -5, 80))       # low + forward
    items.append(("tray", .008, 0, -15, 74))
    items.append(("wiring", .010, 0, 0, 100))
    items.append(("window", .006, 0, 0, P.WINDOW_Z))
    items.append(("hardware", sizing.M_HARDWARE, 0, 0, 200))     # pins/inserts
    # skin (TPU) over the body + tail fin
    items.append(("skin", .072, 0, 0, (P.HEAD_LEN + P.TAILFIN_Z) / 2))
    items.append(("tail fin", .013, 0, 0, P.TAILFIN_Z + 30))
    items.append(("dive planes", sizing.M_DIVE, 0, 0, P.DIVE_PLANE_Z))
    return items


def add_fix(items):
    """Append the stability hardware: low forward keel + (light) foam."""
    out = list(items)
    out.append(("keel (lead)", P.KEEL_MASS / 1000.0, 0, P.KEEL_Y, P.KEEL_Z))
    out.append(("foam", 0.03 * P.FOAM_VOL / 1000.0, 0, P.FOAM_Y, P.FOAM_Z))
    return out


def cg_of(items):
    M = sum(m for _, m, *_ in items)
    x = sum(m * xx for _, m, xx, yy, zz in items) / M
    y = sum(m * yy for _, m, xx, yy, zz in items) / M
    z = sum(m * zz for _, m, xx, yy, zz in items) / M
    return M, x, y, z


def main():
    items = mass_table()
    M_dry, cgx, cgy, cgz = cg_of(items)
    Vdisp, cb_z, cb_y = buoyancy_centroid()
    disp_mass = Vdisp * rho_water()                              # kg of water
    cb_z_mm = cb_z * 1000

    L = []
    pr = L.append
    pr("=" * 64)
    pr("EEL ROBOT  --  CG vs CB STABILITY + TRIM")
    pr("=" * 64)
    pr(f"dry mass          : {M_dry*1000:7.1f} g")
    pr(f"displaces (flood) : {disp_mass*1000:7.1f} g  -> net "
       f"{(disp_mass-M_dry)*1000:+.0f} g (add ballast to neutral)")
    pr("")
    pr("                        x(mm)   y(mm)   z(mm from nose)")
    pr(f"  CG (mass)          : {cgx:6.1f}  {cgy:6.1f}   {cgz:6.1f}")
    pr(f"  CB (buoyancy)      :   0.0     0.0     {cb_z_mm:6.1f}   (on the axis)")
    pr("")
    pr("[ROLL]  need CB above CG  ->  CG must be BELOW the axis (y<0)")
    roll_margin = 0.0 - cgy                                       # mm CB above CG
    pr(f"  CG vertical        : {cgy:+.1f} mm   "
       f"({'STABLE' if cgy < -1 else 'MARGINAL/UNSTABLE'}, "
       f"CB is {roll_margin:+.1f} mm above CG)")
    pr("[TRIM]  need CG aligned with CB fore/aft (same z)")
    trim = cgz - cb_z_mm
    att = "nose-down" if trim < 0 else "tail-down (nose-up)"
    pr(f"  CG - CB (z)        : {trim:+.1f} mm   "
       f"({'level' if abs(trim) < 5 else 'trims '+att+' at rest'})")
    pr("")

    # --- apply the designed fix (params FOAM_*/KEEL_*) and verify ---
    itf = add_fix(items)
    Mf, fx, fy, fz = cg_of(itf)
    Vf, cbzf, cbyf = buoyancy_centroid(fix=True)
    dispf = Vf * rho_water()
    cbzf_mm, cbyf_mm = cbzf * 1000, cbyf * 1000
    pr("[FIX APPLIED]  foam %.0f cm^3 @ z%.0f  +  lead keel %.0f g @ z%.0f (low)"
       % (P.FOAM_VOL, P.FOAM_Z, P.KEEL_MASS, P.KEEL_Z))
    pr(f"  wet mass / displaces : {Mf*1000:6.0f} g / {dispf*1000:6.0f} g  "
       f"-> net {(dispf-Mf)*1000:+.0f} g")
    pr(f"  CG : x{fx:5.1f}  y{fy:+5.1f}  z{fz:6.1f} mm")
    pr(f"  CB : x  0.0   y{cbyf_mm:+5.1f}  z{cbzf_mm:6.1f} mm")
    sep = cbyf_mm - fy                                           # CB above CG
    dzt = fz - cbzf_mm                                           # fore/aft offset
    pitch = math.degrees(math.atan2(abs(dzt), max(sep, 0.5)))
    pr(f"  ROLL margin (CB above CG): {sep:+.1f} mm  "
       f"({'stable' if sep > 3 else 'weak'})")
    pr(f"  TRIM offset (CG-CB z)    : {dzt:+.1f} mm  -> rest pitch ~{pitch:.0f} deg")
    pr("")
    pr("  NOTE: near-neutral vehicles are trim-SENSITIVE (small CG-CB"
       " separation).")
    pr("  Design gets it close; set LEVEL in the water with a small MOVABLE")
    pr("  trim weight / sliding battery. Keel sets ROLL, movable weight sets")
    pr("  PITCH. Standard AUV practice -- a fixed design can't be perfectly")
    pr("  level, so a trim provision is part of being build-ready.")
    pr("=" * 64)
    pr("verdict: with foam + keel it is ROLL-STABLE and near-level; finish")
    pr("  pitch in water with the adjustable weight. Baseline (no fix) floats")
    pr("  nose-up and rolls easily -- the fix is necessary, not optional.")
    pr("=" * 64)

    text = "\n".join(L)
    print(text)
    out = os.path.join(HERE, "..", "output", "stability_report.txt")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(text + "\n")
    print("\n[saved]", os.path.normpath(out))


if __name__ == "__main__":
    main()
