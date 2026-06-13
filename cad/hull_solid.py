"""
hull_solid.py  --  Single watertight hull (no joints) for CFD meshing.

CFD meshers (snappyHexMesh) need ONE closed, watertight surface, not the
jointed assembly. This revolves the body radius profile into a solid of
revolution and exports a binary STL + STEP. Its volume should match the
displaced volume in analysis/sizing.py (~1120 cm^3) -> a sanity cross-check.

Run:  python hull_solid.py  ->  output/cfd_hull.stl, output/cfd_hull.step
"""

import os
import cadquery as cq
import params as P


def build_hull(n=160):
    # nose is truncated at the camera-window face (WINDOW_Z), like the print
    z0 = P.WINDOW_Z
    zs = [z0 + (P.BODY_LENGTH - z0) * i / n for i in range(n + 1)]
    profile = [(0.0, z0)]                           # centre of the flat face
    profile += [(max(P.radius_profile(z), 0.2), z) for z in zs]
    profile += [(0.0, P.BODY_LENGTH)]               # tail on axis
    sol = cq.Workplane("XY").polyline(profile).close().revolve(360)
    return sol.rotate((0, 0, 0), (1, 0, 0), 90)     # axis Y -> Z


def _test():
    out_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "..", "output")
    hull = build_hull()
    stl = os.path.normpath(os.path.join(out_dir, "cfd_hull.stl"))
    step = os.path.normpath(os.path.join(out_dir, "cfd_hull.step"))
    cq.exporters.export(hull, stl)
    cq.exporters.export(hull, step)
    vol = hull.val().Volume() / 1000.0
    print(f"[ok] watertight hull: volume {vol:.1f} cm^3  "
          f"(sizing displaced ~1120 cm^3)")
    print(f"     -> {stl}")
    print(f"     -> {step}")


if __name__ == "__main__":
    _test()
