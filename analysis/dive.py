"""
dive.py  --  Dive-plane performance (active depth control via bow fins).

First-order check of what the bow dive planes can do: how much vertical force
they make at speed, the minimum forward speed needed to overcome the trim
reserve buoyancy and start descending, a rough descent rate, and the key
limitation (no authority at zero speed -- they need flow).

Convention: +plane angle = DIVE (downward lift). Run:  python dive.py
"""

import os
import sys
import math

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "cad"))
import params as P   # noqa: E402

RESERVE_G  = 20.0          # g, trim reserve buoyancy (fail-safe surfacing);
                           # ~3-4% of flooded displacement, see sizing.py [2]
CD_PLANE0  = 0.10          # plane profile drag coeff
OSWALD_E   = 0.7           # span efficiency (low-AR fin)
SPEEDS     = [0.40, 0.55]  # m/s, slow and cruise (cruise ~ swim_sim derated)


def rho():
    return P.RHO_FRESH if P.WATER == "fresh" else P.RHO_SALT


def geom():
    A = 2.0 * (P.DIVE_PLANE_SPAN / 1000.0) * (P.DIVE_PLANE_CHORD / 1000.0)
    AR = P.DIVE_PLANE_SPAN / P.DIVE_PLANE_CHORD       # single-fin aspect ratio
    Cl_max = min(P.DIVE_CL_PER_DEG * P.DIVE_STALL_DEG, 1.1)
    return A, AR, Cl_max


def downforce(V, Cl):
    A, _, _ = geom()
    return 0.5 * rho() * Cl * A * V ** 2


def main():
    A, AR, Cl_max = geom()
    reserve_N = RESERVE_G / 1000.0 * P.G
    L = []
    def pr(s=""):
        L.append(s)

    pr("=" * 60)
    pr("EEL ROBOT  --  DIVE-PLANE PERFORMANCE")
    pr("=" * 60)
    pr(f"  planes: 2 x {P.DIVE_PLANE_SPAN:.0f}x{P.DIVE_PLANE_CHORD:.0f} mm  "
       f"= {A*1e4:.1f} cm^2 total, AR {AR:.2f}")
    pr(f"  max Cl (stall {P.DIVE_STALL_DEG:.0f} deg): {Cl_max:.2f}")
    pr(f"  trim reserve buoyancy: {RESERVE_G:.0f} g = {reserve_N*1000:.0f} mN "
       f"(must be overcome to dive)")
    pr("-" * 60)
    pr("  vertical force at full deflection vs forward speed:")
    for V in SPEEDS:
        Lmax = downforce(V, Cl_max)
        ok = "DIVES" if Lmax > reserve_N else "cannot overcome reserve"
        pr(f"    V={V:.2f} m/s : {Lmax*1000:6.0f} mN  "
           f"({Lmax/reserve_N:4.1f}x reserve)  -> {ok}")
    pr("-" * 60)
    # minimum speed to start diving
    v_min = math.sqrt(2 * reserve_N / (rho() * Cl_max * A))
    pr(f"  min forward speed to dive: {v_min:.2f} m/s")
    # rough steady descent at cruise
    V = SPEEDS[-1]
    Lmax = downforce(V, Cl_max)
    Cdi = Cl_max ** 2 / (math.pi * AR * OSWALD_E)
    D_plane = 0.5 * rho() * (CD_PLANE0 + Cdi) * A * V ** 2
    D_body = 0.5 * rho() * P.CD_AXIAL * P.frontal_area() * V ** 2
    gamma = math.degrees(math.atan(Lmax / (D_body + D_plane)))
    w = V * math.sin(math.radians(gamma))
    pr(f"  at V={V:.2f} m/s, full dive:")
    pr(f"    glide angle (1st order): {gamma:.0f} deg below horizontal")
    pr(f"    descent rate           : {w*1000:.0f} mm/s")
    pr(f"    time to 2 m depth      : {2.0/w:.1f} s")
    pr("=" * 60)
    pr("  LIMITATION: dive planes need forward flow -- ZERO authority at rest.")
    pr("  The robot holds depth by neutral trim and dives/climbs only while")
    pr("  swimming. To hover/descend at zero speed you'd need a variable-")
    pr("  buoyancy engine instead (see the dive-method options).")
    pr("=" * 60)

    text = "\n".join(L)
    print(text)
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "..", "output", "dive_report.txt")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(text + "\n")
    print(f"\n[saved] {os.path.normpath(out)}")


if __name__ == "__main__":
    main()
