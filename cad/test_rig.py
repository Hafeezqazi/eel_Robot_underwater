"""
test_rig.py  --  Bollard-thrust test cradle (bench tool, printable).

Holds the robot's head in a saddle so it can beat its body while tethered to
a force gauge in line with the swim axis -> reads static (bollard) thrust.
Also used for the dry bench shake-out of the gait before going in water.

Features (all parametric off the head radius in params.py):
  * base plate with 4 bolt holes (clamp to a bench / tank rail)
  * saddle with a cylindrical seat matching the head, + 2 strap slots
  * rear post with an eyelet for the force-gauge line (on the body axis)

Axes: base on XY (Z up); robot lies along X; gauge pulls along -X.
Run:  python test_rig.py   ->  output/print_test_rig.stl
"""

import os
import cadquery as cq
import params as P

SEAT_R   = P.R_MAX + 2.0     # mm, saddle seat radius (head + clearance)
BASE_L   = 200.0            # mm (X)
BASE_W   = 90.0             # mm (Y)
BASE_T   = 10.0            # mm plate thickness
SADDLE_W = 70.0           # mm (X) saddle block length
SADDLE_H = SEAT_R + 22.0  # mm saddle height above base
AXIS_Z   = BASE_T + SEAT_R + 6.0   # body-axis height above ground


def build_rig():
    base = (cq.Workplane("XY").box(BASE_L, BASE_W, BASE_T)
            .translate((0, 0, BASE_T / 2.0)))

    # 4 bench bolt holes
    base = (base.faces(">Z").workplane()
            .pushPoints([(BASE_L / 2 - 15, BASE_W / 2 - 15),
                         (BASE_L / 2 - 15, -BASE_W / 2 + 15),
                         (-BASE_L / 2 + 15, BASE_W / 2 - 15),
                         (-BASE_L / 2 + 15, -BASE_W / 2 + 15)])
            .hole(5.0))

    # saddle block centred at x=0
    saddle = (cq.Workplane("XY").box(SADDLE_W, BASE_W, SADDLE_H)
              .translate((0, 0, BASE_T + SADDLE_H / 2.0)))
    # cylindrical seat (axis along X) cut into the top
    seat = (cq.Workplane(cq.Plane(origin=(0, 0, AXIS_Z), xDir=(0, 1, 0),
                                  normal=(1, 0, 0)))
            .circle(SEAT_R).extrude(SADDLE_W + 10, both=True))
    saddle = saddle.cut(seat)
    # 2 strap slots (through Y), thin in X
    for x in (-22.0, 22.0):
        slot = (cq.Workplane("XY").box(6.0, BASE_W + 10, SADDLE_H)
                .translate((x, 0, BASE_T + SADDLE_H / 2.0)))
        saddle = saddle.cut(slot)

    # rear gauge post at -X with an eyelet on the body axis
    post = (cq.Workplane("XY").box(14.0, 44.0, AXIS_Z + 16.0)
            .translate((-BASE_L / 2 + 20, 0, (AXIS_Z + 16.0) / 2.0)))
    eye = (cq.Workplane(cq.Plane(origin=(-BASE_L / 2 + 20, 0, AXIS_Z),
                                 xDir=(0, 1, 0), normal=(1, 0, 0)))
           .circle(5.0).extrude(40, both=True))
    post = post.cut(eye)

    return base.union(saddle).union(post)


def _test():
    out_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "..", "output")
    rig = build_rig()
    path = os.path.normpath(os.path.join(out_dir, "print_test_rig.stl"))
    cq.exporters.export(rig, path)
    bb = rig.val().BoundingBox()
    print(f"[ok] test rig: {bb.xlen:.0f} x {bb.ylen:.0f} x {bb.zlen:.0f} mm")
    print(f"     seat radius {SEAT_R:.0f} mm, axis height {AXIS_Z:.0f} mm "
          f"-> {path}")


if __name__ == "__main__":
    _test()
