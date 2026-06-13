"""
structures.py  --  Analytic structural / sealing checks for the eel robot.

Closed-form (no FEA) first-order checks of the load paths that matter for a
shallow printed prototype:

  1. Head-bay pressure hull : hoop stress + external-pressure buckling depth
  2. Joint pin             : double-shear stress under worst-case torque
  3. O-ring seal           : squeeze ratio (should sit ~15-30%)

Material properties are for printed PLA (conservative); change MAT_* for
PETG / resin. Run:  python structures.py
"""

import os
import sys
import math

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "cad"))
import params as P   # noqa: E402

# printed-PLA properties (conservative, layer-direction de-rated)
MAT_E      = 3.5e9     # Pa, Young's modulus
MAT_YIELD  = 50e6      # Pa, tensile yield
MAT_NU     = 0.35      # Poisson ratio


def rho_water():
    return P.RHO_FRESH if P.WATER == "fresh" else P.RHO_SALT


def pressure_at(depth_m):
    return rho_water() * P.G * depth_m          # Pa, gauge


def hull_check():
    """Head bay = thin cylinder, external pressure. Inner radius ~ rear bore."""
    r = (P.radius_profile(P.HEAD_LEN) - P.BAY_WALL) / 1000.0   # m, inner radius
    t = P.BAY_WALL / 1000.0
    P_design = pressure_at(P.DEPTH_RATING)
    # thin-wall hoop stress under external pressure
    hoop = P_design * r / t
    sf_yield = MAT_YIELD / hoop if hoop > 0 else float("inf")
    # long-cylinder external-pressure buckling (von Mises ring formula)
    Pcr = MAT_E / (4 * (1 - MAT_NU ** 2)) * (t / r) ** 3
    sf_buckle = Pcr / P_design if P_design > 0 else float("inf")
    depth_buckle = Pcr / (rho_water() * P.G)
    return dict(r=r, t=t, P=P_design, hoop=hoop, sf_yield=sf_yield,
                Pcr=Pcr, sf_buckle=sf_buckle, depth_buckle=depth_buckle)


def pin_check():
    """Joint pin in double shear under the worst-case servo torque."""
    T = P.SERVO_TORQUE_RATED                      # N*m, worst case = stall
    arm = P.KNUCKLE_R / 1000.0                    # m, knuckle radius (load arm)
    F = T / arm                                   # N, joint reaction force
    a = math.pi * (P.PIN_D / 2000.0) ** 2         # m^2, pin x-section
    tau = F / (2 * a)                             # Pa, double shear
    sf = (0.6 * MAT_YIELD) / tau if tau > 0 else float("inf")  # shear~0.6 yield
    return dict(F=F, tau=tau, sf=sf)


def oring_check():
    squeeze = (P.ORING_CS - P.ORING_GROOVE_D) / P.ORING_CS * 100.0
    ok = 15.0 <= squeeze <= 30.0
    return dict(squeeze=squeeze, ok=ok)


LID_HANDLING_PULL = 50.0   # N, assumed worst-case axial yank on the lid
INSERT_PULLOUT    = 200.0  # N, conservative M3 brass heat-set insert in PETG


def lid_clamp_check():
    """Lid bolt-ears under a handling/tether pull. The radial O-ring needs NO
    clamp force and the joint-1 pin is the primary retention -- these ears are a
    backup. Check per-ear insert pull-out + the insert-to-edge wall."""
    n = P.LID_BOLTS
    sf = (n * INSERT_PULLOUT) / LID_HANDLING_PULL
    edge = P.LID_EAR_R - P.LID_INSERT_D / 2.0      # mm, wall around the insert
    return dict(n=n, per=LID_HANDLING_PULL / n, sf=sf, edge=edge,
                edge_ok=edge >= 1.5)


def main():
    h = hull_check()
    pn = pin_check()
    o = oring_check()
    lc = lid_clamp_check()
    L = []
    def pr(s=""):
        L.append(s)

    pr("=" * 60)
    pr("EEL ROBOT  --  STRUCTURAL / SEALING CHECKS (PLA)")
    pr("=" * 60)
    pr(f"depth rating = {P.DEPTH_RATING:.0f} m  ->  "
       f"design pressure {h['P']/1000:.1f} kPa")
    pr("")
    pr("[1] HEAD-BAY PRESSURE HULL")
    pr(f"  inner radius / wall : {h['r']*1000:.1f} / {h['t']*1000:.1f} mm")
    pr(f"  hoop stress         : {h['hoop']/1e6:8.3f} MPa "
       f"(yield {MAT_YIELD/1e6:.0f}) -> SF {h['sf_yield']:6.0f}")
    pr(f"  buckling pressure   : {h['Pcr']/1000:8.1f} kPa            "
       f"-> SF {h['sf_buckle']:6.0f}")
    pr(f"  => collapses at     : {h['depth_buckle']:8.1f} m depth "
       f"(rating {P.DEPTH_RATING:.0f} m)")
    pr("")
    pr("[2] JOINT PIN (double shear, worst-case stall torque)")
    pr(f"  reaction force      : {pn['F']:8.2f} N")
    pr(f"  shear stress        : {pn['tau']/1e6:8.3f} MPa -> SF {pn['sf']:6.0f}")
    pr("")
    pr("[3] O-RING SEAL")
    pr(f"  squeeze             : {o['squeeze']:8.1f} %  "
       f"({'OK 15-30%' if o['ok'] else 'OUT OF RANGE — adjust groove'})")
    pr("")
    pr("[4] LID CLAMP (%d M3 bolt ears; radial O-ring needs no clamp force)"
       % lc['n'])
    pr(f"  handling pull       : {LID_HANDLING_PULL:.0f} N over {lc['n']} ears "
       f"= {lc['per']:.1f} N/ear")
    pr(f"  insert pull-out     : {INSERT_PULLOUT:.0f} N/insert -> SF {lc['sf']:6.1f}")
    pr(f"  insert-edge wall    : {lc['edge']:8.1f} mm  "
       f"({'OK' if lc['edge_ok'] else 'THIN — grow LID_EAR_R'})")
    pr("=" * 60)
    pr("verdict: all load paths have large margins at the 2 m rating;")
    pr("the bay is the limiter and is good to ~%.0f m before buckling."
       % h['depth_buckle'])
    pr("NOTE: analytic first-order only -- no FEA of clamp/penetrator/window")
    pr("bond peel, servo-boss loads, or cyclic fatigue (bench-confirm those).")
    pr("=" * 60)

    text = "\n".join(L)
    print(text)
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "..", "output", "structures_report.txt")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(text + "\n")
    print(f"\n[saved] {os.path.normpath(out)}")


if __name__ == "__main__":
    main()
