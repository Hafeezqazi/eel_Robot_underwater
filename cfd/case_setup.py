"""
case_setup.py  --  Stage the CFD case: copy the hull STL + report flow params.

Run AFTER cad/hull_solid.py has produced output/cfd_hull.stl. Copies that
surface into constant/triSurface/ and prints the Reynolds number and the
recommended inlet speed so you can sanity-check 0/U before meshing.

This does NOT run OpenFOAM (you do that with ./Allrun on a machine that has
OpenFOAM installed). Run:  python case_setup.py
"""

import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "cad"))
import params as P   # noqa: E402

CFD_SPEED = 0.5           # m/s, inlet (also set in 0/U) -- drag study speed
NU_WATER  = 1.0e-6        # m^2/s, kinematic viscosity of water


def main():
    src = os.path.normpath(os.path.join(HERE, "..", "output", "cfd_hull.stl"))
    dst_dir = os.path.join(HERE, "constant", "triSurface")
    os.makedirs(dst_dir, exist_ok=True)
    dst = os.path.join(dst_dir, "cfd_hull.stl")
    if not os.path.exists(src):
        print(f"[!] {src} missing -- run cad/hull_solid.py first")
        return
    shutil.copyfile(src, dst)

    L = P.BODY_LENGTH / 1000.0
    Re = CFD_SPEED * L / NU_WATER
    A = P.frontal_area()
    drag_est = 0.5 * (P.RHO_FRESH) * P.CD_AXIAL * A * CFD_SPEED ** 2

    out = []

    def pr(s=""):
        print(s)
        out.append(s)

    pr("=" * 56)
    pr("CFD CASE SETUP  --  steady drag study (simpleFoam, kOmegaSST)")
    pr("=" * 56)
    pr(f"  staged surface : {os.path.normpath(dst)}")
    pr(f"  body length L  : {L:.3f} m")
    pr(f"  inlet speed U  : {CFD_SPEED:.2f} m/s   (set in 0/U)")
    pr(f"  Reynolds Re    : {Re:.3e}   -> turbulent, kOmegaSST")
    pr(f"  frontal area   : {A*1e4:.1f} cm^2   (Cd_axial assumed {P.CD_AXIAL})")
    pr(f"  analytic drag  : {drag_est*1000:.1f} mN  (compare to CFD forces)")
    pr("-" * 56)
    pr("  this script only STAGES the case (geometry + Reynolds + a drag")
    pr("  estimate from the assumed Cd). Run the solve to MEASURE Cd:")
    pr("  next:  ./Allrun        (needs OpenFOAM in PATH)")
    pr("         postProcess -func forces  ->  drag coefficient")
    pr("=" * 56)
    rep = os.path.join(HERE, "..", "output", "cfd_report.txt")
    with open(rep, "w", encoding="utf-8") as fh:
        fh.write("\n".join(out) + "\n")
    print(f"[saved] {os.path.normpath(rep)}")


if __name__ == "__main__":
    main()
