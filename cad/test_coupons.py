"""
test_coupons.py  --  small printable coupons to de-risk fit + sealing BEFORE the
full body print (Codex review C2-P0-3 / C2-P1-4). Each is a representative slice
of a real interface, so a few grams of filament proves the fit/seal cheaply.

  servo_pocket  : a wall with a servo-body slot + 2 mount pilots (does YOUR
                  servo drop in? do the mount screws line up?)
  potting_cup   : the lid wire-gland bore as a stand-alone cup with a
                  strain-relief flare (pot a wire bundle, soak it -- §12)
  oring_bore +  : the bay rear-bore ring + a plug stub carrying the O-ring
  oring_plug      groove, to check the RADIAL squeeze/fit on your printer

Run:  python test_coupons.py
      -> output/coupon_servo.stl, coupon_potting.stl,
         coupon_oring_bore.stl, coupon_oring_plug.stl
"""

import os
import cadquery as cq
import params as P

PAD = 4.0


def servo_pocket():
    """Fit gauge for the servo body + its 2 mount screws."""
    L = P.SERVO_BODY_L + 2 * PAD
    W = P.SERVO_BODY_W + 2 * P.WALL
    H = P.SERVO_BODY_H + PAD
    blk = cq.Workplane("XY").box(L, W, H)
    blk = blk.cut(cq.Workplane("XY").box(P.SERVO_BODY_L + 0.6,
                                         P.SERVO_BODY_W + 0.6, H + 1))   # slot
    for s in (+1, -1):                                  # 2 mount-screw pilots
        blk = blk.cut(cq.Workplane("XY").cylinder(H + 1, 1.05)
                      .translate((s * (P.SERVO_BODY_L / 2 + PAD / 2), 0, 0)))
    return blk


def potting_cup():
    """Wire-gland bore as a cup: bore = WIRE_GLAND_D, 2 mm floor, a top
    counterbore = strain-relief flare. Pot a wire bundle and soak it."""
    od = P.WIRE_GLAND_D + 6.0
    depth = 16.0
    cup = cq.Workplane("XY").cylinder(depth, od / 2)
    cup = cup.cut(cq.Workplane("XY").cylinder(depth, P.WIRE_GLAND_D / 2)
                  .translate((0, 0, 2)))                       # bore, 2 mm floor
    cup = cup.cut(cq.Workplane("XY").cylinder(4, P.WIRE_GLAND_D / 2 + 2)
                  .translate((0, 0, depth / 2 - 2)))           # strain-relief flare
    return cup


def _rear():
    r = P.radius_profile(P.HEAD_LEN)
    return r, r - P.BAY_WALL


def oring_bore():
    """Female: a short ring matching the bay rear bore."""
    rear_r, bore_r = _rear()
    return (cq.Workplane("XY").cylinder(14, rear_r)
            .cut(cq.Workplane("XY").cylinder(15, bore_r)))


def oring_plug():
    """Male: a plug stub with the O-ring groove (radial seal test)."""
    _, bore_r = _rear()
    plug_r = bore_r - 0.2
    plug = cq.Workplane("XY").cylinder(14, plug_r)
    groove = (cq.Workplane("XY").cylinder(P.ORING_GROOVE_W, plug_r)
              .cut(cq.Workplane("XY").cylinder(P.ORING_GROOVE_W + 1,
                                               plug_r - P.ORING_GROOVE_D)))
    return plug.cut(groove)


def _test():
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "output")
    parts = [("coupon_servo", servo_pocket()),
             ("coupon_potting", potting_cup()),
             ("coupon_oring_bore", oring_bore()),
             ("coupon_oring_plug", oring_plug())]
    for name, sol in parts:
        path = os.path.normpath(os.path.join(out, name + ".stl"))
        cq.exporters.export(sol, path)
        print(f"[ok] {name}: {sol.val().Volume()/1000:5.1f} cm^3 -> {path}")


if __name__ == "__main__":
    _test()
