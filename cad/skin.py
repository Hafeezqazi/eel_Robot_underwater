"""
skin.py  --  Flexible outer skin sleeve (TPU / silicone).

The segmented body has open gaps at every joint (see the swim preview). A
thin elastomer sleeve pulled over the spine restores a smooth hydrodynamic
surface, keeps grit out of the joints, and stretches as the body undulates.

Geometry: a thin shell following the body radius profile over the driven
region (head rear -> tail base), standing off the hull by SKIN_GAP, with a
shallow CORRUGATION (flex groove) centred on each joint so it bends without
buckling. Print in TPU (~1.2 mm wall) or use as a mould core for silicone.

Run:  python skin.py   ->  output/print_skin.stl
"""

import os
import math
import cadquery as cq
import params as P

SKIN_GAP  = 1.0     # mm, clearance over the hull
SKIN_WALL = 1.2     # mm, sleeve wall thickness
GROOVE_DEPTH = 1.5  # mm, flex-groove radial dip at each joint
GROOVE_WIDTH = 10.0 # mm, axial width of each flex groove
Z0 = P.HEAD_LEN - 10.0      # start 10 mm onto the head rear: anchors the
                            # sleeve and keeps joint 1's flex groove complete
Z1 = P.TAILFIN_Z            # ends at the tail-fin base
SHAFT_CUT_R = P.DIVE_SHAFT_D / 2.0 + 2.0   # mm, clearance hole where the
                            # dive-plane shaft crosses the sleeve (each side)


def _skin_radius(z):
    """Sleeve mid-wall radius at station z, with flex grooves at joints."""
    r = P.radius_profile(z) + SKIN_GAP + SKIN_WALL / 2.0
    for zj in P.JOINT_Z:                       # subtract a smooth groove dip
        d = abs(z - zj)
        if d < GROOVE_WIDTH / 2.0:
            r -= GROOVE_DEPTH * 0.5 * (1.0 + math.cos(math.pi * d /
                                                      (GROOVE_WIDTH / 2.0)))
    return r


def build_skin(n=80):
    """Thin sleeve as a solid of revolution (robust vs a many-section loft).

    Profile (radius vs axial position) is a closed thin strip swept 360 deg
    about the body axis. Built about the workplane Y axis, then rotated so
    the axis lies along global Z.
    """
    zs = [Z0 + (Z1 - Z0) * i / n for i in range(n + 1)]
    mid = [_skin_radius(z) for z in zs]
    pts_out = [(m + SKIN_WALL / 2.0, z) for z, m in zip(zs, mid)]
    pts_in = [(m - SKIN_WALL / 2.0, z) for z, m in zip(reversed(zs),
                                                       reversed(mid))]
    profile = pts_out + pts_in
    sol = (cq.Workplane("XY").polyline(profile).close().revolve(360))
    sol = sol.rotate((0, 0, 0), (1, 0, 0), 90)
    # clearance holes where the dive-plane shaft exits (both sides, along X)
    r_here = P.radius_profile(P.DIVE_PLANE_Z)
    shaft_cut = (cq.Workplane(cq.Plane(origin=(-(r_here + 8.0), 0,
                                               P.DIVE_PLANE_Z),
                                       xDir=(0, 1, 0), normal=(1, 0, 0)))
                 .circle(SHAFT_CUT_R).extrude(2 * (r_here + 8.0)))
    sol = sol.cut(shaft_cut)
    # tether exit hole (top, just aft of joint 1): the tether leaves the lid
    # penetrator, crosses the flooded joint-1 gap and exits up through here
    z_tet = P.HEAD_LEN + 10.0
    r_tet = P.radius_profile(z_tet)
    tether_cut = (cq.Workplane(cq.Plane(origin=(0, r_tet - 6.0, z_tet),
                                        xDir=(1, 0, 0), normal=(0, 1, 0)))
                  .circle(4.5).extrude(12.0))
    return sol.cut(tether_cut)


def _test():
    out_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "..", "output")
    skin = build_skin()
    path = os.path.normpath(os.path.join(out_dir, "print_skin.stl"))
    cq.exporters.export(skin, path)
    vol = skin.val().Volume() / 1000.0
    mass_tpu = vol * 1.21          # TPU ~1.21 g/cm^3
    print(f"[ok] skin sleeve: {Z0:.0f}->{Z1:.0f} mm, wall {SKIN_WALL} mm")
    print(f"     volume {vol:.1f} cm^3  (~{mass_tpu:.0f} g in TPU)  -> {path}")


if __name__ == "__main__":
    _test()
