"""
joints.py  --  Revolute joint hardware for the eel robot.

Convention (shared by body.py and assembly.py):
  * Robot axis      = global Z  (nose at z=0, tail at z=+500 mm)
  * Joint pin axis  = global Y  (vertical)  ->  rotation = YAW (swim plane)
  * A joint lives on a cut plane z = JOINT_Z[i]. The part AHEAD carries a
    TONGUE (single blade) pointing aft (+Z); the part BEHIND carries a
    CLEVIS (two-prong fork) opening forward (-Z) that straddles the tongue.
    One pin (Y) passes clevis-prong -> tongue -> clevis-prong.

All primitives here are built in JOINT-LOCAL coordinates: the pin axis is
the global Y line through (x=0, z=0). body.py translates them to the right
station. Reusable building block = lug() (a rounded, bored plate).

Run directly to export a demo revolute pair:
    python joints.py        ->  output/joint_demo.step / .stl
"""

import os
import cadquery as cq
import params as P

KNUCKLE_R = P.KNUCKLE_R   # mm, rounded pivot-end radius of every lug (>= pin)


def _ycyl(radius, y0, y1, x=0.0, z=0.0):
    """Solid cylinder along the global Y axis, from y0 to y1."""
    h = y1 - y0
    return (cq.Workplane(cq.Plane(origin=(x, y0, z),
                                  xDir=(1, 0, 0), normal=(0, 1, 0)))
            .circle(radius).extrude(h))


def lug(y_center, y_thick, reach, kr=KNUCKLE_R):
    """One rounded, pin-bored plate.

    Pivot knuckle centred on the joint axis (x=0, z=0); the plate body
    extends aft to z=+reach. Thin in Y (thickness y_thick) centred at
    y=y_center. Bored for the pin along Y.
    """
    shaft = (cq.Workplane("XY")
             .box(2 * kr, y_thick, reach)
             .translate((0, y_center, reach / 2.0)))     # z: 0 -> reach
    knuckle = (cq.Workplane(cq.Plane(origin=(0, y_center - y_thick / 2.0, 0),
                                     xDir=(1, 0, 0), normal=(0, 1, 0)))
               .circle(kr).extrude(y_thick))             # disk thin in Y @ z=0
    plate = shaft.union(knuckle)
    bore = _ycyl(P.PIN_D / 2.0 + P.PIN_CLEAR,
                 y_center - y_thick, y_center + y_thick)
    return plate.cut(bore)


# --- servo-horn + rubber-band hardware ----------------------------------
HORN_R      = 7.0     # mm, horn disc radius
HORN_T      = 2.5     # mm, horn thickness (along Y)
HORN_ARM    = 16.0    # mm, horn arm length (+Z, reaches onto the tongue)
HORN_HOLE_D = 1.7     # mm, M2 screw clearance
HOLE_Z      = (8.0, 13.0)   # z-positions where the horn bolts to the tongue
HORN_Y      = P.TONGUE_T / 2.0 + 0.6 + HORN_T / 2.0   # sits just above tongue


def tongue(reach=None):
    """Single blade (on the forward part's rear face), thickness TONGUE_T.

    Carries the servo-HORN mounting holes: the servo's arm bolts down onto
    this blade, so turning the servo swings this (forward) segment.
    """
    reach = reach if reach is not None else P.JOINT_OVERLAP
    tg = lug(0.0, P.TONGUE_T, reach)
    for hz in HOLE_Z:                                  # horn screw holes
        tg = tg.cut(_ycyl(1.0, -P.TONGUE_T, P.TONGUE_T, z=hz))
    return tg


def servo_horn():
    """The servo arm: clips on the shaft (joint axis) and bolts to the tongue.

    Flat arm in the X-Z plane, thin in Y, sitting just above the tongue.
    Centre bore = servo shaft; two holes = screws into the tongue.
    """
    disc = (cq.Workplane(cq.Plane(origin=(0, HORN_Y - HORN_T / 2.0, 0),
                                  xDir=(1, 0, 0), normal=(0, 1, 0)))
            .circle(HORN_R).extrude(HORN_T))
    arm = (cq.Workplane("XY").box(10.0, HORN_T, HORN_ARM)
           .translate((0, HORN_Y, HORN_ARM / 2.0)))
    horn = disc.union(arm)
    horn = horn.cut(_ycyl(2.6, HORN_Y - HORN_T, HORN_Y + HORN_T))   # shaft bore
    for hz in HOLE_Z:
        horn = horn.cut(_ycyl(HORN_HOLE_D / 2.0,
                              HORN_Y - HORN_T, HORN_Y + HORN_T, z=hz))
    return horn


def band_post(x=0.0, z=0.0, h=11.0):
    """Small post sticking up (+Y) to loop a rubber band over (passive joints)."""
    post = _ycyl(2.0, 0.0, h, x=x, z=z)
    cap = _ycyl(3.0, h - 2.0, h, x=x, z=z)            # mushroom cap holds band
    return post.union(cap)


def clevis(reach=None):
    """Two-prong fork (on the aft part's front face) straddling the tongue."""
    reach = reach if reach is not None else P.JOINT_OVERLAP
    yo = P.CLEVIS_GAP / 2.0 + P.CLEVIS_PRONG / 2.0
    top = lug(+yo, P.CLEVIS_PRONG, reach)
    bot = lug(-yo, P.CLEVIS_PRONG, reach)
    return top.union(bot)


def pin(extra=4.0):
    """The joint pin itself (for the assembly / BOM render)."""
    span = P.CLEVIS_GAP + 2 * P.CLEVIS_PRONG + extra
    return _ycyl(P.PIN_D / 2.0, -span / 2.0, +span / 2.0)


def pin_axis_length():
    """How tall the pin/bore must be to clear the full fork."""
    return P.CLEVIS_GAP + 2 * P.CLEVIS_PRONG + 4.0


# ----------------------------------------------------------------------
# self-test: export a demo revolute pair (clevis + tongue rotated + pin)
# ----------------------------------------------------------------------
def _demo():
    out_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "..", "output")
    assy = cq.Assembly(name="joint_demo")
    assy.add(clevis(), name="clevis", color=cq.Color("steelblue"))
    # tongue belongs to the forward part; show it rotated 20 deg about Y
    tg = tongue().rotate((0, 0, 0), (0, 1, 0), 20.0)
    assy.add(tg, name="tongue", color=cq.Color("orange"))
    assy.add(pin(), name="pin", color=cq.Color("gray"))

    step = os.path.normpath(os.path.join(out_dir, "joint_demo.step"))
    assy.save(step)
    # also a fused STL for quick viewing
    fused = clevis().union(tongue()).union(pin())
    stl = os.path.normpath(os.path.join(out_dir, "joint_demo.stl"))
    cq.exporters.export(fused, stl)
    print(f"[ok] wrote {step}")
    print(f"[ok] wrote {stl}")
    print(f"     pin bore dia {P.PIN_D + 2*P.PIN_CLEAR:.1f} mm, "
          f"fork height {pin_axis_length():.1f} mm, "
          f"travel +/-{P.JOINT_TRAVEL_DEG:.0f} deg")


if __name__ == "__main__":
    _demo()
