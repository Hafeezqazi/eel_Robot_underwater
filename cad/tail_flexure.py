"""
tail_flexure.py  --  printable TPU living-hinge variants for the PASSIVE tail
joints. Turns "tune a rubber band" into a defined part:
a link with two bolt pads joined by a thin flexing web. Print the bracket of
thicknesses, fit each, and pick the one that hits the target beat by the bench
swing test (analysis/tail_stiffness.py: joint 4 ~4.0 mm, joint 5 ~2.8 mm).

Print in TPU (95A). Run:  python tail_flexure.py
      -> output/print_flexure_2p8.stl, _3p4.stl, _4p0.stl
"""

import os
import cadquery as cq
import params as P   # noqa: F401  (kept for consistency / future param use)

PAD = 12.0          # mm, bolt-pad length (along the body axis)
PAD_T = 4.0         # mm, pad thickness
WEB_W = 10.0        # mm, flexure width
WEB_L = 8.0         # mm, flexure free length (the living hinge)
VARIANTS = [2.8, 3.4, 4.0]   # mm, web thickness bracket


def flexure(t):
    """One link: pad -- thin web (thickness t) -- pad, with an M2.5 hole/pad."""
    pad = cq.Workplane("XY").box(PAD, WEB_W + 4, PAD_T)
    off = WEB_L / 2 + PAD / 2
    a = pad.translate((-off, 0, 0))
    b = pad.translate((off, 0, 0))
    web = cq.Workplane("XY").box(WEB_L, WEB_W, t)
    link = a.union(web).union(b)
    for sx in (-off, off):                              # 1 bolt hole per pad
        link = link.cut(cq.Workplane("XY").cylinder(PAD_T + 1, 1.4)
                        .translate((sx, 0, 0)))
    return link


def _test():
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "output")
    for t in VARIANTS:
        name = "print_flexure_%s" % ("%.1f" % t).replace(".", "p")
        path = os.path.normpath(os.path.join(out, name + ".stl"))
        cq.exporters.export(flexure(t), path)
        print(f"[ok] {name}: web {t:.1f} mm -> {path}")


if __name__ == "__main__":
    _test()
