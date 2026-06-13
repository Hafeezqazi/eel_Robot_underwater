"""
body.py  --  Parametric body segment builder for the eel robot.

Each driven segment (seg1..seg5) is a tapered, free-flooding shell that:
  * front face: carries a CLEVIS (fork) for the joint to the part ahead,
    and a SERVO that drives that joint (shaft coaxial with the pin axis);
  * rear face : carries a TONGUE that plugs into the next segment's clevis
    (seg5 instead carries a tail-fin mount).

Built in LOCAL coords: front face at z=0, rear face at z=+L, taper from
radius r0 (front) to r1 (rear). assembly.py translates + rotates each
segment to its station and joint angle. Free-flooding: open tapered tube,
so water fills it and the waterproof servos run wet (only head bay is dry).

Run directly to export test parts:
    python body.py     ->  output/test_seg1.stl, output/test_seg5.stl
"""

import os
import cadquery as cq
import params as P
from joints import clevis, tongue, _ycyl, pin_axis_length

SERVO_CLR = P.SERVO_POCKET_CLEAR
BAND_Y = 8.5       # mm, height of the rubber-band path above the centreline
                   # (clears the clevis prong tops at ~7.5 mm, and still fits
                   # under the thin seg5 shell ceiling)


def frustum_shell(r0, r1, length, wall, gap=0.0):
    """Hollow tapered tube, open both ends (free-flooding).

    `gap` insets the tube from each end by gap/2 so adjacent segments don't
    collide when the joint bends. The clevis/tongue still bridge the gap.
    """
    z0, z1 = gap / 2.0, length - gap / 2.0
    ra = r0 + (r1 - r0) * (z0 / length)          # radii at the inset stations
    rb = r0 + (r1 - r0) * (z1 / length)
    outer = (cq.Workplane("XY", origin=(0, 0, z0)).circle(ra)
             .workplane(offset=z1 - z0).circle(rb)
             .loft(combine=True))
    inner = (cq.Workplane("XY", origin=(0, 0, z0)).circle(max(ra - wall, 0.6))
             .workplane(offset=z1 - z0).circle(max(rb - wall, 0.6))
             .loft(combine=True))
    return outer.cut(inner)


MOUNT_X = 8.0                  # mm, screw-boss offset each side of the servo
MOUNT_Z = P.SERVO_BODY_L - 3.0  # mm, boss station along the servo


def servo_mock():
    """Approximate servo + output horn + mounting flanges, for visualisation.

    Origin at the output-shaft centre, shaft +Y, body hanging -Y, body +Z.
    Two flanges reach out to the segment's screw bosses.
    """
    body = (cq.Workplane("XY")
            .box(P.SERVO_BODY_W, P.SERVO_BODY_H, P.SERVO_BODY_L)
            .translate((0, -P.SERVO_BODY_H / 2.0, P.SERVO_BODY_L / 2.0)))
    horn = (cq.Workplane(cq.Plane(origin=(0, 0, 0), xDir=(1, 0, 0),
                                  normal=(0, 1, 0)))
            .circle(6.0).extrude(3.0))           # round horn at the shaft
    out = body.union(horn)
    for sx in (-1, 1):                            # mounting flanges -> bosses
        tab = (cq.Workplane("XY").box(2 * MOUNT_X, 2.5, 6.0)
               .translate((0, -1.5, MOUNT_Z)))
        out = out.union(tab)
    return out


def servo_mount(r0):
    """Two printed SCREW BOSSES in the segment that the servo flanges bolt to.

    Posts rise from the shell floor to the flange height beside the servo; the
    servo's two mounting screws thread into the holes. (Boss positions are
    representative -- tweak MOUNT_X / MOUNT_Z to your exact servo.)
    """
    floor = -(r0 - P.WALL - 0.5)
    flange_y = -0.5
    out = None
    for sx in (-MOUNT_X, MOUNT_X):
        post = (cq.Workplane("XY").box(5.0, flange_y - floor, 6.0)
                .translate((sx, (flange_y + floor) / 2.0, MOUNT_Z)))
        post = post.cut(_ycyl(1.0, floor, flange_y + 1.0, x=sx, z=MOUNT_Z))
        out = post if out is None else out.union(post)
    return out


def servo_pocket():
    """Negative volume: servo body cavity + shaft clearance, at the front."""
    pocket = (cq.Workplane("XY")
              .box(P.SERVO_BODY_W + 2 * SERVO_CLR,
                   P.SERVO_BODY_H + 2 * SERVO_CLR,
                   P.SERVO_BODY_L + 2 * SERVO_CLR)
              .translate((0, -(P.SERVO_BODY_H + 2 * SERVO_CLR) / 2.0,
                          (P.SERVO_BODY_L + 2 * SERVO_CLR) / 2.0)))
    shaft = _ycyl(4.0, -2.0, P.R_MAX)            # clearance up through the top
    return pocket.union(shaft)


def hang_post(z, r_inner):
    """Rubber-band anchor: a post hanging DOWN from the shell ceiling.

    The clevis/tongue overlap zone (z = 0..JOINT_OVERLAP at each joint) is
    fully occupied, so the anchors root on the shell instead: a small rod
    drops from the inner wall to BAND_Y with a mushroom cap at the bottom;
    the band loops under the cap. r_inner = shell inner radius at z.
    """
    top = r_inner + 1.5                         # embed into the shell wall
    rod = _ycyl(2.0, BAND_Y, top, z=z)
    cap = _ycyl(3.5, BAND_Y, BAND_Y + 2.0, z=z)   # mushroom keeps the band on
    return rod.union(cap)


def tail_mount():
    """Vertical slot + bolt bores on seg5 rear to bolt on the tail fin."""
    base = (cq.Workplane("XY").box(4.0, 2 * P.R_TAIL, 16.0)
            .translate((0, 0, 8.0)))             # blade plate extends aft
    bore = (_ycyl(1.6, -P.R_TAIL, P.R_TAIL, z=6.0)
            .union(_ycyl(1.6, -P.R_TAIL, P.R_TAIL, z=12.0)))
    return base.cut(bore)


def build_segment(part, rear="tongue", rear_post=False):
    """Build one body segment from a params.segment_table() entry.

    Driven segments (part['driven']) get a servo pocket; passive ones don't
    (the rear compliant tail has no servo). rear: 'tongue' or 'tail'.
    rear_post: the joint BEHIND this segment is passive -> print a rubber-
    band anchor near this segment's rear. Passive segments themselves get
    an anchor just aft of their front (passive) joint, beyond the
    clevis/tongue overlap. The band loops between the two anchors across
    the pin and springs the joint back to centre.
    Returns a single cq solid (Workplane) in local coords.
    """
    L = part["z1"] - part["z0"]
    r0, r1 = part["r0"], part["r1"]

    seg = frustum_shell(r0, r1, L, P.WALL, gap=P.SEGMENT_GAP)

    # front clevis (prongs extend +Z into the segment, straddling the
    # incoming tongue from the part ahead); pin axis at (x=0, z=0).
    seg = seg.union(clevis())

    # rear feature
    if rear == "tongue":
        seg = seg.union(tongue().translate((0, 0, L)))
    else:                                       # last segment tail mount
        seg = seg.union(tail_mount().translate((0, 0, L)))

    # servo pocket + mounting bosses only on DRIVEN segments
    if part["driven"]:
        seg = seg.cut(servo_pocket())
        seg = seg.union(servo_mount(r0))          # screw bosses for the servo

    # rubber-band anchors for the PASSIVE compliant joints (printed in
    # place, hanging from the shell ceiling clear of the overlap zone)
    def _r_in(z):
        f = z / L
        return (r0 + (r1 - r0) * f) - P.WALL
    if not part["driven"]:                       # own front joint is passive
        zp = P.JOINT_OVERLAP + 3.0               # just aft of the tongue tip
        seg = seg.union(hang_post(zp, _r_in(zp)))
    if rear_post and rear == "tongue":           # joint behind is passive
        zp = L - 8.0
        seg = seg.union(hang_post(zp, _r_in(zp)))

    # clean through-bores for the pins (every joint has a pin)
    fork_h = pin_axis_length()
    seg = seg.cut(_ycyl(P.PIN_D / 2.0 + P.PIN_CLEAR,
                        -fork_h / 2.0, fork_h / 2.0, z=0.0))
    if rear == "tongue":
        seg = seg.cut(_ycyl(P.PIN_D / 2.0 + P.PIN_CLEAR,
                            -fork_h / 2.0, fork_h / 2.0, z=L))

    # drain/vent hole at the segment's low point so it floods/drains freely
    rm = 0.5 * (r0 + r1)
    seg = seg.cut(_ycyl(P.DRAIN_HOLE_D / 2.0, -(rm + 3.0),
                        -(rm - P.WALL - 3.0), z=L / 2.0))
    return seg


def body_segments():
    """Return [(name, solid, part_dict), ...] for ALL body segments seg1..seg5
    (driven AND passive). Passive ones simply have no servo pocket; segments
    ahead of a passive joint carry the matching rubber-band post."""
    parts = [p for p in P.segment_table() if p["name"].startswith("seg")]
    out = []
    for i, p in enumerate(parts):
        rear = "tail" if i == len(parts) - 1 else "tongue"
        rear_post = (i + 1 < len(parts)) and not parts[i + 1]["driven"]
        out.append((p["name"], build_segment(p, rear=rear,
                                             rear_post=rear_post), p))
    return out


# back-compat alias (older imports)
driven_segments = body_segments


def _test():
    out_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "..", "output")
    parts = {p["name"]: p for p in P.segment_table()}
    s1 = build_segment(parts["seg1"], rear="tongue")
    s5 = build_segment(parts["seg5"], rear="tail")
    for name, sol in (("test_seg1", s1), ("test_seg5", s5)):
        path = os.path.normpath(os.path.join(out_dir, name + ".stl"))
        cq.exporters.export(sol, path)
        vol = sol.val().Volume() / 1000.0       # cm^3
        print(f"[ok] {name}: volume {vol:6.1f} cm^3  -> {path}")


if __name__ == "__main__":
    _test()
