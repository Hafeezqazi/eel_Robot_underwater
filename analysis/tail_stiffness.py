"""
tail_stiffness.py  --  Size the PASSIVE compliant tail so it undulates at the
tail-beat frequency instead of flopping or staying rigid.

The rear 2 joints have no servo; a rubber band / TPU flexure provides the
restoring stiffness. Model each passive joint as a torsional spring + the
inertia of everything aft of it (structure + water added-mass). Its natural
frequency  f_n = (1/2pi) sqrt(k / I)  should sit a touch ABOVE the beat so the
tail tracks the body wave in phase. Solve for k, then convert to a buildable
rubber-band rate OR a printed TPU-flexure thickness.

Numbers are first-order (added-mass is approximate) -- confirm with a bench
swing test: pluck the tail, measure its natural frequency, tune the band/
flexure until f_n ~ target. Run:  python tail_stiffness.py
"""

import os
import sys
import math

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "cad"))
import params as P   # noqa: E402

ADDED_MASS_FACTOR = 2.6     # water added-mass multiplier on structural inertia
E_TPU = 35e6                # Pa, flexible TPU (~95A) bending modulus
BAND_ARM = 0.010            # m, rubber-band moment arm (the band post radius)
TARGET_RATIO = 1.25         # f_n / f_beat  (slightly stiff -> tracks in phase)
FLEX_W = 0.010              # m, TPU flexure width
FLEX_L = 0.008              # m, TPU flexure free length


def seg_mass(r0, r1, L):
    rm = 0.5 * (r0 + r1) / 1000.0
    return 2 * math.pi * rm * (L / 1000.0) * (P.WALL / 1000.0) * P.RHO_PLA * 0.5


def tail_inertia(joint_z):
    """Structural moment of inertia (kg m^2) of everything aft of joint_z."""
    I = 0.0
    for p in P.segment_table():
        if p["z0"] < joint_z:
            continue
        L = p["z1"] - p["z0"]
        m = seg_mass(p["r0"], p["r1"], L) if p["name"].startswith("seg") else 0.013
        d = ((p["z0"] + p["z1"]) / 2 - joint_z) / 1000.0       # m, lever
        I += m * d ** 2 + m * (L / 1000.0) ** 2 / 12.0          # parallel-axis
    return I


def main():
    f_beat = P.CRUISE_FREQ_HZ
    f_n = TARGET_RATIO * f_beat
    w = 2 * math.pi * f_n
    L = []
    pr = L.append
    pr("=" * 60)
    pr("PASSIVE TAIL STIFFNESS  (rear 2 joints, no servo)")
    pr("=" * 60)
    pr(f"tail-beat freq    : {f_beat:.1f} Hz   target f_n = {f_n:.2f} Hz "
       f"(x{TARGET_RATIO})")
    pr("")
    pr(f"{'joint z':>8} {'I_struct':>10} {'I+water':>9} {'k(Nm/rad)':>10} "
       f"{'band N/m':>9} {'TPU t(mm)':>10}")
    for jz in (P.JOINT_Z[3], P.JOINT_Z[4]):                      # the 2 passive
        Is = tail_inertia(jz)
        Ie = Is * ADDED_MASS_FACTOR
        k = Ie * w ** 2                                          # N*m/rad
        k_band = k / BAND_ARM ** 2                               # N/m
        # TPU flexure bending: k = E*(w*t^3/12)/L  -> solve t
        t = (k * 12 * FLEX_L / (E_TPU * FLEX_W)) ** (1 / 3) * 1000
        pr(f"{jz:8.0f} {Is*1e6:9.1f}u {Ie*1e6:8.1f}u {k:10.3f} "
           f"{k_band:9.0f} {t:10.1f}")
    pr("")
    pr("  Build options per passive joint (use the value for its z):")
    pr("   A) RUBBER BAND : pick a band whose rate ~ 'band N/m' at the post")
    pr("      (10 mm arm). Stack/shorten bands to raise the rate; measure it")
    pr("      (hang a known mass, read stretch).")
    pr("   B) TPU FLEXURE : print the inter-segment link in TPU ~'t mm' thick")
    pr(f"      x {FLEX_W*1000:.0f} mm wide x {FLEX_L*1000:.0f} mm long (living hinge).")
    pr("")
    pr("  Tune on the bench: pluck the assembled tail, time 10 swings ->")
    pr(f"  f_n; add/remove stiffness until f_n ~ {f_n:.1f} Hz.")
    pr("=" * 60)
    text = "\n".join(L)
    print(text)
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "..", "output", "tail_stiffness_report.txt")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(text + "\n")
    print("\n[saved]", os.path.normpath(out))


if __name__ == "__main__":
    main()
