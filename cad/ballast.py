"""
ballast.py  --  printable retention hardware for the stability fix. The foam discs, lead keel and trim weight are NOT optional (see
analysis/stability.py); this makes installing them repeatable instead of prose.

  keel_strap    : flat strap that pins the lead keel into the forward belly
                  (2x M3 into the hull, a shallow saddle locates the keel)
  trim_rail +   : a slotted rail + a sliding carrier for the ~15 g trim weight;
  trim_carrier    slide to level the pitch, M3 setscrew locks it
  foam_retainer : open spider ring that press-fits the bore behind the rear
                  foam disc so it can't slide aft (spokes keep it free-flooding)

Run:  python ballast.py
      -> output/print_keel_strap.stl, print_trim_rail.stl,
         print_trim_carrier.stl, print_foam_retainer.stl
"""

import os
import cadquery as cq
import params as P

KEEL_W = 18.0       # mm, keel cross-section width (matches internals keel box)


def keel_strap():
    span = KEEL_W + 2 * 10.0                 # keel + a 10 mm screw tab each side
    t, depth = 2.5, 14.0
    s = cq.Workplane("XY").box(depth, span, t)
    s = s.cut(cq.Workplane("XY").box(depth + 1, KEEL_W + 0.6, 1.2)
              .translate((0, 0, t / 2 - 0.6)))               # saddle for the keel
    for y in (KEEL_W / 2 + 5, -(KEEL_W / 2 + 5)):
        s = s.cut(cq.Workplane("XY").cylinder(t + 1, 1.7).translate((0, y, 0)))
    return s


def trim_rail():
    L, w, t = 70.0, 12.0, 3.0
    rail = cq.Workplane("XY").box(L, w, t)
    rail = rail.cut(cq.Workplane("XY").box(L - 16, 4.2, t + 1))      # slide slot
    for x in (L / 2 - 5, -(L / 2 - 5)):                              # mount holes
        rail = rail.cut(cq.Workplane("XY").cylinder(t + 1, 1.7).translate((x, 0, 0)))
    return rail


def trim_carrier():
    c = cq.Workplane("XY").box(14, 14, 10)
    c = c.cut(cq.Workplane("XY").box(16, 4.4, 3.4).translate((0, 0, -10 / 2 + 1.7)))
    c = c.cut(cq.Workplane("XY").cylinder(15, 1.7))                  # setscrew/weight
    return c


def foam_retainer():
    zc, length = P.FOAM_PLUGS[-1][0], P.FOAM_PLUGS[-1][1]
    z = zc + length / 2 + 3.0                                        # just aft of disc
    ri = P.radius_profile(z) - P.WALL - 0.4                          # press-fit
    ring = (cq.Workplane("XY").cylinder(3, ri)
            .cut(cq.Workplane("XY").cylinder(4, ri - 2.5)))          # thin ring
    for ang in (0, 90):                                             # 2 cross spokes
        ring = ring.union(cq.Workplane("XY").box(2 * ri - 1, 3, 3)
                          .rotate((0, 0, 0), (0, 0, 1), ang))
    return ring


def _test():
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "output")
    parts = [("print_keel_strap", keel_strap()),
             ("print_trim_rail", trim_rail()),
             ("print_trim_carrier", trim_carrier()),
             ("print_foam_retainer", foam_retainer())]
    for name, sol in parts:
        path = os.path.normpath(os.path.join(out, name + ".stl"))
        cq.exporters.export(sol, path)
        print(f"[ok] {name}: {sol.val().Volume()/1000:5.1f} cm^3 -> {path}")


if __name__ == "__main__":
    _test()
