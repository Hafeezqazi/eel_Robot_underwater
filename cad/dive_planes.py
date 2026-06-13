"""
dive_planes.py  --  Bow dive planes (active depth control -> 3-D diving).

A pair of horizontal fins on a common transverse (X) shaft passing through the
body centreline at DIVE_PLANE_Z. ONE extra waterproof servo (the 4th and last)
pitches the shaft; the planes set an angle of attack that produces vertical
lift while the robot swims forward -> it climbs or dives. Zero pitch -> level.

Each fin ROOT starts at DIVE_ROOT_X (outboard of the hull + TPU skin), so the
full DIVE_PLANE_SPAN is exposed to flow -- this matches the lift area assumed
in analysis/dive.py. Only the bare shaft crosses the hull / skin.

Built in LOCAL coords: shaft axis = X, chord along Z, thickness along Y, shaft
centred at the origin. assembly.py places the pair at DIVE_PLANE_Z and applies
the commanded pitch about X. Servo mounts inside the flooded seg1 (not modelled
here; shown as a mock in the assembly), exactly like the joint servos.

Run:  python dive_planes.py
      ->  output/print_dive_plane.stl, print_dive_shaft.stl, print_dive_crank.stl
"""

import os
import cadquery as cq
import params as P

HUB_R = 7.0          # mm, root hub radius (clamps the shaft)
HUB_L = 16.0         # mm, root hub length (along span/X)


def _xcyl(r, x0, x1, y=0.0, z=0.0):
    """Cylinder along the global X axis from x0 to x1."""
    return (cq.Workplane(cq.Plane(origin=(x0, y, z), xDir=(0, 1, 0),
                                  normal=(1, 0, 0)))
            .circle(r).extrude(x1 - x0))


def plane(side=+1):
    """One dive plane. side=+1 -> starboard (+X), -1 -> port (-X).

    Root sits at DIVE_ROOT_X (outboard of hull + skin), tip at
    DIVE_ROOT_X + SPAN, so the whole span is in clean flow. The root hub
    (clamps the shaft with a set screw) overlaps the first HUB_L of the span.
    """
    root = P.DIVE_ROOT_X
    span = P.DIVE_PLANE_SPAN
    c = P.DIVE_PLANE_CHORD
    t = P.DIVE_PLANE_T
    # flat plate: span along X (root..tip), chord along Z, thin in Y
    plate = (cq.Workplane("XY").box(span, t, c)
             .translate((root + span / 2.0, 0, 0)))
    # rounded leading edge (half round bar along span at z = -c/2)
    le = _xcyl(t / 2.0, root, root + span, z=-c / 2.0)
    # taper the trailing tip (cut a wedge off the outboard TE)
    tip_cut = (cq.Workplane("XY").box(span * 0.5, t * 2, c)
               .rotate((0, 0, 0), (0, 1, 0), 18.0)
               .translate((root + span, 0, c * 0.6)))
    foil = plate.union(le).cut(tip_cut)
    # root hub (outboard of the hull, accessible set-screw clamp) + shaft bore
    hub = _xcyl(HUB_R, root, root + HUB_L)
    foil = foil.union(hub).cut(_xcyl(P.DIVE_SHAFT_D / 2.0 + 0.15,
                                     root - 2.0, root + span + 1.0))
    if side < 0:
        foil = foil.mirror("YZ")
    return foil


def shaft():
    """Transverse pitch shaft (steel rod) through both planes + body."""
    reach = P.DIVE_ROOT_X + P.DIVE_PLANE_SPAN + 2.0
    return _xcyl(P.DIVE_SHAFT_D / 2.0, -reach, reach)


# ----- fin drive: 1 servo turns the whole rod; far end rides in a bushing ----
HULL_R = P.radius_profile(P.DIVE_PLANE_Z)   # body radius where the rod exits
SVX = -8.0                                  # x-station of the servo/crank


def dive_bushing(x):
    """Flanged bushing set in the hull wall; the rod spins inside it (a plain
    bearing, NOT a motor). Supports each side where the rod exits the body."""
    od = P.DIVE_SHAFT_D / 2.0 + 2.5
    bore = P.DIVE_SHAFT_D / 2.0 + 0.25
    s = 1.0 if x >= 0 else -1.0
    tube = _xcyl(od, x - 4 * s, x + 4 * s)
    flange = _xcyl(od + 2.5, x, x + 2.0 * s)
    return tube.union(flange).cut(_xcyl(bore, x - 6 * s, x + 6 * s))


def dive_crank():
    """Lever CLAMPED to the rod (points down) — the servo link drives this."""
    hub = _xcyl(5.0, SVX - 4, SVX + 4)
    arm = (cq.Workplane("XY").box(4.0, 9.0, 4.0)
           .translate((SVX, -7.5, 4.0)))
    return hub.union(arm).cut(_xcyl(P.DIVE_SHAFT_D / 2.0 + 0.15, SVX - 6, SVX + 6))


def dive_servo():
    """The fin servo: output shaft along X (rod axis), mounted below the rod."""
    return (cq.Workplane("XY")
            .box(P.SERVO_BODY_L, P.SERVO_BODY_H, P.SERVO_BODY_W)
            .translate((SVX - P.SERVO_BODY_L / 2.0 - 1, -15.0, 0)))


def dive_servo_horn():
    """Servo output arm (rotates about X); a link joins it to the rod crank."""
    hub = _xcyl(4.0, SVX - 2, SVX + 2).translate((0, -15.0, 0))
    arm = (cq.Workplane("XY").box(4.0, 9.0, 4.0)
           .translate((SVX, -10.5, 4.0)))
    return hub.union(arm)


def dive_link():
    """Push-rod connecting the servo horn to the rod crank (the coupling)."""
    return (cq.Workplane("XY").box(3.0, 8.0, 3.0)
            .translate((SVX, -7.0, 4.0)))


def _test():
    out_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "..", "output")
    pr = plane(+1)
    cq.exporters.export(pr, os.path.normpath(
        os.path.join(out_dir, "print_dive_plane.stl")))
    cq.exporters.export(shaft(), os.path.normpath(
        os.path.join(out_dir, "print_dive_shaft.stl")))
    cq.exporters.export(dive_crank(), os.path.normpath(
        os.path.join(out_dir, "print_dive_crank.stl")))
    area = (P.DIVE_PLANE_SPAN * P.DIVE_PLANE_CHORD) / 100.0   # cm^2 per fin
    print(f"[ok] dive plane: span {P.DIVE_PLANE_SPAN:.0f} x chord "
          f"{P.DIVE_PLANE_CHORD:.0f} mm  (~{area:.1f} cm^2/fin, x2), "
          f"root at x={P.DIVE_ROOT_X:.1f} mm (clear of hull + skin)")
    print(f"     pitch +/-{P.DIVE_PLANE_MAX_DEG:.0f} deg on a "
          f"{P.DIVE_SHAFT_D:.0f} mm shaft -> print_dive_plane.stl (print 2, "
          f"mirror one) + print_dive_crank.stl")


if __name__ == "__main__":
    _test()
